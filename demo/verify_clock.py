#!/usr/bin/env python3
"""Verify a Metrecept receipt against the Merkle clock from a cold start.

Does not import the gateway. Checks, in order:

  1. The compact JWS is well-formed and the leaf is sha256(ed25519_sig)
     — never the payload.
  2. Inclusion of that leaf in a claimed slot (RFC 6962 proof).
  3. If a commitment is present: the committed digest equals the slot root.

Standard library only. Mirrored from scripts/verify_clock.py in the monorepo.

Usage:
  python demo/verify_clock.py --receipt <jws> --slot path/to/slot.json
  python demo/verify_clock.py --receipt <jws> --base https://api.metrecept.co.uk
  python demo/verify_clock.py --genesis genesis.json   # https://metrecept.co.uk/clock/genesis.json
  python demo/verify_clock.py --digest <64 hex> --base https://api.metrecept.co.uk

`--digest` checks an *external* leaf: a 32-byte digest a key-holder sealed
into the hour via POST /v1/clock/leaf. Its leaf is
sha256(b"metrecept-clock-external-leaf/v1" || digest) — domain-separated
from receipt leaves, so neither can pose as the other. Metrecept did not see
or sign what the digest names; this proves only the hour.

Exit 0 on inclusion that matches a committed (or at least sealed) root.
Exit 2 if the receipt is in an *open* slot — that is our log, not a clock.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.parse
import urllib.request

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
EXTERNAL_LEAF_DOMAIN = b"metrecept-clock-external-leaf/v1"
LEAF_ALGO_EXTERNAL = "sha256('metrecept-clock-external-leaf/v1' || digest32)"


def external_leaf_from_digest_hex(digest_hex: str) -> bytes:
    s = (digest_hex or "").strip()
    try:
        digest = bytes.fromhex(s)
    except ValueError:
        digest = b""
    if len(s) != 64 or len(digest) != 32:
        raise SystemExit("--digest must be 64 hex chars (32 bytes)")
    return hashlib.sha256(EXTERNAL_LEAF_DOMAIN + digest).digest()


def b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_from_jws(jws: str) -> bytes:
    parts = (jws or "").split(".")
    if len(parts) != 3:
        raise SystemExit("not a compact JWS")
    sig = b64u_decode(parts[2])
    if len(sig) != 64:
        raise SystemExit("ed25519 signature must be 64 bytes")
    return sha256(sig)


def leaf_hash(leaf: bytes) -> bytes:
    return sha256(LEAF_PREFIX + leaf)


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha256(NODE_PREFIX + left + right)


def verify_inclusion(leaf: bytes, proof: list, root_hex: str) -> bool:
    h = leaf_hash(leaf)
    for step in proof:
        sibling = bytes.fromhex(step["hash"])
        side = step.get("side")
        if side == "L":
            h = node_hash(sibling, h)
        elif side == "R":
            h = node_hash(h, sibling)
        else:
            return False
    return h.hex() == root_hex


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))


def inclusion_from_slot_file(leaf: bytes, slot: dict) -> dict:
    """Recompute proof from published leaves when the file carries them."""
    leaves_hex = slot.get("leaves") or []
    leaf_hex = leaf.hex()
    try:
        index = leaves_hex.index(leaf_hex)
    except ValueError:
        raise SystemExit(f"leaf {leaf_hex} not in slot {slot.get('slot')}")
    leaves = [bytes.fromhex(h) for h in leaves_hex]
    # Rebuild proof locally — do not trust a pre-packaged proof alone.
    layer = [leaf_hash(x) for x in leaves]
    idx = index
    proof = []
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            if i + 1 < len(layer):
                left, right = layer[i], layer[i + 1]
                nxt.append(node_hash(left, right))
                if idx == i:
                    proof.append({"side": "R", "hash": right.hex()})
                elif idx == i + 1:
                    proof.append({"side": "L", "hash": left.hex()})
            else:
                nxt.append(layer[i])
        idx //= 2
        layer = nxt
    root = layer[0].hex()
    claimed = slot.get("root_sha256")
    if claimed and claimed != root:
        raise SystemExit(f"recomputed root {root} != claimed {claimed}")
    return {
        "slot": slot.get("slot"),
        "index": index,
        "leaf_count": len(leaves),
        "root_sha256": root,
        "proof": proof,
        "status": slot.get("status"),
        "commitment": slot.get("commitment") or slot.get("commitment_full"),
        "verified": True,
        "included": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", help="compact JWS (X-Metrecept-Receipt value)")
    parser.add_argument(
        "--digest",
        help="64-hex digest sealed as an external leaf via POST /v1/clock/leaf",
    )
    parser.add_argument("--slot", help="path to a sealed slot JSON")
    parser.add_argument("--genesis", help="path to a downloaded https://metrecept.co.uk/clock/genesis.json")
    parser.add_argument(
        "--base",
        default="",
        help="API base, e.g. https://api.metrecept.co.uk (live inclusion lookup)",
    )
    parser.add_argument(
        "--write-ots",
        metavar="PATH",
        help="write the first OTS attestation to PATH (for `ots verify`)",
    )
    args = parser.parse_args()

    genesis = load_json(args.genesis) if args.genesis else None
    if args.digest and args.receipt:
        print("give --digest or --receipt, not both", file=sys.stderr)
        return 1
    if args.digest:
        leaf = external_leaf_from_digest_hex(args.digest)
        print(f"digest       {args.digest.strip().lower()}")
        print(f"leaf_sha256  {leaf.hex()}")
        print(f"leaf_type=external  leaf_algo    {LEAF_ALGO_EXTERNAL}")
        print("             (Metrecept did not see or sign what this digest names)")
    else:
        receipt = args.receipt or (genesis or {}).get("sample_receipt")
        if not receipt:
            print("need --receipt, --digest, or --genesis with sample_receipt", file=sys.stderr)
            return 1
        leaf = leaf_from_jws(receipt)
        print(f"leaf_sha256  {leaf.hex()}")
        print("leaf_type=receipt_signature  leaf_algo    sha256(ed25519_sig)  (payload not hashed)")

    if args.slot:
        slot = load_json(args.slot)
        inc = inclusion_from_slot_file(leaf, slot)
        marked = slot.get("external_leaves")
        if args.digest and isinstance(marked, list):
            if leaf.hex() not in marked:
                print("slot does not mark this leaf as external", file=sys.stderr)
                return 1
            print("marked       external on the slot view")
    elif genesis:
        slot = genesis.get("slot") or genesis
        inc = inclusion_from_slot_file(leaf, slot)
    elif args.base:
        base = args.base.rstrip("/")
        url = (
            base
            + "/v1/public/clock/inclusion?leaf="
            + urllib.parse.quote(leaf.hex())
        )
        inc = fetch_json(url)
        if not inc.get("included"):
            print("not included in any known slot", file=sys.stderr)
            return 1
        if args.digest and inc.get("leaf_type") != "external":
            print("the clock does not mark this leaf as external", file=sys.stderr)
            return 1
        root = inc.get("root_sha256")
        if not root:
            print("OPEN SLOT — our log, not a clock. Seal + commit the root.", file=sys.stderr)
            return 2
        if not verify_inclusion(leaf, inc.get("proof") or [], root):
            print("inclusion proof failed", file=sys.stderr)
            return 1
        inc["verified"] = True
    else:
        print("need --slot, --genesis, or --base", file=sys.stderr)
        return 1

    print(f"slot         {inc.get('slot')}")
    print(f"index        {inc.get('index')} / {inc.get('leaf_count')}")
    print(f"root_sha256  {inc.get('root_sha256')}")
    print(f"status       {inc.get('status')}")
    print(f"included     {inc.get('included')}  verified={inc.get('verified')}")

    commitment = inc.get("commitment") or {}
    digest = commitment.get("digest_sha256")
    if digest:
        if digest != inc.get("root_sha256"):
            print(
                f"commitment digest {digest} != root {inc.get('root_sha256')}",
                file=sys.stderr,
            )
            return 1
        print(f"commitment   {commitment.get('method')} {commitment.get('status')}")
        print("             digest matches root")
    eth = commitment.get("ethereum") if isinstance(commitment, dict) else None
    if isinstance(eth, dict) and eth.get("tx"):
        print(f"ethereum     {eth.get('chain')} {eth.get('tx')}")
        inp = (eth.get("input") or "").replace("0x", "").replace("0X", "")
        if inp and inp != inc.get("root_sha256"):
            print("ethereum input data != root", file=sys.stderr)
            return 1
        if eth.get("explorer"):
            print(f"             {eth.get('explorer')}")
    btc = commitment.get("bitcoin") if isinstance(commitment, dict) else None
    if isinstance(btc, dict) and btc.get("txid"):
        print(f"bitcoin      {btc.get('txid')} confirmed={btc.get('confirmed')} block={btc.get('block_height')}")
        if btc.get("explorer"):
            print(f"             {btc.get('explorer')}")

    if args.write_ots:
        atts = (commitment.get("attestations") or []) if isinstance(commitment, dict) else []
        blob = None
        for att in atts:
            if att.get("ots_b64"):
                blob = base64.b64decode(att["ots_b64"])
                break
        if not blob:
            print("no ots_b64 in commitment", file=sys.stderr)
            return 1
        with open(args.write_ots, "wb") as f:
            f.write(blob)
        print(f"wrote        {args.write_ots} ({len(blob)} bytes)")
        print("next         ots verify " + args.write_ots + "   # after Bitcoin confirm")

    if inc.get("status") == "open":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
