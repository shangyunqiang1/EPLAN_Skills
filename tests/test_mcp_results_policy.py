import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server"))
import server
import tool_policy


def test_all_pinned_tools_are_explicitly_classified():
    app, registry, _ = server.build_app()
    actual = set(app._tool_manager._tools)
    expected = set().union(*tool_policy.BUILTIN_CATEGORIES.values())
    assert actual == expected
    assert all(tool.annotations is not None for tool in app._tool_manager.list_tools())
    assert app._tool_manager.get_tool("eplan_get_current_project").annotations.readOnlyHint is True
    assert app._tool_manager.get_tool("eplan_execute_custom_script").annotations.readOnlyHint is False


def test_protocol_failure_flags_preserve_text_and_normal_status():
    app = FastMCP("result-probe")
    app.tool(name="business_failure")(lambda: json.dumps({"success": False, "message": "Not connected"}))
    app.tool(name="normal_state")(lambda: {"connected": False, "alive": False})
    app.tool(name="schema_probe")(lambda count: count)
    def crash():
        raise ValueError("probe failure")
    app.tool(name="crash")(crash)
    server.install_result_adapter(app)
    server.install_result_adapter(app)
    async def check():
        async with create_connected_server_and_client_session(app) as session:
            failed = await session.call_tool("business_failure", {})
            assert failed.isError is True
            assert json.loads(failed.content[0].text)["success"] is False
            assert not (await session.call_tool("normal_state", {})).isError
            assert (await session.call_tool("crash", {})).isError
            assert (await session.call_tool("schema_probe", {})).isError
    asyncio.run(check())


def test_core_action_and_discovery_failures_propagate():
    async def check(mode):
        app, registry, _ = server.build_app(mode)
        async with create_connected_server_and_client_session(app) as session:
            assert not (await session.call_tool("eplan_status", {})).isError
            assert not (await session.call_tool("eplan_ping", {})).isError
            if mode == "full":
                failed = await session.call_tool("eplan_get_current_project", {})
            else:
                failed = await session.call_tool("eplan_tools_call", {"name": "eplan_get_current_project", "arguments": {}})
            assert failed.isError is True
    asyncio.run(check("full"))
    asyncio.run(check("discovery"))


def test_unknown_extensions_are_conservative_even_when_name_matches_builtin():
    app = FastMCP("extension")
    app.tool(name="eplan_status")(lambda: "extension")
    server.apply_tool_policy(app)
    assert app._tool_manager.get_tool("eplan_status").annotations.readOnlyHint is False
    app.tool(name="eplan_doctor")(lambda: {})
    server.apply_tool_policy(app, trusted_extra={"eplan_doctor": "read_only"})
    assert app._tool_manager.get_tool("eplan_doctor").annotations.readOnlyHint is True
