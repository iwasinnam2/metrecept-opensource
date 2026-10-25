"""Emit open-repo/demo/n8n_retry_hit_receipt_template.json."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("n8n_retry_hit_receipt_template.json")

CRED = {
    "httpHeaderAuth": {
        "id": "PLACEHOLDER_CREDENTIAL_ID",
        "name": "Metrecept API Key",
    }
}

OVERVIEW = """## Prove an n8n AI retry was a cache HIT

### How it works
n8n retries OpenAI-shaped calls. This workflow posts the same JSON bytes through Metrecept, an OpenAI-compatible gateway. Call 1 is a MISS. With `prove_retry` on, Call 2 is those exact bytes again and should be a HIT. A HIT carries a signed Ed25519 receipt. The workflow loads the public JWKS and checks the signature in a Code node, so the JSON you see is verified — not a header you have to trust. After you believe it, set `prove_retry` false: one crossing per webhook, and your own retries become the HIT. Receipts exist on HITs only. Prefix overlap is labelled and is not a HIT. The gateway records; it does not stop a bad call. Org spend caps return 402 on a MISS flood; HITs would still serve.

The proof carries `receipt_verify_url`. Forward that one line in the Slack message, ticket, or email this workflow already sends: whoever opens it lands on metrecept.co.uk/verify, which reads the JWS from the URL fragment and checks Ed25519 in their browser against the public JWKS — no account. It is `null` when no JWS was carried.

Both calls are tagged `X-Metrecept-Session: <session_id>` (default `n8n-<execution id>`, or pass `session_id` in the webhook body). After the calls, GET /v1/sessions/<session_id> returns one signed `kind: "session"` receipt for the whole run — call count, hits, misses, pipe charge, first and last timestamp — and the proof carries it as `session_receipt_verify_url`. The session receipt is $0 and included. The per-call HIT receipt above is a separate kind that bills on the seat. Both links prove the gateway signed that record; neither grades the answer, and neither stopped anything.

### Setup steps
1. Get a Metrecept API key (Intermediate, $0 seat): metrecept.co.uk/billing/intermediate
2. Create HTTP Header Auth — Header Name `Authorization`, Header Value `Bearer sk-at-...` — and select it on Call 1, Call 2, and GET session receipt.
3. Click **Test once** (pinned sample, `model: mock`, no upstream key). Expect call1 MISS, call2 HIT, receipt_verified true, and a `session_receipt_verify_url`.
4. Webhook clients POST `{ "prompt": "..." }` or `{ "messages": [...] }`. Send `{ "prove_retry": false }` for single-call mode; send `{ "session_id": "..." }` (lowercase `a-z0-9_-`, max 64) to group several webhook calls under one session receipt.

### Customization
Change `model` in Config from `mock` to a real id after you add a provider key (BYOK) per metrecept.co.uk/docs. Point existing OpenAI Chat Model nodes at `https://api.metrecept.co.uk/v1`. If you already installed `n8n-nodes-metrecept`, its Chat/Verify operations can replace the HTTP + Code steps."""

VERIFY_JS = r"""const crypto = require('crypto');

function b64uDecode(text) {
  return Buffer.from(text, 'base64url');
}

function jwkThumbprint(jwk) {
  const canonical = JSON.stringify({ crv: jwk.crv, kty: jwk.kty, x: jwk.x });
  return crypto.createHash('sha256').update(canonical, 'ascii').digest().toString('base64url');
}

const carry = $('Carry receipt').first().json;
const http = $input.first().json;
const directory = http.body || http;
const receipt = String(carry.receipt_jws || '').trim();

let receipt_verified = false;
let receipt_reason = 'receipt_invalid';
let kid = '';
let receipt_payload = null;

