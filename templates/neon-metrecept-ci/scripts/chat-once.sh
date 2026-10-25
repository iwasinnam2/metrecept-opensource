#!/usr/bin/env bash
# Smoke chat on an cache tip (mock model — no upstream key required).
set -euo pipefail

: "${METRECEPT_API_URL:=https://api.metrecept.co.uk}"
: "${METRECEPT_API_KEY:?METRECEPT_API_KEY required}"
: "${METRECEPT_TIP:?METRECEPT_TIP required}"

curl -sS "${METRECEPT_API_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${METRECEPT_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "X-Metrecept-Cache-Tree: ${METRECEPT_TIP}" \
  -d '{"model":"mock","messages":[{"role":"user","content":"neon-metrecept-ci ping"}]}' \
  | tee /tmp/metrecept-chat-once.json

grep -Eq '"object"[[:space:]]*:[[:space:]]*"chat.completion"|"choices"' /tmp/metrecept-chat-once.json
echo "chat-once ok on tip ${METRECEPT_TIP}"
