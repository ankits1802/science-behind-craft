#!/usr/bin/env bash
set -euo pipefail
[ "$1 $2" = "run list" ] || { echo "this stub answers gh run list only, not gh $*" >&2; exit 2; }
shift 2
workflow=""
event=""
branch=""
program="."
while [ "$#" -gt 0 ]; do
  case "$1" in
    --workflow) workflow="$2"; shift 2 ;;
    --event) event="$2"; shift 2 ;;
    --branch) branch="$2"; shift 2 ;;
    --jq) program="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[ "${RUNS_UNREAD:-}" != yes ] || { echo "HTTP 502: the runs could not be listed" >&2; exit 1; }
jq --arg workflow "$workflow" --arg event "$event" --arg branch "$branch" \
  '[.[] | select(.workflowName == $workflow and .headBranch == $branch and ($event == "" or .event == $event))]' \
  "$RUNS" | jq -r "$program"
