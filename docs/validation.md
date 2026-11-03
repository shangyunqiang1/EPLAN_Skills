# 验证记录

## v0.2.0 / v0.2.1 — 2026-11-03

- 本地最终离线回归：**1441 passed, 3 skipped, 8 deselected**。包含英文 Windows 中文输出回归；保留既有上游弃用警告，未运行工程写入类 live 测试。
- 严格 stdio 检查通过：220 个本地工具均有分类注解；未连接时的当前项目查询返回正文失败且 `isError=true`，普通状态查询保持非错误。
- 新测试覆盖 Python/.NET stdout 污染、非法 UTF-8、超时回收子进程、schema 错误、discovery 转发和未知扩展保守分类。
- 以锁文件和 `--require-hashes --only-binary=:all:` 在项目测试目录与当前用户数据目录各安装了新的核心环境，`pip check` 和全部固定包版本检查通过；旧 venv 保留。安装失败/健康检查失败不切换环境的回归通过。
- 三个文档网关均通过真实公开服务示例检索，且通过严格协议检查。禁用服务不联网、远端失败不使本地 MCP 退出、Markdown 结果与失败标志兼容均有回归测试。
- 中文 doctor、地址校验、独立子进程连接验证、原子配置保存、坏配置容错均通过离线测试。只读诊断与系统 TCP 表一致：当前 EPLAN 有进程但无可见 Remote Client 监听；用户明确选择暂时跳过实机连接，因此本轮没有声称实际连接或工程操作已验证。
- 可选符号搜索依赖已解析并固定 Windows x64 / Python 3.13 wheel 哈希；未安装大型模型或验证符号推理。
- CI 增加 Windows / Python 3.11 和 3.13 两个环境，运行完整离线回归、固定依赖安装、严格本地协议验证和打包。公共 RAG 可用性不作为 CI 前提。

## v0.1.1 安装与实机验证 — 2026-11-03

- 当前用户 Codex 安装并启用插件，依赖安装至用户数据目录。
- EPLAN 2025.0.3 实机已成功完成 Remote Client 连接、ping 和只读当前项目查询（`selectionset /TYPE:PROJECT`）。发现本机服务只监听网卡地址，需显式指定已确认的本机地址和端口。
- 实机验证发现原生 gRPC 受 HTTP 代理影响；增加仅针对本机地址的 `no_grpc_proxy` 例外后连接成功。例外仅作用于 MCP 子进程，不改变系统或文档 HTTP 请求配置。
- 连接时 EPLAN Remote Client 的 .NET Console 诊断曾混入 stdout；v0.1.1 在延迟初始化 CLR 后将 Console 输出导向 stderr，实机连接复测没有 JSON-RPC 解析错误。新增真实 CLR 子进程回归测试。
- 离线测试：**1391 passed, 3 skipped, 8 deselected**。
- 三个文档 MCP 均完成实际示例检索并返回结果，不含私人项目数据。
- 本轮没有编辑、关闭、保存工程，也没有验证工程写入、导出或 EEC Pro 生成。

## v0.1.0

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
