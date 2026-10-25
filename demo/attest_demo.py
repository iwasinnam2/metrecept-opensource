#!/usr/bin/env python3
"""Co-sign a crossing: the caller's own signature, bound into the gateway's receipt.

A receipt signed by the gateway says "the gateway counted this crossing". An
attestation is the caller's own Ed25519 signature over the body it sent,
carried as the `X-Metrecept-Attest` request header. The gateway checks it
against the body it received and binds its hash into the receipt
(`attest_sha256`, `attest_kid`, `body_sha256`). Two keys, one record;
neither party can mint it alone, and a stranger checks both halves.

No account is needed for `keygen`, `sign` and `check`. Only `send` talks
to the gateway and needs an API key (env METRECEPT_API_KEY). A real co-signed
pair minted on the hosted gateway is in demo/fixtures/cosigned/ so `check`
can be run cold.

Usage:
  python demo/attest_demo.py keygen  [--out attest.seed]
  python demo/attest_demo.py sign    --key attest.seed --body body.json
  python demo/attest_demo.py send    --key attest.seed --body body.json
                                     [--session <id>] [--base URL] [--out-dir DIR]
  python demo/attest_demo.py check   --receipt <jws|file|link> --attest <jws|file>
                                     [--body body.json] [--base URL]

Requires only `cryptography`. The signing rules (canonical JSON digest,
header `jwk`, `kid` = RFC 7638 thumbprint) are written out below so they
can be re-implemented in any language; nothing here is Metrecept code.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import stat
import sys
import time
import urllib.error
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verify_receipt  # noqa: E402  (same directory; the cold verifier)

ATTEST_HEADER = "X-Metrecept-Attest"
SESSION_HEADER = "X-Metrecept-Session"
RECEIPT_HEADER = "X-Metrecept-Receipt"
ATTEST_TYP = "metrecept-attest+jws"
DEFAULT_BASE = "https://api.metrecept.co.uk"
LINK = "https://metrecept.co.uk/functions/receipt?kind={kind}#{jws}"


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def canonical_body_sha256(body: object) -> str:
    """SHA-256 over canonical JSON: keys sorted, no whitespace, UTF-8,
    non-ASCII left as is. The gateway recomputes exactly this from the body
    it parsed, so the digest does not depend on anyone's serialiser."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def public_jwk(key: Ed25519PrivateKey) -> dict[str, str]:
    x = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    jwk = {"crv": "Ed25519", "kty": "OKP", "x": b64u(x)}
    return {**jwk, "kid": verify_receipt.jwk_thumbprint(jwk)}


