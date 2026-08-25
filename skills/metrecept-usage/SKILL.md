---
name: metrecept-usage
description: >
  Metrecept usage snapshot via MCP metrecept_usage (cache hits, fetches, meters).
  Use when checking pipe rent, hit ratio, or fetch caps — Metrecept, mcp, usage.
---

# Metrecept usage

Call `metrecept_usage()` for a usage snapshot from `GET /v1/usage`
(hit ratio, fetch counts, estimated pipe rent).

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
