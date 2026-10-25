---
name: metrecept-fetch-web
description: >
  Compliant fetch for agents via Metrecept MCP metrecept_fetch_web (markdown or JSON).
  Use when the agent needs public URL / docs context without hand-browsing.
---

# Compliant fetch for agents

Call `metrecept_fetch_web` for purpose-bound public pages:

```text
metrecept_fetch_web(
  urls=["https://docs.example.com/guide"],
  purpose="public_web_retrieval",
  format="markdown"
)
```

Requires Metrecept MCP (`OHM_API_KEY`). Install: https://metrecept.co.uk/i