try {
  const parts = receipt.split('.');
  if (parts.length !== 3) {
    receipt_reason = 'not_compact_jws';
  } else {
    const header = JSON.parse(b64uDecode(parts[0]).toString('utf8'));
    kid = header.kid || '';
    if (header.alg !== 'EdDSA') {
      receipt_reason = 'unexpected_alg';
    } else {
      const list = directory.keys || [];
      const jwk = list.find(function (k) {
        return k.kty === 'OKP' && k.crv === 'Ed25519' && (k.kid === kid || jwkThumbprint(k) === kid);
      });
      if (!jwk) {
        receipt_reason = 'kid_not_in_jwks';
      } else {
        const publicKey = crypto.createPublicKey({ key: jwk, format: 'jwk' });
        const signingInput = Buffer.from(parts[0] + '.' + parts[1], 'ascii');
        receipt_verified = crypto.verify(null, signingInput, publicKey, b64uDecode(parts[2]));
        receipt_payload = JSON.parse(b64uDecode(parts[1]).toString('utf8'));
        receipt_reason = receipt_verified ? null : 'signature_mismatch';
      }
    }
  }
} catch (e) {
  receipt_verified = false;
  receipt_reason = 'verify_threw';
}

return [{ json: Object.assign({}, carry, { receipt_verified: receipt_verified, receipt_reason: receipt_reason, receipt_kid: kid, receipt_payload: receipt_payload }) }];
"""

PROOF_JS = r"""function executed(name) {
  try {
    const p = $(name);
    if (p && typeof p.isExecuted === 'boolean') return p.isExecuted;
    return !!p.first();
  } catch (e) {
    return false;
  }
}

const carry = $('Carry receipt').first().json;
const sessionHttp = $input.first().json;
let session = null;
let session_receipt_verify_url = null;
if (sessionHttp.statusCode === 200 && sessionHttp.body) {
  const b = sessionHttp.body;
  session = {
    session_id: b.session_id,
    event_count: b.event_count,
    pipe_usd: b.pipe_usd,
    cache_hits: b.cache_hits,
    cache_misses: b.cache_misses,
    first_ts: b.first_ts,
    last_ts: b.last_ts
  };
  const sjws = String(b.receipt || '').trim();
  if (sjws.split('.').length === 3) {
    session_receipt_verify_url = 'https://metrecept.co.uk/verify#' + sjws;
  }
}

const isHit = function (s) {
  return String(s || '').trim().toLowerCase() === 'hit';
};

let receipt_verified = null;
let receipt_reason = null;
if (executed('JWKS failed')) {
  receipt_verified = false;
  receipt_reason = 'jwks_unavailable';
} else if (executed('Verify Ed25519')) {
  const v = $('Verify Ed25519').first().json;
  receipt_verified = v.receipt_verified === true;
  receipt_reason = v.receipt_reason || null;
} else if (isHit(carry.call1_cache) || isHit(carry.call2_cache)) {
  receipt_verified = false;
  receipt_reason = 'missing_header';
}

const prove = !(carry.prove_retry === false || carry.prove_retry === 'false' || carry.prove_retry === 0);
const cache2raw = carry.call2_cache;
const call2 = (cache2raw === undefined || cache2raw === null || cache2raw === '')
  ? null
  : { cache: String(cache2raw), billed_usd: carry.call2_billed_usd };

