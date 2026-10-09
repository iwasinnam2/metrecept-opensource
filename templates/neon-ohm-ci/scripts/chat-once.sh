#!/usr/bin/env bash
# Smoke chat on an Ohm tip (mock model — no upstream key required).
set -euo pipefail

: "${OHM_API_URL:=https://api.withohm.dev}"
: "${OHM_API_KEY:?OHM_API_KEY required}"
: "${OHM_TIP:?OHM_TIP required}"

curl -sS "${OHM_API_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${OHM_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "X-Ohm-Cache-Tree: ${OHM_TIP}" \
  -d '{"model":"mock","messages":[{"role":"user","content":"neon-ohm-ci ping"}]}' \
  | tee /tmp/ohm-chat-once.json

grep -Eq '"object"[[:space:]]*:[[:space:]]*"chat.completion"|"choices"' /tmp/ohm-chat-once.json
echo "chat-once ok on tip ${OHM_TIP}"
