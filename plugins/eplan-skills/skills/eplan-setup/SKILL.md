---
name: eplan-setup
description: Set up and troubleshoot the bundled local EPLAN MCP server on Windows, including Python dependencies, EPLAN Remote Client access and optional symbol search.
---

# 设置 EPLAN Skills

1. 确认 Windows 和 64 位 Python 3.11 或更新版本，并核对 EPLAN 的版本及授权。文档网关也需安装 Python 依赖，但不要求运行 EPLAN。
2. 从本技能的 `SKILL.md` 所在目录向上两级定位插件根目录，运行其中的 `scripts/setup.ps1`。例如，源码检出在仓库根目录时运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\plugins\eplan-skills\scripts\setup.ps1
   ```

   安装到插件缓存后，使用缓存中插件根目录下的 `scripts/setup.ps1` 的实际路径。脚本创建独立 Python 环境并安装依赖；要启用可选符号检索依赖，增加 `-IncludeSymbolSearch` 参数。
3. 启用 EPLAN Remote Client，重启插件后先调用只读 `eplan_doctor`，按实际监听地址调用 `eplan_connect` 并验证 `eplan_ping`。用户明确要求保存连接时才用 `eplan_connection_configure`；成功后保存、失败保留旧设置，重启 MCP 生效。不要自动重放超时的工程修改，也不要据连接成功声称工程写入已验证。
4. 默认数据目录为 `%LOCALAPPDATA%\EPLAN_Skills`，可设置 `EPLAN_SKILLS_DATA_DIR`。固定依赖安装到独立 `environments/`，通过哈希和健康检查后启用，旧环境保留。非默认安装可设置 `EPLAN_PLATFORM_ROOT`。工具模式默认 `full`，可设 `EPLAN_MCP_MODE=discovery`。
5. 用 `eplan_documentation_configure` 选择 `all`、`p8`、`p8-keyword`、`eec` 或 `offline`，重启 MCP 刷新列表。默认全部启用；禁用服务不请求远端。可选符号搜索执行 setup 的 `-IncludeSymbolSearch` 并设置 `EPLAN_SKILLS_SYMBOL_SEARCH=1`，使用独立锁定依赖环境。

文档检索将查询文本发送到 Canary E-cad 托管的服务。符号检索会在本地生成图像向量并发送到远端；使用前确认所发送内容符合用户的要求。版本、端口及授权以实际 EPLAN 安装为准。
