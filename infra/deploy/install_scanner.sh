#!/usr/bin/env bash
set -euo pipefail

PACKAGES=(clamav-daemon clamav-freshclam clamdscan)
CONF=/etc/clamav/clamd.conf
SOCKET=/var/run/clamav/clamd.ctl
SIGNATURES=/var/lib/clamav
DROP_IN=/etc/systemd/system/clamav-daemon.service.d/kalavigyan.conf
MEMORY_MAX=2G
SIGNATURE_WAIT_SECONDS=600
PING_TRIES=60
PING_INTERVAL=3
EICAR_HEAD='X5O!P%@AP[4\PZX54(P^)7CC)7}$'
EICAR_TAIL='EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

say() { printf '%s\n' "$*" >&2; }
die() { say "::error::$*"; exit 1; }

[ "$(id -u)" = 0 ] || die "run as root"

install_packages() {
  local missing=() name
  for name in "${PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$name" 2>/dev/null | grep -q "install ok installed" || missing+=("$name")
  done
  if [ "${#missing[@]}" -eq 0 ]; then
    say "the upload scanner's packages are installed"
    return 0
  fi
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >&2 || say "::warning::apt-get update failed; the scanner is installed from the lists already held"
  apt-get install -y --no-install-recommends "${missing[@]}" >&2 || die "the upload scanner could not be installed: ${missing[*]}"
  say "installed ${missing[*]}"
}

set_option() {
  local key="$1" value="$2"
  if grep -q "^${key} ${value}\$" "$CONF"; then
    return 1
  fi
  if grep -q "^${key} " "$CONF"; then
    sed -i "s|^${key} .*|${key} ${value}|" "$CONF"
  else
    printf '%s %s\n' "$key" "$value" >> "$CONF"
  fi
  say "clamd.conf: ${key} ${value}"
}

configure() {
  local changed=no drop_in
  [ -f "$CONF" ] || die "$CONF is missing after the install"
  grep -q "^LocalSocket ${SOCKET}\$" "$CONF" || die "clamd does not listen on $SOCKET, where the API's MALWARE_SCAN_SOCKET points"
  set_option LocalSocketMode 666 && changed=yes
  set_option ConcurrentDatabaseReload no && changed=yes
  set_option StreamMaxLength 25M && changed=yes
  drop_in="$(printf '[Service]\nMemoryAccounting=yes\nMemoryMax=%s\nRestart=on-failure\nRestartSec=10\n' "$MEMORY_MAX")"
  if [ "$(cat "$DROP_IN" 2>/dev/null || true)" != "$drop_in" ]; then
    install -d -m 0755 "$(dirname "$DROP_IN")"
    printf '%s\n' "$drop_in" > "$DROP_IN"
    systemctl daemon-reload
    changed=yes
    say "clamav-daemon runs under MemoryMax=$MEMORY_MAX"
  fi
  printf '%s' "$changed"
}

wait_for_signatures() {
  local deadline=$(( $(date +%s) + SIGNATURE_WAIT_SECONDS ))
  systemctl enable --now clamav-freshclam >/dev/null 2>&1 || die "clamav-freshclam did not start"
  until compgen -G "$SIGNATURES/main.c[lv]d" >/dev/null && compgen -G "$SIGNATURES/daily.c[lv]d" >/dev/null; do
    [ "$(date +%s)" -lt "$deadline" ] || die "freshclam fetched no signatures in ${SIGNATURE_WAIT_SECONDS}s (journalctl -u clamav-freshclam)"
    sleep 10
  done
}

start_daemon() {
  local changed="$1"
  systemctl enable clamav-daemon >/dev/null 2>&1 || true
  if [ "$changed" = yes ] || ! systemctl is-active --quiet clamav-daemon; then
    systemctl restart clamav-daemon || die "clamav-daemon did not start (journalctl -u clamav-daemon)"
  fi
  clamdscan --ping="${PING_TRIES}:${PING_INTERVAL}" >/dev/null 2>&1 || die "clamd does not answer on $SOCKET"
}

self_test() {
  local verdict
  verdict="$(printf 'district,artisans\nKachchh,412\n' | clamdscan --no-summary --stream - 2>&1)" || die "clamd refused a clean table: $verdict"
  if verdict="$(printf '%s%s' "$EICAR_HEAD" "$EICAR_TAIL" | clamdscan --no-summary --stream - 2>&1)"; then
    die "clamd passed the EICAR test file: $verdict"
  fi
  case "$verdict" in
    *FOUND*) say "the upload scanner passes a clean file and finds the EICAR test file" ;;
    *) die "clamd could not scan the EICAR test file: $verdict" ;;
  esac
}

install_packages
changed="$(configure)"
wait_for_signatures
start_daemon "$changed"
self_test
