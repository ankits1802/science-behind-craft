#!/usr/bin/env bash
set -euo pipefail

. /etc/kalavigyan/box.env
APP="${KV_APP:-/opt/kalavigyan}"
SNIPPET=/etc/nginx/snippets/kalavigyan-origin-verify.conf

[ "$(id -u)" = 0 ] || { echo "::error::run as root" >&2; exit 1; }
umask 077
work="$(mktemp -d /run/kv-env.XXXXXX)"
trap 'rm -rf "$work"' EXIT

aws ssm get-parameters-by-path --region "$KV_REGION" --path "$KV_ENV_PATH" --recursive --with-decryption \
  --query 'Parameters[].[Name,Value]' --output json | cat > "$work/raw.json"

python3 -I - "$work" "$KV_ENV_PATH" <<'PY'
import json
import re
import sys
from pathlib import Path

work = Path(sys.argv[1])
prefix = sys.argv[2].rstrip("/") + "/"
rows = json.loads((work / "raw.json").read_text())
values = {}
for name, value in rows:
    key = name[len(prefix):] if name.startswith(prefix) else name.rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
        print(f"skipped parameter with a key that is not an env name: {key}", file=sys.stderr)
        continue
    if "'" in value or "\n" in value or "\r" in value:
        print(f"::error::{key} holds a quote or a line break and cannot be written to an env file", file=sys.stderr)
        sys.exit(1)
    values[key] = value

def render(keys):
    return "".join(f"{k}='{values[k]}'\n" for k in sorted(keys))

fetcher_keys = [k for k in values if k.startswith("FETCHER_") or k in {"APP_ENV", "LOG_LEVEL"}]
(work / "app.env").write_text(render(values))
(work / "fetcher.env").write_text(render(fetcher_keys))
secret = values.get("ORIGIN_VERIFY_SECRET", "")
if secret and re.fullmatch(r"[A-Za-z0-9]{32,}", secret):
    (work / "origin.conf").write_text(
        "set $kv_origin_ok 0;\n"
        "if ($remote_addr = 127.0.0.1) { set $kv_origin_ok 1; }\n"
        "if ($remote_addr = ::1) { set $kv_origin_ok 1; }\n"
        f'if ($http_x_origin_verify = "{secret}") {{ set $kv_origin_ok 1; }}\n'
        "if ($kv_origin_ok = 0) { return 403; }\n"
    )
print(f"{len(values)} keys for the API, {len(fetcher_keys)} for the fetcher", file=sys.stderr)
PY

place() {
  local src="$1" dst="$2"
  if ! cmp -s "$src" "$dst" 2>/dev/null; then
    install -o root -g kalavigyan -m 0640 "$src" "$dst.new"
    mv -f "$dst.new" "$dst"
    echo "updated $dst (sha256 $(sha256sum "$dst" | cut -c1-12))" >&2
  else
    echo "unchanged $dst" >&2
  fi
}
place "$work/app.env" "$APP/.env"
place "$work/fetcher.env" "$APP/fetcher.env"

if [ -f "$work/origin.conf" ]; then
  if ! cmp -s "$work/origin.conf" "$SNIPPET"; then
    cp -p "$SNIPPET" "$work/origin.prev" 2>/dev/null || true
    install -o root -g root -m 0640 "$work/origin.conf" "$SNIPPET"
    if nginx -t >/dev/null 2>&1; then
      systemctl reload nginx
      echo "nginx now requires CloudFront's origin header" >&2
    else
      if [ -f "$work/origin.prev" ]; then cp -p "$work/origin.prev" "$SNIPPET"; else printf 'allow 127.0.0.1;\nallow ::1;\ndeny all;\n' > "$SNIPPET"; fi
      echo "::error::nginx refused the origin-header snippet; the previous one is back" >&2
      exit 1
    fi
  fi
else
  echo "::warning::ORIGIN_VERIFY_SECRET is not in Parameter Store; nginx stays closed to everything but loopback" >&2
fi
