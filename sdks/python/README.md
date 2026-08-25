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
