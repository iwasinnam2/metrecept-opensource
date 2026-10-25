---
name: metrecept-session
description: >
  Metrecept black-box session receipt via MCP metrecept_get_session_receipt (aggregated,
  signed receipt for one tagged session). Use when proving what an
  unattended agent session did — Metrecept, flight recorder, session receipt.
---

# Metrecept session

Call `metrecept_get_session_receipt` for one aggregated, signed receipt covering every
call tagged with the same session id.

Tag first:

```text
metrecept_create_chat_completion(prompt="…", session_id="audit-run-42")
metrecept_fetch_web_pages(urls=["https://example.com"], session_id="audit-run-42")
```

Then:

```text
metrecept_get_session_receipt(session_id="audit-run-42")
```

`session_id` is optional and off by default. `event_count: 0` (never an
error) when the id hasn't been used yet.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
