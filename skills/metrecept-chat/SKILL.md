---
name: metrecept-chat
description: >
  Chat through Metrecept via MCP metrecept_chat (OpenAI-compatible ingress +
  Redis exact-replay). Use for receipted model calls, BYOK, or chat with
  optional compliant fetch_urls — Metrecept, receipts, prompt-cache, BYOK.
---

# Metrecept chat

Call `metrecept_chat` for OpenAI-compatible chat through the pipe (Redis
cache on identical prompts; signed receipt on HIT). `ohm_chat` is the
same handler.

```text
metrecept_chat(
  prompt="…",
  model="mock",
  fetch_urls=None,              # or ["https://example.com"]
  purpose="public_web_retrieval",
  upstream_api_key="",          # BYOK override; else OHM_UPSTREAM_KEY
  session_id=""                 # Black-box flight-recorder tag
)
```

For gpt/claude models, set `OHM_UPSTREAM_KEY` or pass `upstream_api_key`.
Pass the same `session_id` across chat / fetch / API-call tools in one
unattended session, then pull the aggregated receipt with
`metrecept_session`.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`). Stdio command is
`ohm-mcp` from `pip install withohm-mcp`. Docs: https://metrecept.co.uk/docs/cursor
