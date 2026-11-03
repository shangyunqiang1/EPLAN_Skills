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
