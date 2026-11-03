"""Selectable documentation MCP gateways; no model keys or EPLAN access."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from runtime_environment import atomic_json, find_environment, configure_console

SERVICES = {
    "eplan-rag": ("https://rag2026.covaga.xyz/mcp", "P8 2026", {"eplan_search", "eplan_stats"}),
    "eplan-wiki-2027": ("https://rag2027.covaga.xyz/mcp", "P8 2027", {"eplan2027_search", "eplan2027_get", "eplan2027_stats"}),
    "eecpro-rag": ("https://rageecpro.covaga.xyz/mcp", "EEC Pro 2026", {"eecpro_search", "eecpro_stats"}),
}
PROFILES = {"all": set(SERVICES), "p8": {"eplan-rag", "eplan-wiki-2027"},
            "p8-keyword": {"eplan-wiki-2027"}, "eec": {"eecpro-rag"}, "offline": set()}


def data_root():
    return Path(os.environ.get("EPLAN_SKILLS_DATA_DIR", str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EPLAN_Skills"))).expanduser().resolve()


def load_profile(root):
    try:
        value = json.loads((Path(root) / "documentation.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "all"
    if not isinstance(value, dict) or set(value) != {"profile"} or value["profile"] not in PROFILES:
        raise ValueError("文档服务配置无效；未向远端发送请求。")
    return value["profile"]


def configure(root, profile):
    if profile not in PROFILES:
        return {"success": False, "message": "未知文档配置。", "profiles": list(PROFILES)}
    atomic_json(Path(root) / "documentation.json", {"profile": profile})
    return {"success": True, "profile": profile, "enabled": sorted(PROFILES[profile]),
            "message": "配置已保存，请重启插件 MCP 以刷新工具列表。"}


def register_configuration_tool(app, root):
    if app._tool_manager.get_tool("eplan_documentation_configure") is not None:
        raise RuntimeError("eplan_documentation_configure 工具名称冲突。")
    def eplan_documentation_configure(profile: str) -> dict:
        """设置文档服务：all、p8、p8-keyword、eec 或 offline；只保存本机配置。"""
        return configure(root, profile)
    app.tool(name="eplan_documentation_configure")(eplan_documentation_configure)


class Gateway:
    def __init__(self, name, root):
        self.name, self.root = name, Path(root)
        self.url, self.version, self.allowed = SERVICES[name]
        self.status_name = name.replace("-", "_") + "_status"
        self.known = {}
        self.error = None

    def enabled(self):
        return self.name in PROFILES[load_profile(self.root)]

    async def remote(self, operation, *args):
        import anyio
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        with anyio.fail_after(30):
            async with streamablehttp_client(self.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await getattr(session, operation)(*args)

    async def list_tools(self):
        from mcp.types import Tool, ToolAnnotations
        status = Tool(name=self.status_name, description=f"只读检查 {self.version} 文档服务启用状态与版本说明。",
                      inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                      annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
        try:
            enabled = self.enabled()
        except (OSError, ValueError):
            self.error = "configuration_invalid"
            return [status]
        if not enabled:
            self.known = {}
            self.error = None
            return [status]
        try:
            result = await self.remote("list_tools")
            self.known = {tool.name: tool for tool in result.tools if tool.name in self.allowed}
            for tool in self.known.values():
                tool.annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
            self.error = None
        except Exception as exc:
            self.error = type(exc).__name__
        return [status, *self.known.values()]

    async def call_tool(self, name, arguments):
        from mcp.types import CallToolResult, TextContent
        def result(payload, failed=False):
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))], isError=failed)
        try:
            enabled = self.enabled()
        except (OSError, ValueError):
            return result({"success": False, "message": "文档服务配置无效。"}, True)
        if name == self.status_name:
            return result({"success": True, "enabled": enabled, "documentationVersion": self.version,
                           "lastErrorType": self.error,
                           "message": "索引版本不代表本机 EPLAN API 版本；查询会发送至 Canary E-cad 服务。"})
        if not enabled or name not in self.allowed:
            return result({"success": False, "message": "此文档服务未启用或工具未获支持。"}, True)
        try:
            answer = await self.remote("call_tool", name, arguments or {})
            body = answer.structuredContent
            if not isinstance(body, dict) and len(answer.content) == 1 and answer.content[0].type == "text":
                try:
                    body = json.loads(answer.content[0].text)
                except (ValueError, TypeError):
                    body = None
            if isinstance(body, dict) and body.get("success") is False:
                answer.isError = True
            self.error = None
            return answer
        except Exception as exc:
            self.error = type(exc).__name__
            return result({"success": False, "message": "远端文档服务暂不可用；本机 EPLAN MCP 不受影响。",
                           "errorType": self.error}, True)


async def serve(name, root):
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    gateway = Gateway(name, root)
    server = Server(name)
    server.list_tools()(gateway.list_tools)
    server.call_tool()(gateway.call_tool)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=SERVICES)
    parser.add_argument("--profile", choices=PROFILES)
    args = parser.parse_args()
    root = data_root()
    if args.profile:
        print(json.dumps(configure(root, args.profile), ensure_ascii=False))
        return 0
    if not args.server:
        parser.error("请选择 --server 或 --profile")
    python = find_environment(root) or find_environment(root, "symbols")
    if python is None:
        print("请先运行插件 scripts/setup.ps1 安装固定依赖。", file=sys.stderr)
        return 1
    if Path(sys.executable).resolve() != python.resolve():
        return subprocess.call([str(python), "-u", str(Path(__file__).resolve()), "--server", args.server])
    asyncio.run(serve(args.server, root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
