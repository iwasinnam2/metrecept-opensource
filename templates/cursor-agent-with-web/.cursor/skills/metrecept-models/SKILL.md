---
name: metrecept-models
description: >
  List model ids the Metrecept gateway routes to via MCP metrecept_list_models (BYOK upstreams
  included). Use when picking a model for metrecept_create_chat_completion or checking what the gateway
  can reach — Metrecept, models, routing.
---

# Metrecept models

Call the Metrecept MCP tool `metrecept_list_models` to list the model ids the gateway routes to.

## Call

```text
metrecept_list_models()
```

Returns model ids from `GET /v1/models` (mock works without keys; gpt/claude
need BYOK — your own provider key).

Requires Metrecept MCP attached (`METRECEPT_BASE_URL`, `METRECEPT_API_KEY`). See `docs/CURSOR.md`.
