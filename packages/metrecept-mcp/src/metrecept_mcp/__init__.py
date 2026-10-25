"""Metrecept MCP server — thin MIT client for the hosted Metrecept gateway.

Every real call is authenticated with a Metrecept API key and returns or
records a signed Ed25519 receipt (compact JWS) that anyone can verify.

Transports:
  * stdio (default) — local Cursor attach; auth via METRECEPT_API_KEY env.
  * streamable HTTP (stateless) — remote attach per MCP 2026-07-28 stateless
    core; auth via the incoming `Authorization: Bearer sk-at-*` header
    (per-request pass-through), falling back to METRECEPT_API_KEY env.

Run remote: `METRECEPT_MCP_TRANSPORT=http metrecept-mcp` (or `metrecept-mcp-http`).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

try:
    from mcp.server import MCPServer
    from mcp.server.mcpserver import Context
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "MCP support missing: pip install metrecept-mcp "
        "(or, in the monorepo: pip install 'at-utility[mcp]')"
    ) from exc

mcp = MCPServer("metrecept")

DEFAULT_BASE = "https://api.metrecept.co.uk/v1"
# Public API hosts. api.withohm.dev is the compatibility hostname of the
# sibling brand Ohm, kept so existing configurations get the same check.
_PUBLIC_API_HOSTS = ("api.metrecept.co.uk", "api.withohm.dev")
UPSTREAM_HEADER = "X-Metrecept-Upstream-Key"


def _env(name: str, default: str = "") -> str:
    """Read METRECEPT_<name>; fall back to the compatibility OHM_<name> variable."""
    v = os.environ.get(f"METRECEPT_{name}")
    if v is None:
        v = os.environ.get("OHM_" + name)
    return default if v is None else v


def _header_lookup(ctx: Optional[Context], name: str) -> str:
    """Case-insensitive header read from the transport (None on stdio)."""
    headers = getattr(ctx, "headers", None) if ctx is not None else None
    if not headers:
        return ""
    lowered = name.lower()
    for k, v in headers.items():
        if k.lower() == lowered:
            return (v or "").strip()
    return ""


def _cfg(ctx: Optional[Context] = None) -> tuple[str, str, str]:
    base = (_env("BASE_URL") or DEFAULT_BASE).rstrip("/")
    # Remote (HTTP) attach: per-request Authorization pass-through wins so a
    # single stateless deployment can serve many tenants without shared keys.
    key = ""
    bearer = _header_lookup(ctx, "Authorization")
    if bearer.lower().startswith("bearer "):
        key = bearer[7:].strip()
    if not key:
        key = (_env("API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "Metrecept API key required: send 'Authorization: Bearer sk-at-*' on the "
            "MCP HTTP request, or set METRECEPT_API_KEY env for stdio. Create a seat "
            "at https://metrecept.co.uk/billing/intermediate "
            "(do not use local bootstrap sk-at-dev in production)."
        )
    # Never point the local bootstrap key at the public API (verification / misuse).
    if key == "sk-at-dev" and any(h in base for h in _PUBLIC_API_HOSTS):
        raise RuntimeError(
            "sk-at-dev is a local bootstrap key only. Issue a real seat key at "
            "https://metrecept.co.uk/billing/intermediate for the public API."
        )
    upstream = _header_lookup(ctx, UPSTREAM_HEADER) or _env("UPSTREAM_KEY")
    return base, key, upstream


def _safe_error_body(text: str, status: int) -> str:
    """Return upstream errors without echoing Authorization or raw secrets."""
    snippet = (text or "")[:2000]
    for needle in ("Bearer ", "sk-at-", "sk-proj-", "sk-ant-"):
        if needle in snippet:
            snippet = "[redacted upstream error body]"
            break
    return json.dumps({"error": snippet, "status": status})


SESSION_HEADER = "X-Metrecept-Session"


def _headers(
    upstream: str = "", ctx: Optional[Context] = None, session_id: str = ""
) -> dict[str, str]:
    _, key, env_up = _cfg(ctx)
    h = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    up = upstream or env_up
    if up:
        h[UPSTREAM_HEADER] = up
    if session_id:
        h[SESSION_HEADER] = session_id
    return h


async def metrecept_fetch_web(
    urls: list[str],
    purpose: str = "public_web_retrieval",
    query: str = "",
    format: str = "markdown",
    session_id: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """
    Compliant, metered public-web fetch through the Metrecept gateway.

    Terms/DPA must already be bound on the tenant at Checkout.
    This tool does not forge per-request legal acks.

    Args:
      urls: Public http(s) pages to fetch.
      purpose: One of public_web_retrieval, business_catalog,
        public_company_info, job_listings.
      query: Optional focus question for the model summarizer.
      format: markdown (default) or json — json returns title/text/meta/json_ld
        structure injected as context.
      session_id: Optional session tag (same id passed to
        metrecept_chat/metrecept_api_call); pull the aggregate later with metrecept_session.

    Returns redacted markdown or JSON-shaped context (model summary when via chat).
    """
    base, _, _ = _cfg(ctx)
    fmt = (format or "markdown").strip().lower()
    if fmt not in ("markdown", "json"):
        fmt = "markdown"
    body: dict[str, Any] = {
        "model": "mock",
        "messages": [{"role": "user", "content": query or "Summarize the web context."}],
        "fetch_web_context": True,
        "web_purpose": purpose,
        "web_urls": urls,
        "web_format": fmt,
        "cache_control": "no_store",
    }
    if query:
        body["web_query"] = query
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            f"{base}/chat/completions",
            headers=_headers(ctx=ctx, session_id=session_id),
            json=body,
        )
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        data = res.json()
        content = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or ""
        )
        return content or json.dumps(data)


async def _get(path: str, ctx: Optional[Context] = None) -> str:
    try:
        base, _, _ = _cfg(ctx)
    except RuntimeError as exc:
        return str(exc)
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(f"{base}{path}", headers=_headers(ctx=ctx))
        return res.text


async def metrecept_usage(ctx: Optional[Context] = None) -> str:
    """Return the tenant usage snapshot."""
    return await _get("/usage", ctx)


async def metrecept_models(ctx: Optional[Context] = None) -> str:
    """List routable model ids."""
    return await _get("/models", ctx)


async def metrecept_cache_trees(ctx: Optional[Context] = None) -> str:
    """List the tenant's cache-tree inventory: named exact-replay namespaces (GET /v1/cache/trees)."""
    return await _get("/cache/trees", ctx)


