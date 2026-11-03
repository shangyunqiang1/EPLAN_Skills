"""Exercise the doctor without a live EPLAN process or project access."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "eplan_doctor", ROOT / "plugins/eplan-skills/scripts/eplan_doctor.py"
)
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class FakeManager:
    def __init__(self, status=None, ping=None):
        self.status = status or {"connected": False, "api_loaded": False, "target_version": None,
                                 "host": None, "port": None, "last_error": ""}
        self.ping_result = ping or {"alive": True}
        self.ping_calls = 0
        self.connect_calls = 0

    def get_status(self):
        return dict(self.status)

    def ping(self):
        self.ping_calls += 1
        return self.ping_result

    def connect(self, *args, **kwargs):
        self.connect_calls += 1
        raise AssertionError("doctor must never call connect")


@pytest.fixture
def environment(monkeypatch):
    manager = FakeManager()
    monkeypatch.setitem(sys.modules, "eplan_connection", SimpleNamespace(get_manager=lambda: manager))
    monkeypatch.setattr(doctor, "_probe_versions", lambda: {
        "available": True, "versions": [{"version": "2025", "runtime": "netfx"}]
    })
    monkeypatch.setattr(doctor, "_windows_process_snapshot", lambda: {
        "available": True, "pids": [42],
        "listeners": [{"address": "127.0.0.1", "port": 49152, "pid": 42}]
    })
    monkeypatch.setattr(doctor, "_local_addresses", lambda: {"localhost", "127.0.0.1"})
    return manager


def test_doctor_never_connects_on_unconnected_session(environment, tmp_path):
    result = doctor.diagnose(tmp_path)
    assert result["success"] is True
    assert result["diagnosis"]["code"] == "api_not_loaded"
    assert result["processes"]["listeners"][0]["pid"] == 42
    assert environment.connect_calls == 0
    assert environment.ping_calls == 0
    assert not (tmp_path / "connection.json").exists()


def test_doctor_reports_busy_without_retry(environment, tmp_path):
    environment.status.update(connected=True, api_loaded=True)
    environment.ping_result = {"alive": False, "timed_out": True}
    result = doctor.diagnose(tmp_path)
    assert result["diagnosis"]["code"] == "busy"
    assert environment.ping_calls == 1
    assert environment.connect_calls == 0


def test_doctor_reports_healthy_connected_and_previous_failure(environment, tmp_path):
    environment.status.update(connected=True, api_loaded=True)
    assert doctor.diagnose(tmp_path)["diagnosis"]["code"] == "connected"
    environment.status.update(connected=False, last_error="connection failure")
    assert doctor.diagnose(tmp_path)["diagnosis"]["code"] == "connection_error"
    assert environment.connect_calls == 0


def test_doctor_reports_inspection_permission_without_claiming_disabled(environment, monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "_windows_process_snapshot", lambda: {
        "available": False, "reason": "permission_denied", "pids": [42], "listeners": []
    })
    result = doctor.diagnose(tmp_path)
    assert result["diagnosis"]["code"] == "detection_incomplete"
    assert result["processes"]["reason"] == "permission_denied"
    assert environment.connect_calls == 0


def test_doctor_distinguishes_stopped_and_no_visible_listener(environment, monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "_windows_process_snapshot", lambda: {
        "available": True, "pids": [], "listeners": []
    })
    assert doctor.diagnose(tmp_path)["diagnosis"]["code"] == "not_running"
    monkeypatch.setattr(doctor, "_windows_process_snapshot", lambda: {
        "available": True, "pids": [42], "listeners": []
    })
    result = doctor.diagnose(tmp_path)
    assert result["diagnosis"]["code"] == "service_not_detected"
    assert "不能单独证明" in result["diagnosis"]["message"]


def test_process_snapshot_limits_tcp_rows_to_eplan(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    process_api = SimpleNamespace(
        process_ids=lambda name: [42] if name == "EPLAN.exe" else [os.getpid()],
        tcp_listeners=lambda: [("127.0.0.1", 49152, 42), ("127.0.0.1", 1234, 99)],
    )
    monkeypatch.setitem(sys.modules, "process_control", process_api)
    result = doctor._windows_process_snapshot()
    assert result == {"available": True, "pids": [42], "listeners": [
        {"address": "127.0.0.1", "port": 49152, "pid": 42}
    ]}


def test_incomplete_process_snapshot_is_not_interpreted_as_no_eplan(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "process_control", SimpleNamespace(
        process_ids=lambda name: [], tcp_listeners=lambda: []
    ))
    assert doctor._windows_process_snapshot()["reason"] == "process_snapshot_incomplete"


def test_permission_error_from_tcp_table_is_preserved(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    def denied():
        raise PermissionError("test access denied")
    monkeypatch.setitem(sys.modules, "process_control", SimpleNamespace(
        process_ids=lambda name: [42], tcp_listeners=denied
    ))
    assert doctor._windows_process_snapshot() == {
        "available": False, "reason": "permission_denied", "pids": [42], "listeners": []
    }


def test_diagnostics_never_echo_proxy_or_transport_error_secrets(environment, monkeypatch, tmp_path):
    monkeypatch.setenv("HTTP_PROXY", "http://secret-user:secret-pass@example.invalid:8123")
    monkeypatch.setenv("no_grpc_proxy", "localhost,example.invalid/secret-token")
    environment.status["last_error"] = "secret-transport-error"
    result = doctor.diagnose(tmp_path)
    output = json.dumps(result, ensure_ascii=False)
    assert "secret" not in output
    assert result["proxy"]["proxyConfigured"] is True
    assert result["proxy"]["localGrpcBypassHosts"] == ["localhost"]
    assert result["connection"]["hasError"] is True


@pytest.mark.parametrize("host,port,version", [
    ("", "49152", None), (" localhost", "49152", None),
    ("http://localhost", "49152", None), ("user:password@example.org", "49152", None),
    ("localhost:49152", "49152", None), ("0.0.0.0", "49152", None),
    ("localhost", "-1", None), ("localhost", "65536", None),
    ("localhost", "49152", "2025/../../"),
])
def test_invalid_endpoint_never_starts_probe_or_overwrites(monkeypatch, tmp_path, host, port, version):
    target = tmp_path / "connection.json"
    target.write_text('{"old":true}', encoding="utf-8")
    monkeypatch.setattr(doctor, "_verify_connection", lambda settings: pytest.fail("must not probe"))
    result = doctor.configure(tmp_path, host, port, version)
    assert result["success"] is False and result["stage"] == "validation"
    assert target.read_text(encoding="utf-8") == '{"old":true}'


def test_failed_live_validation_preserves_old_settings(monkeypatch, tmp_path):
    old = {"host": "localhost", "port": "49152", "version": "2025"}
    (tmp_path / "connection.json").write_text(json.dumps(old), encoding="utf-8")
    monkeypatch.setattr(doctor, "_verify_connection", lambda settings: {
        "success": False, "stage": "ping", "reason": "busy"
    })
    result = doctor.configure(tmp_path, "example.invalid", "49153", "2025")
    assert result["success"] is False and result["reason"] == "busy"
    assert doctor.load_connection_settings(tmp_path) == old


def test_successful_explicit_configuration_is_saved_and_reloaded(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(doctor, "_verify_connection", lambda settings: calls.append(dict(settings)) or {"success": True})
    monkeypatch.setattr(doctor, "_local_addresses", lambda: {"localhost"})
    result = doctor.configure(tmp_path, "localhost", "049152", "2025")
    assert result["success"] is True and result["isLocal"] is True
    assert calls == [{"host": "localhost", "port": "49152", "version": "2025"}]
    assert doctor.load_connection_settings(tmp_path) == calls[0]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["connection.json"]


def test_failed_atomic_replace_preserves_old_config(monkeypatch, tmp_path):
    original = '{"host":"localhost","port":"49152"}'
    path = tmp_path / "connection.json"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(doctor, "_verify_connection", lambda settings: {"success": True})
    def denied(src, dst):
        raise PermissionError("simulated")
    monkeypatch.setattr(doctor.os, "replace", denied)
    result = doctor.configure(tmp_path, "localhost", "49153")
    assert result["success"] is False and result["stage"] == "save"
    assert path.read_text(encoding="utf-8") == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["connection.json"]


def test_load_rejects_malformed_or_unexpected_settings(tmp_path):
    assert doctor.load_connection_settings(tmp_path) is None
    path = tmp_path / "connection.json"
    path.write_text('{"host":"localhost","port":"49152","password":"secret"}', encoding="utf-8")
    with pytest.raises(ValueError):
        doctor.load_connection_settings(tmp_path)
    path.write_text('{not json', encoding="utf-8")
    with pytest.raises(ValueError):
        doctor.load_connection_settings(tmp_path)


def test_live_check_uses_separate_python_process_and_timeout(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setitem(sys.modules, "eplan_connection", SimpleNamespace(__file__=str(tmp_path / "eplan_connection.py")))
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout='EPLAN_CONNECTION_CHECK={"success":true}\n')
    monkeypatch.setattr(doctor.subprocess, "run", run)
    assert doctor._verify_connection({"host": "localhost", "port": "49152"}) == {"success": True}
    args, options = calls[0]
    assert args[0] == sys.executable and args[1] == "-c"
    assert args[-3:] == ["localhost", "49152", ""]
    assert options["timeout"] == 45 and options["capture_output"] is True


def test_live_check_timeout_is_reported_without_saving(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "eplan_connection", SimpleNamespace(__file__=str(tmp_path / "eplan_connection.py")))
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("probe", 45)
    monkeypatch.setattr(doctor.subprocess, "run", timeout)
    result = doctor.configure(tmp_path, "localhost", "49152")
    assert result["success"] is False and result["reason"] == "timeout"
    assert not (tmp_path / "connection.json").exists()


def test_register_checks_both_names_before_adding_any(tmp_path):
    app = FastMCP("collision")
    app.tool(name="eplan_connection_configure")(lambda: "external")
    original = app._tool_manager.get_tool("eplan_connection_configure")
    with pytest.raises(RuntimeError, match="eplan_connection_configure"):
        doctor.register_tools(app, tmp_path)
    assert app._tool_manager.get_tool("eplan_doctor") is None
    assert app._tool_manager.get_tool("eplan_connection_configure") is original


def test_registers_documented_tool_names(tmp_path):
    app = FastMCP("doctor")
    doctor.register_tools(app, tmp_path)
    assert {tool.name for tool in app._tool_manager.list_tools()} == {
        "eplan_doctor", "eplan_connection_configure"
    }
