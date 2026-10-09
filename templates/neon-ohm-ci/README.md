# neon-ohm-ci

Drop-in CI compose: **Neon branches database state** (and AI Gateway per branch in beta); **withOhm branches exact-replay inventory**. Same PR slug. Upgrade alongside Gateway — not instead of it.

Docs: [Compose with Neon](https://www.withohm.dev/docs/compose-neon) · [Cache trees](https://www.withohm.dev/docs/cache-trees) · [CI preview](https://www.withohm.dev/use-cases/ci-preview)

## Fence

| Product | Branches | Noun |
|---------|----------|------|
| Neon | Postgres state (+ Gateway endpoint per branch in beta) | Preview connection / branch |
| withOhm | Exact-replay inventory | `X-Ohm-Cache-Tree` |

## Quick start

1. Copy the workflows into your app repo:

| Template file | Copy to |
|---------------|---------|
| `.github/workflows/ohm-preview.yml` | `.github/workflows/ohm-preview.yml` |
| `.github/workflows/ohm-promote-on-merge.yml` | `.github/workflows/ohm-promote-on-merge.yml` |

2. Optionally copy `scripts/ohm_tree.sh` (or keep the inline curl fallbacks in the workflows).

3. Secrets / vars:

| Name | Required | Notes |
|------|----------|--------|
| `OHM_API_KEY` | yes | Intermediate or design-partner `sk-at-…` |
| `OHM_API_URL` | no | Default `https://api.withohm.dev` |
| `OHM_UPSTREAM_KEY` | for real model calls | BYOK on cache miss |
| `DATABASE_URL` | if you run app tests | Neon branch connection string |

4. Behavior:

- **Every PR:** ensure tip `pr-<N>`; smoke chat with `X-Ohm-Cache-Tree`
- **On merge:** `POST /v1/cache/trees/pr-N/promote` into `main`

## Minimal curl (no Actions)

```bash
export OHM_KEY=sk-at-…
export OHM_API_URL=https://api.withohm.dev
export OHM_TIP=pr-842

curl -sS -X POST "$OHM_API_URL/v1/cache/trees" \
  -H "Authorization: Bearer $OHM_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$OHM_TIP\",\"parent\":\"main\"}" || true

curl -sS "$OHM_API_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OHM_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Ohm-Cache-Tree: $OHM_TIP" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ohm-ci-self-proof-v1"}]}'

curl -sS -X POST "$OHM_API_URL/v1/cache/trees/${OHM_TIP}/promote" \
  -H "Authorization: Bearer $OHM_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## What’s inside

| Path | Role |
|------|------|
| `.github/workflows/ohm-preview.yml` | PR: fork tip + smoke |
| `.github/workflows/ohm-promote-on-merge.yml` | Merge: promote tip → `main` |
| `scripts/ohm_tree.sh` | `fork` / `promote` / `echo-tree` helpers |

Powered by [withOhm](https://www.withohm.dev) — pipe rent, not token wholesale. BYOK.
