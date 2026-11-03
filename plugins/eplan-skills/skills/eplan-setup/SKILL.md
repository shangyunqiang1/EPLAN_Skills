---
name: eplan-setup
description: Set up and troubleshoot the bundled local EPLAN MCP server on Windows, including Python dependencies, EPLAN Remote Client access and optional symbol search.
---

# 设置 EPLAN Skills

1. 确认当前系统为 Windows、已安装 64 位 Python 3.10 或更新版本和 EPLAN Electric P8，并核对 EPLAN 的版本及授权。文档检索可以独立使用；本地 MCP 操作需要运行在 EPLAN 所在电脑。
2. 从本技能的 `SKILL.md` 所在目录向上两级定位插件根目录，运行其中的 `scripts/setup.ps1`。例如，源码检出在仓库根目录时运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\plugins\eplan-skills\scripts\setup.ps1
   ```

   安装到插件缓存后，使用缓存中插件根目录下的 `scripts/setup.ps1` 的实际路径。脚本创建独立 Python 环境并安装依赖；要启用可选符号检索依赖，增加 `-IncludeSymbolSearch` 参数。
3. 在 EPLAN 的工作站设置中启用 Remote Client 远程访问，启动 EPLAN，然后重启插件或新建会话。先调用 `eplan_versions`，再按需调用 `eplan_connect` 和 `eplan_status` 检查连接；不要据此声称项目编辑或生产流程已验证。
4. 默认数据目录为 `%LOCALAPPDATA%\EPLAN_Skills`，可在运行安装脚本和启动插件前设置 `EPLAN_SKILLS_DATA_DIR`。非默认 EPLAN 安装目录可设置 `EPLAN_PLATFORM_ROOT`。`EPLAN_MCP_MODE=discovery` 会缩减首批暴露的工具，默认是 `full`。可选符号检索设置 `EPLAN_SKILLS_SYMBOL_SEARCH=1`，并先安装对应依赖。

文档检索将查询文本发送到 Canary E-cad 托管的服务。符号检索会在本地生成图像向量并发送到远端；使用前确认所发送内容符合用户的要求。版本、端口及授权以实际 EPLAN 安装为准。
