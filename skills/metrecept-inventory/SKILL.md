---
name: metrecept-inventory
description: >
  Metrecept cache-tree inventory via MCP metrecept_cache_trees and
  metrecept_cache_inventory. Use when checking what is cached, on which tip,
  and for how long — Metrecept, mcp, inventory, cache trees.
---

# Metrecept inventory

```text
metrecept_cache_trees()
metrecept_cache_inventory(tree_id="main", limit=25, offset=0)
```

`metrecept_cache_trees` lists named exact-replay namespaces.
`metrecept_cache_inventory` lists entry metadata only (digest, model, TTL,
size) — never cached message content.

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
