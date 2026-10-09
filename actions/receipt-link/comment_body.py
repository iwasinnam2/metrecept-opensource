#!/usr/bin/env python3
"""Build the PR comment for one Metrecept session receipt. Pure; stdlib only.

The comment carries the verify link and the signed counts. It says what the
link proves and does not. It never fabricates a link for a session that
minted no receipt.
Design: docs/superpowers/specs/2026-10-09-receipt-link-distribution-design.md
"""

from __future__ import annotations

PUBLIC_VERIFY_BASE = "https://metrecept.co.uk/verify"

HONESTY = (
    "This link proves the Metrecept key signed this record of the run; "
    "anyone can check it in their browser against the public key directory, "
    "no account. It does not grade the work, and it did not stop anything."
)


def _verify_url(session: dict) -> str:
    url = str(session.get("verify_url") or "").strip()
    if url:
        return url
    jws = str(session.get("receipt") or "").strip()
    if jws.count(".") == 2 and all(jws.split(".")):
        return f"{PUBLIC_VERIFY_BASE}#{jws}"
    return ""


def build_comment(session: dict) -> str:
    sid = str(session.get("session_id") or "")
    count = int(session.get("event_count") or 0)
    url = _verify_url(session)
    if count <= 0 or not url:
        return (
            "### Metrecept session receipt\n\n"
            f"No events were tagged with session `{sid}`, so no receipt was minted. "
            "A run without a receipt is a run without a link, not a failed run.\n"
        )
    pipe = float(session.get("pipe_usd") or 0.0)
    parts = [
        f"{count} events",
        f"${pipe:.4f} pipe",
        f"{int(session.get('cache_hits') or 0)} cache hits",
        f"{int(session.get('cache_misses') or 0)} misses",
    ]
    for key, label in (("api_calls", "API calls"), ("fetches", "fetches"), ("cache_bypasses", "bypasses")):
        n = int(session.get(key) or 0)
        if n:
            parts.append(f"{n} {label}")
    return (
        "### Metrecept session receipt\n\n"
        f"Receipt: {url}\n\n"
        f"{' · '.join(parts)} · session `{sid}`\n\n"
        f"{HONESTY}\n"
    )
