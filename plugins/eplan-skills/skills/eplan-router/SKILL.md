---
name: eplan-router
description: Route EPLAN Electric P8 and EEC Pro requests to the bundled development skills and documentation MCPs. Use for EPLAN scripting, APIs, actions, Remote Client, macros, parts, EEC models, generation or when the product is unclear.
---

# EPLAN router

Derived from Canary E-cad's `eplan-scripting-skill` router. Identify the product and load the relevant bundled skill before working:

- **Electric P8:** read [eplan-scripting](../eplan-scripting/SKILL.md) for C# scripts, actions, API, Remote Client, parts, pages, macros, symbols and Cogineer.
- **EEC Pro:** read [eec-pro-development](../eec-pro-development/SKILL.md) for typicals, mechatronic models, formulas, configurations, EOX, Job Server and generation.
- **EEC Pro generation into P8:** read both skills. Use the EEC skill for the model and generation; use the P8 skill for macros, pages and API integration. A typical workbook inserted into P8 without EEC belongs to the P8 skill.
- **Plugin installation or setup:** read [eplan-setup](../eplan-setup/SKILL.md).

Choose the relevant reference listed in each skill. When diagnosing automation hangs or timeouts, start with the P8 `references/pitfalls.md`. Confirm API identifiers against the installed EPLAN version and its documentation; technical reflection does not establish licensing entitlement.

For documentation searches use the bundled MCP connections: `eplan-rag` for P8 2026 semantic search, `eplan-wiki-2027` for P8 2027 keyword search, and `eecpro-rag` for EEC Pro. They query third-party hosted services; send only information the user permits to leave the machine. When the local `eplan` server is connected, live introspection can help verify the actual installed version. Treat any action that modifies a project according to the user's instructions and preserve their existing work.
