#!/usr/bin/env python3
"""Emit a Metrecept signed receipt as an OpenTelemetry GenAI span.

Reference implementation for the distribution wedge described in
docs/superpowers/specs/2026-09-05-otel-genai-finops-distribution-design.md.

The point this script demonstrates: OpenTelemetry GenAI semantic
conventions (https://github.com/open-telemetry/semantic-conventions-genai)
describe *self-reported* spans — cost, tool calls, model usage — with no
cryptographic evidence attached. A Metrecept receipt (X-Ohm-Receipt /
X-Metrecept-Receipt, a compact Ed25519 JWS) already arrives as an ordinary
HTTP response header on every cache HIT. Any generic OTel HTTP-client
instrumentation can capture that header exactly the way it already
captures status code or latency — no Metrecept code needs to run inside
the span-producing process. That's "only model what generic
instrumentation can record at runtime," the OTel GenAI SIG's own rule 6
for accepting a new convention.

This script is deliberately standalone, same stance as verify_receipt.py
next to it: no `at_utility` / `metrecept` package import, no network call
back to Metrecept except the one public JWKS fetch every stranger-verifier
in this repo already makes. The verify routine below is a duplicate of
verify_receipt.py's, not an import of it — each demo file in this
directory is meant to be copy-pasted on its own.

Usage:
  pip install opentelemetry-sdk cryptography
  python demo/otel_receipt_span.py "<receipt-jws>" --base https://api.metrecept.co.uk

  # Also export to a real collector (any OTLP-compatible backend —
  # LangFuse, Phoenix, Langtrace, a local otel-collector, etc.):
  pip install opentelemetry-exporter-otlp-proto-http
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python demo/otel_receipt_span.py "<jws>"

Attribute namespace: standard `gen_ai.*` attributes are used only where
they already exist in the published conventions and genuinely apply
(chat-completion cache hits). Everything Metrecept-specific — the receipt
itself, pipe cost, replay counts — stays under the vendor-prefixed
`metrecept.*` namespace, non-normative, until/unless the OTel GenAI SIG
adopts something under `gen_ai.*` directly. See CONTRIBUTING.md at
https://github.com/open-telemetry/semantic-conventions-genai for why this
script does not invent new `gen_ai.*` names unilaterally.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.request
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DIRECTORY_PATH = "/.well-known/http-message-signatures-directory"


# --- Verification (duplicated from verify_receipt.py, on purpose — see
# module docstring; keep the two in lockstep by hand, same convention used
# repo-wide for client/server verification-code pairs). ---------------------


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


def verify_jws(receipt: str, base: str) -> tuple[bool, str, dict[str, Any]]:
    """Returns (verified, kid, payload). Never raises; failures are (False, "", {})."""
    parts = receipt.strip().split(".")
    if len(parts) != 3:
        return False, "", {}
    try:
        header = json.loads(b64u_decode(parts[0]))
    except Exception:  # noqa: BLE001
        return False, "", {}
    if header.get("alg") != "EdDSA":
        return False, header.get("kid", ""), {}
    kid = header.get("kid", "")

    try:
        directory_url = base.rstrip("/") + DIRECTORY_PATH
        with urllib.request.urlopen(directory_url, timeout=15) as res:
            directory = json.loads(res.read().decode("utf-8"))
        jwk = next(
            (
                k
                for k in directory.get("keys", [])
                if k.get("kty") == "OKP"
                and k.get("crv") == "Ed25519"
                and jwk_thumbprint(k) == kid
            ),
            None,
        )
        if jwk is None:
            return False, kid, {}
        public = Ed25519PublicKey.from_public_bytes(b64u_decode(jwk["x"]))
        public.verify(
            b64u_decode(parts[2]), (parts[0] + "." + parts[1]).encode("ascii")
        )
    except Exception:  # noqa: BLE001
        return False, kid, {}

    try:
        payload = json.loads(b64u_decode(parts[1]))
    except Exception:  # noqa: BLE001
        return False, kid, {}
    return True, kid, payload


# --- Receipt -> OTel span attribute mapping ---------------------------------


def receipt_to_span_attributes(
    verified: bool, kid: str, receipt: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Build the OTel span attribute dict for one receipt.

    Uses established `gen_ai.*` attributes only where they already exist
    and genuinely describe the payload (a chat-completion cache hit).
    Everything else — the receipt, its verification result, pipe cost,
    replay/aggregate counts — is vendor-namespaced under `metrecept.*`.
    """
    kind = payload.get("kind", "unknown")
    attrs: dict[str, Any] = {
        "metrecept.receipt.kind": kind,
        "metrecept.receipt.jws": receipt,
        "metrecept.receipt.verified": verified,
        "metrecept.receipt.kid": kid,
        "metrecept.receipt.schema_version": payload.get("v"),
    }

    if kind == "cache_hit":
        # A cache-hit receipt genuinely describes one chat-completion call —
        # the established gen_ai.* attributes apply.
        if payload.get("model"):
            attrs["gen_ai.operation.name"] = "chat"
            attrs["gen_ai.request.model"] = payload["model"]
        attrs["metrecept.pipe_usd"] = payload.get("pipe_usd")
        attrs["metrecept.tokens_replayed"] = payload.get("tokens_replayed")
        attrs["metrecept.request_sha256"] = payload.get("request_sha256")
        attrs["metrecept.plane"] = payload.get("plane")
        attrs["metrecept.admit"] = payload.get("admit")

    elif kind == "api_call":
        # A receipted third-party business-API round trip is not a GenAI
        # inference call at all — no gen_ai.* attributes apply. Stays
        # entirely under metrecept.* on purpose.
        attrs["metrecept.pipe_usd"] = payload.get("pipe_usd")
        attrs["metrecept.request_sha256"] = payload.get("request_sha256")

    elif kind == "session":
        # An aggregate over one agent session (Black Box Phase B) — closer
        # to gen_ai.agent/invoke-agent territory conceptually, but the SIG's
        # own conventions for agent spans are still unfinalized (rule 9's
        # "stay in the GenAI domain" cuts the other way here: don't guess
        # at an in-flux convention). Reported as metrecept.* only.
        attrs["metrecept.pipe_usd"] = payload.get("pipe_usd")
        attrs["metrecept.event_count"] = payload.get("event_count")
        attrs["metrecept.cache_hits"] = payload.get("cache_hits")
        attrs["metrecept.cache_misses"] = payload.get("cache_misses")
        attrs["metrecept.api_calls"] = payload.get("api_calls")

    elif kind == "statement":
        attrs["metrecept.pipe_usd"] = payload.get("pipe_usd")
        attrs["metrecept.event_count"] = payload.get("event_count")
        attrs["metrecept.estimated_provider_avoided_usd"] = payload.get(
            "estimated_provider_avoided_usd"
        )

    # Drop None values — OTel attribute values must not be None.
    return {k: v for k, v in attrs.items() if v is not None}


