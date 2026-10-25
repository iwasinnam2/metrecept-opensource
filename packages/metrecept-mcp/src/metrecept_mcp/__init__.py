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

import base64
import hashlib
import json
import os
import re
import time
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

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


async def metrecept_fetch_web_pages(
    urls: Annotated[list[str], Field(description='Public http(s) page URLs to fetch; keep it to a handful (per-source and total character caps from metrecept_get_fetch_policy apply).')],
    purpose: Annotated[str, Field(description='Compliance purpose: public_web_retrieval (default), business_catalog, public_company_info or job_listings.')] = "public_web_retrieval",
    query: Annotated[str, Field(description='Optional plain-text question that focuses the summary; empty string for a general summary.')] = "",
    format: Annotated[str, Field(description='"markdown" (default) or "json" (title/text/meta/json_ld); anything else falls back to markdown.')] = "markdown",
    session_id: Annotated[str, Field(description='Optional session tag grouping this call with others; read the signed aggregate later with metrecept_get_session_receipt.')] = "",
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
        metrecept_create_chat_completion/metrecept_call_api); pull the aggregate later with metrecept_get_session_receipt.

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


async def metrecept_get_usage(ctx: Optional[Context] = None) -> str:
    """Return the tenant usage snapshot."""
    return await _get("/usage", ctx)


async def metrecept_list_models(ctx: Optional[Context] = None) -> str:
    """List routable model ids."""
    return await _get("/models", ctx)


async def metrecept_list_cache_trees(
    include_archived: Annotated[bool, Field(description="Also list archived trees (hidden by default). Default false.")] = False,
    ctx: Optional[Context] = None,
) -> str:
    """List the tenant's cache-tree inventory: named exact-replay namespaces (GET /v1/cache/trees)."""
    return await _get("/cache/trees" + ("?include_archived=true" if include_archived else ""), ctx)


async def metrecept_list_cache_entries(
    tree_id: Annotated[str, Field(description='Cache tree id from metrecept_list_cache_trees (default "main").')] = "main",
    limit: Annotated[int, Field(description='Entries per page, 1-100 (clamped server-side; default 25).')] = 25,
    offset: Annotated[int, Field(description="Zero-based offset into the tree's digest index; add limit to page forward (default 0).")] = 0,
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


async def metrecept_get_savings(ctx: Optional[Context] = None) -> str:
    """Return the cache savings snapshot: replayed prompts and estimated spend avoided (GET /v1/savings). Use metrecept_publish_savings_receipt to mint a shareable public receipt of these savings."""
    return await _get("/savings", ctx)


async def metrecept_publish_savings_receipt(
    display_name: Annotated[str, Field(description='Optional public name shown on the receipt (team or project); empty shows "an anonymous workspace".')] = "",
    ctx: Optional[Context] = None,
) -> str:
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
    name: Annotated[str, Field(description='Service id matching [a-z0-9_-]{1,64}, e.g. "vehicle_data". Re-using a name overwrites it.')],
    base_url: Annotated[str, Field(description='Absolute public http(s) base URL of the vendor API, e.g. "https://api.vendor.example". Private/internal hosts are rejected.')],
    allowed_path_prefix: Annotated[str, Field(description='Path prefix every call must stay under (default "/").')] = "/",
    auth_header_name: Annotated[str, Field(description='Header the vendor expects the credential in, e.g. "Authorization" or "X-Api-Key" (default "Authorization").')] = "Authorization",
    purpose: Annotated[str, Field(description='Compliance purpose label (default business_api_audit).')] = "business_api_audit",
    ctx: Optional[Context] = None,
) -> str:
    """
    Register a named third-party API service for receipted audit-mode calls
    (POST /v1/api_services). One-time setup before metrecept_call_api.

    Stores only the non-secret shape — base URL, allowed path prefix, and the
    auth header *name* to inject. The credential itself is never sent here or
    persisted; it travels per-call via metrecept_call_api's service_key argument.

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


async def metrecept_list_api_services(ctx: Optional[Context] = None) -> str:
    """List the tenant's registered third-party API services (GET /v1/api_services)."""
    return await _get("/api_services", ctx)


