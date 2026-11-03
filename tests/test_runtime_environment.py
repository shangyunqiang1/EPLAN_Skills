import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/eplan-skills/scripts"))
import runtime_environment as runtime


@pytest.fixture
def fixture_runtime(tmp_path, monkeypatch):
    plugin = tmp_path / "plugin"
    (plugin / "requirements").mkdir(parents=True)
    (plugin / "requirements/runtime.lock").write_text("mcp==1.30.0 --hash=sha256:abc\n")
    monkeypatch.setattr(runtime, "PLUGIN_ROOT", plugin)
    return tmp_path / "data"


def test_failed_install_keeps_previous_environment_and_pointer(fixture_runtime, monkeypatch):
    root = fixture_runtime
    root.mkdir()
    legacy = root / "venv/Scripts/python.exe"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("old environment")
    pointer = root / "active-environments.json"
    pointer.write_text('{"core":"previous"}')
    def fail(args):
        raise subprocess.CalledProcessError(1, "simulated install")
    monkeypatch.setattr(runtime, "run_command", fail)
    with pytest.raises(subprocess.CalledProcessError):
        runtime.install_environment(root)
    assert pointer.read_text() == '{"core":"previous"}'
    assert legacy.read_text() == "old environment"
    assert runtime.find_environment(root) is None


def test_successful_install_activates_only_verified_environment(fixture_runtime, monkeypatch):
    root = fixture_runtime
    calls = []
    def run(args):
        calls.append([str(v) for v in args])
        if str(args[2]) == "venv":
            path = runtime.python_in(args[3])
            path.parent.mkdir(parents=True)
            path.write_text("python")
    monkeypatch.setattr(runtime, "run_command", run)
    target = runtime.install_environment(root)
    assert runtime.find_environment(root) == target
    install = next(args for args in calls if "install" in args)
    assert "--require-hashes" in install and "--only-binary=:all:" in install
    assert any("check" in args for args in calls)
    assert (target.parents[1] / "complete.json").is_file()


def test_health_failure_never_marks_or_activates(fixture_runtime, monkeypatch):
    root = fixture_runtime
    def run(args):
        if str(args[2]) == "venv":
            path = runtime.python_in(args[3])
            path.parent.mkdir(parents=True)
            path.touch()
    monkeypatch.setattr(runtime, "run_command", run)
    monkeypatch.setattr(runtime, "check_health", lambda *args: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(RuntimeError):
        runtime.install_environment(root)
    assert not (root / "active-environments.json").exists()
    assert runtime.find_environment(root) is None


def test_lock_changes_and_path_escape_are_not_trusted(fixture_runtime):
    root = fixture_runtime
    root.mkdir()
    runtime.atomic_json(root / "active-environments.json", {"core": "../../outside"})
    assert runtime.find_environment(root) is None
    assert not (root.parent / "outside").exists()


def test_chinese_cli_output_works_with_english_windows_encoding():
    script = "import sys; sys.path.insert(0,sys.argv[1]); from runtime_environment import configure_console; configure_console(); print('中文安装成功'); print('中文诊断',file=sys.stderr)"
    result = subprocess.run([sys.executable, "-c", script, str(ROOT / "plugins/eplan-skills/scripts")],
        capture_output=True, encoding="utf-8", timeout=15, check=True,
        env=dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0"))
    assert "中文安装成功" in result.stdout and "中文诊断" in result.stderr
