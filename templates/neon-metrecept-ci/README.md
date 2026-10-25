# neon-metrecept-ci

Drop-in CI compose: **Neon branches database state** (and AI Gateway per branch in beta); **Metrecept branches exact-replay inventory**. Same PR slug. Upgrade alongside Gateway — not instead of it.

Docs: [Compose with Neon](https://metrecept.co.uk/docs/compose-neon) · [Cache trees](https://metrecept.co.uk/docs/cache-trees) · [CI preview](https://metrecept.co.uk/use-cases/ci-preview)

## Fence

| Product | Branches | Noun |
|---------|----------|------|
| Neon | Postgres state (+ Gateway endpoint per branch in beta) | Preview connection / branch |
| Metrecept | Exact-replay inventory | `X-Metrecept-Cache-Tree` |

## Quick start

1. Copy the workflows into your app repo:

| Template file | Copy to |
|---------------|---------|
| `.github/workflows/metrecept-preview.yml` | `.github/workflows/metrecept-preview.yml` |
| `.github/workflows/metrecept-promote-on-merge.yml` | `.github/workflows/metrecept-promote-on-merge.yml` |

2. Optionally copy `scripts/metrecept_tree.sh` (or keep the inline curl fallbacks in the workflows).

3. Secrets / vars:

| Name | Required | Notes |
|------|----------|--------|
| `METRECEPT_API_KEY` | yes | Intermediate or design-partner `sk-at-…` |
| `METRECEPT_API_URL` | no | Default `https://api.metrecept.co.uk` |
| `METRECEPT_UPSTREAM_KEY` | for real model calls | BYOK on cache miss |
| `DATABASE_URL` | if you run app tests | Neon branch connection string |

4. Behavior:

- **Every PR:** ensure tip `pr-<N>`; smoke chat with `X-Metrecept-Cache-Tree`
- **On merge:** `POST /v1/cache/trees/pr-N/promote` into `main`

## Minimal curl (no Actions)

```bash
export METRECEPT_KEY=sk-at-…
export METRECEPT_API_URL=https://api.metrecept.co.uk
export METRECEPT_TIP=pr-842

curl -sS -X POST "$METRECEPT_API_URL/v1/cache/trees" \
  -H "Authorization: Bearer $METRECEPT_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$METRECEPT_TIP\",\"parent\":\"main\"}" || true

curl -sS "$METRECEPT_API_URL/v1/chat/completions" \
  -H "Authorization: Bearer $METRECEPT_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Metrecept-Cache-Tree: $METRECEPT_TIP" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"metrecept-ci-self-proof-v1"}]}'

curl -sS -X POST "$METRECEPT_API_URL/v1/cache/trees/${METRECEPT_TIP}/promote" \
  -H "Authorization: Bearer $METRECEPT_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## What’s inside

| Path | Role |
|------|------|
| `.github/workflows/metrecept-preview.yml` | PR: fork tip + smoke |
| `.github/workflows/metrecept-promote-on-merge.yml` | Merge: promote tip → `main` |
| `scripts/metrecept_tree.sh` | `fork` / `promote` / `echo-tree` helpers |

Powered by [Metrecept](https://metrecept.co.uk) — signed receipts for every agent call. BYOK.
