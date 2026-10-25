---
name: metrecept-models
description: >
  List model ids the Metrecept gateway routes to via MCP metrecept_models (BYOK upstreams
  included). Use when picking a model for metrecept_chat or checking what the gateway
  can reach — Metrecept, models, routing.
---

# Metrecept models

Call the Metrecept MCP tool `metrecept_models` to list the model ids the gateway routes to.

## Call

```text
metrecept_models()
```

Returns model ids from `GET /v1/models` (mock works without keys; gpt/claude
need BYOK — your own provider key).

Requires Metrecept MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