def emit_span(attrs: dict[str, Any]) -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    resource = Resource.create({"service.name": "metrecept-receipt-demo"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
        except ImportError:
            print(
                "OTEL_EXPORTER_OTLP_ENDPOINT is set but "
                "opentelemetry-exporter-otlp-proto-http is not installed — "
                "console export only. "
                "pip install opentelemetry-exporter-otlp-proto-http",
                file=sys.stderr,
            )
        else:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )

    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("metrecept.receipt_export")

    span_name = f"{attrs.get('gen_ai.operation.name', 'metrecept')} " + (
        attrs.get("gen_ai.request.model") or attrs["metrecept.receipt.kind"]
    )
    with tracer.start_as_current_span(span_name) as span:
        for key, value in attrs.items():
            span.set_attribute(key, value)

    provider.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "receipt", help="X-Ohm-Receipt / X-Metrecept-Receipt header value (compact JWS)"
    )
    parser.add_argument("--base", default="https://api.metrecept.co.uk")
    args = parser.parse_args()

    verified, kid, payload = verify_jws(args.receipt, args.base)
    if not payload:
        print("FAIL: receipt did not verify — refusing to emit a span for it")
        return 1

    print(f"Verification: {'OK' if verified else 'FAIL'} (kid={kid})")
    attrs = receipt_to_span_attributes(verified, kid, args.receipt, payload)

    try:
        emit_span(attrs)
    except ImportError:
        print(
            "opentelemetry-sdk is not installed — printing the attribute "
            "mapping instead. pip install opentelemetry-sdk to emit a real span.\n"
        )
        print(json.dumps(attrs, indent=2, sort_keys=True, default=str))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
