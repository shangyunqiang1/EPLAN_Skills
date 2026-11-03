# Bochica 与 EPLAN_Skills 改进对照

实施进度：下文以 v0.1.2 为调查基线。v0.2.0 已实现六项对应改进，加入严格协议测试、统一失败标志、固定依赖及独立环境、中文诊断与显式连接配置、工具分类和可选文档网关。验收结果见 [validation.md](validation.md)。Bochica 的模型与聊天界面没有移植，继续由 Codex / Claude Code 承担。

调研日期：2026-11-03。Bochica 基线为 commit `e2002146b516b1d805109aedda1b0bbb55c23f52`；EPLAN_Skills 基线为 v0.1.2 / commit `243148f`。本次阅读两侧源码，并对本插件和 SDK 做了三个隔离验证；没有启动 Bochica、调用模型或连接 EPLAN。没有修改插件运行逻辑、安装配置或发布版本。

## 结论与优先级

建议优先补齐失败状态、协议验证、安装可复现性和连接诊断。Bochica 是独立桌面应用，EPLAN_Skills 是运行于 Codex/Claude Code 的插件：聊天界面、模型配置、会话管理和宿主权限界面不需要搬进插件。Bochica 的普通文件撤销也不能视为 EPLAN 工程回滚。

| 优先级 | 改进 | 本插件现状及证据 | 建议验收 |
| --- | --- | --- | --- |
| P1 | 统一工具失败状态 | `_json_wrapper` 将失败/异常序列化为文本；隔离调用未连接的 `eplan_get_current_project`，实际得到 `isError=false`、正文 `success=false`。[当前实现](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server/server.py#L94-L105) | 明确的执行失败应在 MCP 标志和正文中一致；保留正文兼容性。`connected=false` 等正常状态查询不应一律视为错误。覆盖 core、action 与 discovery 转发。 |
| P1 | 严格检查协议输出 | `smoke_mcp.py` 检查握手、工具及内容 JSON，却未明确捕获协议解析日志；模拟服务先输出普通日志再服务 MCP 时，SDK 记录解析错误后仍完成握手。[测试入口](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/scripts/smoke_mcp.py#L18-L38) | 在 CI 中故意注入 Python/.NET 非协议 stdout，应明确失败；stderr 日志应允许。不能只以退出码或最终握手成功判定协议纯净。 |
| P1 | 固定依赖并保留可回退环境 | 源码已固定提交和文件哈希，但 Python 依赖仍是范围版本；安装总是写入同一个用户 `venv`。[依赖](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server/requirements.txt#L5-L11)、[安装](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/scripts/setup.ps1#L14-L29) | 固定完整依赖及哈希；按依赖锁生成独立环境，检查通过后再切换。模拟下载/安装失败时，旧环境仍能启动。源码回退不能代替依赖环境回退。 |
| P1 | 中文连接诊断工具 | 已有版本检测、状态与 ping；本机监听地址异常的处理目前主要写在文档中；`get_status()` 返回已知状态，不主动探测健康。[连接说明](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/docs/usage.md#L5-L15)、[状态实现](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server/eplan_connection.py#L1257-L1276) | 增加只读 doctor，报告 Python/CLR、EPLAN 进程、其实际监听地址、代理例外和 ping。用户选择或明确允许后保存已验证的连接配置；自动重连仅限连接操作，不重放工程修改。 |
| P2 | 工具分类和元数据 | 当前注册没有传入工具 annotations；离线枚举 217 个工具，带 annotations 的为 0。[注册](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server/server.py#L329-L378) | 按只读、工程修改、任意脚本、导出/文件操作整理能力清单，并给宿主提供相应提示；新增工具必须分类。注解不是权限强制机制，仍由宿主执行授权策略。 |
| P2 | 文档服务可选择，突出版本差异 | 当前三个远端 RAG 都在默认配置中；Bochica 将 2026/EEC Pro 作为可选服务。[本插件配置](https://github.com/shangyunqiang1/EPLAN_Skills/blob/243148f/plugins/eplan-skills/mcp.json#L11-L22) | 在宿主支持的配置方式内提供按需启用方案和离线说明；验证一个远端不可用时本机 MCP 仍能用。用户的 P8 2025 与 2026/2027 索引需要明确区分，不能将索引版本当作本机 API 保证。 |

P1 表示建议优先实现，并非声称本次发生了工程损坏。前三项可先离线验证；连接诊断随后在目标机器上做只读验收。工程写入、备份恢复、导出与 EEC Pro 生成应单独使用测试工程验收。

## 本轮隔离验证

环境：项目 `.venv`，Python 3.13、MCP SDK 1.30.0；只启动临时或本插件的本地 MCP 进程。

1. **失败状态**：新建未连接的 MCP 会话，调用只读 `eplan_get_current_project`，返回 `protocolIsError=false`、`bodySuccess=false`。没有连接 EPLAN 或读取工程。
2. **协议污染**：临时 FastMCP 服务启动时先向 stdout 输出 `unexpected diagnostic`，再正常提供工具。SDK 记录 `Failed to parse JSONRPC`，但 initialize 与 tools/list 仍成功。此结果说明当前依赖的 SDK 能容忍该污染，不代表当前 v0.1.2 正在输出污染；v0.1.1 已修复已知 .NET 日志污染。
3. **工具注解**：离线构建插件服务并枚举工具，结果为 `toolCount=217`、`toolsWithAnnotations=0`。没有执行这些工具。

## 已有能力与不宜直接照搬的内容

- 本插件已经固定上游提交、保存来源/许可及文件哈希，具有外部 venv、版本化运行副本、stdio Python/.NET 日志隔离、本机 gRPC 代理例外和 Windows CI；这些不能再写成完全缺失。缺口主要在完整依赖锁、安装切换和诊断的自动化。
- 上游和本插件都支持 full 工具模式。本次没有 Codex 工具加载开销的测量，保持当前 full 默认；不因工具数多就改成 discovery。[Bochica 默认配置](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/mcp-servers.ts#L23-L50)
- Bochica 的状态服务主要是定时组合 `eplan_status`、`eplan_ping` 和 `eplan_connect({})`，不是独立的网卡/端口自动修复实现。[状态调用](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/apps/desktop/src/main/eplan-status.ts#L43-L106)
- Bochica 通用 MCP 层也只按 `result.isError` 计算 `ok`，不解析正文 `success:false`；所以失败状态这一项是对两侧源码共同发现的改进，不是上游已经解决可直接复制的功能。[调用结果](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/agent/src/mcp.ts#L277-L289)
- 上游离线安装包的思路可以作为后续可选分发方式。插件当前保留外部 venv 即可；如提供独立 Python 离线包，需额外维护体积、哈希、更新和第三方许可，不能假定复制桌面 App 打包目录就可直接使用。

## Bochica 侧源码证据

## 可复现环境和供应链

- Bochica 将 Windows x64 Python 和 uv 版本、下载地址与 SHA-256 固定在 [runtime.ts](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/runtime.ts#L18-L30)，构建脚本检查下载及缓存哈希，依赖安装使用 `--require-hashes`（[prepare-runtime.ts](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/apps/desktop/scripts/prepare-runtime.ts#L77-L89)、[安装](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/apps/desktop/scripts/prepare-runtime.ts#L182-L201)）。候选：核查本插件安装是否固定上游提交和完整依赖、校验下载，按实际部署需要采用锁文件与失败即停止；不必照搬桌面安装包。验证：全新环境重复安装、损坏缓存和错误哈希均应失败，记录运行时版本。
- [runtime.ts](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/runtime.ts#L73-L108) 区分开发覆盖路径与打包运行时。候选：清楚记录本插件解释器和服务路径的选择、版本和缺失时报错，避免无意使用错误环境；测试带空格路径及缺失解释器。

## 连接、超时与协议

- Bochica [状态检查](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/apps/desktop/src/main/eplan-status.ts#L75-L87) 区分已连接、ping 超时忙碌和主动连接；[MCP 管理](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/agent/src/mcp.ts#L180-L217) 用 generation 防止过期异步连接结果生效，并在关闭后处理重新连接。候选：明确 EPLAN 未运行、Remote Client 未启用、忙碌和连接失败的诊断；验证启动顺序、断开后重启和长任务中超时。避免把超时直接当作未执行而重试写入。
- [MCP transport](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/agent/src/mcp.ts#L251-L281) 把 stdio 的 stderr 单独接收，工具调用设十分钟超时并支持进度重置。候选：测试服务 stdout 只包含协议消息、stderr 不破坏协议，以及调用超时后结果未知的提示；具体时间应以本插件和宿主能力为准。

## 工具分类和知识源

- [默认配置](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/mcp-servers.ts#L23-L50) 对本地服务使用 full/stdio，2027 文档 RAG 必需，2026 与 EEC Pro 可选；远端知识源的可用性、版本匹配和数据外发须单独评估。候选：按用户 EPLAN 版本明确知识源、远端依赖和离线失败行为，不应直接强制启用同一个外部服务。
- [工具策略](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/tool-policy.ts#L179-L187) 将未知工具默认视为需询问的工程修改，[模式](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/modes.ts#L52-L60) 按任务筛选工具。候选：维护工具能力/风险清单，新增上游工具时检测漂移；依靠 Codex 现有审批机制，不复制桌面聊天模式。以只读、工程写入、任意脚本及外部导出分别验证。
- 上游为权限分类准备了测试（[tool-policy.test.ts](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/tool-policy.test.ts)），为运行时选择准备了测试（[runtime.test.ts](https://github.com/Canary-ECAD/bochica/blob/e2002146b516b1d805109aedda1b0bbb55c23f52/packages/eplan/src/runtime.test.ts)）；这些是测试代码存在的证据，并非本次测试通过的证据。

## 恢复边界

工程写入前备份与恢复流程值得评估，但必须实测 EPLAN 工程备份、恢复路径及失败处理。普通文件撤销不能证明能够回滚 EPLAN 工程；未验证情况下不应作此承诺。
