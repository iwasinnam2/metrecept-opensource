#!/usr/bin/env bash
# Proves the core claim live: an identical request MISSes once, then HITs for
# free — and the HIT carries a signed receipt you can verify yourself.
#
# Usage:
#   OHM_API_KEY=sk-at-... ./demo/hit_miss_demo.sh
#
# Get a free key (no card) at https://metrecept.co.uk/billing/intermediate
set -euo pipefail

BASE_URL="${OHM_BASE_URL:-https://api.metrecept.co.uk}"

if [ -z "${OHM_API_KEY:-}" ]; then
  echo "Set OHM_API_KEY first — get a free \$0 key at https://metrecept.co.uk/billing/intermediate" >&2
  exit 1
fi

BODY='{"model":"mock","messages":[{"role":"user","content":"withohm-open demo '"$(date +%s)"'"}]}'

echo "== Request 1 (expect MISS) =="
resp1=$(curl -sSi "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OHM_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BODY")
echo "$resp1" | grep -i "^x-at-cache:" || echo "(no X-AT-Cache header — check your key)"

echo
echo "== Request 2, identical body (expect HIT) =="
resp2=$(curl -sSi "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OHM_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BODY")
echo "$resp2" | grep -i "^x-at-cache:"
echo "$resp2" | grep -i "^x-at-billed-usd:" || true

receipt=$(echo "$resp2" | grep -i "^x-ohm-receipt:" | sed 's/^[Xx]-[Oo]hm-[Rr]eceipt: *//' | tr -d '\r')

if [ -n "$receipt" ]; then
  echo
  echo "== Verifying the signed receipt (zero Metrecept code) =="
  python3 "$(dirname "$0")/verify_receipt.py" "$receipt" --base "$BASE_URL"
else
  echo "(no X-Ohm-Receipt header on this response — receipts may be disabled for this tenant)"
fi
