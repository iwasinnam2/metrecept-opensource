---
name: metrecept-fetch-web
description: >
  Compliant fetch for agents via Metrecept MCP metrecept_fetch_web_pages (markdown or JSON).
  Use when the agent needs public URL / docs context without hand-browsing.
---

# Compliant fetch for agents

Call `metrecept_fetch_web_pages` for purpose-bound public pages:

```text
metrecept_fetch_web_pages(
  urls=["https://docs.example.com/guide"],
  purpose="public_web_retrieval",
  format="markdown"
)
```

Requires Metrecept MCP (`METRECEPT_API_KEY`). Install: https://metrecept.co.uk/i
