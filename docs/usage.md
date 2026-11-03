# 使用说明

## 前提与连接

在运行 EPLAN 的 Windows 电脑上安装 Python 和插件依赖，使用已获授权的 EPLAN 功能。参照 [README](../README.md) 执行安装脚本后，启动 EPLAN，并在 **文件 → 设置 → 工作站 → 接口 → 远程访问** 启用 Remote Client 远程访问。设置位置、授权和支持的版本以实际安装为准。

新建客户端会话后，可以请求助手按顺序执行：

1. 调用本地 `eplan` MCP 的 `eplan_versions`，检查检测到的安装版本。
2. 根据需要调用 `eplan_connect`，再用 `eplan_status` 检查连接。如果自动发现失败，检查实际监听端口并明确指定；不要仅凭默认端口判断。
3. 确认操作目标，先在测试项目上尝试读取、导出或编辑，再检查 EPLAN 中的实际结果。

可先调用 `eplan_doctor` 获得中文诊断。它只读状态；未连接时不会自动连接，检测权限不足时会明确说明，不能把“没有读到端口”解释为 Remote Client 已关闭。需要记住地址时，明确调用 `eplan_connection_configure(host="实际地址", port="实际端口", version="主版本")`，连接与心跳成功后才保存。重启 MCP 后 `eplan_connect()` 使用已保存的默认配置。忙碌或超时不会自动重放工程修改。

如果 `localhost` 连接失败，但 EPLAN 已运行，可按进程核对实际监听地址与端口。某些安装仅绑定网卡地址；用已确认属于本机 EPLAN 的地址调用 `eplan_connect(host="实际监听地址", port="实际端口", version="安装的主版本")`。不要扫描未知端口或把固定端口当成运行状态的证明。启动器只在当前 MCP 进程中把本机地址加入原生 gRPC 的代理例外，保留现有代理设置和文档 HTTP 请求行为。

本地 MCP 可以执行脚本和更改项目；在用户授权范围内操作，保留现有工程并核验结果。此插件的集成与离线测试不能代替目标机器上的 EPLAN 连接和工程验证。

## 配置

在运行依赖安装脚本和启动客户端之前设置环境变量，并在更改后重启客户端：

| 变量 | 作用 |
|---|---|
| `EPLAN_SKILLS_DATA_DIR` | 指定插件可写数据目录；默认 `%LOCALAPPDATA%\EPLAN_Skills`，包含 Python 环境及日志。安装与运行时须使用相同目录。 |
| `EPLAN_PLATFORM_ROOT` | EPLAN 平台安装根目录，适用于非默认安装位置。 |
| `EPLAN_MCP_MODE` | 默认 `full` 暴露完整工具集；设为 `discovery` 后通过搜索、描述及调用工具按需访问。 |
| `EPLAN_SKILLS_SYMBOL_SEARCH` | 设为 `1` 启用可选符号搜索，先执行安装脚本并附加 `-IncludeSymbolSearch`。 |

例如，在同一个 PowerShell 会话设置数据目录并安装：

```powershell
$env:EPLAN_SKILLS_DATA_DIR = 'D:\EPLAN-Skills-Data'
powershell -ExecutionPolicy Bypass -File .\plugins\eplan-skills\scripts\setup.ps1
```

让客户端继承相同的环境变量后再启动。若依赖安装失败，检查 Python、网络、权限和脚本的具体错误；不要将许可证文件、EPLAN DLL 或工程文件放进公开仓库。

## 选择技能与文档

v0.2.0 按依赖锁和 wheel 哈希安装独立环境，`active-environments.json` 指向通过健康检查的环境。失败不会切换现有环境。旧环境会保留；回退插件后可重新执行对应版本 setup。不要手动修改插件缓存。

`eplan-router` 根据任务选择 `eplan-scripting` 和 `eec-pro-development`。涉及 EEC Pro 生成 P8 工程时，两种技能都适用。`eplan-setup` 提供安装和诊断步骤。

| MCP 名称 | 内容 |
|---|---|
| `eplan` | 本机 EPLAN 操作和检查 |
| `eplan-rag` | P8 2026 文档语义检索 |
| `eplan-wiki-2027` | P8 2027 文档关键词检索 |
| `eecpro-rag` | EEC Pro 文档检索 |

远端检索由 Canary E-cad 运营，服务可用性和内容版本由上游决定；参考 [数据与隐私说明](privacy.md)。技能中的反射示例仅描述技术访问方式，应另行确认当前 EPLAN 产品版本和授权，不能把技术上可访问视为使用授权。

## 开发验证

三个文档 MCP 通过本机轻量网关连接原服务，需先安装 Python 依赖，但不要求运行 EPLAN。默认 `all`；`eplan_documentation_configure(profile="p8")` 只启用两个 P8 索引，`p8-keyword` 只启用 2027 索引，`eec` 只启用 EEC Pro，`offline` 全部禁用。禁用后仍有本地状态工具，不发送远端请求；重启 MCP 刷新列表。也可在插件根目录运行 `python scripts/documentation.py --profile offline`。P8 2025 的接口应结合本机核对，不能把 2026/2027 索引当作本机 API 保证。

严格协议检查使用 `python scripts/smoke_mcp.py`：普通 stdout 日志、无效 UTF-8、非法 JSON-RPC 或超时均会失败，stderr 不作为协议。`--remote` 另做已启用服务的示例检索；`--connect --host 实际地址 --port 实际端口 --version 2025` 才会连接 EPLAN 并只读查询。`--plugin-root` 指向安装目录；加 `--save-connection` 可验证后保存设置。默认不连接 EPLAN。

在仓库根目录运行 `python scripts/validate.py` 校验插件结构，运行 `python scripts/package.py` 生成可分发包。有关上游来源、固定版本和许可证，请查阅 [第三方来源说明](../THIRD_PARTY_NOTICES.md)。