async def metrecept_cache_inventory(
    tree_id: str = "main",
    limit: int = 25,
    offset: int = 0,
    ctx: Optional[Context] = None,
) -> str:
    """
    List cached entries in a tree: digest, model, TTL, size (GET
    /v1/cache/trees/{tree_id}/entries). Metadata only — never returns cached
    message content.

    Args:
      tree_id: Cache tree id (default "main").
      limit: Max entries to return (capped at 100 server-side).
      offset: Pagination offset into the tree's digest index.
    """
    return await _get(f"/cache/trees/{tree_id}/entries?limit={int(limit)}&offset={int(offset)}", ctx)


async def metrecept_savings(ctx: Optional[Context] = None) -> str:
    """Return the cache savings snapshot: replayed prompts and estimated spend avoided (GET /v1/savings). Use metrecept_receipt to mint a shareable public receipt of these savings."""
    return await _get("/savings", ctx)


async def metrecept_receipt(display_name: str = "", ctx: Optional[Context] = None) -> str:
    """
    Mint a public, shareable savings receipt (POST /v1/savings/receipt).

    Returns a public page URL (metrecept.co.uk/r/<token>) plus a shields.io
    README badge snippet showing estimated upstream spend avoided. The
    receipt is an immutable snapshot, live for 90 days, and exposes only
    the display name — never the tenant id or API key.

    Args:
      display_name: Optional public name on the receipt (e.g. team or
        project name). Defaults to "an anonymous workspace".
    """
    base, _, _ = _cfg(ctx)
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{base}/savings/receipt",
            headers=_headers(ctx=ctx),
            json={"display_name": display_name},
        )
        return res.text


