---
name: ohm-models
description: >
  List model ids the Metrecept pipe routes to via MCP ohm_models (BYOK upstreams
  included). Use when picking a model for ohm_chat or checking what the pipe
  can reach — Metrecept, ohm, models, routing.
---

# Metrecept models

Call the Metrecept MCP tool `ohm_models` to list the model ids the pipe routes to.

## Call

```text
ohm_models()
```

Returns model ids from `GET /v1/models` (mock works without keys; gpt/claude
need BYOK — your own provider key).

Requires Metrecept MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
