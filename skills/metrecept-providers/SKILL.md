---
name: metrecept-providers
description: >
  Metrecept upstream provider and failover status via MCP metrecept_providers.
  Use when a model call fails or routing looks off — Metrecept, mcp, providers.
---

# Metrecept providers

Call `metrecept_providers()` for upstream health and failover state from
`GET /v1/providers`. Check this first when `metrecept_chat` errors on a
non-mock model.

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
