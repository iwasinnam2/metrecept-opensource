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
metrecept_manage_cache_tree(action="fork", tree_id="main", name="pr-42")
metrecept_manage_cache_tree(action="promote", tree_id="pr-42")    # merge into parent
```

`metrecept_list_cache_trees` lists trees. `metrecept_list_cache_entries` lists
entries in one tree — metadata only, never cached message content.
`metrecept_evict_cache_entry` removes one entry so the next identical request
is a fresh miss. `metrecept_delete_cache_tree` deletes a whole non-main tree
(refuses `main` and trees with child forks). `metrecept_manage_cache_tree` creates, forks (copy-on-write, entries shared
by reference) or promotes (merges a tree's own entries into its parent or
`main` by reference; `main` stays the default). None of these is billed.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
