---
name: metrecept-models
description: >
  List model ids the Metrecept gateway routes to via MCP metrecept_list_models
  (BYOK upstreams included).
---

# Metrecept models

```text
metrecept_list_models()
```

Returns model ids from `GET /v1/models` (mock works without keys;
gpt/claude need BYOK).

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
