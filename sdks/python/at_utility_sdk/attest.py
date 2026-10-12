"""Co-sign the crossing: the caller's own signature over the body it sends.

A Metrecept receipt proves the pipe's key signed a count. On its own that
is one party's word. ``attest_headers`` adds the caller's Ed25519 signature
over the request body (``X-Metrecept-Attest``); the pipe verifies it
against the body it received and binds its hash into the receipt. The
receipt then carries ``attest_sha256``, ``attest_kid``, ``body_sha256``,
and neither party could have minted it alone.

    from at_utility_sdk.attest import new_attest_key, attest_headers, check_cosigned

    key = new_attest_key()                      # keep it; it names you
    body = {"model": "mock", "messages": [{"role": "user", "content": "hi"}]}
    headers = attest_headers(body, key)         # {"X-Metrecept-Attest": <jws>}
    resp = client.chat.completions.with_raw_response.create(
        **body, extra_headers=headers
    )
    receipt = resp.headers["x-metrecept-receipt"]
    payload = check_receipt(receipt)            # pipe's half, public key
    check_cosigned(payload, headers["X-Metrecept-Attest"])  # your half + binding

``body_sha256`` is SHA-256 over canonical JSON (sorted keys, no
whitespace, UTF-8, non-ASCII unescaped) of the dict you pass, so you do
not need to control your HTTP library's serialiser. Pass the same dict you
send. If the pipe's view of the body differs, it answers 400
``attest_invalid`` rather than minting an unbound receipt.

Requires ``cryptography`` (loaded lazily; ``openai_client`` never imports
this module). Mirrors ``at_utility.attest`` on the gateway; keep the two
in lockstep (tests/test_attest.py).
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any, Optional

ATTEST_HEADER = "X-Metrecept-Attest"
ATTEST_TYP = "metrecept-attest+jws"
ATTEST_V = 1


class AttestError(ValueError):
    pass


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical_body_sha256(body: Any) -> str:
    """SHA-256 hex over canonical JSON of a dict/list (or raw JSON text/bytes)."""
    if isinstance(body, (bytes, bytearray)):
        body = json.loads(bytes(body).decode("utf-8"))
    elif isinstance(body, str):
        body = json.loads(body)
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def thumbprint(jwk: dict[str, Any]) -> str:
    """RFC 7638 over the OKP required members only: crv, kty, x."""
    members = {"crv": jwk.get("crv"), "kty": jwk.get("kty"), "x": jwk.get("x")}
    canonical = json.dumps(members, separators=(",", ":"), sort_keys=True)
    return _b64u(hashlib.sha256(canonical.encode("ascii")).digest())


def new_attest_key():
    """Fresh Ed25519 private key. Persist it: ``attest_kid`` in every receipt
    you co-sign is this key's thumbprint, and that is how your receipts are
    recognised as yours. ``export_seed`` / ``load_seed`` round-trip it."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def export_seed(key) -> str:
    """base64url of the 32-byte private seed. Secret. Store like an API key."""
    from cryptography.hazmat.primitives import serialization

    raw = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    return _b64u(raw)


def load_seed(seed_b64u: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = _b64u_decode(seed_b64u.strip())
    if len(raw) != 32:
        raise AttestError("attest seed must be 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(raw)


def public_jwk(key) -> dict[str, str]:
    from cryptography.hazmat.primitives import serialization

    x = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    members = {"crv": "Ed25519", "kty": "OKP", "x": _b64u(x)}
    return {**members, "kid": thumbprint(members)}


def sign_attestation(body: Any, key, *, created: Optional[int] = None) -> str:
    """Compact JWS for ``X-Metrecept-Attest`` over ``body`` (the dict you send)."""
    jwk = public_jwk(key)
    header = {
        "alg": "EdDSA",
        "typ": ATTEST_TYP,
        "kid": jwk["kid"],
        "jwk": {"kty": jwk["kty"], "crv": jwk["crv"], "x": jwk["x"]},
    }
    payload = {
        "v": ATTEST_V,
        "body_sha256": canonical_body_sha256(body),
        "iat": int(created if created is not None else time.time()),
    }
    signing_input = (
        _b64u(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
        + "."
        + _b64u(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    )
    return signing_input + "." + _b64u(key.sign(signing_input.encode("ascii")))


def attest_headers(body: Any, key, *, created: Optional[int] = None) -> dict[str, str]:
    """``{"X-Metrecept-Attest": <jws>}`` to spread into ``extra_headers``."""
    return {ATTEST_HEADER: sign_attestation(body, key, created=created)}


def check_cosigned(receipt_payload: dict[str, Any], attest_jws: str) -> dict[str, Any]:
    """Offline check of the caller's half and the binding.

    ``receipt_payload`` must already be signature-verified against the
    pipe's published key (``check_receipt`` / scripts/verify_receipt.py).
    Verifies: sha256(attest_jws) == receipt.attest_sha256; attestation is an
    EdDSA JWS of typ metrecept-attest+jws whose header.jwk is OKP/Ed25519
    with kid == RFC 7638 thumbprint == receipt.attest_kid; the signature
    verifies on that key; attestation.body_sha256 == receipt.body_sha256.
    Returns the attestation payload. Raises AttestError.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    expected = receipt_payload.get("attest_sha256")
    if not expected:
        raise AttestError("receipt carries no attest_sha256; it was not co-signed")
    text = (attest_jws or "").strip()
    if hashlib.sha256(text.encode("ascii")).hexdigest() != expected:
        raise AttestError("this attestation is not the one bound into the receipt")
    parts = text.split(".")
    if len(parts) != 3 or not all(parts):
        raise AttestError("attestation is not a compact JWS")
    try:
        header = json.loads(_b64u_decode(parts[0]))
        payload = json.loads(_b64u_decode(parts[1]))
        sig = _b64u_decode(parts[2])
    except Exception as exc:  # noqa: BLE001
        raise AttestError("attestation segments do not decode") from exc
    if header.get("alg") != "EdDSA" or header.get("typ") != ATTEST_TYP:
        raise AttestError(f"attestation alg/typ must be EdDSA/{ATTEST_TYP}")
    jwk = header.get("jwk") or {}
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519" or not jwk.get("x"):
        raise AttestError("attestation header must carry an OKP/Ed25519 jwk")
    kid = header.get("kid")
    if kid != thumbprint(jwk):
        raise AttestError("attestation kid is not the RFC 7638 thumbprint of its jwk")
    if kid != receipt_payload.get("attest_kid"):
        raise AttestError("receipt attest_kid does not match the attestation key")
    try:
        Ed25519PublicKey.from_public_bytes(_b64u_decode(jwk["x"])).verify(
            sig, (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception as exc:  # noqa: BLE001
        raise AttestError("attestation signature does not verify") from exc
    if payload.get("v") != ATTEST_V:
        raise AttestError(f"attestation v must be {ATTEST_V}")
    if payload.get("body_sha256") != receipt_payload.get("body_sha256"):
        raise AttestError("attestation body_sha256 differs from the receipt's body_sha256")
    return payload


__all__ = [
    "ATTEST_HEADER",
    "ATTEST_TYP",
    "AttestError",
    "attest_headers",
    "canonical_body_sha256",
    "check_cosigned",
    "export_seed",
    "load_seed",
    "new_attest_key",
    "public_jwk",
    "sign_attestation",
    "thumbprint",
]
