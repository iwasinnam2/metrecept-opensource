# cursor-agent-with-web

**Compliant fetch for agents** — clone this, set one key, Cursor can pull public docs into context.

No sales call. Steal the skeleton.

## Clone → set key → fetch

```bash
git clone https://github.com/iwasinnam2/withohm-open.git
cd withohm-open/templates/cursor-agent-with-web
```

1. Get a free Intermediate seat (card on file, $0 membership): https://metrecept.co.uk/billing/intermediate
   Or open the one-liner install: https://metrecept.co.uk/i
2. Copy `.cursor/mcp.json.example` → your Cursor MCP config (or merge into project `.cursor/mcp.json`).
3. Set `OHM_API_KEY` to your `sk-at-…` key. Optional: `OHM_UPSTREAM_KEY` for BYOK model calls.
4. In Cursor chat: ask the agent to fetch a public docs URL.

Paste this to a teammate:

```text
Add Metrecept MCP from https://metrecept.co.uk/i
```

## What’s inside

| Path | Role |
|------|------|
| `.cursor/mcp.json.example` | Metrecept MCP (`ohm_fetch_web`, `ohm_chat`, `ohm_usage`) |
| `.cursor/skills/ohm-fetch-web/SKILL.md` | Skill: compliant fetch for agents |
| `AGENTS.md` | One-screen agent instructions |

## Show your savings

Once cache hits accrue, ask the agent for `ohm_receipt` — it mints a public
savings receipt and returns badge markdown like:

```markdown
[![Metrecept savings](https://img.shields.io/endpoint?url=https%3A%2F%2Fapi.metrecept.co.uk%2Fv1%2Fpublic%2Freceipts%2F<token>%2Fbadge)](https://metrecept.co.uk/r/<token>)
```

Paste it here (or in any repo on the pipe).

Powered by [Metrecept](https://metrecept.co.uk) — pipe rent, not token wholesale. BYOK.
