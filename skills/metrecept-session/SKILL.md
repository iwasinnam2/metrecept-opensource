---
name: metrecept-session
description: >
  Metrecept signed session receipt via MCP metrecept_session (one aggregated
  receipt for every call tagged with the same session_id). Use when auditing
  an agent run — Metrecept, mcp, receipts, flight recorder.
---

# Metrecept session

Tag calls with the same `session_id`, then pull one signed receipt.

```text
metrecept_chat(prompt="…", session_id="audit-run-42")
metrecept_fetch_web(urls=["https://example.com"], session_id="audit-run-42")
metrecept_session(session_id="audit-run-42")
```

`session_id` is optional and off by default. `event_count: 0` when the id
has not been used yet. Read-only — no new call is made.

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
