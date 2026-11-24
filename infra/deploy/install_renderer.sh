#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PIN="$HERE/chromium.pin"
BROWSERS=/opt/chrome-headless-shell
SHELL_DIR=chrome-headless-shell-linux64
BINARY=chrome-headless-shell
SKIPPED=" ca-certificates libc6 libcurl3-gnutls libgtk-3-0 libgtk-4-1 libvulkan1 wget xdg-utils "

say() { printf '%s\n' "$*" >&2; }
die() { say "::error::$*"; exit 1; }
pinned() { sed -n "s/^$1=//p" "$PIN"; }

[ "$(id -u)" = 0 ] || die "run as root"
[ -f "$PIN" ] || die "$PIN is missing; the release does not say which browser draws the page previews"
CHROME_VERSION="$(pinned CHROME_VERSION)"
CHROME_URL="$(pinned CHROME_URL)"
CHROME_SHA256="$(pinned CHROME_SHA256)"
[[ "$CHROME_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "$PIN: CHROME_VERSION '$CHROME_VERSION' is not a Chrome for Testing version"
[[ "$CHROME_URL" == "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chrome-headless-shell-linux64.zip" ]] || die "$PIN: CHROME_URL is not the pinned headless shell's download"
[[ "$CHROME_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "$PIN: CHROME_SHA256 is not a sha256"
TARGET="$BROWSERS/$CHROME_VERSION/$SHELL_DIR"

install_browser() {
  local stage
  if [ -x "$TARGET/$BINARY" ]; then
    say "chrome-headless-shell $CHROME_VERSION is already installed in $TARGET"
    return 0
  fi
  install -d -o root -g root -m 0755 "$BROWSERS" "$BROWSERS/$CHROME_VERSION"
  stage="$(mktemp -d "$BROWSERS/.incoming.XXXXXX")"
  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 5 --retry-delay 10 --retry-all-errors --connect-timeout 30 --max-time 900 -o "$stage/shell.zip" "$CHROME_URL" \
    || ! echo "${CHROME_SHA256}  $stage/shell.zip" | sha256sum -c - >&2 \
    || ! unzip -q "$stage/shell.zip" -d "$stage" \
    || ! chown -R root:root "$stage/$SHELL_DIR" \
    || ! chmod -R go-w,a+rX "$stage/$SHELL_DIR" \
    || ! mv -T "$stage/$SHELL_DIR" "$TARGET"; then
    rm -rf "$stage"
    die "chrome-headless-shell $CHROME_VERSION could not be installed from $CHROME_URL; nothing was changed"
  fi
  rm -rf "$stage"
  say "installed chrome-headless-shell $CHROME_VERSION in $TARGET"
}

wanted_libraries() {
  local line name
  while IFS= read -r line; do
    name="${line%%|*}"
    name="${name%%(*}"
    name="${name//[[:space:]]/}"
    [ -n "$name" ] || continue
    case "$SKIPPED" in *" $name "*) continue ;; esac
    printf '%s\n' "$name"
  done < "$TARGET/deb.deps"
}

candidate() {
  local policy
  policy="$(apt-cache policy "$1" 2>/dev/null)" || return 1
  grep -q "Candidate: [^(]" <<<"$policy"
}

resolved() {
  local name
  while IFS= read -r name; do
    if ! candidate "$name" && candidate "${name}t64"; then name="${name}t64"; fi
    printf '%s\n' "$name"
  done
}

install_libraries() {
  local wanted=() missing
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >&2 || say "::warning::apt-get update failed; the libraries are resolved against the lists already held"
  mapfile -t wanted < <(wanted_libraries | resolved)
  if [ "${#wanted[@]}" -gt 0 ]; then
    apt-get install -y --no-install-recommends "${wanted[@]}" >&2 \
      || die "the libraries chrome-headless-shell needs could not be installed: ${wanted[*]}"
  fi
  missing="$(ldd "$TARGET/$BINARY" | awk '/not found/ {print $1}' | tr '\n' ' ')"
  [ -z "$missing" ] || die "chrome-headless-shell $CHROME_VERSION still lacks: $missing"
}

point_current() {
  ln -sfn "$TARGET" "$BROWSERS/current.tmp"
  mv -Tf "$BROWSERS/current.tmp" "$BROWSERS/current"
  say "the renderer draws with $(readlink -f "$BROWSERS/current")"
}

install_browser
install_libraries
point_current
