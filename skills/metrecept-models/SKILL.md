---
name: metrecept-models
description: >
  List model ids the Metrecept pipe routes to via MCP metrecept_models (BYOK
  upstreams included). Use when picking a model for metrecept_chat —
  Metrecept, mcp, models.
---

# Metrecept models

Call `metrecept_models()` for model ids from `GET /v1/models`.
`mock` works without keys; gpt/claude need BYOK (`METRECEPT_UPSTREAM_KEY`).

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
