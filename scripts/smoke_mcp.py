"""Read-only MCP handshake/list/status; never connects to or edits EPLAN."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/eplan-skills"


async def check_session(session, local=False):
    await session.initialize()
    result = await session.list_tools()
    names = {tool.name for tool in result.tools}
    assert names, "Empty tool list"
    if local:
        assert {"eplan_versions", "eplan_status", "eplan_connect"} <= names
        status = await session.call_tool("eplan_status", {})
        assert not status.isError, status
        for content in status.content:
            if content.type == "text":
                json.loads(content.text)
    return len(names)


async def main(remote=False):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    params = StdioServerParameters(command=sys.executable, args=[str(PLUGIN / "scripts/run_mcp.py")], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            count = await check_session(session, local=True)
            print(f"Local stdio: handshake, {count} tools, read-only status OK")
    if remote:
        servers = json.loads((PLUGIN / "mcp.json").read_text())["mcpServers"]
        for name, config in servers.items():
            if config["type"] != "streamable-http":
                continue
            async with streamablehttp_client(config["url"]) as (read, write, _):
                async with ClientSession(read, write) as session:
                    count = await check_session(session)
                    print(f"Remote {name}: handshake, {count} tools OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true", help="Also contact upstream public documentation MCPs")
    asyncio.run(main(parser.parse_args().remote))
