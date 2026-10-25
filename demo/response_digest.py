#!/usr/bin/env python3
"""Recompute a receipt's `response_sha256` from what you were served.

Usage:
  python demo/response_digest.py body.json                 # JSON crossing
  python demo/response_digest.py --sse stream.txt          # streamed crossing (raw SSE)
  python demo/response_digest.py --bytes response.bin      # api_call: body bytes
  ... --receipt <receipt-jws>                              # also compare to the receipt

Every crossing receipt (`cache_hit`, `cache_miss`, `cache_bypass`,
`api_call`) may carry `response_sha256`: the SHA-256 of the completion
**as served**. The rule, so a stranger can recompute it with no Metrecept
code (this file imports only the standard library, on purpose):

* JSON crossing — canonical JSON of the body: keys sorted, separators
  `,` and `:` with no whitespace, UTF-8, non-ASCII left unescaped.
* Streamed crossing — assemble the OpenAI-shaped SSE chunks into one
  `chat.completion` object by the rule in `assemble_completion` below (the
  gateway's own rule, verbatim), then hash that object as above. A stream that
  never carried a `finish_reason` has no digest; the receipt will not carry
  one either.
* `api_call` — the decoded response body bytes exactly as returned, hashed
  before any Content-Encoding.

A `cache_hit` and the `cache_miss` that filled it therefore carry one
request digest and one response digest. Two carriages of one JSON-filled
blob (served once as JSON, once as a stream) may legitimately differ: the
stream drops provider extras such as `system_fingerprint`.

Exits 0 when the digest is printed (and matches the receipt, if given);
exits 1 on mismatch or when the stream did not finish.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from typing import Any, Optional


def canonical_digest(obj: Any) -> str:
    canonical = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def bytes_digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _data_payload(line: str) -> Optional[dict[str, Any]]:
    text = line.strip()
    if not text or text in ("data: [DONE]", "[DONE]"):
        return None
    if text.startswith("data:"):
        text = text[5:].strip()
    if not text or text == "[DONE]":
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _usage_total(usage: Optional[dict[str, Any]]) -> Optional[int]:
    if not usage:
        return None
    if "total_tokens" in usage and usage["total_tokens"] is not None:
        return max(0, int(usage["total_tokens"]))
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if prompt is None and completion is None:
        inp = usage.get("input_tokens")
        out = usage.get("output_tokens")
        if inp is None and out is None:
            return None
        return max(0, int(inp or 0) + int(out or 0))
    return max(0, int(prompt or 0) + int(completion or 0))


def assemble_completion(lines: list[str]) -> Optional[dict[str, Any]]:
    """The published assembly rule. Mirrors the gateway's
    `stream_usage.assemble_completion_from_sse_lines` exactly; a fixture
    test in the gateway's repo pins the two together."""
    completion_id = ""
    model = ""
    created = 0
    role = "assistant"
    parts: list[str] = []
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, Any]] = None

    for line in lines:
        payload = _data_payload(line)
        if payload is None:
            continue
        completion_id = completion_id or str(payload.get("id") or "")
        model = model or str(payload.get("model") or "")
        created = created or int(payload.get("created") or 0)
        if isinstance(payload.get("usage"), dict):
            usage = payload["usage"]
        for choice in payload.get("choices") or []:
            if not isinstance(choice, dict) or int(choice.get("index") or 0) != 0:
                continue
            delta = choice.get("delta") or {}
            if isinstance(delta, dict):
                if delta.get("role"):
                    role = str(delta["role"])
                piece = delta.get("content")
                if isinstance(piece, str):
                    parts.append(piece)
            if choice.get("finish_reason"):
                finish_reason = str(choice["finish_reason"])

    if finish_reason is None:
        return None
    content = "".join(parts)
    total = _usage_total(usage)
    if total is None:
        total = max(1, sum(len(x) for x in lines) // 4)
        usage = {"prompt_tokens": 0, "completion_tokens": total, "total_tokens": total}
    return {
        "id": completion_id or "chatcmpl-replay",
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": role, "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }


def sse_lines(raw: str) -> list[str]:
    """Split a raw SSE body into `data:` lines; blank separators are dropped."""
    return [line for line in raw.splitlines() if line.strip()]


def assemble(lines: Any) -> Optional[dict[str, Any]]:
    """Short name for `assemble_completion`: takes any iterable of SSE lines
    (a list, or `raw.splitlines()`); the receipt chunk, having no choices,
    changes nothing."""
    return assemble_completion(list(lines))


def digest(obj: Any) -> str:
    """Short name for `canonical_digest`: the hex a receipt's
    `response_sha256` should equal for this object."""
    return canonical_digest(obj)


def receipt_member(jws: str) -> Optional[str]:
    parts = jws.strip().split(".")
    if len(parts) != 3:
        return None
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    value = payload.get("response_sha256")
    return str(value) if value else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default="-", help="file to hash, or '-' for stdin")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--sse", action="store_true", help="input is a raw SSE stream")
    mode.add_argument("--bytes", action="store_true", help="input is an api_call body; hash the bytes")
    parser.add_argument("--receipt", default="", help="compact JWS to compare against")
    args = parser.parse_args()

    data = sys.stdin.buffer.read() if args.path == "-" else open(args.path, "rb").read()

    if args.bytes:
        digest = bytes_digest(data)
    elif args.sse:
        completion = assemble_completion(sse_lines(data.decode("utf-8")))
        if completion is None:
            print("NO DIGEST: the stream never carried a finish_reason; the receipt carries none either")
            return 1
        digest = canonical_digest(completion)
    else:
        digest = canonical_digest(json.loads(data.decode("utf-8")))

    print(digest)
    if args.receipt:
        named = receipt_member(args.receipt)
        if named is None:
            print("receipt carries no response_sha256")
            return 1
        if named != digest:
            print(f"MISMATCH: receipt names {named}")
            return 1
        print("OK: matches the receipt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
