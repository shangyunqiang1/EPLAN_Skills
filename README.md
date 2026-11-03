# EPLAN_Skills

将 [Canary E-cad](https://github.com/Canary-ECAD) 的 EPLAN 工具和知识整合为一个插件：在 Windows 本机通过 MCP 操作 EPLAN Electric P8，按需检索 P8 与 EEC Pro 文档，并使用 P8、EEC Pro 开发技能。

## 包含内容

- **本地 EPLAN MCP**：连接运行中的 EPLAN，提供项目、页面、导入导出、脚本、数据模型等工具。
- **文档 MCP**：P8 2026 语义搜索、P8 2027 关键词搜索与 EEC Pro 文档搜索，连接 Canary E-cad 托管的服务。
- **四个技能**：EPLAN 路由、P8 脚本/API/Remote Client、EEC Pro 开发和本地安装配置。

本项目面向 Windows 电脑，运行 MCP 需要 64 位 Python 3.11 或更新版本并安装依赖。本地工程操作还需要 EPLAN、对应功能授权和 Remote Client；查阅技能或文档不要求运行 EPLAN。

## 安装

在 [Codex](https://developers.openai.com/codex) 中添加此仓库的插件市场并安装：

```powershell
codex plugin marketplace add shangyunqiang1/EPLAN_Skills
codex plugin add eplan-skills@eplan-skills
```

Claude Code 用户可在会话中执行：

```text
/plugin marketplace add shangyunqiang1/EPLAN_Skills
/plugin install eplan-skills@eplan-skills
```

本地 MCP 使用前需安装 Python 依赖。在 Windows 克隆本仓库并在仓库根目录运行：

```powershell
git clone https://github.com/shangyunqiang1/EPLAN_Skills.git
cd EPLAN_Skills
powershell -ExecutionPolicy Bypass -File .\plugins\eplan-skills\scripts\setup.ps1
```

也可以运行已安装插件目录中的 `scripts/setup.ps1`，或使用 `eplan-setup` 技能。v0.2.0 起，按完整依赖锁创建 `%LOCALAPPDATA%\EPLAN_Skills\environments\` 下的独立环境，核对 wheel 哈希及健康状态后才启用。旧环境与 v0.1.x 的 `venv` 会保留。设置 `EPLAN_SKILLS_DATA_DIR` 可改变数据目录；安装与启动时应保持一致。升级后重新执行一次 setup，再重启插件或新建会话。

在 EPLAN 的 **文件 → 设置 → 工作站 → 接口 → 远程访问** 中启用 Remote Client 远程访问，然后启动 EPLAN。可以先让助手列出已安装版本、连接 EPLAN 并读取连接状态。修改项目前请确认目标项目和保存状态；先用测试项目验证工作流。更多配置和排错见 [使用说明](docs/usage.md)。

## 中文诊断与文档开关

- `eplan_doctor`：只读汇总 Python/CLR、EPLAN 版本、进程、实际监听地址、代理例外及连接状态，不会自动连接。
- `eplan_connection_configure`：用户明确要求保存连接时，先隔离验证连接与心跳，成功后保存本机配置；失败保留旧配置。
- `eplan_documentation_configure`：选择 `all`、`p8`、`p8-keyword`、`eec` 或 `offline`，重启 MCP 刷新工具列表。默认全部启用；禁用服务不连接远端，远端故障不终止本机 MCP。
- 工具保留 `full` 默认，并提供只读、工程修改、任意执行、文件操作等分类提示。授权仍由宿主处理。

运行管理参考了 [Bochica](https://github.com/Canary-ECAD/bochica)；聊天界面、模型和会话管理继续由 Codex / Claude Code 提供。

## 来源与许可

本插件整合并改编自 [Canary-ECAD/eplan-mcp](https://github.com/Canary-ECAD/eplan-mcp)、[eplan-scripting-skill](https://github.com/Canary-ECAD/eplan-scripting-skill)、[eec-pro-skill](https://github.com/Canary-ECAD/eec-pro-skill)；文档服务由 [eplan-cloudflare-rags](https://github.com/Canary-ECAD/eplan-cloudflare-rags) 提供。上游代码和技能采用 MIT 许可证，版权属于 Christian D. Lopez；具体版本、改动及完整许可见 [第三方来源说明](THIRD_PARTY_NOTICES.md)。

插件仅连接上游文档检索服务，未附带 EPLAN 本机 DLL 或专有文档索引。Bochica 和 ecad-view 为上游独立应用，不包含在此插件中。EPLAN 是其各自权利人的商标；本项目与 EPLAN 公司无关联，也未获其认可或支持。

文档检索会将查询发送给第三方服务，可选的符号搜索会发送图像向量。使用前请阅读[数据与隐私说明](docs/privacy.md)。

## 下载与开发

可从 [GitHub Releases](https://github.com/shangyunqiang1/EPLAN_Skills/releases) 下载独立插件 ZIP 和 SHA256 校验文件。ZIP 内为单个插件，不含 marketplace；从仓库安装则使用前述 marketplace 命令。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r plugins/eplan-skills/requirements/runtime.lock
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/validate.py
.\.venv\Scripts\python.exe -m pytest tests plugins/eplan-skills/vendor/eplan-mcp/eplan-p8-mcp-server/tests -m "not live" -q
.\.venv\Scripts\python.exe scripts/package.py
```

验证记录见 [docs/validation.md](docs/validation.md)。更新上游前先审查提交与许可证，按 [来源清单](THIRD_PARTY_NOTICES.md) 更新对应文件，随后执行 `python scripts/record_upstream.py` 重建来源映射并检查差异；该脚本只读取 `.upstream/` 中已检出的仓库，不自动下载或覆盖源码。更新后同步版本及来源说明，重新验证和打包。