async def metrecept_call_api(
    service: Annotated[str, Field(description='Registered service name (see metrecept_list_api_services).')],
    path: Annotated[str, Field(description='Path under the service\'s allowed_path_prefix, e.g. "/v1/lookup".')],
    query: Annotated[Optional[dict[str, Any]], Field(description='Optional query-string parameters as a flat object.')] = None,
    service_key: Annotated[str, Field(description='Vendor credential forwarded to the third party and never stored; falls back to METRECEPT_SERVICE_KEY env.')] = "",
    purpose: Annotated[str, Field(description='Compliance purpose label (default business_api_audit).')] = "business_api_audit",
    session_id: Annotated[str, Field(description='Optional session tag grouping this call into a metrecept_get_session_receipt receipt.')] = "",
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
      service: Registered service name (see metrecept_list_api_services).
      path: Path under the service's allowed_path_prefix, e.g. "/v1/lookup".
      query: Optional query-string parameters.
      service_key: Third-party API credential (env METRECEPT_SERVICE_KEY fallback).
      purpose: Ingest-style purpose label (default business_api_audit).
      session_id: Optional session tag (same id passed to
        metrecept_create_chat_completion/metrecept_fetch_web_pages); pull the aggregate later with metrecept_get_session_receipt.
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


async def metrecept_get_session_receipt(
    session_id: Annotated[str, Field(description='The same session_id passed on the tagged chat, fetch and API calls.')],
    ctx: Optional[Context] = None,
) -> str:
    """
    Aggregated, signed receipt for one audit-mode session
    

    Aggregates every chat completion and metrecept_call_api tagged with the same
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


async def _delete(path: str, ctx: Optional[Context] = None) -> str:
    try:
        base, _, _ = _cfg(ctx)
    except RuntimeError as exc:
        return str(exc)
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.delete(f"{base}{path}", headers=_headers(ctx=ctx))
        if res.status_code >= 400:
            return _safe_error_body(res.text, res.status_code)
        return res.text


def _seg(value: str) -> str:
    """Percent-encode one URL path segment (no slashes pass through)."""
    from urllib.parse import quote

    return quote(str(value or ""), safe="")


async def metrecept_unregister_api_service(
    name: Annotated[str, Field(description='Registered service name to remove, e.g. "vehicle_data" ([a-z0-9_-]{1,64}).')],
    ctx: Optional[Context] = None,
) -> str:
    """Unregister a third-party API service (DELETE /v1/api_services/{name})."""
    return await _delete(f"/api_services/{_seg(name)}", ctx)


async def metrecept_get_usage_history(
    days: Annotated[int, Field(description='Window length in UTC days ending today, 1-90 (default 30; out-of-range values are clamped).')] = 30,
    ctx: Optional[Context] = None,
) -> str:
    """Per-UTC-day usage meter series (GET /v1/usage/history?days=N)."""
    d = max(1, min(int(days), 90))
    return await _get(f"/usage/history?days={d}", ctx)


async def metrecept_evict_cache_entry(
    digest: Annotated[str, Field(description='Request digest exactly as returned in entries[].digest by metrecept_list_cache_entries: a 64-character lowercase hex SHA-256 of the normalized request (the server accepts 8-200 characters of A-Z a-z 0-9 : _ - and rejects anything else with 400 invalid_digest).')],
    tree_id: Annotated[str, Field(description='Cache tree id that holds the entry (default "main").')] = "main",
    ctx: Optional[Context] = None,
) -> str:
    """Evict one cached entry by digest (DELETE /v1/cache/trees/{tree_id}/entries/{digest})."""
    return await _delete(f"/cache/trees/{_seg(tree_id)}/entries/{_seg(digest)}", ctx)


async def metrecept_delete_cache_tree(
    tree_id: Annotated[str, Field(description='Id of the tree to delete; any tree except "main".')],
    ctx: Optional[Context] = None,
) -> str:
    """Delete a non-main cache tree (DELETE /v1/cache/trees/{tree_id})."""
    return await _delete(f"/cache/trees/{_seg(tree_id)}", ctx)


class CacheTreeResult(BaseModel):
    """Structured result of metrecept_manage_cache_tree (fields depend on action)."""

    action: Literal["create", "fork", "promote"] = Field(description="The action that was requested.")
    ok: bool = Field(description="True when the gateway accepted the request (HTTP 2xx).")
    status: int = Field(description="HTTP status returned by the gateway (200 on success).")
    tree_id: Optional[str] = Field(default=None, description="create/fork: id of the new tree.")
    name: Optional[str] = Field(default=None, description="create/fork: name of the new tree (same as tree_id).")
    parent_tree_id: Optional[str] = Field(default=None, description="create/fork: tree the new tree reads through to copy-on-write.")
    tree_status: Optional[str] = Field(default=None, description='create/fork: lifecycle status of the new tree, "active".')
    default: Optional[bool] = Field(default=None, description="create/fork: always false; main stays the tenant default.")
    created_at: Optional[int] = Field(default=None, description="create/fork: creation time, Unix seconds (UTC).")
    promoted_from: Optional[str] = Field(default=None, description="promote: the child tree whose entries were merged.")
    promoted_into: Optional[str] = Field(default=None, description="promote: the target tree that now references them.")
    digests_considered: Optional[int] = Field(default=None, description="promote: digests in the child's local index.")
    digests_referenced: Optional[int] = Field(default=None, description="promote: new references added to the target (digests it could not already resolve).")
    bytes_copied: Optional[int] = Field(default=None, description="promote: always 0; promote shares bytes by reference.")
    billed: Optional[bool] = Field(default=None, description="Always false on success: tree management is not billed.")
    error: Optional[str] = Field(default=None, description="On failure: gateway error code, e.g. tree_exists, parent_missing, tree_missing, cannot_promote_main, parent_frozen, invalid_cache_tree, tree_id_required.")


async def metrecept_manage_cache_tree(
    action: Annotated[Literal["create", "fork", "promote"], Field(description='"create": new tree under parent (default main). "fork": new child of tree_id. "promote": merge tree_id\'s own entries into the target tree (default its parent).')],
    tree_id: Annotated[str, Field(description="fork: tree to fork (main allowed). promote: tree whose entries are merged (not main). Required for fork and promote; ignored by create.")] = "",
    name: Annotated[str, Field(description='create/fork: optional id for the new tree, [a-z0-9_-]{1,64}; empty generates "t-" plus 10 hex characters. Ignored by promote.')] = "",
    parent: Annotated[str, Field(description='create only: parent tree id the new tree reads through to; empty means "main".')] = "",
    into: Annotated[str, Field(description='promote only: target tree id; empty means the child\'s parent. Use "main" to land a grandchild directly in main.')] = "",
    ctx: Optional[Context] = None,
) -> CacheTreeResult:
    base, _, _ = _cfg(ctx)
    if action == "create":
        url = f"{base}/cache/trees"
        body = {k: v for k, v in (("name", name), ("parent", parent)) if v}
    elif action in ("fork", "promote"):
        if not tree_id:
            return CacheTreeResult(action=action, ok=False, status=400, error="tree_id_required")
        url = f"{base}/cache/trees/{_seg(tree_id)}/{action}"
        if action == "fork":
            body = {"name": name} if name else {}
        else:
            body = {"into": into} if into else {}
    else:
        return CacheTreeResult(action="create", ok=False, status=400, error="invalid_action")
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, headers=_headers(ctx=ctx), json=body)
    try:
        data = res.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if res.status_code >= 400:
        code = ""
        err = data.get("error")
        if isinstance(err, dict):
            code = (err.get("details") or {}).get("code") or err.get("code") or ""
        elif isinstance(err, str):
            code = err
        if not code and isinstance(data.get("detail"), dict):
            code = data["detail"].get("code", "")
        return CacheTreeResult(action=action, ok=False, status=res.status_code, error=code or "http_error")
    if action == "promote":
        return CacheTreeResult(
            action=action, ok=True, status=res.status_code,
            promoted_from=data.get("from"), promoted_into=data.get("into"),
            digests_considered=data.get("digests_considered"),
            digests_referenced=data.get("digests_referenced"),
            bytes_copied=data.get("bytes_copied"), billed=data.get("billed", False),
        )
    return CacheTreeResult(
        action=action, ok=True, status=res.status_code,
        tree_id=data.get("tree_id"), name=data.get("name"),
        parent_tree_id=data.get("parent_tree_id"), tree_status=data.get("status"),
        default=data.get("default"), created_at=data.get("created_at"),
        billed=data.get("billed", False),
    )


async def metrecept_list_providers(ctx: Optional[Context] = None) -> str:
    """Return upstream provider readiness."""
    return await _get("/providers", ctx)


async def metrecept_get_fetch_policy(ctx: Optional[Context] = None) -> str:
    """Return the compliance policy: which web-fetch purposes are allowed and their limits (GET /v1/compliance/policy)."""
    return await _get("/compliance/policy", ctx)


async def metrecept_create_chat_completion(
    prompt: Annotated[str, Field(description='The user message text.')],
    model: Annotated[str, Field(description='Model id from metrecept_list_models; "mock" (default) needs no upstream key, others need BYOK.')] = "mock",
    fetch_urls: Annotated[Optional[list[str]], Field(description='Optional public URLs whose compliant, redacted content is attached as context before the model answers (Terms/DPA must be accepted).')] = None,
    purpose: Annotated[str, Field(description='Fetch purpose used only when fetch_urls is set (default public_web_retrieval).')] = "public_web_retrieval",
    upstream_api_key: Annotated[str, Field(description='Optional vendor key for this call (else METRECEPT_UPSTREAM_KEY env); forwarded, never stored.')] = "",
    session_id: Annotated[str, Field(description='Optional session tag; read the signed aggregate later with metrecept_get_session_receipt.')] = "",
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
        with other metrecept_create_chat_completion/metrecept_fetch_web_pages/metrecept_call_api calls in the same
        unattended agent session; pull the aggregate signed receipt later
        with metrecept_get_session_receipt(session_id).
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
_AUTH = "Requires a Metrecept API key (METRECEPT_API_KEY env on stdio, or Authorization: Bearer on remote HTTP); results are scoped to that key's tenant only."
async def _post_json(path: str, body: dict[str, Any], ctx: Optional[Context] = None, *, session_id: str = "", upstream: str = "", timeout: float = 30.0) -> tuple[int, str, Any]:
    """POST JSON to the gateway; return (status, text, response)."""
    base, _, _ = _cfg(ctx)
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(
            f"{base}{path}",
            headers=_headers(upstream, ctx=ctx, session_id=session_id),
            json=body,
        )
    return res.status_code, res.text, res


async def metrecept_freeze_cache_tree(
    tree_id: Annotated[str, Field(description='Id of the cache tree to freeze or unfreeze; any tree except "main".')],
    frozen: Annotated[bool, Field(description="true (default) freezes the tree; false unfreezes it back to active.")] = True,
    ctx: Optional[Context] = None,
) -> str:
    try:
        status, text, _ = await _post_json(f"/cache/trees/{_seg(tree_id)}/freeze", {"frozen": bool(frozen)}, ctx)
    except RuntimeError as exc:
        return str(exc)
    return _safe_error_body(text, status) if status >= 400 else text


async def metrecept_archive_cache_tree(
    tree_id: Annotated[str, Field(description='Id of the cache tree to archive or restore; any tree except "main".')],
    archived: Annotated[bool, Field(description="true (default) archives the tree; false restores it to the status it had before archiving.")] = True,
    ctx: Optional[Context] = None,
) -> str:
    try:
        status, text, _ = await _post_json(f"/cache/trees/{_seg(tree_id)}/archive", {"archived": bool(archived)}, ctx)
    except RuntimeError as exc:
        return str(exc)
    return _safe_error_body(text, status) if status >= 400 else text


class PrewarmMessage(BaseModel):
    """One chat message of the transcript to pre-warm."""

    role: Literal["system", "user", "assistant"] = Field(description="Message role.")
    content: str = Field(description="Message text, exactly as the next real turn will send it.")


async def metrecept_prewarm_cache(
    session_id: Annotated[str, Field(description="Session id of the conversation to keep warm; the same id the client sends on its real chat turns.")],
    messages: Annotated[list[PrewarmMessage], Field(description="The conversation's current transcript (system, user and assistant turns in order). The cached prefix is computed from it; nothing is stored.")],
    model: Annotated[str, Field(description='Anthropic model id, must start with "claude" (e.g. "claude-sonnet-4-5"); other vendors cache automatically and are refused.')],
    upstream_api_key: Annotated[str, Field(description="Optional Anthropic key for this call (else the configured upstream key env); forwarded, never stored.")] = "",
    ctx: Optional[Context] = None,
) -> str:
    body = {
        "model": model,
        "messages": [m.model_dump() if isinstance(m, BaseModel) else dict(m) for m in messages],
    }
    try:
        status, text, _ = await _post_json(
            "/chat/completions/prewarm", body, ctx,
            session_id=session_id, upstream=upstream_api_key, timeout=90.0,
        )
    except RuntimeError as exc:
        return str(exc)
    return _safe_error_body(text, status) if status >= 400 else text


_MINT_KINDS = (
    "cache_miss", "cache_hit", "cache_bypass", "finops", "api_call", "session",
    "custody", "statement", "carve", "savings", "web_fetch",
)
_MINT_HEADERS = ("X-Metrecept-Receipt", "X-Metrecept-Finops-Receipt", "X-Metrecept-Fetch-Receipt")
_JWS_RE = re.compile(r"eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+")
_VERIFY_PREFIX = "https://metrecept.co.uk/verify#"


def _jws_claims(jws: str) -> tuple[dict[str, Any], dict[str, Any]]:
    def _b64(part: str) -> dict[str, Any]:
        raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
        out = json.loads(raw)
        return out if isinstance(out, dict) else {}

    head, payload, _sig = jws.split(".")
    return _b64(head), _b64(payload)


async def metrecept_mint_receipt(
    kind: Annotated[Literal["cache_miss", "cache_hit", "cache_bypass", "finops", "api_call", "session", "custody", "statement", "carve", "savings", "web_fetch"], Field(description='Receipt kind to mint. cache_miss/finops: one fresh "mock" chat call. cache_hit: the same prompt twice, receipt from the replay. cache_bypass: fresh call with cache_control no_store. web_fetch: chat call grounded in https://example.com/. session: one tagged chat call, then the session aggregate. custody: one "access" custody record for a placeholder subject. statement: this month\'s ledger statement. carve: one carve hop over the label, disperse off. savings: savings attestation. api_call: GET through your first registered API service (needs one).')],
    label: Annotated[str, Field(description='Free text mixed into the minted request so each run is unique and recognisable, e.g. a PR or ticket id (default "metrecept-mint").')] = "metrecept-mint",
    ctx: Optional[Context] = None,
) -> str:
    try:
        base, _, _ = _cfg(ctx)
    except RuntimeError as exc:
        return str(exc)
    if kind not in _MINT_KINDS:
        return json.dumps({"error": "invalid_kind", "kinds": list(_MINT_KINDS)})
    tag = f"{label or 'metrecept-mint'} {kind} {time.time_ns()}"
    found: list[str] = []

    async with httpx.AsyncClient(timeout=90.0) as client:
        async def call(method: str, path: str, body: Optional[dict[str, Any]] = None) -> Any:
            res = await client.request(method, f"{base}{path}", headers=_headers(ctx=ctx), json=body)
            if res.status_code >= 400:
                raise _MintError(_safe_error_body(res.text, res.status_code))
            found.extend(res.headers[h] for h in _MINT_HEADERS if res.headers.get(h))
            found.extend(_JWS_RE.findall(res.text))
            try:
                return res.json()
            except ValueError:
                return None

        def chat_body(**extra: Any) -> dict[str, Any]:
            return {"model": "mock", "messages": [{"role": "user", "content": tag}], **extra}

        try:
            if kind in ("cache_miss", "finops"):
                await call("POST", "/chat/completions", chat_body())
            elif kind == "cache_hit":
                await call("POST", "/chat/completions", chat_body())
                found.clear()
                await call("POST", "/chat/completions", chat_body())
            elif kind == "cache_bypass":
                await call("POST", "/chat/completions", chat_body(cache_control="no_store"))
            elif kind == "web_fetch":
                await call("POST", "/chat/completions", chat_body(
                    fetch_web_context=True, web_urls=["https://example.com/"],
                    web_purpose="public_web_retrieval"))
            elif kind == "session":
                sid = f"metrecept-mint-{time.time_ns()}"
                await call("POST", "/chat/completions", chat_body(metrecept_session=sid))
                found.clear()
                await call("GET", f"/sessions/{_seg(sid)}")
            elif kind == "custody":
                await call("POST", "/custody", {
                    "action": "access", "subject_id": "metrecept-mint",
                    "item_sha256": hashlib.sha256(tag.encode()).hexdigest(),
                    "source": "metrecept-mint", "store": "mint"})
            elif kind == "statement":
                await call("GET", "/org/ledger/statement?month=" + time.strftime("%Y-%m", time.gmtime()))
            elif kind == "carve":
                await call("POST", "/carve", {"ingest": tag, "disperse": False})
            elif kind == "savings":
                await call("POST", "/savings/receipt", {})
            elif kind == "api_call":
                data = await call("GET", "/api_services")
                services = (data or {}).get("services") if isinstance(data, dict) else None
                if not services:
                    return json.dumps({"error": "no_api_service", "message": "api_call needs a registered API service; add one with metrecept_register_api_service."})
                svc = services[0]
                found.clear()
                await call("POST", "/api_call", {
                    "service": svc["name"], "path": svc.get("allowed_path_prefix") or "/",
                    "query": {"metrecept_mint": label or "metrecept-mint"}})
        except _MintError as exc:
            return str(exc)

    for jws in found:
        try:
            header, payload = _jws_claims(jws)
        except (ValueError, TypeError):
            continue
        if payload.get("kind") == kind:
            return json.dumps({
                "kind": kind,
                "kid": header.get("kid"),
                "iat": payload.get("iat"),
                "meter_event_id": payload.get("meter_event_id"),
                "receipt": jws,
                "verify_url": _VERIFY_PREFIX + jws,
            })
    return json.dumps({"error": "no_receipt", "message": f"The gateway returned no receipt of kind {kind}."})


class _MintError(Exception):
    pass


_TOOL_DESCRIPTIONS: dict[str, str] = {
    'fetch_web_pages': (
        "Fetch public web pages through the Metrecept compliance filter and return redacted markdown or JSON context, metered and receipted. "
        "Use it when you need the page content itself. Not for a model answer grounded in pages: pass fetch_urls to metrecept_create_chat_completion. Not for an authenticated JSON API you hold a key for: use metrecept_call_api. "
        "Call metrecept_get_fetch_policy first to pick a valid purpose and stay within its character caps; a few URLs per call is the norm. "
        "Pass the same session_id you use on chat and API calls to group them into one metrecept_get_session_receipt receipt. "
        "Behaviour: the tenant must have accepted Terms/DPA at Checkout, otherwise the call is refused. robots.txt is respected (fail-closed), PII is redacted, and login walls, 401/403 and 402 pay-per-crawl refusals are honoured, never bypassed. Never cached. Failures return JSON {\"error\", \"status\"} with secrets redacted. " + _AUTH
    ),
    'get_usage': (
        "Read the tenant's live lifetime usage meters: requests, cache hit/miss tokens and ratio, web fetches, API calls, billed USD per meter and total, today's UTC-day values, plan, billing status and whether the soft web-fetch cap is lifted. "
        "Use it for 'how much have I used / what plan am I on'. Not for per-day trends: use metrecept_get_usage_history. Not for money saved: use metrecept_get_savings. Not for one run's signed record: use metrecept_get_session_receipt. "
        "Read-only, not billed, never cached. A bad or missing key returns the gateway's 401 JSON error. " + _AUTH
    ),
    'list_models': (
        "List model ids the gateway can route chat to (mock plus examples for OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Z.ai, Qwen, xAI) and the prefix routing table. "
        "Use it before metrecept_create_chat_completion to pick a model; any id under a routed prefix is forwarded verbatim. Not for which vendors are actually configured: use metrecept_list_providers. "
        "Static list, read-only, not billed. Non-mock models need your own upstream key (BYOK). " + _AUTH
    ),
    'list_cache_trees': (
        "List every cache tree (isolated exact-replay namespace) the tenant owns, always including the default \"main\", ordered main first then by creation time. All trees come back in one call. Each tree reports its status: active, frozen or archived. "
        "Use it to find a tree_id for the other cache tools. Not for a tree's contents: use metrecept_list_cache_entries. To create, fork or promote use metrecept_manage_cache_tree; to remove a non-main tree use metrecept_delete_cache_tree. "
        "Archived trees are hidden unless include_archived=true. Read-only, not billed, live. " + _AUTH
    ),
    'list_cache_entries': (
        "List entries cached in one tree: request digest, model, token count, byte size and TTL remaining. Metadata only; never returns prompt or response content. "
        "Use it to inspect a tree or to get the digest that metrecept_evict_cache_entry needs. Get tree ids from metrecept_list_cache_trees. Page through with offset = previous offset + limit until fewer than limit entries come back. "
        "Read-only, not billed, live. " + _AUTH
    ),
    'get_savings': (
        "Read the tenant's cumulative savings ledger: cache hit ratio and hit tokens, estimated upstream spend avoided by cache replays, what Metrecept billed for hits and misses, net saving and ROI. "
        "Use it for the money view. Not for raw meters or plan: use metrecept_get_usage; for per-day meters use metrecept_get_usage_history. To share these numbers publicly use metrecept_publish_savings_receipt. "
        "Avoided-spend figures are list-price estimates (the response carries a disclaimer); billed figures are exact. Read-only, not billed, never cached. A bad or missing key returns the gateway's 401 JSON error. " + _AUTH
    ),
    'publish_savings_receipt': (
        "Publish a public, shareable savings receipt: an immutable Ed25519-signed snapshot of current savings at metrecept.co.uk/r/<token>, plus a README badge snippet. "
        "Use it when the user wants to share savings outside the tenant. Not for checking the numbers privately: use metrecept_get_savings (call it first to review). Not for a per-run record: use metrecept_get_session_receipt. "
        "Side effect: creates a public page that lives 90 days and shows only display_name, never the tenant id or key. Not billed. " + _AUTH
    ),
    'register_api_service': (
        "Register or update a third-party API service so metrecept_call_api can make receipted GET calls to it. "
        "Use it once per vendor before metrecept_call_api; confirm with metrecept_list_api_services, remove with metrecept_unregister_api_service. "
        "Stores only the non-secret shape (base URL, path prefix, auth header name, purpose); the credential travels per call as metrecept_call_api's service_key and is never stored. "
        "Re-using a name overwrites that service. Private/internal base URLs are rejected. Not billed. " + _AUTH
    ),
    'list_api_services': (
        "List the tenant's registered third-party API services: name, base URL, path prefix, auth header name and purpose. No credentials are stored, so none are returned. "
        "Use it to confirm a service name before metrecept_call_api. Register new ones with metrecept_register_api_service; remove with metrecept_unregister_api_service. "
        "Read-only, not billed, live, not paginated. " + _AUTH
    ),
    'call_api': (
        "Make a read-only GET call to a registered third-party API through the gateway and return the vendor's response body, with a signed receipt that stores only a hash of path and query. "
        "Use it for authenticated vendor JSON APIs mid-session. Register the service first with metrecept_register_api_service. Not for public web pages: use metrecept_fetch_web_pages. "
        "path must sit under the service's allowed_path_prefix (e.g. prefix \"/v1\" allows \"/v1/lookup\"); query is sent as the URL query string. Pass the same session_id as your chat and fetch calls to group them into one metrecept_get_session_receipt receipt. "
        "Billed per call at the plan rate. Unknown service returns 404 service_not_found; vendor errors and prefix violations return JSON {\"error\", \"status\"}. " + _AUTH
    ),
    'get_session_receipt': (
        "Get one signed, aggregated receipt for a session: every chat completion, web fetch and API call tagged with the same session_id, with event count, total billed USD, cache hits/misses, fetch and API counts, first/last timestamps, the compact JWS and a verify_url. "
        "Use it at the end of an agent run and put verify_url in the PR, ticket or email the run produced; anyone can verify it in a browser, no account needed. Not for a public savings snapshot: use metrecept_publish_savings_receipt. Not for tenant totals: use metrecept_get_usage. "
        "Read-only, makes no upstream call, not billed. An unknown id returns event_count 0, not an error. " + _AUTH
    ),
    'list_providers': (
        "Show which upstream vendors the gateway has configured and ready (mock, openai, anthropic and each OpenAI-compatible vendor), with BYOK header name and billing model. "
        "Use it to debug a failed metrecept_create_chat_completion or check a vendor is ready. Not for picking a model id: use metrecept_list_models. "
        "Reports key presence only; keys are never validated upstream or returned. Read-only, not billed, live. " + _AUTH
    ),
    'get_fetch_policy': (
        "Read the web-fetch compliance policy enforced for this tenant: allowed purpose values, robots.txt and PII-redaction settings, whether Terms/DPA acceptance is required, and per-source and total character caps. "
        "Use it before metrecept_fetch_web_pages or a metrecept_create_chat_completion with fetch_urls, or after a refused fetch to see which rule applied. Not for third-party APIs: metrecept_call_api uses registered services instead. "
        "Read-only, not billed. A bad or missing key returns the gateway's 401 JSON error. " + _AUTH
    ),
    'create_chat_completion': (
        "Send one user message to a model through the Metrecept gateway (OpenAI-compatible) and return the reply text; an exact repeat of a request is served from the tenant's cache. "
        "Use it for model answers, optionally grounded in public pages via fetch_urls. Not for the page content itself: use metrecept_fetch_web_pages. "
        "Start with model \"mock\" to test without an upstream key; pick real ids from metrecept_list_models. purpose only applies when fetch_urls is set; check allowed values with metrecept_get_fetch_policy. Pass one session_id across a run's chat, fetch and API calls, then read metrecept_get_session_receipt. "
        "Metered and receipted per call. Failures (bad model, missing BYOK key, refused fetch, rate limit) return JSON {\"error\", \"status\"}. " + _AUTH
    ),
    'unregister_api_service': (
        "Unregister one of the tenant's third-party API services so metrecept_call_api can no longer reach it. "
        "Use it to retire a vendor integration; check exact names with metrecept_list_api_services. Not for changing settings: re-register the same name with metrecept_register_api_service. "
        "Destructive and immediate, no undo, though no credential is lost because none is stored. Later calls and repeat unregisters return 404 service_not_found; 404 feature_disabled means API passthrough is off. Not billed. " + _AUTH
    ),
    'get_usage_history': (
        "Read the tenant's usage meters as a per-UTC-day series, oldest day first, plus window totals: requests, cache hit/miss tokens and USD, prewarm, web fetches, API calls, custody and statement meters, upstream cache tokens and billed_usd. "
        "Use it for trends or 'what did I spend each day'. Not for lifetime totals or plan: use metrecept_get_usage. Not for spend avoided: use metrecept_get_savings. "
        "Read from the durable per-day ledger; idle days are 0, nothing is estimated. Read-only, not billed. " + _AUTH
    ),
    'evict_cache_entry': (
        "Evict one cached response from a cache tree by its request digest, so the next identical request in that tree is a fresh miss sent upstream and billed as a miss. "
        "Use it to drop a stale or wrong cached answer. Get the digest from metrecept_list_cache_entries. Not for removing a whole tree: use metrecept_delete_cache_tree. "
        "Ownership: eviction removes only this tree's own copy or reference. An entry inherited from a parent is untouched; evict it in the parent. If this tree owns the bytes, trees referencing them after a promote also lose the entry. "
        "Destructive and immediate, no undo; not billed. Errors: 404 tree_missing or entry_missing (also on a repeat), 409 tree_frozen, 400 invalid_digest. " + _AUTH
    ),
    'delete_cache_tree': (
        "Delete a whole non-main cache tree: its metadata, digest index, references and the cached responses it owns. "
        "Use it to clean up after an experiment, typically after metrecept_manage_cache_tree promote. Find ids with metrecept_list_cache_trees. Not for a single entry: use metrecept_evict_cache_entry. "
        "Destructive and immediate, no undo; not billed. Refuses \"main\" (409 cannot_delete_main) and trees with children (409 tree_has_children; delete children first). Responses another tree references after a promote are kept until their TTL. A missing or already-deleted tree returns 404 tree_missing. " + _AUTH
    ),
    'manage_cache_tree': (
        "Create, fork or promote a cache tree (an isolated exact-replay namespace). "
        "Use it to isolate cache for an experiment or PR: fork main, send chat calls into the fork, promote it back when good, then remove it with metrecept_delete_cache_tree. Not for listing trees: use metrecept_list_cache_trees. Not for deleting a tree or entry: use metrecept_delete_cache_tree or metrecept_evict_cache_entry. "
        "create and fork give the new tree an empty local index that reads its parent chain copy-on-write, so it serves parent entries by reference with zero bytes copied; its own new entries stay local. "
        "promote adds references to tree_id's own entries in the target tree (bytes_copied is always 0) and leaves the child intact; it never swaps trees, main stays the default and cannot itself be promoted. "
        "Not billed; audit-logged. Errors return ok=false with status and error: 409 tree_exists, 404 parent_missing, 404 tree_missing, 409 cannot_promote_main, 409 parent_frozen, 409 tree_archived or parent_archived, 400 invalid_cache_tree. " + _AUTH
    ),
}



_TOOL_DESCRIPTIONS.update({
    'freeze_cache_tree': (
        "Freeze a cache tree so it keeps serving its cached responses but accepts no new writes, or unfreeze it (frozen=false) back to active. "
        "Use it to pin a known-good cache, for example a release branch's tree, while experiments continue in forks. Not for hiding or retiring a tree: use metrecept_archive_cache_tree. Not for removing it: use metrecept_delete_cache_tree. "
        "While frozen, misses are served upstream but not stored, eviction returns 409 tree_frozen and the tree cannot be a fork parent or promote target. Idempotent, not billed, audit-logged. "
        "Errors: 409 cannot_freeze_main, 409 tree_archived (restore it first), 404 tree_missing. "
    ),
    'archive_cache_tree': (
        "Archive a cache tree: make it read-only and hide it from metrecept_list_cache_trees, keeping every entry so it can be restored later; archived=false restores it to the status it had before (active or frozen). "
        "Use it to retire a finished experiment's tree without losing it. Not for a temporary write lock: use metrecept_freeze_cache_tree. Not for freeing storage: use metrecept_delete_cache_tree. "
        "Archived trees still serve hits, but writes, eviction, reset and freeze return 409 tree_archived, and they cannot be a fork parent or promote target. List them with include_archived=true. Idempotent, not billed, audit-logged. "
        "Errors: 409 cannot_archive_main, 404 tree_missing. "
    ),
    'prewarm_cache': (
        "Refresh an about-to-expire Anthropic prompt-cache breakpoint for a session with a one-token call, so the next real turn reads the cache instead of paying a fresh cache write. "
        "Use it from an idle timer when a long Claude conversation is about to sit past the cache TTL. Not for the gateway's own exact-replay cache (it never touches it): use metrecept_create_chat_completion. Not for OpenAI or other vendors, whose prompt caching is automatic. "
        "Sends your transcript and your upstream key exactly like a chat call; nothing is stored. Unbilled by the gateway (returns billed:false, billed_usd 0; the vendor still charges its own tokens) and audit-logged. "
        "Errors: 400 prewarm_unsupported_model for non-claude models, 400 cache_autopilot_disabled when the gateway has cache autopilot off, 401/402 for a missing upstream key. "
    ),
    'mint_receipt': (
        "Mint one fresh signed Ed25519 receipt (compact JWS) of a chosen kind by making the smallest real gateway call that produces it, and return the receipt with its kid, iat and a verify_url. "
        "Use it to show or test receipt verification end to end, or to attach a real receipt to a demo or bug report. Not for a run you already made: use metrecept_get_session_receipt. Not for a public savings page: use metrecept_publish_savings_receipt. "
        "Each kind makes real calls billed as normal (cache_miss, finops, cache_bypass, web_fetch and api_call are metered; cache_hit bills one miss then a hit). Anyone can check verify_url in a browser against the public key directory. "
        "Errors come back as JSON {\"error\", ...}: no_api_service when kind api_call has no registered service, no_receipt when none of that kind came back. "
    ),
})
for _short in ('freeze_cache_tree', 'archive_cache_tree', 'prewarm_cache', 'mint_receipt'):
    _TOOL_DESCRIPTIONS[_short] += _AUTH


# MCP has no grouping primitive in the spec (SEP-2084 "Primitive Grouping" was
# not accepted), so tools are grouped by the METRECEPT_TOOLSETS env: a comma
# list of core, cache, receipts (default: all). Each tool carries its group in
# _meta["io.metrecept/toolset"] and as a prefix on its display title.
TOOLSETS: dict[str, tuple[str, ...]] = {
    "cache": (
        "list_cache_trees", "list_cache_entries", "manage_cache_tree",
        "evict_cache_entry", "delete_cache_tree", "freeze_cache_tree",
        "archive_cache_tree", "prewarm_cache",
    ),
    "receipts": ("mint_receipt", "get_session_receipt", "publish_savings_receipt"),
}
_TOOLSET_TITLES = {"core": "Core", "cache": "Cache", "receipts": "Receipts"}
TOOLSET_META_KEY = "io.metrecept/toolset"


def toolset_of(tool_name: str) -> str:
    short = tool_name.removeprefix("metrecept_")
    for group, names in TOOLSETS.items():
        if short in names:
            return group
    return "core"


def enabled_toolsets(raw: Optional[str] = None) -> set[str]:
    if raw is None:
        raw = os.environ.get("METRECEPT_TOOLSETS", "")
    picked = {p.strip().lower() for p in raw.split(",") if p.strip()}
    if not picked or "all" in picked:
        return set(_TOOLSET_TITLES)
    unknown = picked - set(_TOOLSET_TITLES)
    if unknown:
        raise SystemExit(
            f"METRECEPT_TOOLSETS: unknown toolset(s) {sorted(unknown)}; choose from core, cache, receipts, all"
        )
    return picked


def _apply_toolsets(raw: Optional[str] = None) -> None:
    enabled = enabled_toolsets(raw)
    for tool in list(mcp._tool_manager.list_tools()):
        group = toolset_of(tool.name)
        if group not in enabled:
            mcp.remove_tool(tool.name)
            continue
        label = tool.name.removeprefix("metrecept_").replace("_", " ").capitalize()
        label = re.sub(r"\bapi\b", "API", label, flags=re.I)
        tool.title = f"{_TOOLSET_TITLES[group]}: {label}"
        tool.meta = {**(tool.meta or {}), TOOLSET_META_KEY: group}


def _register_tools() -> None:
    for short, desc in _TOOL_DESCRIPTIONS.items():
        mcp.tool(name=f"metrecept_{short}", description=desc)(globals()[f"metrecept_{short}"])


_register_tools()
_apply_toolsets()


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