async def metrecept_register_api_service(
    name: str,
    base_url: str,
    allowed_path_prefix: str = "/",
    auth_header_name: str = "Authorization",
    purpose: str = "business_api_audit",
    ctx: Optional[Context] = None,
) -> str:
    """
    Register a named third-party API service for receipted audit-mode calls
    (POST /v1/api_services). One-time setup before metrecept_api_call.

    Stores only the non-secret shape — base URL, allowed path prefix, and the
    auth header *name* to inject. The credential itself is never sent here or
    persisted; it travels per-call via metrecept_api_call's service_key argument.

    Args:
      name: Short id for the service, e.g. "vehicle_data" ([a-z0-9_-]{1,64}).
      base_url: Absolute http(s) base URL, e.g. "https://api.vendor.example".
      allowed_path_prefix: Path prefix calls must stay under (default "/").
      auth_header_name: Header name the service expects the key under
        (e.g. "Authorization" or "X-Api-Key").
      purpose: Ingest-style purpose label (default business_api_audit).
    """
    base, _, _ = _cfg(ctx)
    body: dict[str, Any] = {
        "name": name,
        "base_url": base_url,
        "allowed_path_prefix": allowed_path_prefix,
        "auth_header_name": auth_header_name,
        "purpose": purpose,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{base}/api_services", headers=_headers(ctx=ctx), json=body
        )
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        return res.text


async def metrecept_api_services(ctx: Optional[Context] = None) -> str:
    """List the tenant's registered third-party API services (GET /v1/api_services)."""
    return await _get("/api_services", ctx)


