"""Strict MCP stdio transport used by the standalone verification script.

The SDK transport intentionally continues after invalid stdout. This variant
records every invalid line and fails after the process has been drained/reaped.
It never includes raw server output in an error.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import anyio
import mcp.types as types
from mcp.client.stdio import (
    StdioServerParameters,
    _create_platform_compatible_process,
    _get_executable_command,
    _terminate_process_tree,
    get_default_environment,
)
from mcp.shared.message import SessionMessage


MAX_LINE_BYTES = 64 * 1024 * 1024
SHUTDOWN_TIMEOUT_SECONDS = 2.0


class StrictProtocolError(RuntimeError):
    """The server wrote non-protocol or incomplete data to stdout."""


@asynccontextmanager
async def strict_stdio_client(server: StdioServerParameters):
    """Yield SDK-compatible streams, validating every stdout line.

    Valid JSON-RPC lines up to 64 MiB work. Windows uses the SDK's job-object
    process launcher/tree cleanup; POSIX uses its isolated process group. The
    caller must bound the whole session with a deadline.
    """
    receive_send, receive = anyio.create_memory_object_stream(0)
    send, send_receive = anyio.create_memory_object_stream(0)
    invalid = False
    stdout_drained = anyio.Event()
    env = get_default_environment()
    if server.env is not None:
        env.update(server.env)

    # Server stderr may include engineering paths or generated script content.
    # It is never interpreted as protocol or printed by the verification tool.
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        try:
            process = await _create_platform_compatible_process(
                command=_get_executable_command(server.command),
                args=server.args, env=env, errlog=errlog, cwd=server.cwd,
            )
        except BaseException:
            await receive.aclose()
            await receive_send.aclose()
            await send.aclose()
            await send_receive.aclose()
            raise

        async def read_stdout() -> None:
            nonlocal invalid
            assert process.stdout is not None
            buffer = bytearray()
            discarding = False
            deliver = True
            try:
                async for chunk in process.stdout:
                    buffer.extend(chunk)
                    while True:
                        end = buffer.find(b"\n")
                        if end < 0:
                            if len(buffer) > MAX_LINE_BYTES:
                                invalid = True
                                discarding = True
                                buffer.clear()
                            break
                        line = bytes(buffer[:end])
                        del buffer[:end + 1]
                        if discarding:
                            discarding = False
                            continue
                        if len(line) > MAX_LINE_BYTES:
                            invalid = True
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(
                                line.decode("utf-8", errors="strict")
                            )
                        except Exception:
                            invalid = True
                            continue
                        if deliver:
                            try:
                                await receive_send.send(SessionMessage(message))
                            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                                # Continue validating output emitted during exit.
                                deliver = False
                if buffer or discarding:
                    invalid = True
            except anyio.ClosedResourceError:
                pass
            finally:
                stdout_drained.set()
                await receive_send.aclose()

        async def write_stdin() -> None:
            assert process.stdin is not None
            try:
                async with send_receive:
                    async for message in send_receive:
                        serialized = message.message.model_dump_json(by_alias=True, exclude_none=True)
                        await process.stdin.send((serialized + "\n").encode("utf-8"))
            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                pass

        try:
            async with anyio.create_task_group() as group, process:
                group.start_soon(read_stdout)
                group.start_soon(write_stdin)
                try:
                    yield receive, send
                finally:
                    # Shield cleanup from the caller's deadline cancellation.
                    with anyio.CancelScope(shield=True):
                        await receive.aclose()
                        if process.stdin is not None:
                            try:
                                await process.stdin.aclose()
                            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                                pass
                        with anyio.move_on_after(SHUTDOWN_TIMEOUT_SECONDS) as wait_scope:
                            await process.wait()
                        if wait_scope.cancel_called:
                            await _terminate_process_tree(process)
                            with anyio.move_on_after(SHUTDOWN_TIMEOUT_SECONDS):
                                await process.wait()
                        with anyio.move_on_after(SHUTDOWN_TIMEOUT_SECONDS):
                            await stdout_drained.wait()
                        await send.aclose()
                        await send_receive.aclose()
                        await receive_send.aclose()
                        group.cancel_scope.cancel()
        except BaseException:
            if invalid:
                raise StrictProtocolError("MCP server wrote invalid data to stdout") from None
            raise
        if invalid:
            raise StrictProtocolError("MCP server wrote invalid data to stdout")
