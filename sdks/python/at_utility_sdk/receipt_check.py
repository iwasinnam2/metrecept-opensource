"""Fail-open local check of Metrecept's signed receipt header — pip twin.

Deliberately duplicated (not imported) from the same stranger-verifier
algorithm already shipped independently in ``scripts/verify_receipt.py``,
``open-repo/demo/verify_receipt.py``, and ``site/src/lib/receiptVerify.ts``:
fetch the public JWKS, resolve the signing key by ``kid``, verify the
Ed25519 signature. This module's only import outside stdlib is
``cryptography``, on purpose, so a pip-installed caller can audit it
without trusting anything else in this package either. See docs/RECEIPTS.md.

A receipt is only minted on a cache HIT; a fresh commit never carries one.
So a missing header here is expected, not a signal, and ``check_receipt``
never warns about absence — only about a receipt that *is* present and
fails to verify, or a JWKS directory that cannot be reached. Never raises.

Used automatically by ``wrap_generate`` (see ``inhouse.py``), and exported
for manual use by ``openai_client`` callers via ``.with_raw_response``
(``openai_client`` returns a bare ``openai.OpenAI(...)`` client with no
header-interception point, so there is nothing to hook automatically
there — see docs/superpowers/specs/2026-09-02-receipt-verify-distribution-
design.md).

Keep this module in lockstep with ``src/at_utility/receipt_check.py`` (same
relationship this package's ``packet_digest`` already has with
``at_utility.cache.inhouse_digest_extras``).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.request
from typing import Any, Mapping, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

log = logging.getLogger("at_utility_sdk.receipt_check")

RECEIPT_HEADER_NAMES = ("x-ohm-receipt", "x-metrecept-receipt")
DIRECTORY_PATH = "/.well-known/http-message-signatures-directory"

# API root -> {kid: jwk}. Process-lifetime; refetched only on a cache-miss
# kid, so key rotation is picked up without a network call on every check.
_jwks_cache: dict[str, dict[str, dict[str, str]]] = {}


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _jwk_thumbprint(jwk: dict) -> str:
    canonical = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"]},
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _receipt_header(headers: Mapping[str, Any]) -> str:
    lowered = {str(k).lower(): v for k, v in headers.items()}
    for name in RECEIPT_HEADER_NAMES:
        value = lowered.get(name)
        if value:
            return str(value)
    return ""


def _api_root(base_url: str) -> str:
    root = (base_url or "").rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    return root


def _fetch_directory(root: str) -> Optional[dict]:
    directory_url = root + DIRECTORY_PATH
    try:
        with urllib.request.urlopen(directory_url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail-open, log and move on
        log.warning(
            "metrecept receipt check: could not fetch %s (%s)", directory_url, exc
        )
        return None


def _resolve_jwk(root: str, kid: str) -> Optional[dict]:
    cached = _jwks_cache.setdefault(root, {})
    if kid in cached:
        return cached[kid]
    directory = _fetch_directory(root)
    if directory is None:
        return None
    for jwk in directory.get("keys", []):
        if jwk.get("kty") == "OKP" and jwk.get("crv") == "Ed25519":
            thumb = _jwk_thumbprint(jwk)
            cached[thumb] = jwk
            published = jwk.get("kid")
            if published:
                cached[published] = jwk
    if kid not in cached:
        log.warning(
            "metrecept receipt check: no Ed25519 key with kid=%r in %s%s",
            kid,
            root,
            DIRECTORY_PATH,
        )
        return None
    return cached[kid]


def check_receipt(headers: Mapping[str, Any], *, base_url: str) -> str:
    """Fail-open check of a Metrecept signed receipt header, if present.

    Returns ``"absent"`` (no header — expected on a fresh commit, silent),
    ``"valid"`` (signature verified), or ``"invalid"`` (present but did not
    verify, or the JWKS directory could not be resolved — one warning was
    already logged). Never raises; callers should not branch on failure.

    Manual usage with ``openai_client``::

        from at_utility_sdk import openai_client, check_receipt

        client = openai_client("sk-at-...")
        resp = client.chat.completions.with_raw_response.create(...)
        check_receipt(resp.headers, base_url=str(client.base_url))
        completion = resp.parse()
    """
    jws = _receipt_header(headers)
    if not jws:
        return "absent"

    parts = jws.split(".")
    if len(parts) != 3:
        log.warning(
            "metrecept receipt check: malformed receipt header (not a compact JWS)"
        )
        return "invalid"

    try:
        header = json.loads(_b64u_decode(parts[0]))
    except Exception as exc:  # noqa: BLE001
        log.warning("metrecept receipt check: could not decode receipt header (%s)", exc)
        return "invalid"

    if header.get("alg") != "EdDSA":
        log.warning("metrecept receipt check: unexpected alg %r", header.get("alg"))
        return "invalid"

    root = _api_root(base_url)
    jwk = _resolve_jwk(root, str(header.get("kid", "")))
    if jwk is None:
        return "invalid"

    try:
        public = Ed25519PublicKey.from_public_bytes(_b64u_decode(jwk["x"]))
        public.verify(
            _b64u_decode(parts[2]), (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception:  # noqa: BLE001
        log.warning(
            "metrecept receipt check: signature does not verify — receipt is forged or altered"
        )
        return "invalid"

    return "valid"
