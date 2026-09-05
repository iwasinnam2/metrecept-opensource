"""Metrecept MCP server — Cursor attach for cache + compliant web fetch.

Transports:
  * stdio (default) — local Cursor attach; auth via OHM_API_KEY env.
  * streamable HTTP (stateless) — remote attach per MCP 2026-07-28 stateless
    core; auth via the incoming `Authorization: Bearer sk-at-*` header
    (per-request pass-through), falling back to OHM_API_KEY env.

Run remote: `OHM_MCP_TRANSPORT=http ohm-mcp` (or `ohm-mcp-http`).
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
        "MCP support missing: pip install withohm-mcp "
        "(or, in the monorepo: pip install 'at-utility[mcp]')"
    ) from exc

mcp = MCPServer("ohm")

DEFAULT_BASE = "https://api.metrecept.co.uk/v1"
UPSTREAM_HEADER = "X-Ohm-Upstream-Key"


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
    base = (os.environ.get("OHM_BASE_URL") or DEFAULT_BASE).rstrip("/")
    # Remote (HTTP) attach: per-request Authorization pass-through wins so a
    # single stateless deployment can serve many tenants without shared keys.
    key = ""
    bearer = _header_lookup(ctx, "Authorization")
    if bearer.lower().startswith("bearer "):
        key = bearer[7:].strip()
    if not key:
        key = (os.environ.get("OHM_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "Metrecept API key required: send 'Authorization: Bearer sk-at-*' on the "
            "MCP HTTP request, or set OHM_API_KEY env for stdio. Create a seat "
            "at https://metrecept.co.uk/billing/intermediate "
            "(do not use local bootstrap sk-at-dev in production)."
        )
    # Never point the local bootstrap key at the public API (verification / misuse).
    if key == "sk-at-dev" and (
        "api.withohm.dev" in base or "api.metrecept.co.uk" in base
    ):
        raise RuntimeError(
            "sk-at-dev is a local bootstrap key only. Issue a real seat key at "
            "https://metrecept.co.uk/billing/intermediate for the public API."
        )
    upstream = _header_lookup(ctx, UPSTREAM_HEADER) or os.environ.get(
        "OHM_UPSTREAM_KEY", ""
    )
    return base, key, upstream


def _safe_error_body(text: str, status: int) -> str:
    """Return upstream errors without echoing Authorization or raw secrets."""
    snippet = (text or "")[:2000]
    for needle in ("Bearer ", "sk-at-", "sk-proj-", "sk-ant-"):
        if needle in snippet:
            snippet = "[redacted upstream error body]"
            break
    return json.dumps({"error": snippet, "status": status})


SESSION_HEADER = "X-Ohm-Session"


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


@mcp.tool()
async def ohm_fetch_web(
    urls: list[str],
    purpose: str = "public_web_retrieval",
    query: str = "",
    format: str = "markdown",
    session_id: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """
    Compliant public-web fetch via Ohm ingest (metered ohm_web_fetch).

    Terms/DPA must already be bound on the tenant at Checkout (or admin mint).
    This tool does not forge per-request legal acks.

    Args:
      urls: Public http(s) pages to fetch.
      purpose: One of public_web_retrieval, business_catalog,
        public_company_info, job_listings.
      query: Optional focus question for the model summarizer.
      format: markdown (default) or json — json returns title/text/meta/json_ld
        structure injected as context.
      session_id: Optional Black Box flight-recorder tag (same id passed to
        ohm_chat/ohm_api_call); pull the aggregate later with ohm_session.

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


@mcp.tool()
async def ohm_usage(ctx: Optional[Context] = None) -> str:
    """Return Ohm usage snapshot: cache hit ratio, fetches, estimated pipe rent (GET /v1/usage)."""
    return await _get("/usage", ctx)


@mcp.tool()
async def ohm_models(ctx: Optional[Context] = None) -> str:
    """List the model ids the Ohm pipe routes to, including BYOK upstreams (GET /v1/models)."""
    return await _get("/models", ctx)


@mcp.tool()
async def ohm_cache_trees(ctx: Optional[Context] = None) -> str:
    """List the tenant's cache-tree inventory: named exact-replay namespaces (GET /v1/cache/trees)."""
    return await _get("/cache/trees", ctx)


