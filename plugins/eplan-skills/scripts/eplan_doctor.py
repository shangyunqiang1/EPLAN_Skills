"""Read-only diagnostics and explicit, verified EPLAN connection settings.

This module deliberately imports the EPLAN connection manager lazily.  Merely
loading the plugin must not select a CLR or connect to a running application.
"""
from __future__ import annotations

import importlib.metadata
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
from typing import Any


_VERSION = re.compile(r"(?:20[0-9]{2}|2\.9)\Z")
_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_CONFIG_NAME = "connection.json"


def _connection_parameters(host: str, port: str, version: str | None) -> dict[str, str]:
    """Validate an endpoint without resolving names or accepting credentials."""
    if not isinstance(host, str) or not host or host != host.strip() or len(host) > 253:
        raise ValueError("主机名不能为空或包含前后空白。")
    if any(char in host for char in "/\\@?#[]") or "://" in host:
        raise ValueError("请输入主机名或 IP 地址，不要包含 URL、端口或凭据。")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if not all(_DNS_LABEL.fullmatch(label) for label in host.split(".")):
            raise ValueError("主机名或 IP 地址格式无效。") from None
    else:
        if ip.is_unspecified or ip.is_multicast:
            raise ValueError("不能连接到通配或多播地址。")

    if not isinstance(port, str) or not re.fullmatch(r"[0-9]{1,6}", port):
        raise ValueError("端口必须是 1 至 65535 的数字字符串。")
    port_num = int(port)
    if not 1 <= port_num <= 65535:
        raise ValueError("端口必须是 1 至 65535 的数字字符串。")
    if version is not None and (not isinstance(version, str) or not _VERSION.fullmatch(version)):
        raise ValueError("版本必须为主版本号，例如 2025 或 2.9。")
    result = {"host": host, "port": str(port_num)}
    if version is not None:
        result["version"] = version
    return result


def load_connection_settings(data_root: Path) -> dict[str, str] | None:
    """Read validated settings, or return None if no configuration exists.

    Malformed files raise ValueError, rather than silently selecting another
    endpoint.  The launcher can display that diagnostic and keep the file.
    """
    path = Path(data_root) / _CONFIG_NAME
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(content)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("连接配置不是有效的 UTF-8 JSON。") from exc
    if not isinstance(data, dict) or set(data) - {"host", "port", "version"}:
        raise ValueError("连接配置格式无效。")
    return _connection_parameters(data.get("host"), data.get("port"), data.get("version"))


