#!/usr/bin/env bash
# Metrecept cache-tree helpers for Neon-compose CI.
# Fence: Neon owns DATABASE_URL / NEON_BRANCH; Metrecept owns X-Metrecept-Cache-Tree.
set -euo pipefail

METRECEPT_API_URL="${METRECEPT_API_URL:-https://api.metrecept.co.uk}"
METRECEPT_BASE_URL="${METRECEPT_BASE_URL:-${METRECEPT_API_URL%/}/v1}"
METRECEPT_API_KEY="${METRECEPT_API_KEY:?METRECEPT_API_KEY is required}"

usage() {
  cat <<'EOF'
Usage:
  metrecept_tree.sh echo-tree [pr_number|slug]   # print TREE_ID (default: pr-$PR_NUMBER)
  metrecept_tree.sh fork <tree_id> [parent]      # POST /cache/trees (ok if exists)
  metrecept_tree.sh promote <tree_id> [into]      # POST /cache/trees/{id}/promote
EOF
}

auth_hdr=(-H "Authorization: Bearer ${METRECEPT_API_KEY}" -H "Content-Type: application/json")

echo_tree() {
  local raw="${1:-}"
  if [[ -z "$raw" ]]; then
    raw="${PR_NUMBER:-${GITHUB_PR_NUMBER:-}}"
    if [[ -z "$raw" && -n "${GITHUB_REF:-}" && "${GITHUB_REF}" =~ refs/pull/([0-9]+)/ ]]; then
      raw="${BASH_REMATCH[1]}"
    fi
  fi
  if [[ -z "$raw" ]]; then
    echo "pr-local"
    return
  fi
  if [[ "$raw" =~ ^pr- ]]; then
    echo "$raw" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | sed 's/-*$//'
  else
    echo "pr-${raw}" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | sed 's/-*$//'
  fi
}

fork_tree() {
  local name="${1:?tree id required}"
  local parent="${2:-main}"
  local code
  code=$(curl -sS -o /tmp/metrecept_fork.json -w "%{http_code}" -X POST \
    "${METRECEPT_BASE_URL}/cache/trees" \
    "${auth_hdr[@]}" \
    -d "{\"name\":\"${name}\",\"parent\":\"${parent}\"}")
  if [[ "$code" == "200" || "$code" == "201" ]]; then
    echo "forked ${name} from ${parent}"
    cat /tmp/metrecept_fork.json
    echo
    return 0
  fi
  if [[ "$code" == "409" ]]; then
    echo "tree ${name} already exists — reusing"
    return 0
  fi
  echo "fork failed HTTP ${code}" >&2
  cat /tmp/metrecept_fork.json >&2 || true
  return 1
}

promote_tree() {
  local name="${1:?tree id required}"
  local into="${2:-}"
  local body="{}"
  if [[ -n "$into" ]]; then
    body="{\"into\":\"${into}\"}"
  fi
  curl -sS -X POST \
    "${METRECEPT_BASE_URL}/cache/trees/${name}/promote" \
    "${auth_hdr[@]}" \
    -d "${body}"
  echo
}

cmd="${1:-}"
case "$cmd" in
  echo-tree) echo_tree "${2:-}" ;;
  fork) fork_tree "${2:-}" "${3:-main}" ;;
  promote) promote_tree "${2:-}" "${3:-}" ;;
  -h|--help|"") usage ;;
  *) usage; exit 1 ;;
esac
