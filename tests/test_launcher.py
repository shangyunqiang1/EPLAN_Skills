"""Protect stdio isolation and external dependency handling."""
import builtins
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("launcher", ROOT / "plugins/eplan-skills/scripts/run_mcp.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_missing_dependencies_only_write_to_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(launcher, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher, "prepare_runtime", lambda: tmp_path / "runtime")
    monkeypatch.setattr(launcher, "find_environment", lambda *args: None)
    assert launcher.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "setup.ps1" in output.err


@pytest.mark.parametrize("invalid_settings", [False, True])
def test_diagnostics_stay_off_protocol_and_transport_is_stdio(tmp_path, monkeypatch, capsys, invalid_settings):
    target = tmp_path / "venv/Scripts/python.exe"
    target.parent.mkdir(parents=True)
    target.touch()
    monkeypatch.setattr(launcher, "find_environment", lambda *args: target)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", str(target))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(launcher, "data_dir", lambda: tmp_path)
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.delenv("EPLAN_MCP_LOG_DIR", raising=False)
    original = builtins.__import__
    observed = {}

    def run(transport):
        observed["transport"] = transport
        print('{"jsonrpc":"2.0"}')

    def import_server(name, *args, **kwargs):
        if name == "server":
            print("import diagnostic")
            return SimpleNamespace(mcp=SimpleNamespace(run=run), apply_tool_policy=lambda *args, **kwargs: None)
        if name == "eplan_connection":
            return SimpleNamespace(EPLANConnectionManager=SimpleNamespace(), get_manager=lambda *args: None)
        if name == "eplan_doctor":
            def load(*args):
                if invalid_settings:
                    raise ValueError("invalid saved settings")
                return None
            return SimpleNamespace(register_tools=lambda *args: None, load_connection_settings=load)
        if name == "documentation":
            return SimpleNamespace(register_configuration_tool=lambda *args: None)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_server)
    assert launcher.main() == 0
    output = capsys.readouterr()
    assert output.out == '{"jsonrpc":"2.0"}\n'
    assert "import diagnostic" in output.err
    assert observed["transport"] == "stdio"
    assert launcher.os.environ["MCP_TRANSPORT"] == "stdio"
    assert launcher.os.environ["EPLAN_MCP_LOG_DIR"] == str(tmp_path / "logs")


def test_generated_files_stay_in_data_runtime(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "mcp_server").mkdir(parents=True)
    (source / "mcp_server/server.py").write_text("# source\n")
    monkeypatch.setattr(launcher, "SERVER_ROOT", source)
    monkeypatch.setattr(launcher, "data_dir", lambda: tmp_path / "data")
    runtime = launcher.prepare_runtime()
    assert runtime.is_relative_to(tmp_path / "data")
    (runtime / "mcp_server/generated.cs").write_text("// runtime\n")
    assert not (source / "mcp_server/generated.cs").exists()
    assert launcher.prepare_runtime() == runtime
    assert (runtime / "mcp_server/server.py").read_text() == "# source\n"


def test_native_grpc_bypasses_only_local_addresses_and_keeps_http_proxy(monkeypatch):
    monkeypatch.setattr(launcher.socket, "gethostname", lambda: "workstation")
    monkeypatch.setattr(launcher.socket, "gethostbyname_ex", lambda host: (host, [], ["10.20.30.40"]))
    monkeypatch.setenv("no_grpc_proxy", "existing.internal")
    monkeypatch.setenv("http_proxy", "http://example.invalid:8080")
    monkeypatch.setenv("NO_PROXY", "existing.http")
    launcher.configure_local_grpc_proxy()
    assert set(launcher.os.environ["no_grpc_proxy"].split(",")) == {"existing.internal", "localhost", "127.0.0.1", "::1", "10.20.30.40"}
    assert launcher.os.environ["http_proxy"] == "http://example.invalid:8080"
    assert launcher.os.environ["NO_PROXY"] == "existing.http"


def test_local_proxy_bypass_survives_hostname_resolution_failure(monkeypatch):
    def fail(host):
        raise OSError("No address")
    monkeypatch.setattr(launcher.socket, "gethostbyname_ex", fail)
    monkeypatch.setenv("no_grpc_proxy", "")
    launcher.configure_local_grpc_proxy()
    assert set(launcher.os.environ["no_grpc_proxy"].split(",")) == {"localhost", "127.0.0.1", "::1"}
