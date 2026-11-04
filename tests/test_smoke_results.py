import asyncio
from pathlib import Path
import sys
from mcp.types import CallToolResult, TextContent
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import smoke_mcp


class Session:
    def __init__(self, text, failed=False):
        self.result = CallToolResult(content=[TextContent(type="text", text=text)], isError=failed)

    async def call_tool(self, *args):
        return self.result


def test_successful_documentation_can_return_markdown_not_json():
    text = "## EPLAN documentation\nA matching document."
    assert asyncio.run(smoke_mcp.checked_call(Session(text), "search")) == text


@pytest.mark.parametrize("session", [Session('{"success":false}'), Session("remote failed", True)])
def test_explicit_failures_still_fail(session):
    with pytest.raises(AssertionError):
        asyncio.run(smoke_mcp.checked_call(session, "search"))


def test_sdk_wrapped_ping_is_read_as_business_result():
    session = Session('{"alive":true}')
    session.result.structuredContent = {"result": '{"alive":true}'}
    assert asyncio.run(smoke_mcp.checked_call(session, "eplan_ping")) == {"alive": True}


def test_sdk_wrapped_failure_without_error_flag_still_fails():
    session = Session('{"success":false}')
    session.result.structuredContent = {"result": '{"success":false}'}
    with pytest.raises(AssertionError):
        asyncio.run(smoke_mcp.checked_call(session, "eplan_get_current_project"))


@pytest.mark.parametrize("content", [{"result": "plain text"}, {"result": '{"alive":true}', "other": 1}])
def test_unrelated_structured_content_is_preserved(content):
    session = Session("text")
    session.result.structuredContent = content
    assert smoke_mcp.payload(session.result) == content
