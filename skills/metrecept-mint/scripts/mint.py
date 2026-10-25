#!/usr/bin/env python3
"""Mint a fresh signed Metrecept receipt and verify it locally.

Usage: mint.py <kind> [label]   kinds: cache_miss cache_hit cache_bypass finops api_call session custody statement carve savings web_fetch
Env: OHM_API_KEY (required), OHM_BASE_URL (default https://api.metrecept.co.uk/v1)
"""
import base64, hashlib, json, os, re, sys, time, urllib.error, urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def b64d(s): return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def get_key():
    k = os.environ.get('OHM_API_KEY', '').strip()
    if not k: sys.exit('error: OHM_API_KEY is not set')
    return k

KINDS = {
    'cache_miss': 'fresh chat prompt (X-Metrecept-Receipt)',
    'cache_hit': 'same chat prompt twice; the second call is the replay',
    'cache_bypass': 'fresh chat prompt with cache_control=no_store',
    'finops': 'FinOps companion of a fresh chat call (X-Metrecept-Finops-Receipt)',
    'api_call': 'GET passthrough to your first registered API service (POST /v1/api_call)',
    'session': 'tagged chat call, then the session aggregate (GET /v1/sessions/{id})',
    'custody': 'one "access" custody record for a placeholder subject (POST /v1/custody)',
    'statement': "this month's ledger statement (GET /v1/org/ledger/statement)",
    'carve': 'carve hop over the label text (POST /v1/carve, disperse off)',
    'savings': 'savings attestation for your org (POST /v1/savings/receipt)',
    'web_fetch': 'chat call with fetch_web_context over https://example.com (X-Metrecept-Fetch-Receipt)',
}
HEADERS = ('X-Metrecept-Receipt', 'X-Metrecept-Finops-Receipt', 'X-Metrecept-Fetch-Receipt')
JWS_RE = re.compile(r'eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+')

def usage():
    print('usage: mint <kind> [label]\nsupported kinds:', file=sys.stderr)
    for k, v in KINDS.items(): print(f'  {k:12} {v}', file=sys.stderr)
    sys.exit(2)

def req(base, key, path, body=None, method=None):
    """Call the gateway; return (parsed JSON body or None, receipt candidates)."""
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data,
        {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=90)
    except urllib.error.HTTPError as e:
        sys.exit(f'error: HTTP {e.code} from gateway on {path.split("?")[0]}')
    except Exception as e:
        sys.exit(f'error: request failed: {type(e).__name__}')
    text = resp.read().decode('utf-8', 'replace')
    found = [resp.headers.get(h) for h in HEADERS if resp.headers.get(h)]
    found += JWS_RE.findall(text)
    try: parsed = json.loads(text)
    except ValueError: parsed = None
    return parsed, found

def chat(base, key, content, **extra):
    return req(base, key, '/v1/chat/completions',
               {"model": "mock", "messages": [{"role": "user", "content": content}], **extra})[1]

def mint_candidates(kind, base, key, label):
    tag = f"{label} {kind} {time.time_ns()}"
    if kind in ('cache_miss', 'finops'): return chat(base, key, tag)
    if kind == 'cache_hit': chat(base, key, tag); return chat(base, key, tag)
    if kind == 'cache_bypass': return chat(base, key, tag, cache_control='no_store')
    if kind == 'session':
        sid = f"metrecept-mint-{time.time_ns()}"
        chat(base, key, tag, metrecept_session=sid)
        return req(base, key, '/v1/sessions/' + sid, method='GET')[1]
    if kind == 'custody':
        return req(base, key, '/v1/custody', {"action": "access", "subject_id": "metrecept-mint",
            "item_sha256": hashlib.sha256(tag.encode()).hexdigest(), "source": "metrecept-mint", "store": "mint"})[1]
    if kind == 'statement':
        return req(base, key, '/v1/org/ledger/statement?month=' + time.strftime('%Y-%m', time.gmtime()), method='GET')[1]
    if kind == 'carve':
        return req(base, key, '/v1/carve', {"ingest": tag, "disperse": False})[1]
    if kind == 'savings':
        return req(base, key, '/v1/savings/receipt', {})[1]
    if kind == 'web_fetch':
        return chat(base, key, tag, fetch_web_context=True, web_urls=['https://example.com/'],
                    web_purpose='public_web_retrieval')
    if kind == 'api_call':
        svcs, _ = req(base, key, '/v1/api_services', method='GET')
        svcs = (svcs or {}).get('services') or []
        if not svcs: sys.exit('error: api_call needs a registered API service (POST /v1/api_services)')
        s = svcs[0]
        return req(base, key, '/v1/api_call', {"service": s['name'], "path": s.get('allowed_path_prefix') or '/',
                                              "query": {"metrecept_mint": label}})[1]

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in KINDS: usage()
    kind = sys.argv[1]
    label = ' '.join(sys.argv[2:]) or 'metrecept-mint'
    base = os.environ.get('OHM_BASE_URL', 'https://api.metrecept.co.uk/v1').rstrip('/')
    if base.endswith('/v1'): base = base[:-3]
    jwss = mint_candidates(kind, base, get_key(), label)
    jws = None
    for j in jwss:
        try:
            if json.loads(b64d(j.split('.')[1])).get('kind') == kind: jws = j; break
        except Exception: pass
    if not jws: sys.exit(f'error: gateway returned no receipt of kind {kind}')
    try:
        d = json.load(urllib.request.urlopen(base + '/.well-known/http-message-signatures-directory', timeout=30))
        keys = {k['kid']: k for k in d['keys']}
        h, p, s = jws.split('.')
        hdr = json.loads(b64d(h)); pl = json.loads(b64d(p))
        if hdr['kid'] not in keys: sys.exit(f"error: kid {hdr['kid']} not in key directory")
        Ed25519PublicKey.from_public_bytes(b64d(keys[hdr['kid']]['x'])).verify(b64d(s), (h + '.' + p).encode())
    except SystemExit: raise
    except Exception as e:
        sys.exit(f'error: signature verification FAILED ({type(e).__name__})')
    if pl.get('kind') != kind: sys.exit('error: kind mismatch')
    print('kind:', pl.get('kind'))
    print('kid:', hdr['kid'])
    print('iat:', pl.get('iat'))
    print('meter_event_id:', pl.get('meter_event_id'))
    print('signature valid')
    print('verify:', 'https://metrecept.co.uk/verify#' + jws)

if __name__ == '__main__':
    main()
