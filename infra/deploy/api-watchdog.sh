#!/bin/bash
U="$1"
for u in $(systemctl list-units "${U}@*" --state=running --no-legend --plain | awk '{print $1}'); do
  p="${u#"${U}"@}"; p="${p%.service}"
  f="/run/api-watchdog-$p"
  if curl -s -o /dev/null --max-time 10 -w '%{http_code}' "http://127.0.0.1:$p/health" | grep -q '^200$'; then
    rm -f "$f"
  else
    n=$(( $(cat "$f" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$f"
    logger -t api-watchdog "$u health failed ($n)"
    if [ "$n" -ge 2 ]; then logger -t api-watchdog "restarting $u"; systemctl restart "$u"; rm -f "$f"; fi
  fi
done
