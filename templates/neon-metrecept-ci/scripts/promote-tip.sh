#!/usr/bin/env bash
# Promote tip inventory into main (merge hygiene for exact-replay).
set -euo pipefail

: "${METRECEPT_API_URL:=https://api.metrecept.co.uk}"
: "${METRECEPT_API_KEY:?METRECEPT_API_KEY required}"
: "${METRECEPT_TIP:?METRECEPT_TIP required}"

code=$(curl -sS -o /tmp/metrecept-promote.json -w "%{http_code}" \
  -X POST "${METRECEPT_API_URL}/v1/cache/trees/${METRECEPT_TIP}/promote" \
  -H "Authorization: Bearer ${METRECEPT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}')

if [[ "$code" != "200" && "$code" != "201" ]]; then
  echo "promote failed HTTP ${code}" >&2
  cat /tmp/metrecept-promote.json >&2 || true
  exit 1
fi

echo "promoted ${METRECEPT_TIP} → main"
cat /tmp/metrecept-promote.json
