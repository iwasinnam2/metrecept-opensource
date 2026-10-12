#!/usr/bin/env python3
"""Verify a withOhm cache-hit receipt from a cold start.

Usage:
  python demo/verify_receipt.py <receipt-jws> [--base https://api.metrecept.co.uk]

Takes the X-Ohm-Receipt response header value, fetches the public JWKS from
/.well-known/http-message-signatures-directory on the given base, resolves
the signing key by the JWS `kid` (RFC 7638 thumbprint), and verifies the
Ed25519 signature. Prints the receipt payload on success; exits non-zero on
any mismatch. Requires only `cryptography` (no withOhm code, on purpose —
the point is that a stranger can check the claim).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.request

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DIRECTORY_PATH = "/.well-known/http-message-signatures-directory"


def b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def jwk_thumbprint(jwk: dict) -> str:
    canonical = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"]},
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", help="X-Ohm-Receipt header value (compact JWS)")
    parser.add_argument("--base", default="https://api.metrecept.co.uk")
    args = parser.parse_args()

    parts = args.receipt.strip().split(".")
    if len(parts) != 3:
        print("FAIL: not a compact JWS (expected three dot-separated parts)")
        return 1
    header = json.loads(b64u_decode(parts[0]))
    if header.get("alg") != "EdDSA":
        print(f"FAIL: unexpected alg {header.get('alg')!r}")
        return 1

    directory_url = args.base.rstrip("/") + DIRECTORY_PATH
    with urllib.request.urlopen(directory_url, timeout=15) as res:
        directory = json.loads(res.read().decode("utf-8"))

    kid = header.get("kid", "")
    jwk = next(
        (
            k
            for k in directory.get("keys", [])
            if k.get("kty") == "OKP"
            and k.get("crv") == "Ed25519"
            and (k.get("kid") == kid or jwk_thumbprint(k) == kid)
        ),
        None,
    )
    if jwk is None:
        print(f"FAIL: no Ed25519 key with kid={kid!r} in {directory_url}")
        return 1

    public = Ed25519PublicKey.from_public_bytes(b64u_decode(jwk["x"]))
    try:
        public.verify(
            b64u_decode(parts[2]), (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception:  # noqa: BLE001
        print("FAIL: signature does not verify — receipt is forged or altered")
        return 1

    payload = json.loads(b64u_decode(parts[1]))
    print("OK: signature verifies against", directory_url)
    print(summarize(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _short(value: object) -> str:
    text = str(value or "")
    return f"{text[:16]}\u2026" if len(text) > 16 else text


def summarize(payload: dict) -> str:
    """One line in words. The signature check above is the same for every
    kind; only this line changes. Unknown kinds are still verified."""
    kind = payload.get("kind", "?")
    if kind == "cache_hit":
        line = (
            f"cache_hit: model={payload.get('model')!r} tokens_replayed={payload.get('tokens_replayed')} "
            f"pipe_usd={payload.get('pipe_usd')} plane={payload.get('plane')}"
        )
    elif kind in ("cache_miss", "cache_bypass"):
        tree = payload.get("tree_id") or "main"
        tail = (
            f"filled tree={tree} (the window the next HIT replays from)"
            if kind == "cache_miss"
            else f"not cached (caller asked to bypass tree={tree})"
        )
        line = (
            f"{kind}: model={payload.get('model')!r} pipe_usd={payload.get('pipe_usd')} "
            f"plane={payload.get('plane')} request_sha256={_short(payload.get('request_sha256'))} {tail}"
        )
    elif kind == "api_call":
        line = f"api_call: pipe_usd={payload.get('pipe_usd')} request_sha256={_short(payload.get('request_sha256'))}"
    elif kind == "session":
        line = (
            f"session (id hashed, never embedded raw): event_count={payload.get('event_count')} "
            f"api_calls={payload.get('api_calls')} cache_hits={payload.get('cache_hits')} "
            f"cache_misses={payload.get('cache_misses')} fetches={payload.get('fetches')} "
            f"pipe_usd={payload.get('pipe_usd')}"
        )
    else:
        line = f"kind={kind!r} (no one-line summary for this kind; verified all the same)"
    if payload.get("response_sha256"):
        line += f" response_sha256={_short(payload.get('response_sha256'))}"
    return line


if __name__ == "__main__":
    sys.exit(main())
