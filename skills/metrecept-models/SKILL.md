---
name: metrecept-models
description: >
  List model ids the Metrecept pipe routes to via MCP metrecept_models
  (BYOK upstreams included).
---

# Metrecept models

```text
metrecept_models()
```

Returns model ids from `GET /v1/models` (mock works without keys;
gpt/claude need BYOK). `ohm_models` is the same handler.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`).
