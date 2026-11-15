#!/usr/bin/env bash
set -euo pipefail

SHA="${1:?release needs the commit sha}"
TARBALL="${2:?release needs the tarball path}"
KEEP="${KEEP_RELEASES:-5}"
. /etc/kalavigyan/box.env
APP="${KV_APP:-/opt/kalavigyan}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REL="$APP/releases/$SHA"

say() { printf '%s\n' "$*" >&2; }
die() { say "::error::$*"; exit 1; }

[ "$(id -u)" = 0 ] || die "run as root"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || die "release id must be a full commit sha"
[ -x "$KV_PYTHON" ] || die "$KV_PYTHON is missing; the box was not built by user_data.sh"
command -v uv >/dev/null || die "uv is not installed"

install_units() {
  local changed=no f name
  for f in "$HERE"/units/*; do
    name="$(basename "$f")"
    if ! cmp -s "$f" "/etc/systemd/system/$name"; then
      install -m 0644 "$f" "/etc/systemd/system/$name"
      changed=yes
      say "installed /etc/systemd/system/$name"
    fi
  done
  if ! cmp -s "$HERE/api-watchdog.sh" /usr/local/bin/api-watchdog.sh; then
    install -m 0755 "$HERE/api-watchdog.sh" /usr/local/bin/api-watchdog.sh
  fi
  if ! cmp -s "$HERE/blue_green.sh" /usr/local/sbin/kv-blue-green; then
    install -m 0755 "$HERE/blue_green.sh" /usr/local/sbin/kv-blue-green
  fi
  if ! cmp -s "$HERE/render_env.sh" /usr/local/sbin/kv-render-env; then
    install -m 0755 "$HERE/render_env.sh" /usr/local/sbin/kv-render-env
  fi
  if [ "$changed" = yes ]; then systemctl daemon-reload; fi
  systemctl enable --now api-watchdog.timer >/dev/null 2>&1 || say "::warning::api-watchdog.timer did not start"
}

build_release() {
  if [ -f "$REL/.complete" ]; then
    say "$REL is already built; reusing it"
    return 0
  fi
  rm -rf "$REL"
  install -d -o root -g kalavigyan -m 0755 "$REL"
  tar -xzf "$TARBALL" -C "$REL" --no-same-owner
  [ -f "$REL/backend/pyproject.toml" ] || die "the tarball has no backend/pyproject.toml"
  local args=(sync --no-dev --no-editable --python "$KV_PYTHON")
  if [ -f "$REL/backend/uv.lock" ]; then args+=(--frozen); else say "::warning::backend/uv.lock is missing; resolving dependencies on the box"; fi
  (
    cd "$REL/backend"
    export UV_CACHE_DIR=/var/cache/kalavigyan-uv UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT="$REL/backend/.venv" UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
    uv "${args[@]}"
  ) || { rm -rf "$REL"; die "uv sync failed; the release was removed"; }
  "$REL/backend/.venv/bin/python" -I -c 'import sys; print("venv python", sys.version.split()[0])'
  ln -sfn "$APP/.env" "$REL/backend/.env"
  printf '%s\n' "$SHA" > "$REL/REVISION"
  chown -R root:kalavigyan "$REL"
  chmod -R go-w "$REL"
  touch "$REL/.complete"
}

prune() {
  local keep=() r n=0
  for r in current slot-8000 slot-8001; do
    if [ -e "$APP/$r" ]; then keep+=("$(readlink -f "$APP/$r")"); fi
  done
  while IFS= read -r r; do
    n=$((n + 1))
    [ "$n" -le "$KEEP" ] && keep+=("$r") && continue
    if printf '%s\n' "${keep[@]}" | grep -qxF "$r"; then continue; fi
    rm -rf "$r"
    say "pruned $r"
  done < <(find "$APP/releases" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)
}

install_units
/usr/local/sbin/kv-render-env
if [ -f "$REL/.complete" ] && [ "$(readlink -f "$APP/current" 2>/dev/null || true)" = "$(readlink -f "$REL")" ]; then
  say "$SHA is already live; restarting it so it reads the current environment"
  /usr/local/sbin/kv-blue-green restart
else
  build_release
  /usr/local/sbin/kv-blue-green release "$SHA"
  prune
fi
curl -fsS -m 10 -o /dev/null http://127.0.0.1/health || die "nginx does not answer /health after the release"
/usr/local/sbin/kv-blue-green status
rm -f "$TARBALL"
say "release $SHA is live"
