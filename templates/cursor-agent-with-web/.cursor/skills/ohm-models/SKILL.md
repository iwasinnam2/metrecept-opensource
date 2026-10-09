---
name: ohm-models
description: >
  List model ids the withOhm pipe routes to via MCP ohm_models (BYOK upstreams
  included). Use when picking a model for ohm_chat or checking what the pipe
  can reach — withOhm, ohm, models, routing.
---

# Ohm models

Call the Ohm MCP tool `ohm_models` to list the model ids the pipe routes to.

## Call

```text
ohm_models()
```

Returns model ids from `GET /v1/models` (mock works without keys; gpt/claude
need BYOK — your own provider key).

Requires Ohm MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
