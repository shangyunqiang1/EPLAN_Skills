# v0.1.0 验证记录

日期：2026-11-03。环境：Windows x64、Python 3.13、MCP SDK 1.30.0、pythonnet 3.2.1、basyx-python-sdk 2.2.0。

- 结构校验：4 个扁平技能、4 个 MCP 连接、144 个上游文件映射；技能元数据、内部 Markdown 链接、安装清单、许可证及包文件哈希均通过。
- 官方 Agent Plugins 1.0 JSON Schema：`plugin.json` 与 `mcp.json` 均通过。
- 离线 pytest：**1388 passed, 3 skipped, 8 deselected**。未运行 `live` 测试。保留上游代码产生的弃用/语法警告，未为消除警告修改 vendor。
- 在项目内隔离的 `CODEX_HOME` 注册本地 marketplace，并通过 `codex plugin add eplan-skills@eplan-skills` 安装，列表显示 `installed: true`、`enabled: true`。没有修改日常使用的 Codex 插件配置。
- 实际运行 `setup.ps1` 将依赖装入项目测试数据目录的外部 venv；通过打包启动器执行 stdio MCP initialize、tools/list 和只读 `eplan_status`，成功枚举 **217** 个工具。没有调用 `eplan_connect`。
- 三个公开远端文档 MCP：initialize 与 tools/list 全部成功；P8 2026 为 2 个工具，P8 2027 为 3 个工具，EEC Pro 为 2 个工具。没有发送项目数据或修改上游服务。
- ZIP 创建后重新打开，逐文件与插件源目录比对，检查隐藏兼容清单、CRC、许可证与必备组件；输出 SHA256 校验文件。

上游部分文档仍写 199 个工具，整合没有修改这些历史说明；上面的 217 来自当前固定源码及实际依赖环境中的协议枚举。

本记录没有验证真实 EPLAN 连接、脚本执行、工程修改、PDF/BOM 导出、EEC Pro 生成或可选 CLIP 符号搜索。目标电脑仍需按实际版本和授权，用测试工程完成这些验证。

复查命令（先按 README 安装开发依赖和本地运行环境）：

```powershell
python scripts/validate.py
python -m pytest tests plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/tests -m "not live" -q
python scripts/smoke_mcp.py --remote
python scripts/package.py
```

`smoke_mcp.py --remote` 会连接第三方公开服务；去掉 `--remote` 只检查本地 MCP 的协议和状态。CI 只运行本地协议验证，避免把外部服务可用性变成提交检查的前提。
