# A co-signed crossing, minted on the hosted pipe

Three files, one record. No account is needed to check them.

- `body.json` — the request body the caller sent (`model: mock`).
- `attest.jws` — the caller's own Ed25519 signature over that body, sent as
  the `X-Metrecept-Attest` request header. Its public key rides in the JWS
  header; `kid` is the RFC 7638 thumbprint of that key.
- `receipt.jws` — the pipe's receipt for the crossing. Signed by the pipe's
  key (public directory: `https://api.metrecept.co.uk/.well-known/http-message-signatures-directory`).
  It carries `attest_sha256` = sha256 of `attest.jws`, `attest_kid` = the
  caller's kid, and `body_sha256` = the canonical digest of `body.json`.

Check all three from a cold start (needs `pip install cryptography`):

```bash
python demo/attest_demo.py check \
  --receipt demo/fixtures/cosigned/receipt.jws \
  --attest  demo/fixtures/cosigned/attest.jws \
  --body    demo/fixtures/cosigned/body.json
```

Expected: `OK` (pipe signature), `OK (co-sign)` (caller signature and the
binding), `OK (body)` (the body canonicalises to the digest both keys
signed). Change one character of `body.json` and the last line fails.

What it proves: the caller asserted this body, the pipe counted this
crossing, and the two agree on the bytes. What it does not prove: who
holds the caller's key (a key, not a person), whether the model's answer
was right, or anything about a write the pipe did not make.

Minted 13 October 2026, 00:40 UTC, on `api.metrecept.co.uk` with a
throwaway attest key whose seed was not kept. The crossing was tagged with
the planted session id used in the n8n "one ID" run that night, so the same
id reaches this record as well.
