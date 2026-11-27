#!/usr/bin/env bash
set -euo pipefail

REACHING_RUNS=("Backend checks:push" "Deploy backend:" "Deploy web app:")
RUNS_READ=20

reached_at=""
counted=""
age=0

newest_run_holding_expected() {
  local asked workflow event runs at head
  local -a filters
  for asked in "${REACHING_RUNS[@]}"; do
    workflow="${asked%%:*}"
    event="${asked#*:}"
    filters=(--workflow "$workflow" --branch main --limit "$RUNS_READ")
    [ -z "$event" ] || filters+=(--event "$event")
    if ! runs="$(gh run list -R "$GITHUB_REPOSITORY" "${filters[@]}" --json createdAt,headSha --jq '.[] | "\(.createdAt) \(.headSha)"')"; then
      echo "::warning::the runs of $workflow could not be read, so they do not say when main reached ${EXPECTED:0:12}"
      continue
    fi
    while read -r at head; do
      [ -n "${head:-}" ] || continue
      git merge-base --is-ancestor "$EXPECTED" "$head" 2> /dev/null || continue
      if [[ "$at" > "$reached_at" ]]; then reached_at="$at"; fi
    done <<< "$runs"
  done
}

measure_age() {
  local since
  newest_run_holding_expected
  if [ -n "$reached_at" ]; then
    since="$(date -d "$reached_at" +%s)"
    counted="the newest run of main that holds it, started $reached_at"
  else
    since="$(git log -1 --format=%ct "$EXPECTED")"
    counted="its commit date, since no run of main that holds it could be read"
  fi
  age=$(( $(date +%s) - since ))
  echo "${EXPECTED:0:12} reached main $(( age / 60 )) minutes ago, counted from $counted"
}

case "$MODE:$BUILT" in
  deploy:none) verdict=no-build ;;
  deploy:failure) verdict=refused ;;
  deploy:success|asked:success) if [ "$REACHED" = yes ]; then verdict=served; else verdict=behind; fi ;;
  latest:success)
    if [ -z "$HAVE" ]; then verdict=silent
    elif [ "$REACHED" = yes ]; then verdict=served
    else
      measure_age
      if [ "$age" -lt "$GRACE_SECONDS" ]; then verdict=building; else verdict=behind; fi
    fi
    ;;
  *) echo "::error::unknown mode $MODE with build $BUILT"; exit 1 ;;
esac
echo "verdict=$verdict" >> "$GITHUB_OUTPUT"
unread=""
[ "$MODE" = latest ] || unread=", so the pages were not read against an older build or API"
{
  echo "### Production commit"
  echo ""
  echo "Production serves \`${HAVE:-no commit}\` and its API \`${HAVE_API:-no release}\`; it should serve \`${EXPECTED:-any commit}\` or a later commit of main, with the API that build needs. Verdict: $verdict (waited ${WAITED:-0}s)."
} >> "$GITHUB_STEP_SUMMARY"
case "$verdict" in
  served) echo "production serves $HAVE" ;;
  no-build) echo "::notice::this deploy started no web build; production serves ${HAVE:-no commit}, so the pages are not read" ;;
  building) echo "::notice::the newest deployable commit ${EXPECTED:0:12} reached main less than $(( GRACE_SECONDS / 60 )) minutes ago; its build may still be running" ;;
  behind) echo "::error::production still serves ${HAVE:-no commit} on the site and ${HAVE_API:-no release} on the API, not ${EXPECTED:0:12} or a later commit of main with the API it needs, after waiting ${WAITED:-0}s: its Vercel build or the backend deploy it needs failed or never finished$unread"; exit 1 ;;
  silent) echo "::error::$WEB_ORIGIN/api/version reports no commit"; exit 1 ;;
  refused) echo "::error::the deploy hook did not start the build of ${EXPECTED:0:12}$unread"; exit 1 ;;
esac
