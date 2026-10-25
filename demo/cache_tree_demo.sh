#!/usr/bin/env bash
# Proves named cache trees stay isolated: the same request body MISSes on
# each of two independent trees the first time it's sent there, even though
# it already HIT on the other tree (or on main). See docs/CACHE_TREES.md.
#
# Usage:
#   METRECEPT_API_KEY=sk-at-... ./demo/cache_tree_demo.sh
set -euo pipefail

BASE_URL="${METRECEPT_BASE_URL:-https://api.metrecept.co.uk}"

if [ -z "${METRECEPT_API_KEY:-}" ]; then
  echo "Set METRECEPT_API_KEY first — get a free \$0 key at https://metrecept.co.uk/billing/intermediate" >&2
  exit 1
fi

STAMP=$(date +%s)
BODY='{"model":"mock","messages":[{"role":"user","content":"tree-demo '"$STAMP"'"}]}'

request() {
  local tree="$1"
  curl -sSi "$BASE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $METRECEPT_API_KEY" \
    -H "Content-Type: application/json" \
    -H "X-Metrecept-Cache-Tree: $tree" \
    -d "$BODY" | grep -i "^x-at-cache:\|^x-metrecept-cache-tree:"
}

echo "== Tree 'demo-a', first send (expect MISS) =="
request "demo-a-$STAMP"

echo
echo "== Tree 'demo-b', SAME body, first send on this tree (expect MISS too — trees are isolated) =="
request "demo-b-$STAMP"

echo
echo "== Tree 'demo-a' again, same body (expect HIT — this tree already saw it) =="
request "demo-a-$STAMP"

echo
echo "A MISS on tree B despite an identical body already HITting on tree A is the whole point:"
echo "one gateway, isolated exact-replay inventory per tree. See docs/CACHE_TREES.md."
