# at-utility-sdk (Python)

Thin helper so the official OpenAI SDK becomes a one-line `base_url` swap for **Metrecept**.

Package name remains `at-utility-sdk` until first PyPI publish; then rename to `ohm-sdk`.

## Install (editable)

```bash
cd sdks/python
pip install -e ".[openai]"
```

## Publish to PyPI

Only after `https://api.withohm.dev/v1` answers chat — see [docs/PLATFORM.md](../../docs/PLATFORM.md).

```bash
cd sdks/python
python -m build
twine upload dist/*
```

## Usage

```python
from at_utility_sdk import openai_client, LOCAL_BASE_URL, DEFAULT_BASE_URL

client = openai_client("sk-at-dev", base_url=LOCAL_BASE_URL)
# After cutover:
# client = openai_client("sk-at-...", base_url=DEFAULT_BASE_URL)
```

In-house metal with no client URL — digest only, prompt stays on the box:

```python
from at_utility_sdk import wrap_generate

chat = wrap_generate(
    my_model.generate,
    api_key="sk-at-...",
    base_url="https://api.metrecept.co.uk/v1",
    model="co-analyst",
)
answer = chat([{"role": "user", "content": "same 10-K question"}])
```

`wrap_generate` checks every HIT's signed receipt automatically —
fail-open, so a missing or invalid receipt never breaks the call, and only
a *present-and-invalid* receipt (or an unreachable key directory) logs a
warning. It's a private, duplicated copy of the same stranger-verifier
algorithm as `scripts/verify_receipt.py` (JWKS fetch + Ed25519 check) — no
new protocol, no new wire field.

`openai_client` returns a bare `openai.OpenAI(...)` client, so there's
nothing to hook automatically. Run the same check manually against
`.with_raw_response`:

```python
from at_utility_sdk import openai_client, check_receipt

client = openai_client("sk-at-...")
resp = client.chat.completions.with_raw_response.create(
    model="mock", messages=[{"role": "user", "content": "hi"}]
)
check_receipt(resp.headers, base_url=str(client.base_url))
completion = resp.parse()
```