async def metrecept_api_call(
    service: str,
    path: str,
    query: Optional[dict[str, Any]] = None,
    service_key: str = "",
    purpose: str = "business_api_audit",
    session_id: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """
    Receipted, metered GET call to a registered third-party business API
    (audit mode): gives an
    agent's mid-session vendor/API calls the same receipted, metered
    treatment as an LLM completion or a compliant web fetch.

    Read-only (GET) and allowlisted-service only in this phase — register
    the service first with metrecept_register_api_service. The service credential
    is BYOK-style: passed here, forwarded to the third party, never persisted.

    Args:
      service: Registered service name (see metrecept_api_services).
      path: Path under the service's allowed_path_prefix, e.g. "/v1/lookup".
      query: Optional query-string parameters.
      service_key: Third-party API credential (env METRECEPT_SERVICE_KEY fallback).
      purpose: Ingest-style purpose label (default business_api_audit).
      session_id: Optional session tag (same id passed to
        metrecept_chat/metrecept_fetch_web); pull the aggregate later with metrecept_session.
    """
    base, _, _ = _cfg(ctx)
    key = service_key or _env("SERVICE_KEY")
    headers = _headers(ctx=ctx, session_id=session_id)
    if key:
        headers["X-Metrecept-Service-Key"] = key
    body: dict[str, Any] = {"service": service, "path": path, "purpose": purpose}
    if query:
        body["query"] = query
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{base}/api_call", headers=headers, json=body)
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        return res.text


async def metrecept_session(session_id: str, ctx: Optional[Context] = None) -> str:
    """
    Aggregated, signed receipt for one audit-mode session
    

    Aggregates every chat completion and metrecept_api_call tagged with the same
    X-Metrecept-Session id into one signed receipt: event count, total cost,
    per-kind counts, first/last timestamps. Read-only — no new call made.

    The response carries `receipt` (compact JWS) and `verify_url`
    (https://metrecept.co.uk/verify#<jws>). Put `verify_url` in whatever
    this session produced — the PR description, the ticket, the email — so
    whoever reads that artefact can verify the run in their browser against
    the public JWKS, no account.

    Args:
      session_id: The same id passed as X-Metrecept-Session on the calls that made
        up this session.
    """
    return await _get(f"/sessions/{session_id}", ctx)


async def metrecept_providers(ctx: Optional[Context] = None) -> str:
    """Return upstream provider readiness."""
    return await _get("/providers", ctx)


async def metrecept_policy(ctx: Optional[Context] = None) -> str:
    """Return the compliance policy: which web-fetch purposes are allowed and their limits (GET /v1/compliance/policy)."""
    return await _get("/compliance/policy", ctx)


async def metrecept_chat(
    prompt: str,
    model: str = "mock",
    fetch_urls: Optional[list[str]] = None,
    purpose: str = "public_web_retrieval",
    upstream_api_key: str = "",
    session_id: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """
    Chat through the Metrecept gateway (OpenAI-compatible); exact repeats are served from cache.

    When fetch_urls is set, Terms/DPA must already be bound on the tenant
    (Checkout). This tool does not forge per-request legal acks.

    Args:
      prompt: User message.
      model: Upstream model id (mock for local; gpt/claude need BYOK).
      fetch_urls: Optional public URLs to attach as compliant web context.
      purpose: Ingest purpose when fetch_urls is set.
      upstream_api_key: Optional BYOK override (else METRECEPT_UPSTREAM_KEY).
      session_id: Optional session tag grouping this call
        with other metrecept_chat/metrecept_fetch_web/metrecept_api_call calls in the same
        unattended agent session; pull the aggregate signed receipt later
        with metrecept_session(session_id).
    """
    base, _, _ = _cfg(ctx)
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if fetch_urls:
        body.update(
            {
                "fetch_web_context": True,
                "web_purpose": purpose,
                "web_urls": fetch_urls,
            }
        )
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            f"{base}/chat/completions",
            headers=_headers(upstream_api_key, ctx=ctx, session_id=session_id),
            json=body,
        )
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        data = res.json()
        return (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or json.dumps(data)
        )


# Tool registration: one metrecept_* tool per handler.
_TOOL_DESCRIPTIONS: dict[str, str] = {
    'fetch_web': (
        "Fetch public web pages through the Metrecept gateway's compliance filter and return redacted markdown or JSON context; each fetch is metered and receipted. Use it when an agent needs public page content with a verifiable record; use metrecept_chat with fetch_urls instead when you want a model answer grounded in those pages. Call metrecept_policy first to see allowed purposes and size limits. The tenant must already have Terms/DPA accepted at Checkout, otherwise the call is refused. Robots.txt, HTTP 401/403 and 402 pay-per-crawl refusals are honoured (no auto-pay). Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only.\n"
        'Args: urls — list of public http(s) URLs (keep it to a handful; per-source and total character caps from policy apply). purpose — one of public_web_retrieval (default), business_catalog, public_company_info, job_listings. query — optional plain-text question to focus the summary. format — "markdown" (default) or "json" (title/text/meta/json_ld). session_id — optional id to group this call with metrecept_chat/metrecept_api_call calls; fetch the signed session receipt later with metrecept_session.\n'
        'Returns the context text; on failure returns JSON {"error", "status"} with secrets redacted. Never cached.'
    ),
    'usage': (
        "Read the tenant's current usage meters: request count, cache hit ratio and hit/miss tokens, web fetches, API calls, billed USD, plan, billing status and whether the soft fetch cap is lifted. Read-only, no charge, live (not cached). Use it to check consumption or plan status; use metrecept_savings for estimated upstream spend avoided, and metrecept_receipt to publish a shareable snapshot (metrecept_usage -> metrecept_savings -> metrecept_receipt). Does not return per-call history or receipts; use metrecept_session for a signed per-session record. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters, no pagination."
    ),
    'models': (
        "List model ids the gateway can route chat to (mock plus examples per vendor: OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Z.ai, Qwen, xAI) and the prefix routing table. Read-only, no charge; static list. Use it before metrecept_chat to pick a model id; any id under a routed prefix is forwarded verbatim. Non-mock models need your own upstream key (BYOK). Use metrecept_providers instead to see which vendors are actually configured/ready. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters."
    ),
    'cache_trees': (
        'List the tenant\'s cache trees (named, isolated exact-replay namespaces, default "main") with their metadata. Read-only, no charge, live. Use it to discover tree ids; then call metrecept_cache_inventory with a tree_id to see the entries inside one tree. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key\'s tenant only. No parameters.'
    ),
    'cache_inventory': (
        "List entries cached in one cache tree: request digest, model, token count, byte size and TTL remaining. Metadata only — never returns prompt or response content. Read-only, no charge, live. Get tree ids from metrecept_cache_trees first. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only.\n"
        'Args: tree_id — tree id (default "main"). limit — entries per page, 1-100 (server caps at 100; default 25). offset — page offset; increase by limit to page through.'
    ),
    'savings': (
        "Read the tenant's savings ledger: cache hit ratio and tokens, estimated upstream spend avoided versus what Metrecept billed, ROI ratio. Figures are estimates. Read-only, no charge, live. Use after metrecept_usage when you need the money view; follow with metrecept_receipt to publish a shareable, signed snapshot. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters."
    ),
    'receipt': (
        "Publish a public, shareable savings receipt: an immutable snapshot of the current savings figures, signed as an Ed25519 JWS, at metrecept.co.uk/r/<token> plus a README badge snippet. Side effect: creates a public page that lives for 90 days and shows only the display name (never tenant id or key). Not billed. Call metrecept_savings first if you want to check the numbers. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only.\n"
        'Args: display_name — optional public name (team or project). Default is an empty string, which the server shows as "an anonymous workspace".'
    ),
    'register_api_service': (
        "Register (or update) a third-party API service so metrecept_api_call can make receipted GET calls to it. Stores only base URL, allowed path prefix, auth header name and purpose — never a credential. Registering an existing name overwrites that service's settings. Private/internal base URLs are rejected. Not billed. Workflow: metrecept_register_api_service -> metrecept_api_services (check) -> metrecept_api_call. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only.\n"
        'Args: name — id matching [a-z0-9_-]{1,64}, e.g. "vehicle_data". base_url — absolute public http(s) URL. allowed_path_prefix — calls must stay under this path (default "/"). auth_header_name — header the vendor expects the key in, e.g. "Authorization" or "X-Api-Key". purpose — compliance purpose label (default business_api_audit).'
    ),
    'api_services': (
        "List the tenant's registered third-party API services (name, base URL, path prefix, auth header name, purpose). No credentials are stored, so none are returned. Read-only, no charge, live, not paginated. Use it to confirm a service exists before metrecept_api_call; register new ones with metrecept_register_api_service. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters."
    ),
    'api_call': (
        'Make a read-only GET call to a registered third-party API through the gateway and return the vendor\'s response body; each call is metered (billed per call at the plan rate) and gets a signed receipt that stores only a hash of path and query. Prerequisite: metrecept_register_api_service. Returns 404 service_not_found if the name is unknown; vendor errors and path-prefix violations come back as JSON {"error", "status"}. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key\'s tenant only.\n'
        'Args: service — registered name (see metrecept_api_services). path — path under the service\'s allowed prefix, e.g. "/v1/lookup". query — optional dict of query-string params. service_key — the vendor credential, forwarded and never stored (falls back to METRECEPT_SERVICE_KEY env). purpose — compliance purpose (default business_api_audit). session_id — optional id grouping this call into a metrecept_session receipt.'
    ),
    'session': (
        "Get one signed, aggregated receipt for a session: every metrecept_chat, metrecept_fetch_web and metrecept_api_call tagged with the same session_id, with event count, total billed USD, cache hits/misses, fetch and API call counts, first/last timestamps, the compact JWS and a verify_url anyone can open to verify it against the public keys, no account needed. Read-only: makes no new upstream call and is not billed. Unknown ids return event_count 0 (not an error). Use metrecept_session for a whole agent run; use metrecept_receipt for a public savings snapshot. Put verify_url in the PR, ticket or email the run produced. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only.\n"
        'Args: session_id — the same id passed as session_id on the tagged calls.'
    ),
    'providers': (
        "Show which upstream vendors the gateway has configured and ready (OpenAI, Anthropic and OpenAI-compatible vendors), whether each is BYOK, and the BYOK header name. Reports key presence only; keys are not validated upstream and never returned. Read-only, no charge, live. Use it when a metrecept_chat call fails or routing looks wrong; use metrecept_models instead to pick a model id. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters."
    ),
    'policy': (
        "Read the web-fetch compliance policy: allowed purposes, robots.txt and PII-redaction settings, whether Terms acceptance is required, and per-source / total character limits. Read-only, no charge. Call it before metrecept_fetch_web or metrecept_chat with fetch_urls to pick a valid purpose and see why a fetch was refused. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only. No parameters."
    ),
    'chat': (
        'Send one user message to a model through the Metrecept gateway (OpenAI-compatible) and return the reply text. Each call is metered and gets a signed receipt; an exact repeat of the same request is served from the tenant\'s cache instead of the upstream model. Optionally attaches compliant public web context. Use metrecept_fetch_web instead if you only want page content. Failures (bad model, missing BYOK key, refused fetch, rate limit) return JSON {"error", "status"}. Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key\'s tenant only.\n'
        'Args: prompt — the user message text. model — model id from metrecept_models; "mock" (default) needs no upstream key, others need BYOK. fetch_urls — optional list of public URLs to add as context (Terms/DPA must be accepted; see metrecept_policy). purpose — fetch purpose when fetch_urls is set (default public_web_retrieval). upstream_api_key — your vendor key for this call (else METRECEPT_UPSTREAM_KEY env); forwarded, never stored. session_id — optional id grouping calls; read the signed aggregate with metrecept_session.'
    ),
}


def _register_tools() -> None:
    for short, desc in _TOOL_DESCRIPTIONS.items():
        mcp.tool(name=f"metrecept_{short}", description=desc)(globals()[f"metrecept_{short}"])


_register_tools()


def _env_flag(name: str, default: bool) -> bool:
    raw = _env(name) or None
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# *.withohm.dev: compatibility hostnames of the sibling brand Ohm.
DEFAULT_ALLOWED_HOSTS = (
    "mcp.withohm.dev,mcp.metrecept.co.uk,"
    "api.withohm.dev,api.metrecept.co.uk,"
    "gateway,localhost,127.0.0.1"
)


def _transport_security():
    """DNS-rebinding protection with configurable Host/Origin allowlists."""
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = [
        h.strip()
        for h in (
            _env("MCP_ALLOWED_HOSTS") or DEFAULT_ALLOWED_HOSTS
        ).split(",")
        if h.strip()
    ]
    region = (os.environ.get("AT_REGION") or "local").strip().lower()
    env = (os.environ.get("AT_ENV") or "").strip().lower()
    if env != "production" and region in {"", "local", "dev", "test"}:
        hosts.extend(["test", "testserver"])
    origins = [
        o.strip()
        for o in (_env("MCP_ALLOWED_ORIGINS")).split(",")
        if o.strip()
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        # Bare hostnames also allow host:port forms
        allowed_hosts=sorted({*hosts, *(f"{h}:*" for h in hosts if ":" not in h)}),
        allowed_origins=origins,
    )


def http_app(*, json_response: bool = True, streamable_http_path: str = "/mcp"):
    """Stateless streamable-HTTP ASGI app (MCP 2026-07-28 stateless core).

    No session identifiers, no server-held stream state: cacheable, routable,
    horizontally scalable behind any load balancer. Standalone serves
    `POST /mcp`; pass `streamable_http_path="/"` when mounting under `/mcp`.
    """
    return mcp.streamable_http_app(
        streamable_http_path=streamable_http_path,
        stateless_http=True,
        json_response=json_response,
        transport_security=_transport_security(),
    )


def main() -> None:
    """Entry point. METRECEPT_MCP_TRANSPORT=stdio (default) | http | streamable-http."""
    transport = (_env("MCP_TRANSPORT") or "stdio").strip().lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        main_http()
        return
    mcp.run()


def main_http() -> None:
    """Run the stateless remote MCP server over streamable HTTP."""
    mcp.run(
        "streamable-http",
        host=_env("MCP_HOST", "0.0.0.0"),
        port=int(_env("MCP_PORT", "8091")),
        stateless_http=True,
        json_response=_env_flag("MCP_JSON_RESPONSE", True),
        transport_security=_transport_security(),
    )


if __name__ == "__main__":
    main()
