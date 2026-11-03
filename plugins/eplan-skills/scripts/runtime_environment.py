"""Install hash-locked environments; switch only after a complete health check."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import uuid

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"core": "runtime.lock", "symbols": "symbols.lock"}


def configure_console():
    """Keep Chinese diagnostics usable on English Windows and redirected logs."""
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def lock_file(profile="core"):
    return PLUGIN_ROOT / "requirements" / PROFILES[profile]


def lock_digest(profile="core"):
    return hashlib.sha256(lock_file(profile).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def python_in(environment):
    return Path(environment) / "Scripts/python.exe"


def _read_marker(path, digest, profile):
    try:
        marker = json.loads((path / "complete.json").read_text(encoding="utf-8"))
        return marker.get("lockSha256") == digest and marker.get("profile") == profile and python_in(path).is_file()
    except (OSError, ValueError, AttributeError):
        return False


def find_environment(data_root, profile="core"):
    """Do not fall back to an unverified shared venv or an arbitrary path."""
    root = Path(data_root).resolve() / "environments"
    digest = lock_digest(profile)
    prefix = profile + "-" + digest[:16] + "-"
    try:
        active = json.loads((Path(data_root) / "active-environments.json").read_text(encoding="utf-8"))
        selected = (root / active.get(profile, "")).resolve()
        if selected.parent == root and selected.name.startswith(prefix) and _read_marker(selected, digest, profile):
            return python_in(selected)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    if root.is_dir():
        for candidate in sorted(root.glob(prefix + "*")):
            if candidate.is_dir() and candidate.resolve().parent == root and _read_marker(candidate, digest, profile):
                return python_in(candidate)
    return None


def atomic_json(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".settings-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(content, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def installation_lock(data_root):
    path = Path(data_root) / "setup.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + 30
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("另一个安装任务仍在运行，请稍后重试。") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_command(args):
    subprocess.run([str(arg) for arg in args], check=True)


def check_health(python, profile):
    run_command([python, "-m", "pip", "check", "--disable-pip-version-check"])
    expected = dict(re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s;\\]+)", lock_file(profile).read_text(encoding="utf-8")))
    script = "import sys,json; from importlib.metadata import version; expected=json.loads(sys.argv[1]); assert all(version(n)==v for n,v in expected.items()), 'Locked dependency mismatch'; from mcp.server.fastmcp import FastMCP"
    run_command([python, "-c", script, json.dumps(expected)])


def install_environment(data_root, profile="core"):
    root = Path(data_root).resolve()
    digest = lock_digest(profile)
    tag = f"py{sys.version_info.major}{sys.version_info.minor}-win-amd64"
    directory = root / "environments" / f"{profile}-{digest[:16]}-{tag}"
    with installation_lock(root):
        if _read_marker(directory, digest, profile):
            check_health(python_in(directory), profile)
        else:
            if directory.exists():
                failed = directory.with_name(directory.name + "-failed-" + uuid.uuid4().hex[:8])
                intended = (root / "environments").resolve()
                if directory.resolve().parent != intended or failed.resolve().parent != intended:
                    raise ValueError("Environment path escaped the data directory")
                directory.rename(failed)
            run_command([sys.executable, "-m", "venv", directory])
            python = python_in(directory)
            run_command([python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                         "--require-hashes", "--only-binary=:all:", "-r", lock_file(profile)])
            check_health(python, profile)
            atomic_json(directory / "complete.json", {"profile": profile, "lockSha256": digest,
                                                       "python": sys.version.split()[0]})
        pointer = root / "active-environments.json"
        try:
            active = json.loads(pointer.read_text(encoding="utf-8"))
        except FileNotFoundError:
            active = {}
        if not isinstance(active, dict):
            raise ValueError("运行环境配置格式无效，原文件未被覆盖。")
        active[profile] = directory.name
        atomic_json(pointer, active)
    return python_in(directory)


def main():
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--symbols", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32" or struct.calcsize("P") != 8 or sys.version_info < (3, 11):
        parser.error("需要 Windows x64 和 Python 3.11 或更新版本。")
    profile = "symbols" if args.symbols else "core"
    if profile == "symbols" and sys.version_info[:2] != (3, 13):
        parser.error("可选符号搜索锁文件针对 Python 3.13 x64，请用 setup.ps1 -Python 指定该解释器。")
    result = install_environment(args.data_dir, profile)
    print(f"安装验证通过：{result}。旧环境已保留；请重启插件 MCP。")


if __name__ == "__main__":
    main()