def _atomic_save(data_root: Path, settings: dict[str, str]) -> None:
    """Write in the same directory before atomically replacing old settings."""
    data_root = Path(data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".connection-", suffix=".tmp", dir=data_root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(settings, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, data_root / _CONFIG_NAME)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _local_addresses() -> set[str]:
    addresses = {"localhost", "127.0.0.1", "::1"}
    try:
        hostname = socket.gethostname()
        addresses.add(hostname.lower().rstrip("."))
        addresses.update(socket.gethostbyname_ex(hostname)[2])
    except OSError:
        pass
    return addresses


def _exception_kind(exc: BaseException) -> str:
    if isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 5:
        return "permission_denied"
    return "unavailable"


def _windows_process_snapshot() -> dict[str, Any]:
    """List only EPLAN PIDs and their listeners, without probing any port."""
    if sys.platform != "win32":
        return {"available": False, "reason": "unsupported_platform", "pids": [], "listeners": []}
    try:
        from process_control import process_ids, tcp_listeners

        pids = sorted(set(process_ids("EPLAN.exe")))
        # process_ids can return [] when the underlying snapshot's first row
        # could not be read. Verify that the snapshot includes this process
        # before treating an empty EPLAN list as proof it is not running.
        if not pids and os.getpid() not in process_ids(Path(sys.executable).name):
            return {"available": False, "reason": "process_snapshot_incomplete", "pids": [], "listeners": []}
    except Exception as exc:
        return {"available": False, "reason": _exception_kind(exc), "pids": [], "listeners": []}
    if not pids:
        return {"available": True, "pids": [], "listeners": []}
    try:
        listeners = [
            {"address": str(address), "port": int(port), "pid": int(pid)}
            for address, port, pid in tcp_listeners()
            if pid in pids
        ]
    except Exception as exc:
        return {"available": False, "reason": _exception_kind(exc), "pids": pids, "listeners": []}
    listeners.sort(key=lambda item: (item["pid"], item["port"], item["address"]))
    return {"available": True, "pids": pids, "listeners": listeners}


def _proxy_summary(addresses: set[str]) -> dict[str, Any]:
    """Never echo proxy URLs, environment contents, credentials, or tokens."""
    has_proxy = any(bool(os.environ.get(key)) for key in (
        "grpc_proxy", "GRPC_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
        "all_proxy", "ALL_PROXY",
    ))
    bypass = os.environ.get("no_grpc_proxy", os.environ.get("NO_GRPC_PROXY", ""))
    entries = {part.strip().lower().rstrip(".") for part in bypass.split(",") if part.strip()}
    local_bypassed = sorted(address for address in addresses if address.lower().rstrip(".") in entries)
    return {"proxyConfigured": has_proxy, "localGrpcBypassConfigured": bool(local_bypassed),
            "localGrpcBypassHosts": local_bypassed}


def _pythonnet_version() -> str | None:
    try:
        return importlib.metadata.version("pythonnet")
    except importlib.metadata.PackageNotFoundError:
        return None


def _probe_versions() -> dict[str, Any]:
    try:
        from eplan_connection import detect_installed_versions

        return {"available": True, "versions": detect_installed_versions()}
    except Exception as exc:
        return {"available": False, "reason": _exception_kind(exc), "versions": []}


def diagnose(data_root: Path) -> dict[str, Any]:
    """Inspect local state.  A running connection may be pinged, never opened."""
    from eplan_connection import get_manager

    manager = get_manager()
    status = dict(manager.get_status())
    # Error strings from a transport may contain proxy endpoints or other
    # sensitive environment details. Classify their presence without echoing.
    status["hasError"] = bool(status.pop("last_error", ""))
    processes = _windows_process_snapshot()
    versions = _probe_versions()
    local_addresses = _local_addresses()
    result: dict[str, Any] = {
        "success": True,
        "python": {"executable": sys.executable, "version": sys.version.split()[0],
                   "architectureBits": 64 if sys.maxsize > 2**32 else 32,
                   "pythonnetVersion": _pythonnet_version(), "clrLoaded": "clr" in sys.modules},
        "eplanInstallations": versions,
        "processes": processes,
        "connection": status,
        "proxy": _proxy_summary(local_addresses),
    }
    try:
        configured = load_connection_settings(data_root)
    except (ValueError, OSError, UnicodeError) as exc:
        result["savedConfiguration"] = {"valid": False, "errorType": type(exc).__name__}
    else:
        result["savedConfiguration"] = {"valid": True, "configured": configured is not None}
        if configured is not None:
            result["savedConfiguration"]["endpoint"] = configured

    if status.get("connected"):
        try:
            ping = manager.ping()
        except Exception as exc:
            ping = {"alive": False, "errorType": type(exc).__name__}
        result["ping"] = ping
        if ping.get("alive"):
            code, message = "connected", "EPLAN 已连接并响应。"
        elif ping.get("timed_out"):
            code, message = "busy", "EPLAN 心跳超时，可能正在忙碌；不要自动重试工程修改。"
        else:
            code, message = "connection_error", "已建立的连接未通过心跳检查。"
    elif not versions["available"] or not processes["available"]:
        code, message = "detection_incomplete", "进程、监听端口或安装信息无法完整读取，请检查诊断详情。"
    elif not versions["versions"]:
        code, message = "not_installed", "未检测到 EPLAN 安装。"
    elif not processes["pids"]:
        code, message = "not_running", "未检测到正在运行的 EPLAN 进程。"
    elif status.get("hasError"):
        code, message = "connection_error", "此前的连接未成功，请结合本机监听地址检查。"
    elif not processes["listeners"]:
        code, message = "service_not_detected", "未发现 EPLAN 进程的 TCP 监听；这不能单独证明远程访问已关闭。"
    elif not status.get("api_loaded"):
        code, message = "api_not_loaded", "EPLAN 进程正在运行；此 MCP 会话尚未加载 EPLAN API。"
    else:
        code, message = "not_connected", "已检测到 EPLAN 监听端口；此 MCP 会话尚未连接。"
    result["diagnosis"] = {"code": code, "message": message}
    return result


_PROBE_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from eplan_connection import EPLANConnectionManager
manager = EPLANConnectionManager(sys.argv[4] or None)
answer = {'success': False, 'stage': 'connect'}
try:
    connected = manager.connect(host=sys.argv[2], port=sys.argv[3])
    if connected.get('success') is True:
        ping = manager.ping(timeout_seconds=15.0)
        if ping.get('alive') is True:
            answer = {'success': True}
        elif ping.get('timed_out'):
            answer = {'success': False, 'stage': 'ping', 'reason': 'busy'}
        else:
            answer = {'success': False, 'stage': 'ping', 'reason': 'no_response'}
    else:
        answer = {'success': False, 'stage': 'connect', 'reason': 'unreachable'}
except Exception as exc:
    answer = {'success': False, 'stage': 'connect', 'reason': type(exc).__name__}
finally:
    try:
        if manager.connected:
            manager.disconnect()
    except Exception:
        pass
print('EPLAN_CONNECTION_CHECK=' + json.dumps(answer), flush=True)
"""


def _verify_connection(settings: dict[str, str]) -> dict[str, Any]:
    """Probe in a fresh process so a failed check cannot retarget the session."""
    import eplan_connection

    server_root = str(Path(eplan_connection.__file__).resolve().parent)
    args = [sys.executable, "-c", _PROBE_SCRIPT, server_root, settings["host"],
            settings["port"], settings.get("version", "")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=45, env=env,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"success": False, "stage": "connect", "reason": "timeout"}
    except OSError as exc:
        return {"success": False, "stage": "start", "reason": _exception_kind(exc)}
    prefix = "EPLAN_CONNECTION_CHECK="
    lines = [line[len(prefix):] for line in result.stdout.splitlines() if line.startswith(prefix)]
    if result.returncode != 0 or len(lines) != 1:
        return {"success": False, "stage": "probe", "reason": "invalid_response"}
    try:
        parsed = json.loads(lines[0])
    except ValueError:
        return {"success": False, "stage": "probe", "reason": "invalid_response"}
    if not isinstance(parsed, dict) or type(parsed.get("success")) is not bool:
        return {"success": False, "stage": "probe", "reason": "invalid_response"}
    return parsed


def configure(data_root: Path, host: str, port: str, version: str | None = None) -> dict[str, Any]:
    """Validate an explicit endpoint and atomically save only after live ping."""
    try:
        settings = _connection_parameters(host, port, version)
    except ValueError as exc:
        return {"success": False, "stage": "validation", "message": str(exc)}
    verified = _verify_connection(settings)
    if verified.get("success") is not True:
        return {"success": False, "stage": verified.get("stage", "probe"),
                "reason": verified.get("reason", "unknown"),
                "message": "连接验证未通过，原有连接配置保持不变。"}
    try:
        _atomic_save(data_root, settings)
    except OSError as exc:
        return {"success": False, "stage": "save", "reason": _exception_kind(exc),
                "message": "连接已验证，但保存失败；原有连接配置保持不变。"}
    return {"success": True, "settings": settings,
            "isLocal": settings["host"].lower().rstrip(".") in _local_addresses(),
            "message": "连接与心跳验证通过，配置已保存；重启插件 MCP 后用于默认连接。"}


def register_tools(app: Any, data_root: Path) -> None:
    """Register tools on FastMCP; the caller owns server and policy setup."""
    root = Path(data_root)
    manager = getattr(app, "_tool_manager", None)
    if manager is None or not callable(getattr(manager, "get_tool", None)):
        raise RuntimeError("无法检查已有 MCP 工具，未注册 EPLAN 诊断工具。")
    duplicates = [name for name in ("eplan_doctor", "eplan_connection_configure")
                  if manager.get_tool(name) is not None]
    if duplicates:
        raise RuntimeError("MCP 工具名称已被占用：" + ", ".join(duplicates))

    def eplan_doctor() -> dict[str, Any]:
        """只读检查 EPLAN 安装、进程、监听地址和当前连接；不会自动连接。"""
        return diagnose(root)

    def eplan_connection_configure(host: str, port: str, version: str | None = None) -> dict[str, Any]:
        """验证用户指定的 EPLAN 地址并保存；不会重放任何工程操作。

        此操作只在用户明确要求设置连接时调用，验证通过才会替换本机配置。
        """
        return configure(root, host, port, version)

    app.tool(name="eplan_doctor")(eplan_doctor)
    app.tool(name="eplan_connection_configure")(eplan_connection_configure)
