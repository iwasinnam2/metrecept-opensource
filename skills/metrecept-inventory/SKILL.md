---
name: metrecept-inventory
description: >
  Metrecept cache-tree inventory via MCP metrecept_cache_trees and
  metrecept_cache_inventory (exact-replay namespaces; digest/model/TTL/size).
---

# Metrecept inventory

```text
metrecept_cache_trees()
metrecept_cache_inventory(tree_id="main", limit=25, offset=0)
```

`metrecept_cache_trees` lists trees. `metrecept_cache_inventory` lists
entries in one tree — metadata only, never cached message content.
`metrecept_cache_trees` / `metrecept_cache_inventory` are the same handlers.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
