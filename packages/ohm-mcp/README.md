# withohm-mcp

Slim MCP server for [Metrecept](https://metrecept.co.uk): prompt cache
replay, multi-provider model routing (BYOK), and compliant public-web fetch
as Cursor tools — without installing the full gateway stack. Runs over
stdio (default) or as a stateless remote streamable-HTTP server.

Package name `withohm-mcp` is a legacy id until rename. Product is Metrecept.

## Install

The distribution name is `withohm-mcp`. It is **not on PyPI yet** (`ohm-mcp`
on PyPI is an unrelated third-party package). Install from GitHub:

```bash
pip install "git+https://github.com/iwasinnam2/metrecept-opensource.git#subdirectory=packages/ohm-mcp"
```

No local install: attach the hosted server at
`https://api.metrecept.co.uk/mcp` with `Authorization: Bearer sk-at-…`.

## Cursor attach (stdio)

```json
{
  "mcpServers": {
    "metrecept": {
      "command": "ohm-mcp",
      "env": {
        "OHM_API_KEY": "sk-at-YOUR_ISSUED_KEY",
        "OHM_UPSTREAM_KEY": "sk-proj-optional-byok-key",
        "OHM_BASE_URL": "https://api.metrecept.co.uk/v1"
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

- `ohm_chat` — chat through the pipe; identical prompts replay from Redis cache.
- `ohm_fetch_web` — compliant public URL fetch (robots-gated, PII-redacted, metered).
- `ohm_usage` — usage snapshot: cache hit ratio, fetches, estimated pipe rent.
- `ohm_models` — model ids the pipe routes to, including BYOK upstreams.
- `ohm_cache_trees` — list the tenant's cache-tree inventory (named exact-replay namespaces).
- `ohm_cache_inventory` — list cached entries in a tree: digest, model, TTL, size (metadata only).
- `ohm_savings` — cache savings snapshot: replayed prompts, estimated spend avoided.
- `ohm_receipt` — mint a public savings receipt (`/r/…`) from the savings snapshot.
- `ohm_providers` — upstream provider and failover status.
- `ohm_policy` — compliance policy: allowed web-fetch purposes and limits.

`metrecept_*` names alias the same handlers.

## Remote (stateless streamable HTTP)

```bash
OHM_MCP_TRANSPORT=http ohm-mcp   # or: ohm-mcp-http — serves POST /mcp on :8091
```

Production hosted endpoint: `https://api.metrecept.co.uk/mcp`.

Auth is per-request: clients send `Authorization: Bearer sk-at-*` (and
optional `X-Ohm-Upstream-Key`) on the MCP HTTP request; `OHM_API_KEY` env is
the stdio/local fallback.

## Env

| Variable | Required | Purpose |
|---|---|---|
| `OHM_API_KEY` | stdio: yes | Your Metrecept tenant key (`sk-at-…`); HTTP mode can use per-request `Authorization` instead |
| `OHM_BASE_URL` | no | Defaults to `https://api.metrecept.co.uk/v1` |
| `OHM_UPSTREAM_KEY` | no | BYOK provider key for cache-miss model calls |

MIT licensed. The hosted service is commercial — see
[Pricing](https://metrecept.co.uk/pricing) and
[Terms](https://metrecept.co.uk/docs/terms).

Note for maintainers: `src/ohm_mcp/__init__.py` in the monorepo root is the
source of truth; run `scripts/sync_ohm_mcp.ps1` before building this package.
