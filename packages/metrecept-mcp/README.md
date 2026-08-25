# metrecept-mcp

Slim MCP server for [Metrecept](https://metrecept.co.uk): exact-match prompt
replay, multi-provider model routing (BYOK), and compliant public-web fetch
as Cursor tools — without installing the full gateway stack. Runs over
stdio (default) or as a stateless remote streamable-HTTP server.

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
        "METRECEPT_API_KEY": "sk-metre-YOUR_ISSUED_KEY",
        "METRECEPT_UPSTREAM_KEY": "sk-proj-optional-byok-key",
        "METRECEPT_BASE_URL": "https://api.metrecept.co.uk/v1"
      }
    }
  }
}
```

Hosted streamable HTTP (no local install): `https://api.metrecept.co.uk/mcp`
with `Authorization: Bearer sk-metre-…`. Stdio remains the
[metrecept.co.uk/i](https://metrecept.co.uk/i) one-click default.

Get a key from the $0 Intermediate seat at
[metrecept.co.uk/billing/intermediate](https://metrecept.co.uk/billing/intermediate).

## Tools

- `metrecept_chat` — chat through the pipe; identical prompts replay from Redis cache.
- `metrecept_fetch_web` — compliant public URL fetch (robots-gated, PII-redacted, metered).
- `metrecept_usage` — usage snapshot: cache hit ratio, fetches, estimated pipe rent.
- `metrecept_models` — model ids the pipe routes to, including BYOK upstreams.
- `metrecept_cache_trees` — list the tenant's cache-tree inventory (named exact-replay namespaces).
- `metrecept_cache_inventory` — list cached entries in a tree: digest, model, TTL, size (metadata only).
- `metrecept_savings` — cache savings snapshot: replayed prompts, estimated spend avoided.
- `metrecept_receipt` — mint a public savings receipt (`/r/…`) from the savings snapshot.
- `metrecept_providers` — upstream provider and failover status.
- `metrecept_policy` — compliance policy: allowed web-fetch purposes and limits.
- `metrecept_register_api_service` / `metrecept_api_services` / `metrecept_api_call` — receipted API passthrough.
- `metrecept_session` — signed flight-recorder receipt for one tagged session.

## Remote (stateless streamable HTTP)

```bash
METRECEPT_MCP_TRANSPORT=http metrecept-mcp   # or: metrecept-mcp-http — serves POST /mcp on :8091
```

Production hosted endpoint: `https://api.metrecept.co.uk/mcp`.

Auth is per-request: clients send `Authorization: Bearer sk-metre-*` (and
optional `X-Metrecept-Upstream-Key`) on the MCP HTTP request;
`METRECEPT_API_KEY` env is the stdio/local fallback.

## Env

| Variable | Required | Purpose |
|---|---|---|
| `METRECEPT_API_KEY` | stdio: yes | Your Metrecept tenant key (`sk-metre-…`); HTTP mode can use per-request `Authorization` instead |
| `METRECEPT_BASE_URL` | no | Defaults to `https://api.metrecept.co.uk/v1` |
| `METRECEPT_UPSTREAM_KEY` | no | BYOK provider key for cache-miss model calls |

MIT licensed. The hosted service is commercial — see
[Pricing](https://metrecept.co.uk/pricing) and
[Terms](https://metrecept.co.uk/docs/terms).

Note for maintainers: `src/metrecept_mcp/__init__.py` in the monorepo root is the
source of truth; run `scripts/sync_metrecept_mcp.ps1` before building this package.
