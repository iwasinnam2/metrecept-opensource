"""The receipt as a link — pip twin of ``at_utility.receipts.verify_url``.

A signed receipt in a response header dies at the client. A URL survives
being pasted into the PR body, the ticket, the email, the Slack message
the agent is already producing. ``receipt_trailer`` returns that one line.
Whoever opens it lands on https://metrecept.co.uk/verify, which reads the
JWS out of the URL fragment and checks Ed25519 in their browser against
the public JWKS — no account. Fragment, never query string: the receipt
is not written to anyone's access log.

Stdlib only, on purpose. Keep ``PUBLIC_VERIFY_BASE`` in lockstep with
``at_utility.receipts.PUBLIC_VERIFY_BASE`` (tests/test_receipt_link_sdk.py).
Design: docs/superpowers/specs/2026-10-09-receipt-link-distribution-design.md
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

PUBLIC_VERIFY_BASE = "https://metrecept.co.uk/verify"
VERIFY_HEADER_NAME = "x-metrecept-verify"
RECEIPT_HEADER_NAMES = ("x-metrecept-receipt",)
RECEIPT_SSE_KEY = "metrecept"
# The stamped link (twin of ``at_utility.receipts.share_link``): unfurlers
# fetch without the fragment, so the kind rides in the query and the site
# serves "Metrecept | 1x Signed Receipt · <kind>" as the preview; the JWS
# stays after the # and is handed to /verify unchanged.
RECEIPT_LINK_BASE = "https://metrecept.co.uk/functions/receipt"
LINK_KINDS = frozenset(
    {"session", "cache_hit", "cache_miss", "cache_bypass", "api_call", "custody", "statement", "carve", "disperse"}
)


def verify_url(jws: str) -> str:
    """Public, no-login verify link for one compact JWS."""
    text = (jws or "").strip()
    if text.count(".") != 2 or not all(text.split(".")):
        raise ValueError("verify_url expects a compact JWS (three dot-separated parts)")
    return f"{PUBLIC_VERIFY_BASE}#{text}"


def receipt_kind(jws: str) -> str:
    """The ``kind`` the receipt's own payload carries (unverified read of the
    middle segment), ``""`` when it cannot be read."""
    parts = (jws or "").strip().split(".")
    if len(parts) != 3 or not all(parts):
        return ""
    try:
        import base64

        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, TypeError):
        return ""
    return str(payload.get("kind") or "") if isinstance(payload, dict) else ""


def share_link(jws: str) -> str:
    """The link to paste where a preview will be drawn: stamped with the
    receipt's kind when the site names that kind, else ``verify_url``."""
    url = verify_url(jws)
    kind = receipt_kind(jws)
    if kind in LINK_KINDS:
        return f"{RECEIPT_LINK_BASE}?kind={kind}#{jws.strip()}"
    return url


def _lower(headers: Mapping[str, Any]) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in headers.items() if v is not None}


def verify_url_from_headers(headers: Mapping[str, Any]) -> str:
    """Link from a response's headers: X-Metrecept-Verify if present, else
    built from either receipt header name. ``""`` when the response carried
    no receipt (a fresh MISS on an older edge, for example)."""
    lowered = _lower(headers)
    direct = lowered.get(VERIFY_HEADER_NAME, "").strip()
    if direct:
        return direct
    for name in RECEIPT_HEADER_NAMES:
        jws = lowered.get(name, "").strip()
        if jws:
            try:
                return verify_url(jws)
            except ValueError:
                return ""
    return ""


def receipt_trailer(source: Mapping[str, Any], *, label: str = "Receipt") -> str:
    """One markdown line to append to the artefact the agent produced.

    ``source`` is either a response-headers mapping (any case) or the JSON
    body of ``GET /v1/sessions/{id}`` (``verify_url`` / ``receipt`` keys).
    Returns ``"<label>: <url>"`` or ``""`` when there is nothing to link —
    a run without a receipt is a run without a link, not a failure.
    """
    url = ""
    if "verify_url" in source or "receipt" in source:
        url = str(source.get("verify_url") or "").strip()
        if not url and source.get("receipt"):
            try:
                url = verify_url(str(source["receipt"]))
            except ValueError:
                url = ""
    else:
        url = verify_url_from_headers(source)
    return f"{label}: {url}" if url else ""


def receipt_from_sse_lines(lines: Iterable[str]) -> str:
    """The receipt out of a captured stream: the ``data:`` chunk whose
    ``metrecept.receipt`` is a compact JWS. ``""`` when the stream carried
    none (a stream that did not finish cleanly carries none)."""
    for raw in lines:
        line = str(raw).strip()
        if not line.startswith("data:"):
            continue
        body = line[5:].strip()
        if not body or body == "[DONE]":
            continue
        try:
            obj = json.loads(body)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        tag = obj.get(RECEIPT_SSE_KEY)
        jws = str((tag or {}).get("receipt") or "").strip() if isinstance(tag, dict) else ""
        if jws.count(".") == 2 and all(jws.split(".")):
            return jws
    return ""


__all__ = [
    "LINK_KINDS",
    "PUBLIC_VERIFY_BASE",
    "RECEIPT_HEADER_NAMES",
    "RECEIPT_LINK_BASE",
    "RECEIPT_SSE_KEY",
    "VERIFY_HEADER_NAME",
    "receipt_from_sse_lines",
    "receipt_kind",
    "share_link",
    "receipt_trailer",
    "verify_url",
    "verify_url_from_headers",
]
