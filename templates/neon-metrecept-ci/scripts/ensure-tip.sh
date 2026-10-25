#!/usr/bin/env bash
# Ensure a Metrecept cache tip exists (fork from main). Idempotent enough for CI:
# create succeeds, or list confirms the tip is already present.
set -euo pipefail

: "${METRECEPT_API_URL:=https://api.metrecept.co.uk}"
: "${METRECEPT_API_KEY:?METRECEPT_API_KEY required}"
: "${METRECEPT_TIP:?METRECEPT_TIP required}"

code=$(curl -sS -o /tmp/metrecept-tip-create.json -w "%{http_code}" \
  -X POST "${METRECEPT_API_URL}/v1/cache/trees" \
  -H "Authorization: Bearer ${METRECEPT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${METRECEPT_TIP}\"}")

if [[ "$code" == "200" || "$code" == "201" ]]; then
  echo "tip created: ${METRECEPT_TIP}"
  exit 0
fi

# Already exists / conflict — verify via list
list=$(curl -sS "${METRECEPT_API_URL}/v1/cache/trees" \
  -H "Authorization: Bearer ${METRECEPT_API_KEY}")
if echo "$list" | grep -Fq "\"${METRECEPT_TIP}\""; then
  echo "tip already present: ${METRECEPT_TIP}"
  exit 0
fi

echo "ensure-tip failed HTTP ${code}" >&2
cat /tmp/metrecept-tip-create.json >&2 || true
exit 1
