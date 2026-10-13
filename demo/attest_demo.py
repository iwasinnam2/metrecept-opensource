#!/usr/bin/env python3
"""Co-sign a crossing: your key over the body, the pipe's key over the count.

A Metrecept receipt is the pipe saying "this body crossed, this is what it
cost". On its own that is one party's word. This demo adds the other party:
you sign the request body with your own Ed25519 key and send the signature
as the `X-Metrecept-Attest` header. The pipe checks it against the body it
received and binds its hash into the receipt it mints. The receipt then
carries `attest_sha256`, `attest_kid` and `body_sha256`, and an auditor
verifies both signatures against two public keys without asking either
party. Neither of you could have produced that receipt alone.

Nothing here imports Metrecept code. `cryptography` is the only dependency.

  python demo/attest_demo.py check-sample              # no account, no key: verify a real co-signed crossing
  python demo/attest_demo.py keygen  [--key attest.key] # your signing key (keep it; attest_kid names it)
  python demo/attest_demo.py sign    body.json          # print the X-Metrecept-Attest value for that body
  python demo/attest_demo.py send    body.json          # send it (needs METRECEPT_API_KEY) and verify the answer

What a co-signed receipt proves: the key named by `attest_kid` signed
exactly the bytes the pipe counted, and the pipe's key signed the count.
What it does not prove: who holds that key, or that the body meant
"approved". Names a key, not a person.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_receipt import b64u_decode, jwk_thumbprint, verify  # noqa: E402

ATTEST_HEADER = "X-Metrecept-Attest"
ATTEST_TYP = "metrecept-attest+jws"
DEFAULT_BASE = "https://api.metrecept.co.uk"
DEFAULT_KEY = "attest.key"
SAMPLE = Path(__file__).resolve().parent / "samples" / "cosigned.json"


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def canonical_body_sha256(body: object) -> str:
    """The digest both parties agree on: canonical JSON of the body you send.

    Sorted keys, no whitespace, UTF-8, non-ASCII left as-is. Hashing the
    canonical form means you do not need to control how your HTTP library
    serialises; pass the same dict you send.
    """
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def public_jwk(key: Ed25519PrivateKey) -> dict:
    x = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    members = {"crv": "Ed25519", "kty": "OKP", "x": b64u(x)}
    return {**members, "kid": jwk_thumbprint(members)}


def sign_attestation(body: object, key: Ed25519PrivateKey) -> str:
    """Compact JWS for X-Metrecept-Attest. The public key rides in the header
    (`jwk`), so the pipe and any stranger verify it without a registry;
    `kid` must equal the RFC 7638 thumbprint of that jwk."""
    jwk = public_jwk(key)
    header = {
        "alg": "EdDSA",
        "typ": ATTEST_TYP,
        "kid": jwk["kid"],
        "jwk": {"kty": jwk["kty"], "crv": jwk["crv"], "x": jwk["x"]},
    }
    payload = {"v": 1, "body_sha256": canonical_body_sha256(body), "iat": int(time.time())}
    signing_input = (
        b64u(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
        + "."
        + b64u(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    )
    return signing_input + "." + b64u(key.sign(signing_input.encode("ascii")))


# --- key file -----------------------------------------------------------------

def save_key(key: Ed25519PrivateKey, path: Path) -> None:
    raw = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    path.write_text(b64u(raw) + "\n", encoding="ascii")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_key(path: Path) -> Ed25519PrivateKey:
    raw = b64u_decode(path.read_text(encoding="ascii").strip())
    if len(raw) != 32:
        raise SystemExit(f"{path}: not a 32-byte Ed25519 seed")
    return Ed25519PrivateKey.from_private_bytes(raw)


def load_body(path: str) -> dict:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise SystemExit("body must be a JSON object (the chat/completions request)")
    return body


# --- commands -----------------------------------------------------------------

def cmd_keygen(args: argparse.Namespace) -> int:
    path = Path(args.key)
    if path.exists() and not args.force:
        print(f"{path} exists; pass --force to overwrite (that retires the old attest_kid)")
        return 1
    key = Ed25519PrivateKey.generate()
    save_key(key, path)
    jwk = public_jwk(key)
    print(f"wrote {path} (secret; store it like an API key)")
    print(f"attest_kid {jwk['kid']}")
    print("every receipt you co-sign will carry that kid; it names this key, not you")
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    key = load_key(Path(args.key))
    body = load_body(args.body)
    attest = sign_attestation(body, key)
    print(f"body_sha256 {canonical_body_sha256(body)}")
    print(f"{ATTEST_HEADER}: {attest}")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    api_key = os.environ.get("METRECEPT_API_KEY") or os.environ.get("OHM_API_KEY")
    if not api_key:
        print("set METRECEPT_API_KEY (one $0 key: https://metrecept.co.uk/billing/intermediate)")
        print("or run `check-sample` to verify a crossing that already happened, no key needed")
        return 2
    key = load_key(Path(args.key))
    body = load_body(args.body)
    attest = sign_attestation(body, key)
    data = json.dumps(body).encode("utf-8")  # any serialisation; the pipe canonicalises
    req = urllib.request.Request(
        args.base.rstrip("/") + "/v1/chat/completions",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            ATTEST_HEADER: attest,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            headers = {k.lower(): v for k, v in res.headers.items()}
            res.read()
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", "replace")
        print(f"HTTP {exc.code}: {text[:400]}")
        if exc.code == 400 and "attest" in text:
            print("the pipe refused to mint an unbound receipt: fail-closed is the design")
        return 1
    receipt = headers.get("x-metrecept-receipt") or headers.get("x-ohm-receipt")
    if not receipt:
        print("no receipt header on the response; status", headers.get("x-at-cache"))
        return 1
    print(f"x-at-cache: {headers.get('x-at-cache')}")
    print(f"X-Metrecept-Receipt: {receipt}")
    print(f"{ATTEST_HEADER}: {attest}")
    print(f"verify link: https://metrecept.co.uk/verify#{receipt}")
    print()
    return _report(verify(receipt, args.base, attest))


def cmd_check_sample(args: argparse.Namespace) -> int:
    path = Path(args.sample)
    sample = json.loads(path.read_text(encoding="utf-8"))
    body, attest, receipt = sample["body"], sample["attest"], sample["receipt"]
    print(f"sample: {path.name} minted {sample.get('minted')} on {sample.get('base', DEFAULT_BASE)}")
    print("body (what the caller signed):")
    print("  " + json.dumps(body, sort_keys=True, ensure_ascii=False))
    local = canonical_body_sha256(body)
    print(f"body_sha256 recomputed here  {local}")
    att_payload = json.loads(b64u_decode(attest.split(".")[1]))
    print(f"body_sha256 in the attestation {att_payload.get('body_sha256')}")
    if att_payload.get("body_sha256") != local:
        print("FAIL: the attestation does not cover this body")
        return 1
    print()
    return _report(verify(receipt, sample.get("base", DEFAULT_BASE), attest))


def _report(result: tuple) -> int:
    ok, payload, lines = result
    for line in lines:
        print(line)
    if payload is not None:
        keep = {k: payload.get(k) for k in ("kind", "iat", "attest_kid", "attest_sha256", "body_sha256", "request_sha256", "pipe_usd") if k in payload}
        print(json.dumps(keep, indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("keygen", help="generate your Ed25519 attest key")
    p.add_argument("--key", default=DEFAULT_KEY)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_keygen)

    p = sub.add_parser("sign", help="print the X-Metrecept-Attest value for a body")
    p.add_argument("body", help="JSON file: the chat/completions request body")
    p.add_argument("--key", default=DEFAULT_KEY)
    p.set_defaults(fn=cmd_sign)

    p = sub.add_parser("send", help="send the body with your attestation and verify the receipt")
    p.add_argument("body")
    p.add_argument("--key", default=DEFAULT_KEY)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("check-sample", help="verify the bundled real co-signed crossing (no account)")
    p.add_argument("--sample", default=str(SAMPLE))
    p.set_defaults(fn=cmd_check_sample)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
