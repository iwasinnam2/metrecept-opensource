#!/usr/bin/env bash
# Promote tip inventory into main (merge hygiene for exact-replay).
set -euo pipefail

: "${OHM_API_URL:=https://api.withohm.dev}"
: "${OHM_API_KEY:?OHM_API_KEY required}"
: "${OHM_TIP:?OHM_TIP required}"

code=$(curl -sS -o /tmp/ohm-promote.json -w "%{http_code}" \
  -X POST "${OHM_API_URL}/v1/cache/trees/${OHM_TIP}/promote" \
  -H "Authorization: Bearer ${OHM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}')

if [[ "$code" != "200" && "$code" != "201" ]]; then
  echo "promote failed HTTP ${code}" >&2
  cat /tmp/ohm-promote.json >&2 || true
  exit 1
fi

echo "promoted ${OHM_TIP} → main"
cat /tmp/ohm-promote.json
