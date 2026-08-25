---
name: metrecept-chat
description: >
  Chat through Metrecept via MCP metrecept_chat (OpenAI-compatible ingress +
  exact-match Redis replay). Use for BYOK model calls, prompt replay, or chat
  with optional compliant fetch_urls — Metrecept, mcp, prompt-cache, BYOK.
---

# Metrecept chat

Call `metrecept_chat` for OpenAI-compatible chat through the Metrecept pipe.
Identical canonical requests HIT; unique turns MISS.

## Call

```text
metrecept_chat(
  prompt="…",
  model="mock",
  fetch_urls=None,
  purpose="public_web_retrieval",
  upstream_api_key="",
  session_id=""
)
```

- `session_id` is optional. Pass the same id on every call in one run, then
  pull a signed receipt with `metrecept_session`.
- For gpt/claude models, set `METRECEPT_UPSTREAM_KEY` or pass `upstream_api_key`.
- For scrape-only (no chat), use `metrecept_fetch_web`.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `sk-metre-…`).
Docs: https://metrecept.co.uk/docs/cursor
