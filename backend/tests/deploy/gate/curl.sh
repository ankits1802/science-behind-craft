#!/usr/bin/env bash
for asked in "$@"; do
  case "$asked" in
    */api/version)
      if [ "$WEB_COMMIT" = unreachable ]; then exit 7; fi
      printf '{"commit": "%s", "ref": "main"}\n' "$WEB_COMMIT"
      exit 0
      ;;
  esac
done
if [ "$LIVE_RELEASE" = unreachable ]; then exit 7; fi
printf '{"status": "ok", "release": "%s", "version": "1"}\n' "$LIVE_RELEASE"
