#!/usr/bin/env bash
set -euo pipefail

COMMIT='^[0-9a-f]{40}$'

say() { printf '%s\n' "$*"; }

[[ "$WAIT_SECONDS" =~ ^[0-9]+$ ]] || { say "::error::wait-seconds must be a whole number of seconds"; exit 1; }
[ -z "$EXPECTED" ] || [[ "$EXPECTED" =~ $COMMIT ]] || { say "::error::commit must be a full commit id"; exit 1; }

web_commit() {
  curl -fsS -m 15 -H 'cache-control: no-cache' "$ORIGIN/api/version" 2> /dev/null | jq -r '.commit // empty' 2> /dev/null || true
}

api_release() {
  [ -n "${API_ORIGIN:-}" ] || return 0
  curl -fsS -m 15 -H 'cache-control: no-cache' "$API_ORIGIN/health" 2> /dev/null | jq -r '.release // empty' 2> /dev/null || true
}

held() {
  git cat-file -e "$1^{commit}" 2> /dev/null || git fetch --quiet origin main 2> /dev/null || true
  git cat-file -e "$1^{commit}" 2> /dev/null
}

descends() {
  [ "$1" = "$2" ] && return 0
  held "$2" && git merge-base --is-ancestor "$1" "$2"
}

api_paths=()
if [ -n "${API_ORIGIN:-}" ]; then
  command -v yq > /dev/null || { say "::error::yq is not on the runner; cannot read the Backend checks push paths"; exit 1; }
  mapfile -t globs < <(yq -r '.on.push.paths[]' .github/workflows/backend-checks.yml)
  [ "${#globs[@]}" -gt 0 ] || { say "::error::Backend checks lists no push paths"; exit 1; }
  for glob in "${globs[@]}"; do api_paths+=(":(glob)$glob"); done
fi

serves_api_of() {
  local web="$1" api="$2"
  [ -n "${API_ORIGIN:-}" ] || return 0
  [[ "$api" =~ $COMMIT ]] || return 1
  descends "$web" "$api" && return 0
  held "$api" && held "$web" && git merge-base --is-ancestor "$api" "$web" && git diff --quiet "$api" "$web" -- "${api_paths[@]}"
}

[ "$BUILT" = success ] && [ -n "$EXPECTED" ] || WAIT_SECONDS=0
start="$(date +%s)"
deadline=$(( start + WAIT_SECONDS ))
reached=no
while :; do
  have="$(web_commit)"
  api="$(api_release)"
  if [ -n "$EXPECTED" ] && [ -n "$have" ] && descends "$EXPECTED" "$have" && serves_api_of "$have" "$api"; then reached=yes; break; fi
  [ "$(date +%s)" -lt "$deadline" ] || break
  say "production serves ${have:-no commit}${API_ORIGIN:+ and its API ${api:-no release}}; waiting for ${EXPECTED:0:12} on both ($(( $(date +%s) - start ))s of ${WAIT_SECONDS}s)"
  sleep 20
done
waited=$(( $(date +%s) - start ))
{
  echo "served=$have"
  echo "api=$api"
  echo "reached=$reached"
  echo "waited=$waited"
} >> "$GITHUB_OUTPUT"
say "production serves ${have:-no commit}${API_ORIGIN:+ and its API ${api:-no release}}; ${EXPECTED:+reached ${EXPECTED:0:12}: $reached after ${waited}s}"
