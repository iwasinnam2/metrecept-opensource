"""In-house wrap — stdlib client for pip users.

Keep digest extras in lockstep with ``at_utility.cache.inhouse_digest_extras``.

Every ``/inhouse/check`` HIT response is locally, fail-open checked against
the signed receipt it may carry (``at_utility_sdk.receipt_check`` — see
docs/superpowers/specs/2026-09-02-receipt-verify-distribution-design.md).
A missing receipt never raises; only a present-and-invalid one logs a
warning.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Sequence

from at_utility_sdk.receipt_check import check_receipt

HttpPost = Callable[
    [str, dict[str, Any]],
    tuple[int, Mapping[str, str], dict[str, Any]],
]


def _normalize_content(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _inhouse_extras(
    *,
    temperature: Any = None,
    max_tokens: Any = None,
    cache_control: Any = None,
) -> dict[str, Any]:
    return {
        "fetch_web_context": False,
        "web_query": None,
        "web_urls": [],
        "web_purpose": None,
        "web_format": None,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "cache_control": cache_control,
    }


def packet_digest(
    *,
    model: str,
    messages: Sequence[dict[str, Any]],
    temperature: Any = None,
    max_tokens: Any = None,
    cache_control: Any = None,
) -> str:
    msgs = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            normalized = _normalize_content(content)
            if normalized != content:
                msg = {**msg, "content": normalized}
        msgs.append(msg)
    payload = {
        "model": model,
        "messages": msgs,
        "extras": _inhouse_extras(
            temperature=temperature,
            max_tokens=max_tokens,
            cache_control=cache_control,
        ),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _normalize_base(base_url: str) -> str:
    root = (base_url or "").rstrip("/")
    if not root.endswith("/v1"):
        root = f"{root}/v1"
    return root


def _header(headers: Mapping[str, str], name: str) -> str:
    want = name.lower()
    for k, v in headers.items():
        if k.lower() == want:
            return str(v)
    return ""


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _urllib_post(
    url: str, api_key: str, payload: dict[str, Any]
) -> tuple[int, Mapping[str, str], dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            return int(resp.status), dict(resp.headers), body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"error": raw}
        return int(exc.code), dict(exc.headers or {}), body


def wrap_generate(
    generate: Callable[[Sequence[dict[str, Any]]], str],
    *,
    api_key: str,
    base_url: str,
    model: str = "inhouse",
    http_post: HttpPost | None = None,
    local_blobs: dict[str, str] | None = None,
) -> Callable[[Sequence[dict[str, Any]]], str]:
    root = _normalize_base(base_url)
    blobs: dict[str, str] = local_blobs if local_blobs is not None else {}

    def post(path: str, payload: dict[str, Any]) -> tuple[int, Mapping[str, str], dict[str, Any]]:
        if http_post is not None:
            return http_post(path, payload)
        return _urllib_post(f"{root}{path}", api_key, payload)

    def wrapped(messages: Sequence[dict[str, Any]]) -> str:
        msgs = list(messages)
        digest = packet_digest(model=model, messages=msgs)
        if digest in blobs:
            status, headers, body = post("/inhouse/check", {"model": model, "digest": digest})
            if status >= 400:
                raise RuntimeError(f"inhouse check failed ({status}): {body}")
            check_receipt(headers, base_url=base_url)
            return blobs[digest]
        status, headers, body = post("/inhouse/check", {"model": model, "digest": digest})
        if status >= 400:
            raise RuntimeError(f"inhouse check failed ({status}): {body}")
        cache = _header(headers, "x-at-cache").upper()
        if cache == "HIT" or body.get("hit") is True:
            check_receipt(headers, base_url=base_url)
            content = generate(msgs)
            blobs[digest] = content
            return content
        token = body.get("wrap_token")
        if not token:
            raise RuntimeError("inhouse check MISS with no wrap_token")
        content = generate(msgs)
        blobs[digest] = content
        status, _headers, committed = post(
            "/inhouse/commit",
            {"wrap_token": token, "total_tokens": _approx_tokens(content)},
        )
        if status >= 400:
            raise RuntimeError(f"inhouse commit failed ({status}): {committed}")
        # The receipt check is intentionally not hooked on the commit path,
        # so absence stays silent here (fail-open).
        return content

    return wrapped
