"""Thin helpers so OpenAI clients become a one-line base_url drop-in for Metrecept.

Package path remains at_utility_sdk / at-utility-sdk until a coordinated
package-name cutover. Product is Metrecept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from at_utility_sdk.inhouse import wrap_generate
from at_utility_sdk.receipt_check import check_receipt


# Public API host (live). Use LOCAL_BASE_URL for local development.
DEFAULT_BASE_URL = "https://api.metrecept.co.uk/v1"
LOCAL_BASE_URL = "http://127.0.0.1:8081/v1"
UPSTREAM_KEY_HEADER = "X-Ohm-Upstream-Key"


@dataclass
class AtUtilityClientOptions:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 120.0
    upstream_api_key: str = ""


def openai_client(
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    upstream_api_key: str = "",
    default_headers: Optional[dict[str, str]] = None,
    **kwargs: Any,
) -> Any:
    """
    Drop-in replacement with optional BYOK:

        from at_utility_sdk import openai_client
        client = openai_client("sk-at-...", upstream_api_key="sk-proj-...")

    Returns a bare ``openai.OpenAI(...)`` client — headers are not
    intercepted here (see ``wrap_generate`` for the automatic check). To
    verify a signed receipt on a HIT, call ``.with_raw_response`` and pass
    the headers to ``check_receipt``:

        resp = client.chat.completions.with_raw_response.create(...)
        check_receipt(resp.headers, base_url=str(client.base_url))
        completion = resp.parse()
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install openai package: pip install openai") from exc
    headers = dict(default_headers or {})
    if upstream_api_key:
        headers[UPSTREAM_KEY_HEADER] = upstream_api_key
    if headers:
        kwargs = {**kwargs, "default_headers": headers}
    return OpenAI(api_key=api_key, base_url=base_url, **kwargs)


def usage_url(base_url: str = DEFAULT_BASE_URL) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/usage"
    return f"{root}/v1/usage"


def enterprise_skus_url(base_url: str = DEFAULT_BASE_URL) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/enterprise/skus"
    return f"{root}/v1/enterprise/skus"


def compliance_policy_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Authenticated GET — live public-only ingest policy (docs/LEGAL.md)."""
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/compliance/policy"
    return f"{root}/v1/compliance/policy"


# Allowed web_purpose values when fetch_web_context=true
ALLOWED_WEB_PURPOSES = frozenset(
    {
        "public_web_retrieval",
        "business_catalog",
        "public_company_info",
        "job_listings",
    }
)


def web_context_extra(
    *,
    purpose: str,
    urls: Optional[list[str]] = None,
    query: Optional[str] = None,
    compliance_ack: bool = True,
    terms_ack: bool = True,
    dpa_ack: bool = True,
    cache_control: Optional[str] = None,
) -> dict[str, Any]:
    """Build OpenAI `extra_body` fields for compliant web retrieval."""
    if purpose not in ALLOWED_WEB_PURPOSES:
        raise ValueError(
            f"purpose must be one of {sorted(ALLOWED_WEB_PURPOSES)}; "
            "lead harvest / dossiers / gated access are prohibited (docs/LEGAL.md)"
        )
    if not compliance_ack:
        raise ValueError("compliance_ack must be True for web context")
    if not terms_ack or not dpa_ack:
        raise ValueError("terms_ack and dpa_ack must be True (docs/legal/)")
    body: dict[str, Any] = {
        "fetch_web_context": True,
        "web_purpose": purpose,
        "web_compliance_ack": True,
        "terms_ack": True,
        "dpa_ack": True,
    }
    if urls:
        body["web_urls"] = urls
    if query:
        body["web_query"] = query
    if cache_control:
        body["cache_control"] = cache_control
    return body


__all__ = [
    "ALLOWED_WEB_PURPOSES",
    "AtUtilityClientOptions",
    "DEFAULT_BASE_URL",
    "LOCAL_BASE_URL",
    "UPSTREAM_KEY_HEADER",
    "check_receipt",
    "compliance_policy_url",
    "openai_client",
    "usage_url",
    "enterprise_skus_url",
    "web_context_extra",
    "wrap_generate",
]
