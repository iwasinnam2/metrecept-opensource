# Metrecept MCP server

MCP server for [Metrecept](https://metrecept.co.uk), which issues a signed
Ed25519 receipt (compact JWS) for each call an autonomous AI agent makes:
model chat, compliant public-web fetch, and third-party API calls. Runs over
stdio (default) or as a stateless remote streamable-HTTP server. It is a thin
MIT client: the hosted gateway at `https://api.metrecept.co.uk` is
proprietary, and every real call needs a Metrecept API key.

Installed from PyPI as `metrecept-mcp`; the command is `metrecept-mcp` and
the module is `metrecept_mcp`.

> **Ohm is a sibling brand name of Metrecept; some identifiers keep the ohm prefix for compatibility.** These are: the `ohm-mcp` and `ohm-mcp-http` commands and the `ohm_mcp` Python import name (aliases of `metrecept-mcp`, `metrecept-mcp-http` and `metrecept_mcp`); `OHM_*` environment variables (`OHM_API_KEY`, `OHM_BASE_URL`, `OHM_UPSTREAM_KEY`, `OHM_SERVICE_KEY`, `OHM_MCP_*`), read by the MCP server only when the matching `METRECEPT_*` variable is unset; the `api.withohm.dev` and `mcp.withohm.dev` hostnames in the MCP server's host allowlist; and the `X-Ohm-*` headers the hosted gateway still accepts and emits next to their `X-Metrecept-*` equivalents. This client sends only `X-Metrecept-*` headers. Use the Metrecept names in new setups.

## Install

```bash
pip install metrecept-mcp
```

## Cursor attach (stdio)

```json
{
  "mcpServers": {
    "metrecept": {
      "command": "metrecept-mcp",
      "env": {
        "METRECEPT_API_KEY": "sk-at-YOUR_ISSUED_KEY",
        "METRECEPT_UPSTREAM_KEY": "sk-proj-optional-byok-key",
        "METRECEPT_BASE_URL": "https://api.metrecept.co.uk/v1"
      }
    }
  }
}
```

Hosted streamable HTTP (no local install): `https://api.metrecept.co.uk/mcp`
with `Authorization: Bearer sk-at-…`. Stdio remains the
[metrecept.co.uk/i](https://metrecept.co.uk/i) one-click default.

Get a key from the $0 Intermediate seat at
[metrecept.co.uk/billing/intermediate](https://metrecept.co.uk/billing/intermediate).

## Tools

18 tools. All require a Metrecept API key and are scoped to
that key's tenant.

| Tool | What it does |
|---|---|
| `metrecept_create_chat_completion` | One chat call through the gateway (OpenAI-compatible); metered and receipted; exact repeats served from cache; optional web context. |
| `metrecept_fetch_web_pages` | Compliant public-web fetch (purpose-bound, robots-aware, PII-redacted); metered and receipted. |
| `metrecept_call_api` | Receipted, metered GET to a registered third-party API; the vendor key is forwarded, never stored. |
| `metrecept_register_api_service` | Register or update a third-party API (base URL, path prefix, auth header name) for `metrecept_call_api`. |
| `metrecept_list_api_services` | List registered third-party API services. |
| `metrecept_unregister_api_service` | Unregister a third-party API service (destructive; not billed). |
| `metrecept_get_session_receipt` | One signed receipt for every call tagged with a session id, plus a `verify_url` anyone can open. |
| `metrecept_get_usage` | Current usage meters, plan and billing status. |
| `metrecept_get_usage_history` | Per-day usage meter series over the last 1-90 days (default 30). |
| `metrecept_get_savings` | Estimated upstream spend avoided by cache hits versus what was billed. |
| `metrecept_publish_savings_receipt` | Publish a public, signed savings snapshot page and badge (90 days). |
| `metrecept_list_models` | Model ids the gateway can route to (BYOK). |
| `metrecept_list_providers` | Which upstream vendors are configured and ready. |
| `metrecept_get_fetch_policy` | Web-fetch compliance policy: allowed purposes and limits. |
| `metrecept_list_cache_trees` | List the tenant's named cache namespaces. |
| `metrecept_list_cache_entries` | Metadata of cached entries in one namespace (never content). |
| `metrecept_evict_cache_entry` | Evict one cached entry by request digest (destructive; not billed). |
| `metrecept_delete_cache_tree` | Delete a non-main cache namespace (refuses `main`; destructive; not billed). |

## Remote (stateless streamable HTTP)

```bash
METRECEPT_MCP_TRANSPORT=http metrecept-mcp   # or: metrecept-mcp-http — serves POST /mcp on :8091
```

Production hosted endpoint: `https://api.metrecept.co.uk/mcp`.

Auth is per-request: clients send `Authorization: Bearer sk-at-*` (and
optional `X-Metrecept-Upstream-Key`) on the MCP HTTP request; `METRECEPT_API_KEY` env is
the stdio/local fallback.

## Env

| Variable | Required | Purpose |
|---|---|---|
| `METRECEPT_API_KEY` | stdio: yes | Your Metrecept tenant key (`sk-at-…`); HTTP mode can use per-request `Authorization` instead |
| `METRECEPT_BASE_URL` | no | Defaults to `https://api.metrecept.co.uk/v1` |
| `METRECEPT_UPSTREAM_KEY` | no | BYOK provider key for non-mock model calls |

MIT licensed. The hosted service is commercial — see
[Pricing](https://metrecept.co.uk/pricing) and
[Terms](https://metrecept.co.uk/docs/terms).

Note for maintainers: this package is mirrored from the private Metrecept
monorepo, which is the source of truth.
