#!/usr/bin/env python3
"""Verify a Metrecept receipt from a cold start.

Usage:
  python demo/verify_receipt.py <receipt-jws> [--base https://api.metrecept.co.uk]
  python demo/verify_receipt.py <receipt-jws> --attest <X-Metrecept-Attest-jws>

Takes the X-Metrecept-Receipt (legacy X-Ohm-Receipt) response header value,
or a https://metrecept.co.uk/verify#<jws> link, fetches the public JWKS from
/.well-known/http-message-signatures-directory on the given base, resolves
the signing key by the JWS `kid` (RFC 7638 thumbprint), and verifies the
Ed25519 signature. Prints the receipt payload on success; exits non-zero on
any mismatch. Requires only `cryptography` (no Metrecept code, on purpose -
the point is that a stranger can check the claim).

With --attest it also checks the other half of a co-signed receipt: the
caller's own Ed25519 signature over the request body (sent as the
X-Metrecept-Attest header) and the binding between the two
(receipt.attest_sha256 == sha256(attestation),
receipt.body_sha256 == attestation.body_sha256). Two parties, one count.
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
ATTEST_TYP = "metrecept-attest+jws"


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


def extract_jws(text: str) -> str:
    """Accept a bare compact JWS or a verify link with the JWS in the fragment."""
    text = text.strip()
    if "#" in text and "://" in text:
        return text.split("#", 1)[1].strip()
    return text


def verify(receipt: str, base: str = "https://api.metrecept.co.uk", attest: str = "") -> tuple[bool, dict | None, list[str]]:
    """Return (ok, payload, lines). Network: one GET of the key directory."""
    lines: list[str] = []
    parts = extract_jws(receipt).split(".")
    if len(parts) != 3:
        return False, None, ["FAIL: not a compact JWS (expected three dot-separated parts)"]
    header = json.loads(b64u_decode(parts[0]))
    if header.get("alg") != "EdDSA":
        return False, None, [f"FAIL: unexpected alg {header.get('alg')!r}"]

    directory_url = base.rstrip("/") + DIRECTORY_PATH
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
        return False, None, [f"FAIL: no Ed25519 key with kid={kid!r} in {directory_url}"]

    public = Ed25519PublicKey.from_public_bytes(b64u_decode(jwk["x"]))
    try:
        public.verify(
            b64u_decode(parts[2]), (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception:  # noqa: BLE001
        return False, None, ["FAIL: signature does not verify - receipt is forged or altered"]

    payload = json.loads(b64u_decode(parts[1]))
    lines.append(f"OK: signature verifies against {directory_url}")
    lines.append(summarize(payload))
    if attest:
        problem = check_cosigned(payload, attest.strip())
        if problem:
            lines.append(f"FAIL (co-sign): {problem}")
            return False, payload, lines
        lines.append(
            f"OK (co-sign): caller key {payload.get('attest_kid')} signed "
            f"body_sha256 {payload.get('body_sha256')} and the gateway bound that "
            "attestation into this receipt"
        )
    elif payload.get("attest_sha256"):
        lines.append(
            "NOTE: this receipt is co-signed (attest_sha256 present). Pass "
            "--attest <X-Metrecept-Attest JWS> to check the caller's half."
        )
    return True, payload, lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "receipt",
        help="X-Metrecept-Receipt header value (compact JWS) or a "
        "https://metrecept.co.uk/verify#<jws> link",
    )
    parser.add_argument("--base", default="https://api.metrecept.co.uk")
    parser.add_argument(
        "--attest",
        default="",
        help="The X-Metrecept-Attest JWS the caller sent with this request. "
        "When given, also checks the caller's own signature and that the "
        "receipt binds exactly this attestation (co-signed receipt).",
    )
    args = parser.parse_args()

    ok, payload, lines = verify(args.receipt, args.base, args.attest)
    for line in lines:
        print(line)
    if payload is not None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


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
    if payload.get("attest_sha256"):
        line += f" co-signed(attest_kid={payload.get('attest_kid')})"
    return line


def check_cosigned(payload: dict, attest_jws: str) -> str:
    """Return "" when the attestation verifies on its own embedded key and
    the receipt binds exactly it; otherwise one sentence saying what failed.

    Receipt side (already signature-checked above): attest_sha256,
    attest_kid, body_sha256. Attestation side: EdDSA compact JWS, typ
    metrecept-attest+jws, header.jwk OKP/Ed25519 with kid == RFC 7638
    thumbprint, payload {"v":1,"body_sha256":<hex>,"iat":<unix>}.
    """
    expected = payload.get("attest_sha256")
    if not expected:
        return "receipt carries no attest_sha256; it was not co-signed"
    if hashlib.sha256(attest_jws.encode("ascii")).hexdigest() != expected:
        return "this attestation is not the one bound into the receipt"
    parts = attest_jws.split(".")
    if len(parts) != 3 or not all(parts):
        return "attestation is not a compact JWS"
    try:
        header = json.loads(b64u_decode(parts[0]))
        body = json.loads(b64u_decode(parts[1]))
        sig = b64u_decode(parts[2])
    except Exception:  # noqa: BLE001
        return "attestation segments do not decode"
    if header.get("alg") != "EdDSA" or header.get("typ") != ATTEST_TYP:
        return f"attestation alg/typ must be EdDSA/{ATTEST_TYP}"
    jwk = header.get("jwk") or {}
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519" or not jwk.get("x"):
        return "attestation header must carry an OKP/Ed25519 jwk"
    if header.get("kid") != jwk_thumbprint(jwk):
        return "attestation kid is not the RFC 7638 thumbprint of its jwk"
    if header.get("kid") != payload.get("attest_kid"):
        return "receipt attest_kid does not match the attestation key"
    try:
        Ed25519PublicKey.from_public_bytes(b64u_decode(jwk["x"])).verify(
            sig, (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception:  # noqa: BLE001
        return "attestation signature does not verify"
    if body.get("v") != 1:
        return "attestation v must be 1"
    if body.get("body_sha256") != payload.get("body_sha256"):
        return "attestation body_sha256 differs from the receipt's body_sha256"
    return ""


if __name__ == "__main__":
    sys.exit(main())
