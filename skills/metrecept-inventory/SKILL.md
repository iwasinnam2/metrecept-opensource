---
name: metrecept-inventory
description: >
  Metrecept cache-tree inventory and cleanup via MCP metrecept_list_cache_trees,
  metrecept_list_cache_entries, metrecept_evict_cache_entry and
  metrecept_delete_cache_tree (exact-replay namespaces; digest/model/TTL/size).
---

# Metrecept inventory

```text
metrecept_list_cache_trees()
metrecept_list_cache_entries(tree_id="main", limit=25, offset=0)
metrecept_evict_cache_entry(digest="<digest>", tree_id="main")   # destructive
metrecept_delete_cache_tree(tree_id="<non-main tree>")            # destructive
```

`metrecept_list_cache_trees` lists trees. `metrecept_list_cache_entries` lists
entries in one tree — metadata only, never cached message content.
`metrecept_evict_cache_entry` removes one entry so the next identical request
is a fresh miss. `metrecept_delete_cache_tree` deletes a whole non-main tree
(refuses `main` and trees with child forks). Neither mutation is billed.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
