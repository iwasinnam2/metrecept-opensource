# at-utility-sdk (Python)

Thin helper so the official OpenAI SDK becomes a one-line `base_url` swap for **Metrecept**.

Package name remains `at-utility-sdk` until first PyPI publish; then rename to `ohm-sdk`.

## Install (editable)

```bash
cd sdks/python
pip install -e ".[openai]"
```

## Publish to PyPI

Only after `https://api.metrecept.co.uk/v1` answers chat — see [docs/PLATFORM.md](../../docs/PLATFORM.md).

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

### The receipt as a link

Every receipted response carries `X-Metrecept-Verify`, a public link that
checks the signature in the reader's browser — no account. Append it to
whatever the agent already produced (PR body, ticket, email):

```python
from at_utility_sdk import receipt_trailer

body = body + "\n\n" + receipt_trailer(response.headers)
# -> "Receipt: https://metrecept.co.uk/verify#eyJ..."
```

It also accepts the JSON of `GET /v1/sessions/{id}`. Returns `""` when
there is nothing to link. The JWS rides the URL fragment, so it never
reaches a server log.

A streamed MISS cannot carry its receipt in a header (the headers leave
before the provider has finished), so it rides as the last `data:` chunk
before `[DONE]`, with empty `choices`. Read it out of the stream you kept:

```python
from at_utility_sdk import receipt_from_sse_lines, verify_url

jws = receipt_from_sse_lines(captured.splitlines())   # "" when the stream did not finish
link = verify_url(jws) if jws else ""
```
