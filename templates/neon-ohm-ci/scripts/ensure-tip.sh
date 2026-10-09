#!/usr/bin/env bash
# Ensure an Ohm cache tip exists (fork from main). Idempotent enough for CI:
# create succeeds, or list confirms the tip is already present.
set -euo pipefail

: "${OHM_API_URL:=https://api.withohm.dev}"
: "${OHM_API_KEY:?OHM_API_KEY required}"
: "${OHM_TIP:?OHM_TIP required}"

code=$(curl -sS -o /tmp/ohm-tip-create.json -w "%{http_code}" \
  -X POST "${OHM_API_URL}/v1/cache/trees" \
  -H "Authorization: Bearer ${OHM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${OHM_TIP}\"}")

if [[ "$code" == "200" || "$code" == "201" ]]; then
  echo "tip created: ${OHM_TIP}"
  exit 0
fi

# Already exists / conflict — verify via list
list=$(curl -sS "${OHM_API_URL}/v1/cache/trees" \
  -H "Authorization: Bearer ${OHM_API_KEY}")
if echo "$list" | grep -Fq "\"${OHM_TIP}\""; then
  echo "tip already present: ${OHM_TIP}"
  exit 0
fi

echo "ensure-tip failed HTTP ${code}" >&2
cat /tmp/ohm-tip-create.json >&2 || true
exit 1