def sign_attestation(body: object, key: Ed25519PrivateKey, created: int | None = None) -> str:
    jwk = public_jwk(key)
    header = {
        "alg": "EdDSA",
        "typ": ATTEST_TYP,
        "kid": jwk["kid"],
        "jwk": {"kty": "OKP", "crv": "Ed25519", "x": jwk["x"]},
    }
    payload = {
        "v": 1,
        "body_sha256": canonical_body_sha256(body),
        "iat": int(created if created is not None else time.time()),
    }
    signing_input = (
        b64u(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
        + "."
        + b64u(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    )
    return signing_input + "." + b64u(key.sign(signing_input.encode("ascii")))


# ---- key file: 32-byte seed, base64url, one line. Secret; store like an API key.


def write_seed(path: pathlib.Path, key: Ed25519PrivateKey) -> None:
    raw = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    path.write_text(b64u(raw) + "\n", encoding="ascii")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def read_seed(path: pathlib.Path) -> Ed25519PrivateKey:
    raw = verify_receipt.b64u_decode(path.read_text(encoding="ascii").strip())
    if len(raw) != 32:
        raise SystemExit(f"{path}: an attest seed is 32 bytes, got {len(raw)}")
    return Ed25519PrivateKey.from_private_bytes(raw)


def read_body(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    if not isinstance(body, dict):
        raise SystemExit(f"{path}: the request body must be a JSON object")
    return body


def text_or_file(value: str) -> str:
    """A compact JWS, a verify link, or the path of a file holding one."""
    p = pathlib.Path(value)
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    looks_like_path = value.endswith((".jws", ".txt")) or os.sep in value or "/" in value and "://" not in value
    if looks_like_path:
        raise SystemExit(f"{value}: no such file")
    return value.strip()


# ---- subcommands


def cmd_keygen(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out)
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to overwrite (the old kid stops being yours)")
        return 2
    key = Ed25519PrivateKey.generate()
    write_seed(out, key)
    jwk = public_jwk(key)
    print(f"wrote {out} (secret seed, keep it)")
    print(f"kid (RFC 7638 thumbprint): {jwk['kid']}")
    print("every receipt you co-sign carries this kid as attest_kid")
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    key = read_seed(pathlib.Path(args.key))
    body = read_body(args.body)
    jws = sign_attestation(body, key)
    print(f"body_sha256: {canonical_body_sha256(body)}")
    print(f"kid: {public_jwk(key)['kid']}")
    print(f"{ATTEST_HEADER}: {jws}")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    api_key = os.environ.get("METRECEPT_API_KEY", "").strip()
    if not api_key:
        print("send needs METRECEPT_API_KEY in the environment (keygen/sign/check do not)")
        return 2
    key = read_seed(pathlib.Path(args.key))
    body = read_body(args.body)
    attest = sign_attestation(body, key)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        args.base.rstrip("/") + "/v1/chat/completions", data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header(ATTEST_HEADER, attest)
    if args.session:
        req.add_header(SESSION_HEADER, args.session)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            status = res.status
            headers = res.headers  # HTTPMessage: .get() is case-insensitive
            raw = res.read()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}")
        return 1
    receipt = headers.get(RECEIPT_HEADER) or headers.get("X-Ohm-Receipt") or ""
    path = headers.get("X-Metrecept-Path") or headers.get("X-Ohm-Path") or "?"
    print(f"HTTP {status} path={path}")
    if not receipt:
        print("no receipt header on the response; nothing to bind")
        return 1
    ok, payload, lines = verify_receipt.verify(receipt, args.base, attest)
    for line in lines:
        print(line)
    kind = (payload or {}).get("kind", "receipt")
    print(LINK.format(kind=kind, jws=receipt))
    if args.out_dir:
        out = pathlib.Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "body.json").write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out / "attest.jws").write_text(attest + "\n", encoding="ascii")
        (out / "receipt.jws").write_text(receipt + "\n", encoding="ascii")
        (out / "response.json").write_bytes(raw)
        print(f"wrote body.json, attest.jws, receipt.jws, response.json to {out}")
    return 0 if ok else 1


def cmd_check(args: argparse.Namespace) -> int:
    receipt = text_or_file(args.receipt)
    attest = text_or_file(args.attest)
    ok, payload, lines = verify_receipt.verify(receipt, args.base, attest)
    for line in lines:
        print(line)
    if ok and args.body:
        body = read_body(args.body)
        digest = canonical_body_sha256(body)
        if digest == (payload or {}).get("body_sha256"):
            print(f"OK (body): {args.body} canonicalises to body_sha256 {digest}; this is the body both keys signed")
        else:
            print(f"FAIL (body): {args.body} canonicalises to {digest}, receipt says {(payload or {}).get('body_sha256')}")
            ok = False
    if payload is not None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("keygen", help="new Ed25519 attest key (seed file + kid)")
    p.add_argument("--out", default="attest.seed")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_keygen)

    p = sub.add_parser("sign", help="print the X-Metrecept-Attest JWS for a body")
    p.add_argument("--key", required=True)
    p.add_argument("--body", required=True, help="JSON file: the request body you will send")
    p.set_defaults(fn=cmd_sign)

    p = sub.add_parser("send", help="send the body with its attestation; verify the co-signed receipt")
    p.add_argument("--key", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--session", default="", help="planted id for X-Metrecept-Session (optional)")
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--out-dir", default="", help="write body.json / attest.jws / receipt.jws here")
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("check", help="cold-verify a co-signed receipt: both signatures and the binding")
    p.add_argument("--receipt", required=True, help="receipt JWS, verify link, or a file holding one")
    p.add_argument("--attest", required=True, help="X-Metrecept-Attest JWS or a file holding one")
    p.add_argument("--body", default="", help="optional body.json; recomputes body_sha256 and compares")
    p.add_argument("--base", default=DEFAULT_BASE)
    p.set_defaults(fn=cmd_check)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
