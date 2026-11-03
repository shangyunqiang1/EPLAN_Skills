# Changelog

## 0.1.2 — 2026-11-03

- 为插件简介、详细说明和推荐提示词补充中文，保留英文项目名和英文介绍。
- 同步 Codex、Claude Code 兼容清单、插件市场条目与 GitHub 仓库说明。

## 0.1.1 — 2026-11-03

- 实机验证后修复 EPLAN 原生 .NET Console 输出混入 stdio MCP 协议的问题。
- 在 MCP 进程内为本机地址设置 gRPC 代理例外，避免本地 EPLAN 连接经过 HTTP 代理；保留现有例外和 HTTP 配置。
- 补充真实 CLR 输出隔离测试与本机监听地址连接说明。

## 0.1.0 — 2026-11-03

- 整合 Canary-ECAD 的本地 EPLAN MCP、P8 与 EEC Pro 技能，以及三个托管文档 MCP。
- 增加统一路由、中文安装配置技能和使用文档。
- 提供 Agent Plugins 1.0、Codex 和 Claude Code 清单及 marketplace。
- 增加外部 venv 安装、stdio 启动器、离线验证、CI 和独立 ZIP 打包。
- 保留原 MIT 版权、固定上游提交和逐文件来源哈希。
