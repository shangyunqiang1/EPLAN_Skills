"""Strict protocol verification, with opt-in read-only EPLAN and docs checks."""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import anyio
from mcp import ClientSession, StdioServerParameters
from strict_stdio import strict_stdio_client

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/eplan-skills"


def payload(result):
    if isinstance(result.structuredContent, dict):
        return result.structuredContent
    texts = [part.text for part in result.content if part.type == "text"]
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except ValueError:
            return texts[0]
    return texts


async def checked_call(session, name, arguments=None):
    result = await session.call_tool(name, arguments or {})
    value = payload(result)
    if result.isError or (isinstance(value, dict) and value.get("success") is False):
        raise AssertionError("Tool failed: " + name)
    return value


async def local_check(args):
    parameters = StdioServerParameters(command=sys.executable, args=[str(args.plugin_root / "scripts/run_mcp.py")], env=dict(os.environ))
    with anyio.fail_after(args.timeout):
        async with strict_stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=args.timeout)) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                names = {tool.name for tool in tools}
                assert {"eplan_status", "eplan_versions", "eplan_doctor", "eplan_connection_configure"} <= names
                assert all(tool.annotations is not None for tool in tools), "Missing tool annotations"
                project_tool = "eplan_get_current_project" if "eplan_get_current_project" in names else "eplan_tools_call"
                project_arguments = {} if project_tool == "eplan_get_current_project" else {"name": "eplan_get_current_project", "arguments": {}}
                await checked_call(session, "eplan_versions")
                await checked_call(session, "eplan_status")
                diagnosis = await checked_call(session, "eplan_doctor")
                if args.connect:
                    settings = {key: value for key, value in {"host": args.host, "port": args.port, "version": args.version}.items() if value is not None}
                    await checked_call(session, "eplan_connect", settings)
                    ping = await checked_call(session, "eplan_ping")
                    assert ping.get("alive") is True, "EPLAN ping did not succeed"
                    await checked_call(session, project_tool, project_arguments)
                    if args.save_connection:
                        await checked_call(session, "eplan_connection_configure", settings)
                else:
                    result = await session.call_tool(project_tool, project_arguments)
                    assert payload(result).get("success") is False and result.isError, "Business failure flag mismatch"
                summary = {"local": "OK", "tools": len(tools), "annotations": len(tools), "diagnosis": diagnosis["diagnosis"]["code"], "connectedReadOnlyCheck": args.connect}
    # Printing success only after strict transport has drained and validated stdout.
    print(json.dumps(summary, ensure_ascii=False), flush=True)


async def documentation_check(args, name, config):
    parameters = StdioServerParameters(command=sys.executable,
        args=[value.replace("${PLUGIN_ROOT}", str(args.plugin_root)) for value in config["args"]], env=dict(os.environ))
    with anyio.fail_after(args.timeout):
        async with strict_stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=args.timeout)) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                status_name = name.replace("-", "_") + "_status"
                status = await checked_call(session, status_name)
                if not status["enabled"]:
                    outcome = "disabled"
                else:
                    assert status.get("lastErrorType") is None, "Documentation service unavailable"
                    search = next(tool for tool in tools if "search" in tool.name)
                    await checked_call(session, search.name, {"query": "Job Server" if name == "eecpro-rag" else "CommandLineInterpreter", "topK": 1})
                    outcome = "OK"
    print(json.dumps({"documentation": name, "result": outcome}, ensure_ascii=False), flush=True)


async def main(args):
    await local_check(args)
    failed = []
    if args.remote:
        servers = json.loads((args.plugin_root / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        for name, config in servers.items():
            if name == "eplan":
                continue
            try:
                await documentation_check(args, name, config)
            except Exception as exc:
                failed.append(name)
                print(json.dumps({"documentation": name, "result": "failed", "errorType": type(exc).__name__}), flush=True)
    if failed:
        raise RuntimeError("Documentation checks failed: " + ", ".join(failed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN)
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--connect", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--version")
    parser.add_argument("--save-connection", action="store_true")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    args.plugin_root = args.plugin_root.resolve()
    if args.timeout <= 0 or (args.save_connection and (not args.connect or not args.host or not args.port)):
        parser.error("Positive timeout required; saving requires --connect --host --port")
    asyncio.run(main(args))
