# Metrecept MCP server

MCP server for [Metrecept](https://metrecept.co.uk), which issues a signed
Ed25519 receipt (compact JWS) for each call an autonomous AI agent makes:
model chat, compliant public-web fetch, and third-party API calls. Runs over
stdio (default) or as a stateless remote streamable-HTTP server. It is a thin
MIT client: the hosted gateway at `https://api.metrecept.co.uk` is
proprietary, and every real call needs a Metrecept API key.

Installed from PyPI as `metrecept-mcp`; the command is `metrecept-mcp` and
the module is `metrecept_mcp`.

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

23 tools in three toolsets. All require a Metrecept API key and are scoped to
that key's tenant.

MCP has no standard way to group tools yet, so this server uses an env var:
set `METRECEPT_TOOLSETS` to a comma list of `core`, `cache` and `receipts`
(default: all three) to expose only those groups. Every tool also carries its
group in `_meta["io.metrecept/toolset"]` and as a prefix on its title
(`Cache: Freeze cache tree`), so clients can sort or filter them.

```bash
METRECEPT_TOOLSETS=cache,receipts metrecept-mcp   # 11 tools, no chat/fetch/API
```

### Core (`core`, 12 tools)

| Tool | What it does |
|---|---|
| `metrecept_create_chat_completion` | One chat call through the gateway (OpenAI-compatible); metered and receipted; exact repeats served from cache; optional web context. |
| `metrecept_fetch_web_pages` | Compliant public-web fetch (purpose-bound, robots-aware, PII-redacted); metered and receipted. |
| `metrecept_call_api` | Receipted, metered GET to a registered third-party API; the vendor key is forwarded, never stored. |
| `metrecept_register_api_service` | Register or update a third-party API (base URL, path prefix, auth header name) for `metrecept_call_api`. |
| `metrecept_list_api_services` | List registered third-party API services. |
| `metrecept_unregister_api_service` | Unregister a third-party API service (destructive; not billed). |
| `metrecept_get_usage` | Current usage meters, plan and billing status. |
| `metrecept_get_usage_history` | Per-day usage meter series over the last 1-90 days (default 30). |
| `metrecept_get_savings` | Estimated upstream spend avoided by cache hits versus what was billed. |
| `metrecept_list_models` | Model ids the gateway can route to (BYOK). |
| `metrecept_list_providers` | Which upstream vendors are configured and ready. |
| `metrecept_get_fetch_policy` | Web-fetch compliance policy: allowed purposes and limits. |

### Cache (`cache`, 8 tools)

Cache trees are isolated exact-replay namespaces. Tree management, freeze,
archive and pre-warm are not billed.

| Tool | What it does |
|---|---|
| `metrecept_list_cache_trees` | List the tenant's cache trees with their status; archived trees only with `include_archived=true`. |
| `metrecept_list_cache_entries` | Metadata of cached entries in one tree (never content). |
| `metrecept_manage_cache_tree` | Create, fork or promote a cache tree (forks share parent entries copy-on-write; promote merges by reference; not billed). |
| `metrecept_evict_cache_entry` | Evict one cached entry by request digest (destructive; not billed). |
| `metrecept_delete_cache_tree` | Delete a non-main cache tree (refuses `main`; destructive; not billed). |
| `metrecept_freeze_cache_tree` | Freeze a tree (serves hits, stores nothing new) or unfreeze it with `frozen=false`; not billed, audit-logged. |
| `metrecept_archive_cache_tree` | Archive a tree (read-only and hidden from the default listing) or restore it with `archived=false`; `main` can't be archived; not billed, audit-logged. |
| `metrecept_prewarm_cache` | Refresh an about-to-expire Anthropic prompt-cache breakpoint for a session with a one-token call; unbilled by the gateway (`billed: false`). |

### Receipts (`receipts`, 3 tools)

Signed Ed25519 receipts (compact JWS) that anyone can verify in a browser at
`https://metrecept.co.uk/verify`.

| Tool | What it does |
|---|---|
| `metrecept_mint_receipt` | Mint one fresh signed receipt of a chosen kind (cache_miss, cache_hit, cache_bypass, finops, api_call, session, custody, statement, carve, savings, web_fetch) and return it with a `verify_url`. |
| `metrecept_get_session_receipt` | One signed receipt for every call tagged with a session id, plus a `verify_url` anyone can open. |
| `metrecept_publish_savings_receipt` | Publish a public, signed savings snapshot page and badge (90 days). |

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
| `METRECEPT_TOOLSETS` | no | Comma list of toolsets to expose: `core`, `cache`, `receipts` (default: all) |

MIT licensed. The hosted service is commercial — see
[Pricing](https://metrecept.co.uk/pricing) and
[Terms](https://metrecept.co.uk/docs/terms).

Note for maintainers: this package is mirrored from the private Metrecept
monorepo, which is the source of truth.
