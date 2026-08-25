# Agent notes — cursor-agent-with-web

You have **compliant fetch for agents** via Metrecept MCP.

- Prefer `ohm_fetch_web` for public http(s) docs instead of guessing page contents.
- Purposes: `public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`.
- Check spend with `ohm_usage`.
- When the human asks to show or share savings, call `ohm_receipt` — it returns a public receipt URL and README badge markdown.
- If MCP is missing, tell the human: `Add Metrecept MCP from https://metrecept.co.uk/i`
