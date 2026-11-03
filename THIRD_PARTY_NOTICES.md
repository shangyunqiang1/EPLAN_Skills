# 第三方来源 / Third-party notices

EPLAN_Skills 是由 shangyunqiang1 维护的社区整合插件。核心 EPLAN MCP 与领域技能来自 **[Canary E-cad / Canary-ECAD](https://github.com/Canary-ECAD)**，原作者 **Christian D. Lopez**。本仓库不将这些上游成果宣称为原创。

| 上游仓库 | 固定提交 | 本插件使用范围 |
| --- | --- | --- |
| [eplan-mcp](https://github.com/Canary-ECAD/eplan-mcp) | `896e2bf9217f3d9fb28c9f5c26cf00181f37cc73` | `vendor/eplan-mcp/`：P8 MCP、可选符号搜索扩展、上游测试和工具 |
| [eplan-scripting-skill](https://github.com/Canary-ECAD/eplan-scripting-skill) | `11da792a7bfc9d001c56b665941bfaa9e49cb8e2` | P8 skill 与 references；router 经整合适配 |
| [eec-pro-skill](https://github.com/Canary-ECAD/eec-pro-skill) | `2324e40db072621dd8cc14168406e013eecc055d` | EEC Pro skill 与 references |
| [eplan-cloudflare-rags](https://github.com/Canary-ECAD/eplan-cloudflare-rags) | `5fe2c52098b1f2844fb8124b71eb5137d19e7123` | 三个远端文档 MCP 端点配置；未复制其 Worker、索引或文档数据 |

以上四个仓库均为 **MIT**，`Copyright (c) 2025 Christian D. Lopez`。原始许可全文保留在插件 `licenses/` 内；MCP vendor 中也保留原 `LICENSE`。插件内 `upstream-lock.json` 记录提交、映射和逐文件 SHA256（文本换行先统一为 LF，以兼容 Windows Git 换行转换）：`upstreamSha256` 对应固定上游文件，`bundledSha256` 对应随包文件，两者不同表示本集成做过适配。

本集成新增：统一插件及 marketplace 清单、扁平 skill 布局、中文 setup/router、Windows 外部 venv 与 stdio 启动器、验证/打包脚本和 CI。v0.1.1 在上游 `eplan_connection.py` 的延迟 CLR 初始化之后将 .NET Console 输出转到 stderr，以保持 MCP stdout 纯净；其余 MCP 源码保持原样。技能中有关授权的表述改为遵循用户本机 EPLAN 许可，技术可访问性不代表授权。文件路径与跨 skill 引用按打包结构适配。

远端服务由上游运营，服务可用性、数据范围和运营策略由其维护者控制。本仓库没有迁移、托管或接管这些服务。符号搜索使用上游公开端点和可选 CLIP 依赖；模型及 Python 依赖有各自许可证，不包含在本仓库 MIT 授权范围内。

MIT 仅覆盖相应代码与作者可授权的技能内容，**不授予 EPLAN 软件、DLL、商标、专有文档、索引或项目数据的权利**。EPLAN 文档属于其权利人。未打包 EPLAN 安装文件、DLL、许可证、模型权重或文档数据库。Bochica 和 ecad-view 是独立应用，本插件仅提供来源链接，不打包它们。

EPLAN_Skills 与 Canary-ECAD 均非 EPLAN GmbH & Co. KG 官方产品；本插件也不是 Canary-ECAD 官方发行版。EPLAN 等商标归其各自所有人。
