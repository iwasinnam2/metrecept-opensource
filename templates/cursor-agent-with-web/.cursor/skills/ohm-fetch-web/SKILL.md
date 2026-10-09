---
name: ohm-fetch-web
description: >
  Compliant fetch for agents via withOhm MCP ohm_fetch_web (markdown or JSON).
  Use when the agent needs public URL / docs context without hand-browsing.
---

# Compliant fetch for agents

Call `ohm_fetch_web` for purpose-bound public pages:

```text
ohm_fetch_web(
  urls=["https://docs.example.com/guide"],
  purpose="public_web_retrieval",
  format="markdown"
)
```

Requires Ohm MCP (`OHM_API_KEY`). Install: https://www.withohm.dev/i
