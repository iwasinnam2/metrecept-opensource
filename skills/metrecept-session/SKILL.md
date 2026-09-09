---
name: metrecept-session
description: >
  Metrecept black-box session receipt via MCP metrecept_session (aggregated,
  signed receipt for one tagged session). Use when proving what an
  unattended agent session did — Metrecept, flight recorder, session receipt.
---

# Metrecept session

Call `metrecept_session` for one aggregated, signed receipt covering every
call tagged with the same session id. `ohm_session` is the same handler.

Tag first:

```text
metrecept_chat(prompt="…", session_id="audit-run-42")
metrecept_fetch_web(urls=["https://example.com"], session_id="audit-run-42")
```

Then:

```text
metrecept_session(session_id="audit-run-42")
```

`session_id` is optional and off by default. `event_count: 0` (never an
error) when the id hasn't been used yet.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`).