@mcp.tool()
async def ohm_cache_inventory(
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


@mcp.tool()
async def ohm_savings(ctx: Optional[Context] = None) -> str:
    """Return the cache savings snapshot: replayed prompts and estimated spend avoided (GET /v1/savings). Use ohm_receipt to mint a shareable public receipt of these savings."""
    return await _get("/savings", ctx)


@mcp.tool()
async def ohm_receipt(display_name: str = "", ctx: Optional[Context] = None) -> str:
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


@mcp.tool()
async def ohm_register_api_service(
    name: str,
    base_url: str,
    allowed_path_prefix: str = "/",
    auth_header_name: str = "Authorization",
    purpose: str = "business_api_audit",
    ctx: Optional[Context] = None,
) -> str:
    """
    Register a named third-party API service for receipted audit-mode calls
    (POST /v1/api_services). One-time setup before ohm_api_call.

    Stores only the non-secret shape — base URL, allowed path prefix, and the
    auth header *name* to inject. The credential itself is never sent here or
    persisted; it travels per-call via ohm_api_call's service_key argument.

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


@mcp.tool()
async def ohm_api_services(ctx: Optional[Context] = None) -> str:
    """List the tenant's registered third-party API services (GET /v1/api_services)."""
    return await _get("/api_services", ctx)


@mcp.tool()
async def ohm_api_call(
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
    (POST /v1/api_call). Phase A of docs/BLACK_BOX.md's audit-mode: gives an
    agent's mid-session vendor/API calls the same receipted, metered
    treatment as an LLM completion or a compliant web fetch.

    Read-only (GET) and allowlisted-service only in this phase — register
    the service first with ohm_register_api_service. The service credential
    is BYOK-style: passed here, forwarded to the third party, never persisted.

    Args:
      service: Registered service name (see ohm_api_services).
      path: Path under the service's allowed_path_prefix, e.g. "/v1/lookup".
      query: Optional query-string parameters.
      service_key: Third-party API credential (env OHM_SERVICE_KEY fallback).
      purpose: Ingest-style purpose label (default business_api_audit).
      session_id: Optional Black Box flight-recorder tag (same id passed to
        ohm_chat/ohm_fetch_web); pull the aggregate later with ohm_session.
    """
    base, _, _ = _cfg(ctx)
    key = service_key or os.environ.get("OHM_SERVICE_KEY", "")
    headers = _headers(ctx=ctx, session_id=session_id)
    if key:
        headers["X-Ohm-Service-Key"] = key
    body: dict[str, Any] = {"service": service, "path": path, "purpose": purpose}
    if query:
        body["query"] = query
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{base}/api_call", headers=headers, json=body)
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        return res.text


@mcp.tool()
async def ohm_session(session_id: str, ctx: Optional[Context] = None) -> str:
    """
    Aggregated, signed flight-recorder receipt for one audit-mode session
    (GET /v1/sessions/{session_id}, docs/BLACK_BOX.md Phase B).

    Aggregates every chat completion and ohm_api_call tagged with the same
    X-Ohm-Session id into one signed receipt: event count, total cost,
    per-kind counts, first/last timestamps. Read-only — no new call made.

    Args:
      session_id: The same id passed as X-Ohm-Session on the calls that made
        up this session.
    """
    return await _get(f"/sessions/{session_id}", ctx)


@mcp.tool()
async def ohm_providers(ctx: Optional[Context] = None) -> str:
    """Return upstream provider and failover status for the Ohm pipe (GET /v1/providers)."""
    return await _get("/providers", ctx)


@mcp.tool()
async def ohm_policy(ctx: Optional[Context] = None) -> str:
    """Return the compliance policy: which web-fetch purposes are allowed and their limits (GET /v1/compliance/policy)."""
    return await _get("/compliance/policy", ctx)


@mcp.tool()
async def ohm_chat(
    prompt: str,
    model: str = "mock",
    fetch_urls: Optional[list[str]] = None,
    purpose: str = "public_web_retrieval",
    upstream_api_key: str = "",
    session_id: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """
    Chat through Ohm (OpenAI-compatible). Identical prompts hit Redis cache.

    When fetch_urls is set, Terms/DPA must already be bound on the tenant
    (Checkout). This tool does not forge per-request legal acks.

    Args:
      prompt: User message.
      model: Upstream model id (mock for local; gpt/claude need BYOK).
      fetch_urls: Optional public URLs to attach as compliant web context.
      purpose: Ingest purpose when fetch_urls is set.
      upstream_api_key: Optional BYOK override (else OHM_UPSTREAM_KEY).
      session_id: Optional Black Box flight-recorder tag grouping this call
        with other ohm_chat/ohm_fetch_web/ohm_api_call calls in the same
        unattended agent session; pull the aggregate signed receipt later
        with ohm_session(session_id).
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


# techmig-headers-tools (Black Box pivot, 2026-08-19): metrecept_* aliases
# for every ohm_* tool above, registered against the identical handler —
# same implementation, same docstring, same JSON schema. Additive only:
# every existing ohm_* tool name keeps working completely unmodified, and
# a client may call either name interchangeably. See docs/BRAND.md's
# "Technical migration status" for why this is a dual-accept period rather
# than a rename.
_METRECEPT_TOOL_ALIASES: dict[str, Any] = {
    "metrecept_fetch_web": ohm_fetch_web,
    "metrecept_usage": ohm_usage,
    "metrecept_models": ohm_models,
    "metrecept_cache_trees": ohm_cache_trees,
    "metrecept_cache_inventory": ohm_cache_inventory,
    "metrecept_savings": ohm_savings,
    "metrecept_receipt": ohm_receipt,
    "metrecept_register_api_service": ohm_register_api_service,
    "metrecept_api_services": ohm_api_services,
    "metrecept_api_call": ohm_api_call,
    "metrecept_session": ohm_session,
    "metrecept_providers": ohm_providers,
    "metrecept_policy": ohm_policy,
    "metrecept_chat": ohm_chat,
}
for _alias_name, _handler_fn in _METRECEPT_TOOL_ALIASES.items():
    mcp.tool(name=_alias_name)(_handler_fn)


# metre_* aliases: a third additive name for every ohm_* tool above, same
# zero-breakage pattern as _METRECEPT_TOOL_ALIASES above — registered
# against the identical handler, additive only. ohm_*, metrecept_*, and
# metre_* all keep working forever; nothing existing had to change. See
# docs/BRAND.md's "Technical migration status" for why this is dual-accept,
# not a rename.
_METRE_TOOL_ALIASES: dict[str, Any] = {
    "metre_fetch_web": ohm_fetch_web,
    "metre_usage": ohm_usage,
    "metre_models": ohm_models,
    "metre_cache_trees": ohm_cache_trees,
    "metre_cache_inventory": ohm_cache_inventory,
    "metre_savings": ohm_savings,
    "metre_receipt": ohm_receipt,
    "metre_register_api_service": ohm_register_api_service,
    "metre_api_services": ohm_api_services,
    "metre_api_call": ohm_api_call,
    "metre_session": ohm_session,
    "metre_providers": ohm_providers,
    "metre_policy": ohm_policy,
    "metre_chat": ohm_chat,
}
for _alias_name, _handler_fn in _METRE_TOOL_ALIASES.items():
    mcp.tool(name=_alias_name)(_handler_fn)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


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
            os.environ.get("OHM_MCP_ALLOWED_HOSTS") or DEFAULT_ALLOWED_HOSTS
        ).split(",")
        if h.strip()
    ]
    region = (os.environ.get("AT_REGION") or "local").strip().lower()
    env = (os.environ.get("AT_ENV") or "").strip().lower()
    if env != "production" and region in {"", "local", "dev", "test"}:
        hosts.extend(["test", "testserver"])
    origins = [
        o.strip()
        for o in (os.environ.get("OHM_MCP_ALLOWED_ORIGINS") or "").split(",")
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
    """Entry point. OHM_MCP_TRANSPORT=stdio (default) | http | streamable-http."""
    transport = (os.environ.get("OHM_MCP_TRANSPORT") or "stdio").strip().lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        main_http()
        return
    mcp.run()


def main_http() -> None:
    """Run the stateless remote MCP server over streamable HTTP."""
    mcp.run(
        "streamable-http",
        host=os.environ.get("OHM_MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("OHM_MCP_PORT", "8091")),
        stateless_http=True,
        json_response=_env_flag("OHM_MCP_JSON_RESPONSE", True),
        transport_security=_transport_security(),
    )


if __name__ == "__main__":
    main()
