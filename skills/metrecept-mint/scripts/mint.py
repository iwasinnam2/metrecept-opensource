#!/usr/bin/env python3
"""Mint a fresh signed Metrecept receipt and verify it locally.

Usage: mint.py <kind> [label]   kinds: cache_miss, cache_hit, finops
Env: OHM_API_KEY (required), OHM_BASE_URL (default https://api.metrecept.co.uk/v1)
"""
import base64, json, os, sys, time, urllib.error, urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def b64d(s): return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def get_key():
    k = os.environ.get('OHM_API_KEY', '').strip()
    if not k: sys.exit('error: OHM_API_KEY is not set')
    return k

KINDS = {
    'cache_miss': 'fresh prompt, first call (X-Metrecept-Receipt)',
    'cache_hit': 'same prompt sent twice, second call is the replay (X-Metrecept-Receipt)',
    'finops': 'fresh prompt, finops receipt (X-Metrecept-Finops-Receipt)',
}
HEADERS = ('X-Metrecept-Receipt', 'X-Metrecept-Finops-Receipt')

def usage():
    print('usage: mint <kind> [label]\nsupported kinds:', file=sys.stderr)
    for k, v in KINDS.items(): print(f'  {k:11} {v}', file=sys.stderr)
    sys.exit(2)

def post(base, key, body):
    req = urllib.request.Request(base + '/v1/chat/completions', json.dumps(body).encode(),
        {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        sys.exit(f'error: HTTP {e.code} from gateway')
    except Exception as e:
        sys.exit(f'error: request failed: {type(e).__name__}')
    r.read()
    return [r.headers.get(h) for h in HEADERS if r.headers.get(h)]

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in KINDS: usage()
    kind = sys.argv[1]
    label = ' '.join(sys.argv[2:]) or 'metrecept-mint'
    base = os.environ.get('OHM_BASE_URL', 'https://api.metrecept.co.uk/v1').rstrip('/')
    if base.endswith('/v1'): base = base[:-3]
    key = get_key()
    body = {"model": "mock", "messages": [{"role": "user", "content": f"{label} {kind} {time.time_ns()}"}]}
    jwss = post(base, key, body)
    if kind == 'cache_hit': jwss = post(base, key, body)
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