return [{ json: {
  mode: prove ? 'prove_retry' : 'single',
  model: carry.model,
  call1: { cache: carry.call1_cache, billed_usd: carry.call1_billed_usd },
  call2: call2,
  receipt_verified: receipt_verified,
  receipt_reason: receipt_reason,
  receipt_verify_url: carry.receipt_jws ? 'https://metrecept.co.uk/verify#' + String(carry.receipt_jws).trim() : null,
  session: session,
  session_receipt_verify_url: session_receipt_verify_url
} }];
"""

MESSAGES = (
    "={{ ($json.body && $json.body.messages) ? $json.body.messages : "
    "($json.messages ? $json.messages : ((($json.body && $json.body.prompt) || $json.prompt) "
    "? [{ role: 'user', content: String(($json.body && $json.body.prompt) || $json.prompt) }] : [])) }}"
)
PROVE = (
    "={{ !(($json.body && ($json.body.prove_retry === false || $json.body.prove_retry === 'false' "
    "|| $json.body.prove_retry === 0)) || ($json.prove_retry === false || $json.prove_retry === 'false' "
    "|| $json.prove_retry === 0)) }}"
)
MODEL = "={{ ($json.body && $json.body.model) || $json.model || 'mock' }}"
# Lowercase [a-z0-9_-]{1,64}: the gateway silently drops anything else (docs/SESSION_RECEIPT.md).
SESSION_ID = (
    "={{ String((($json.body && $json.body.session_id) || $json.session_id || ('n8n-' + $execution.id)))"
    ".toLowerCase().replace(/[^a-z0-9_-]/g, '-').slice(0, 64) }}"
)
SESSION_HEADER = {"name": "X-Metrecept-Session", "value": "={{ $json.session_id }}"}
CACHE_H = (
    "={{ ($json.headers && ($json.headers['x-at-cache'] || $json.headers['X-AT-Cache'])) || '' }}"
)
BILLED_H = (
    "={{ ($json.headers && ($json.headers['x-at-billed-usd'] || $json.headers['X-AT-Billed-USD'])) || '' }}"
)
RECEIPT_H = (
    "={{ ($json.headers && ($json.headers['x-metrecept-receipt'] || $json.headers['x-metrecept-receipt'] "
    "|| $json.headers['X-Metrecept-Receipt'] || $json.headers['X-Metrecept-Receipt'])) || '' }}"
)
CONTENT_H = (
    "={{ ($json.body && $json.body.choices && $json.body.choices[0] && $json.body.choices[0].message "
    "&& $json.body.choices[0].message.content) || '' }}"
)


def sticky(id_, name, content, x, y, w, h, color=None):
    params = {"content": content, "height": h, "width": w}
    if color is not None:
        params["color"] = color
    return {
        "parameters": params,
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [x, y],
    }


def http_full(id_, name, x, y, method, url, body=None, auth=True, session=False):
    params = {
        "method": method,
        "url": url,
        "options": {
            "response": {"response": {"fullResponse": True, "neverError": True}}
        },
    }
    if auth:
        params["authentication"] = "genericCredentialType"
        params["genericAuthType"] = "httpHeaderAuth"
    if method == "POST":
        headers = [{"name": "Content-Type", "value": "application/json"}]
        if session:
            headers.append(dict(SESSION_HEADER))
        params["sendHeaders"] = True
        params["headerParameters"] = {"parameters": headers}
        params["sendBody"] = True
        params["specifyBody"] = "json"
        params["jsonBody"] = body
    node = {
        "parameters": params,
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [x, y],
        "retryOnFail": False,
    }
    if auth:
        node["credentials"] = CRED
    return node


def set_node(id_, name, x, y, assignments):
    return {
        "parameters": {
            "mode": "manual",
            "assignments": {
                "assignments": [
                    {
                        "id": a["id"],
                        "name": a["name"],
                        "type": a.get("type", "string"),
                        "value": a["value"],
                    }
                    for a in assignments
                ]
            },
            "options": {},
        },
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [x, y],
    }


def iff(id_, name, x, y, cond_id, left, operator):
    return {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "loose",
                    "version": 2,
                },
                "conditions": [
                    {
                        "id": cond_id,
                        "leftValue": left,
                        "rightValue": "",
                        "operator": operator,
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [x, y],
    }


def switch_status(id_, name, x, y):
    def rule(cid, value, key):
        return {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "loose",
                    "version": 2,
                },
                "conditions": [
                    {
                        "id": cid,
                        "leftValue": "={{ $json.statusCode }}",
                        "rightValue": value,
                        "operator": {"type": "number", "operation": "equals"},
                    }
                ],
                "combinator": "and",
            },
            "renameOutput": True,
            "outputKey": key,
        }

    return {
        "parameters": {
            "rules": {
                "values": [
                    rule("sw-200", 200, "ok"),
                    rule("sw-402", 402, "budget"),
                ]
            },
            "options": {"fallbackOutput": "extra"},
        },
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3.2,
        "position": [x, y],
    }


def respond(id_, name, x, y, code, body):
    return {
        "parameters": {
            "respondWith": "json",
            "responseBody": body,
            "options": {"responseCode": code},
        },
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.1,
        "position": [x, y],
        "onError": "continueRegularOutput",
        "alwaysOutputData": True,
    }


def code(id_, name, x, y, js):
    return {
        "parameters": {"jsCode": js.strip() + "\n"},
        "id": id_,
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y],
    }


def edge(src, dst, src_i=0):
    return src, dst, src_i


def main() -> None:
    nodes = [
        sticky(
            "sticky-overview",
            "Overview",
            OVERVIEW,
            -720,
            -48,
            560,
            1120,
            color=5,
        ),
        sticky(
            "sticky-mode",
            "Mode note",
            "## Mode\n`prove_retry` true (default): Call 1 MISS, identical Call 2 HIT in one Test. False: one crossing — leave it on so your own n8n retries are the HIT.",
            0,
            -48,
            360,
            248,
        ),
        sticky(
            "sticky-verify",
            "Verify note",
            "## Verify\nJWKS GET is public. The Code node checks Ed25519 with Node `crypto` (same algorithm as verify_receipt.py). A green `receipt_verified` is only set after that check passes. No JWS on a MISS is expected.\n\nGET session receipt returns the $0 `kind: \"session\"` receipt for everything tagged with this run's `X-Metrecept-Session`; the proof carries it as `session_receipt_verify_url`.",
            400,
            -48,
            400,
            248,
            color=4,
        ),
        sticky(
            "sticky-errors",
            "Errors note",
            "## Errors\n400 missing prompt. 402 budget (MISS flood / org cap — not retried). Other 4xx/5xx → 502. HIT without a JWS is `missing_header`, not a silent success.",
            840,
            -48,
            440,
            248,
        ),
        {
            "parameters": {},
            "id": "node-manual",
            "name": "Test once",
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [40, 320],
        },
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "metrecept-retry-proof",
                "responseMode": "responseNode",
                "options": {},
            },
            "id": "node-webhook",
            "name": "Call in",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [420, 320],
            "webhookId": "metrecept-retry-proof",
        },
        set_node(
            "node-config",
            "Config",
            800,
            320,
            [
                {"id": "c1", "name": "prove_retry", "type": "boolean", "value": PROVE},
                {"id": "c2", "name": "model", "value": MODEL},
                {"id": "c3", "name": "messages", "type": "array", "value": MESSAGES},
                {"id": "c4", "name": "session_id", "value": SESSION_ID},
            ],
        ),
        set_node(
            "node-freeze",
            "Freeze request body",
            1180,
            320,
            [
                {"id": "f1", "name": "prove_retry", "type": "boolean", "value": "={{ $json.prove_retry }}"},
                {"id": "f2", "name": "model", "value": "={{ $json.model }}"},
                {"id": "f3", "name": "messages", "type": "array", "value": "={{ $json.messages }}"},
                {
                    "id": "f4",
                    "name": "request_body",
                    "value": "={{ JSON.stringify({ model: $json.model, messages: $json.messages }) }}",
                },
                {"id": "f5", "name": "session_id", "value": "={{ $json.session_id }}"},
            ],
        ),
        iff(
            "node-if-payload",
            "Payload ok?",
            1180,
            620,
            "if-payload",
            "={{ Array.isArray($json.messages) && $json.messages.length > 0 }}",
            {"type": "boolean", "operation": "true", "singleValue": True},
        ),
        respond(
            "node-respond-400",
            "Respond invalid payload",
            1180,
            920,
            400,
            '={{ JSON.stringify({ error: "invalid_payload", expect: { prompt: "string", messages: "OpenAI messages array", prove_retry: "optional boolean" } }) }}',
        ),
        http_full(
            "node-call1",
            "Call 1",
            1560,
            620,
            "POST",
            "https://api.metrecept.co.uk/v1/chat/completions",
            body="={{ $json.request_body }}",
            session=True,
        ),
        switch_status("node-switch-c1", "HTTP status", 1940, 620),
        set_node(
            "node-extract-c1",
            "Extract call 1",
            2320,
            620,
            [
                {"id": "e1", "name": "prove_retry", "type": "boolean", "value": "={{ $('Freeze request body').item.json.prove_retry }}"},
                {"id": "e2", "name": "model", "value": "={{ $('Freeze request body').item.json.model }}"},
                {"id": "e3", "name": "messages", "type": "array", "value": "={{ $('Freeze request body').item.json.messages }}"},
                {"id": "e4", "name": "request_body", "value": "={{ $('Freeze request body').item.json.request_body }}"},
                {"id": "e5", "name": "call1_cache", "value": CACHE_H},
                {"id": "e6", "name": "call1_billed_usd", "value": BILLED_H},
                {"id": "e7", "name": "call1_status", "type": "number", "value": "={{ $json.statusCode }}"},
                {"id": "e8", "name": "call1_content", "value": CONTENT_H},
                {"id": "e9", "name": "receipt_jws", "value": RECEIPT_H},
                {"id": "e10", "name": "call2_cache", "value": ""},
                {"id": "e11", "name": "call2_billed_usd", "value": ""},
                {"id": "e12", "name": "session_id", "value": "={{ $('Freeze request body').item.json.session_id }}"},
            ],
        ),
        respond(
            "node-respond-402",
            "Respond budget",
            1940,
            920,
            402,
            '={{ JSON.stringify({ error: "budget", detail: "HTTP 402 — MISS flood / org cap. HITs would still serve. This workflow does not retry 402." }) }}',
        ),
        respond(
            "node-respond-502",
            "Respond upstream",
            1940,
            1220,
            502,
            '={{ JSON.stringify({ error: "upstream", status: $json.statusCode, body: JSON.stringify($json.body || $json).slice(0, 500) }) }}',
        ),
        iff(
            "node-if-retry",
            "Prove retry?",
            2700,
            620,
            "if-retry",
            "={{ $json.prove_retry !== false && $json.prove_retry !== 'false' && $json.prove_retry !== 0 && String($json.call1_cache || '').trim().toLowerCase() === 'miss' }}",
            {"type": "boolean", "operation": "true", "singleValue": True},
        ),
        http_full(
            "node-call2",
            "Call 2",
            2700,
            920,
            "POST",
            "https://api.metrecept.co.uk/v1/chat/completions",
            body="={{ $json.request_body }}",
            session=True,
        ),
        switch_status("node-switch-c2", "Call 2 status", 3080, 920),
        set_node(
            "node-extract-c2",
            "Extract call 2",
            3460,
            920,
            [
                {"id": "x1", "name": "prove_retry", "type": "boolean", "value": "={{ $('Extract call 1').item.json.prove_retry }}"},
                {"id": "x2", "name": "model", "value": "={{ $('Extract call 1').item.json.model }}"},
                {"id": "x3", "name": "messages", "type": "array", "value": "={{ $('Extract call 1').item.json.messages }}"},
                {"id": "x4", "name": "request_body", "value": "={{ $('Extract call 1').item.json.request_body }}"},
                {"id": "x5", "name": "call1_cache", "value": "={{ $('Extract call 1').item.json.call1_cache }}"},
                {"id": "x6", "name": "call1_billed_usd", "value": "={{ $('Extract call 1').item.json.call1_billed_usd }}"},
                {"id": "x7", "name": "call1_content", "value": "={{ $('Extract call 1').item.json.call1_content }}"},
                {"id": "x8", "name": "call2_cache", "value": CACHE_H},
                {"id": "x9", "name": "call2_billed_usd", "value": BILLED_H},
                {
                    "id": "x10",
                    "name": "receipt_jws",
                    "value": "={{ ($json.headers && ($json.headers['x-metrecept-receipt'] || $json.headers['x-metrecept-receipt'] || $json.headers['X-Metrecept-Receipt'] || $json.headers['X-Metrecept-Receipt'])) || $('Extract call 1').item.json.receipt_jws }}",
                },
                {"id": "x11", "name": "session_id", "value": "={{ $('Extract call 1').item.json.session_id }}"},
            ],
        ),
        set_node(
            "node-skip-c2",
            "Skip call 2",
            2700,
            1220,
            [
                {"id": "s1", "name": "prove_retry", "type": "boolean", "value": "={{ $json.prove_retry }}"},
                {"id": "s2", "name": "model", "value": "={{ $json.model }}"},
                {"id": "s3", "name": "messages", "type": "array", "value": "={{ $json.messages }}"},
                {"id": "s4", "name": "request_body", "value": "={{ $json.request_body }}"},
                {"id": "s5", "name": "call1_cache", "value": "={{ $json.call1_cache }}"},
                {"id": "s6", "name": "call1_billed_usd", "value": "={{ $json.call1_billed_usd }}"},
                {"id": "s7", "name": "call1_content", "value": "={{ $json.call1_content }}"},
                {"id": "s8", "name": "call2_cache", "value": ""},
                {"id": "s9", "name": "call2_billed_usd", "value": ""},
                {"id": "s10", "name": "receipt_jws", "value": "={{ $json.receipt_jws }}"},
                {"id": "s11", "name": "session_id", "value": "={{ $json.session_id }}"},
            ],
        ),
        set_node(
            "node-carry",
            "Carry receipt",
            3080,
            1220,
            [
                {"id": "k1", "name": "prove_retry", "type": "boolean", "value": "={{ $json.prove_retry }}"},
                {"id": "k2", "name": "model", "value": "={{ $json.model }}"},
                {"id": "k3", "name": "request_body", "value": "={{ $json.request_body }}"},
                {"id": "k4", "name": "call1_cache", "value": "={{ $json.call1_cache }}"},
                {"id": "k5", "name": "call1_billed_usd", "value": "={{ $json.call1_billed_usd }}"},
                {"id": "k6", "name": "call2_cache", "value": "={{ $json.call2_cache }}"},
                {"id": "k7", "name": "call2_billed_usd", "value": "={{ $json.call2_billed_usd }}"},
                {"id": "k8", "name": "receipt_jws", "value": "={{ $json.receipt_jws }}"},
                {"id": "k9", "name": "session_id", "value": "={{ $json.session_id }}"},
            ],
        ),
        iff(
            "node-if-jws",
            "Has JWS?",
            3460,
            1220,
            "if-jws",
            "={{ $json.receipt_jws }}",
            {"type": "string", "operation": "notEmpty", "singleValue": True},
        ),
        http_full(
            "node-jwks",
            "GET JWKS",
            3840,
            1220,
            "GET",
            "https://api.metrecept.co.uk/.well-known/http-message-signatures-directory",
            auth=False,
        ),
        iff(
            "node-if-jwks",
            "JWKS ok?",
            4220,
            1220,
            "if-jwks",
            "={{ $json.statusCode === 200 }}",
            {"type": "boolean", "operation": "true", "singleValue": True},
        ),
        code("node-verify", "Verify Ed25519", 4600, 1220, VERIFY_JS),
        set_node(
            "node-no-jws",
            "No JWS",
            3460,
            1520,
            [
                {"id": "n1", "name": "prove_retry", "type": "boolean", "value": "={{ $json.prove_retry }}"},
                {"id": "n2", "name": "model", "value": "={{ $json.model }}"},
                {"id": "n3", "name": "call1_cache", "value": "={{ $json.call1_cache }}"},
                {"id": "n4", "name": "call1_billed_usd", "value": "={{ $json.call1_billed_usd }}"},
                {"id": "n5", "name": "call2_cache", "value": "={{ $json.call2_cache }}"},
                {"id": "n6", "name": "call2_billed_usd", "value": "={{ $json.call2_billed_usd }}"},
                {"id": "n7", "name": "receipt_jws", "value": "={{ $json.receipt_jws }}"},
                {"id": "n8", "name": "session_id", "value": "={{ $json.session_id }}"},
            ],
        ),
        set_node(
            "node-jwks-fail",
            "JWKS failed",
            4220,
            1520,
            [
                {"id": "j1", "name": "flag", "value": "jwks_unavailable"},
            ],
        ),
        http_full(
            "node-session",
            "GET session receipt",
            4980,
            1220,
            "GET",
            "=https://api.metrecept.co.uk/v1/sessions/{{ encodeURIComponent($('Carry receipt').first().json.session_id) }}",
        ),
        code("node-proof", "Build proof", 5360, 1220, PROOF_JS),
        respond(
            "node-respond-proof",
            "Respond proof",
            5740,
            1220,
            200,
            "={{ JSON.stringify($json) }}",
        ),
    ]

    # (src, dst, src_output_index)
    wires = [
        ("Test once", "Config", 0),
        ("Call in", "Config", 0),
        ("Config", "Freeze request body", 0),
        ("Freeze request body", "Payload ok?", 0),
        ("Payload ok?", "Call 1", 0),
        ("Payload ok?", "Respond invalid payload", 1),
        ("Call 1", "HTTP status", 0),
        ("HTTP status", "Extract call 1", 0),
        ("HTTP status", "Respond budget", 1),
        ("HTTP status", "Respond upstream", 2),
        ("Extract call 1", "Prove retry?", 0),
        ("Prove retry?", "Call 2", 0),
        ("Prove retry?", "Skip call 2", 1),
        ("Call 2", "Call 2 status", 0),
        ("Call 2 status", "Extract call 2", 0),
        ("Call 2 status", "Respond budget", 1),
        ("Call 2 status", "Respond upstream", 2),
        ("Extract call 2", "Carry receipt", 0),
        ("Skip call 2", "Carry receipt", 0),
        ("Carry receipt", "Has JWS?", 0),
        ("Has JWS?", "GET JWKS", 0),
        ("Has JWS?", "No JWS", 1),
        ("GET JWKS", "JWKS ok?", 0),
        ("JWKS ok?", "Verify Ed25519", 0),
        ("JWKS ok?", "JWKS failed", 1),
        ("Verify Ed25519", "GET session receipt", 0),
        ("No JWS", "GET session receipt", 0),
        ("JWKS failed", "GET session receipt", 0),
        ("GET session receipt", "Build proof", 0),
        ("Build proof", "Respond proof", 0),
    ]

    connections: dict = {}
    for src, dst, idx in wires:
        bucket = connections.setdefault(src, {"main": []})
        mains = bucket["main"]
        while len(mains) <= idx:
            mains.append([])
        mains[idx].append({"node": dst, "type": "main", "index": 0})

    wf = {
        "name": "Prove an n8n AI retry was a cache HIT",
        "nodes": nodes,
        "connections": connections,
        "pinData": {
            "Test once": [
                {"json": {"prompt": "n8n retry proof: identical payload"}}
            ]
        },
        "meta": {
            "templateCredsSetupCompleted": False,
            "instanceId": "metrecept-opensource-demo",
        },
    }
    OUT.write_text(json.dumps(wf, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
