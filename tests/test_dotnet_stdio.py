"""The real CLR must not write diagnostics into MCP's stdout stream."""
from pathlib import Path
import subprocess
import sys

import pytest


SERVER = (Path(__file__).resolve().parents[1] / "plugins/eplan-skills/vendor/eplan-mcp"
          / "eplan-p8-mcp-server/mcp_server")


@pytest.mark.skipif(sys.platform != "win32", reason="Requires the Windows .NET Framework runtime")
def test_dotnet_console_diagnostics_go_to_stderr():
    script = """
import sys
sys.path.insert(0, sys.argv[1])
import clr
import System
from eplan_connection import _redirect_dotnet_console
_redirect_dotnet_console()
System.Console.WriteLine('native diagnostic')
print('{"jsonrpc":"2.0"}')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(SERVER)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    assert result.stdout == '{"jsonrpc":"2.0"}\n'
    assert "native diagnostic" in result.stderr
