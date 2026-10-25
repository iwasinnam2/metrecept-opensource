# Cache trees — branchable exact-replay inventory

Named, isolated exact-replay inventory for Metrecept. Complements a data-branching product like Neon (branches Postgres state) without cloning its model — Metrecept branches **exact-replay inventory**, not a database.

Parent concept: [ARCHITECTURE.md](ARCHITECTURE.md)'s Ephemeral Side / Pipeline System split.

## Dual containers

| Ephemeral Side | Pipeline System |
|----------------|-------------------|
| Hot exact-replay inventory (blobs, trees, edge HIT) | Durable money, policy, compliance, trust |
| Fork / reset / promote / freeze | Auth, meters, receipts, audit |

**The idea in one sentence:** other tools branch state, or discount a prefix. Metrecept branches the cache of exact repeats, and every call is still metered and receipted.

## Key layout

| Tree | Redis key |
|------|-----------|
| Default `main` (no header) | Durable, shared exact-replay inventory |
| Named tree | Isolated per-tree inventory, same digest scheme |

- The digest is always a SHA-256 of the canonicalized request (model + messages + extras) — this is what a receipt's `request_sha256` field refers to.
- Tree id: `[a-z0-9_-]{1,64}`; header `X-Metrecept-Cache-Tree` wins over an equivalent body field.
- Unknown / invalid explicit tree -> `400`.
- Exact-match only inside a tree. No semantic cache. No cross-tenant trees.

## Storage honesty (what's actually shipped)

Named-tree blobs use per-tree Redis keys. CoW reads walk the parent chain and serve a parent blob without copying it into the child. **Promote is a metadata write**: for each digest the child holds, the parent gets one ref naming the tree that holds the bytes, the owner blob's expiry is extended to at least the cache TTL and never shortened, and the parent index gains the digest. Bytes are never copied (`bytes_copied` is always `0` in the promote response). A ref whose bytes have expired is a MISS, not a stale HIT. `GET /v1/cache/trees/{tree_id}/entries` shows `served_from`, `ref` and `refs` per digest. This is one blob, many refs, within one tenant; there is no cross-tenant sharing.

This candor is itself part of the pitch: the goal is a repo that tells you what's true today, not what's aspirational.

## Client surface

- Header: `X-Metrecept-Cache-Tree: pr-842` (optional)
- Body: `cache_tree` (optional; header wins)
- Response echo: `X-Metrecept-Cache-Tree`

```bash
curl -sS https://api.metrecept.co.uk/v1/chat/completions \
  -H "Authorization: Bearer $METRECEPT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Metrecept-Cache-Tree: pr-842" \
  -d '{"model":"mock","messages":[{"role":"user","content":"hi"}]}'
```

See [`demo/cache_tree_demo.sh`](../demo/cache_tree_demo.sh) for a runnable example showing that two named trees stay independent.

## API

| Method | Path | Role |
|--------|------|------|
| `GET` | `/v1/cache/trees` | List trees |
| `POST` | `/v1/cache/trees` | Fork `{name, parent?}` |
| `POST` | `/v1/cache/trees/{id}/reset` | `{to: empty\|parent}` |
| `POST` | `/v1/cache/trees/{id}/promote` | Merge child digests into parent |
| `POST` | `/v1/cache/trees/{id}/freeze` | Immutable tip; further writes reject |

Every fork/reset/promote/freeze (and denied variant) is an audited Pipeline action, same as any other governance operation.

## Non-goals

- Postgres / WAL / schema-branch cosplay — this is not a database product
- Semantic / fuzzy cache, at any tree granularity
- Cross-tenant shared trees

## Compose with a data-branching tool

If you already branch database state per PR (e.g. a preview `DATABASE_URL`), pair it with a same-named cache tree in CI: same job, two headers, two clear nouns (data state vs. exact-replay inventory). This doesn't replace database branching — it's the inventory peer in the same workflow, so preview-branch traffic doesn't silently warm (or pollute) the durable `main` inventory.

```bash
export METRECEPT_TIP="pr-${PR_NUMBER}"

curl -sS https://api.metrecept.co.uk/v1/chat/completions \
  -H "Authorization: Bearer $METRECEPT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Metrecept-Cache-Tree: $METRECEPT_TIP" \
  -d @prompt.json

# on green — promote inventory to main
curl -sS -X POST "https://api.metrecept.co.uk/v1/cache/trees/${METRECEPT_TIP}/promote" \
  -H "Authorization: Bearer $METRECEPT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"target":"main"}'
```

## Anti-pattern

Putting every agent/PR job on `main`, then spinning up a second gateway when collisions appear, buys more keys to manage — not isolation. Isolation is a tree problem: keep one gateway, split trees, promote when a tree earns `main`.
