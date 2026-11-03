import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from mcp.types import Tool, CallToolResult, TextContent
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/eplan-skills/scripts"))
import documentation


def test_disabled_gateway_never_contacts_remote(tmp_path, monkeypatch):
    documentation.configure(tmp_path, "offline")
    gateway = documentation.Gateway("eplan-rag", tmp_path)
    async def forbidden(*args):
        pytest.fail("disabled docs contacted remote")
    monkeypatch.setattr(gateway, "remote", forbidden)
    async def check():
        tools = await gateway.list_tools()
        assert [t.name for t in tools] == [gateway.status_name]
        failed = await gateway.call_tool("eplan_search", {"query": "sample"})
        assert failed.isError
    asyncio.run(check())


def test_remote_failure_is_local_status_not_process_crash(tmp_path, monkeypatch):
    gateway = documentation.Gateway("eplan-wiki-2027", tmp_path)
    async def unavailable(*args):
        raise TimeoutError("private transport details")
    monkeypatch.setattr(gateway, "remote", unavailable)
    async def check():
        assert len(await gateway.list_tools()) == 1
        status = await gateway.call_tool(gateway.status_name, {})
        assert not status.isError
        failed = await gateway.call_tool("eplan2027_search", {"query": "sample"})
        assert failed.isError
        assert "private transport details" not in str(failed)
    asyncio.run(check())


def test_gateway_forwards_original_content_and_error_flag(tmp_path, monkeypatch):
    gateway = documentation.Gateway("eecpro-rag", tmp_path)
    answer = CallToolResult(content=[TextContent(type="text", text="original")], isError=True)
    async def remote(operation, *args):
        if operation == "list_tools":
            return SimpleNamespace(tools=[Tool(name="eecpro_search", inputSchema={"type": "object"})])
        return answer
    monkeypatch.setattr(gateway, "remote", remote)
    async def check():
        tools = await gateway.list_tools()
        assert len(tools) == 2 and tools[1].annotations.readOnlyHint
        assert await gateway.call_tool("eecpro_search", {"query": "sample"}) is answer
    asyncio.run(check())


def test_profiles_and_malformed_configuration(tmp_path):
    documentation.configure(tmp_path, "p8")
    assert documentation.load_profile(tmp_path) == "p8"
    (tmp_path / "documentation.json").write_text('{"profile":"unknown"}')
    with pytest.raises(ValueError):
        documentation.load_profile(tmp_path)


def test_gateway_normalizes_explicit_remote_business_failure(tmp_path, monkeypatch):
    gateway = documentation.Gateway("eplan-rag", tmp_path)
    async def remote(*args):
        return CallToolResult(content=[TextContent(type="text", text='{"success":false}')], isError=False)
    monkeypatch.setattr(gateway, "remote", remote)
    result = asyncio.run(gateway.call_tool("eplan_search", {"query": "sample"}))
    assert result.isError is True
