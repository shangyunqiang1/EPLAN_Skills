"""Invalid native/Python output must fail even if the SDK handshake succeeds."""
import asyncio
from pathlib import Path
import sys
import time
import anyio
from mcp import ClientSession, StdioServerParameters
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import strict_stdio

SERVER = "from mcp.server.fastmcp import FastMCP\nm=FastMCP('probe')\nm.tool(name='probe')(lambda: 'ok')\nm.run(transport='stdio')"


def run_probe(prefix):
    async def check():
        with anyio.fail_after(15):
            async with strict_stdio.strict_stdio_client(StdioServerParameters(command=sys.executable, args=["-u", "-c", prefix + "\n" + SERVER])) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    assert len((await session.list_tools()).tools) == 1
    asyncio.run(check())


def test_normal_protocol_allows_stderr():
    run_probe("import sys; print('diagnostic',file=sys.stderr)")


@pytest.mark.parametrize("prefix", ["print('private diagnostic',flush=True)",
    "import os; os.write(1,b'\\xff\\n')", "print('{}',flush=True)"])
def test_invalid_stdout_fails_even_after_successful_handshake(prefix):
    with pytest.raises(strict_stdio.StrictProtocolError) as error:
        run_probe(prefix)
    assert "private diagnostic" not in str(error.value)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CLR")
def test_native_dotnet_stdout_is_rejected():
    with pytest.raises(strict_stdio.StrictProtocolError):
        run_probe("import clr; from System import Console; Console.WriteLine('native diagnostic')")


def test_timeout_reaps_child(monkeypatch):
    created = []
    original = strict_stdio._create_platform_compatible_process
    async def create(**kwargs):
        process = await original(**kwargs)
        created.append(process)
        return process
    monkeypatch.setattr(strict_stdio, "_create_platform_compatible_process", create)
    async def check():
        with anyio.fail_after(0.3):
            async with strict_stdio.strict_stdio_client(StdioServerParameters(command=sys.executable, args=["-c", "import time; time.sleep(120)"])):
                await anyio.sleep(120)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        asyncio.run(check())
    assert time.monotonic() - started < 8
    assert len(created) == 1 and created[0].returncode is not None
