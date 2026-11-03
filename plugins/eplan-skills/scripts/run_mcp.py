"""Launch the vendored EPLAN server without writing into the plugin cache."""
from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PLUGIN_ROOT / "vendor/eplan-mcp/eplan-p8-mcp-server"


def data_dir() -> Path:
    override = os.environ.get("EPLAN_SKILLS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
    return base / "EPLAN_Skills"


def prepare_runtime() -> Path:
    # Upstream writes generated C# next to its modules. Run a versioned copy in
    # writable user data so project content never enters the plugin cache.
    digest = hashlib.sha256((PLUGIN_ROOT / "upstream-lock.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]
    base = data_dir() / "runtime"
    destination = base / digest
    if destination.is_dir():
        return destination
    base.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="staging-", dir=base))
    try:
        shutil.copytree(SERVER_ROOT, staging, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "logs"))
        try:
            staging.rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def configure_local_grpc_proxy() -> None:
    # EPLAN's native gRPC library honors http_proxy. Exempt this workstation
    # only; leave HTTP documentation clients and remote EPLAN hosts unchanged.
    hosts = {"localhost", "127.0.0.1", "::1"}
    try:
        hosts.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    existing = os.environ.get("no_grpc_proxy", os.environ.get("NO_GRPC_PROXY", ""))
    entries = [value.strip() for value in existing.split(",") if value.strip()]
    os.environ["no_grpc_proxy"] = ",".join(dict.fromkeys(entries + sorted(hosts)))


def main() -> int:
    if sys.platform != "win32":
        print("Local EPLAN automation requires Windows; documentation MCPs are remote.", file=sys.stderr)
        return 1
    target = data_dir() / "venv/Scripts/python.exe"
    if not target.is_file():
        print(f"EPLAN dependencies missing. Run: powershell -ExecutionPolicy Bypass -File \"{PLUGIN_ROOT / 'scripts/setup.ps1'}\"", file=sys.stderr)
        return 1
    if Path(sys.executable).resolve() != target.resolve():
        return subprocess.call([str(target), "-u", str(Path(__file__).resolve())])

    os.environ["MCP_TRANSPORT"] = "stdio"
    os.environ.setdefault("EPLAN_MCP_MODE", "full")
    os.environ.setdefault("EPLAN_MCP_LOG_DIR", str(data_dir() / "logs"))
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    configure_local_grpc_proxy()
    runtime_root = prepare_runtime()
    if os.environ.get("EPLAN_SKILLS_SYMBOL_SEARCH") == "1":
        extension = str(runtime_root / "extensions")
        current = os.environ.get("EPLAN_MCP_EXTENSIONS", "")
        os.environ["EPLAN_MCP_EXTENSIONS"] = os.pathsep.join(filter(None, [current, extension]))
    sys.path.insert(0, str(runtime_root / "mcp_server"))
    # Import-time diagnostics belong on stderr; stdout is MCP JSON-RPC only.
    with contextlib.redirect_stdout(sys.stderr):
        from server import mcp
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
