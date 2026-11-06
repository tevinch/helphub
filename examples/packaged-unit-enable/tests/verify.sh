#!/usr/bin/env bash
# Run only on an ephemeral Linux CI runner. Creates a dedicated disposable user.
set -euo pipefail

cd "$(dirname "$0")/.."
for required in nix systemctl; do
  if ! command -v "$required" >/dev/null; then
    echo "Native check requires $required on an ephemeral Linux runner." >&2
    exit 1
  fi
done
test "$(cat /proc/1/comm)" = systemd

test_user=unitcheck
unit=syncthing.service # The fixture uses this name; it does not run Syncthing.
test_home=/var/tmp/unitcheck
state_file=/var/lib/hjem/manifest-unitcheck.json
if id "$test_user" >/dev/null 2>&1 || test -e "$test_home" || sudo test -e "$state_file"; then
  echo 'Disposable test account or state already exists; refusing to reuse it.' >&2
  exit 1
fi

work=$(mktemp -d)
created_user=false
uid=
cleanup() {
  if "$created_user"; then
    sudo systemctl stop "user@${uid}.service" || true
    sudo systemctl stop "user-runtime-dir@${uid}.service" || true
    sudo userdel --remove "$test_user" || true
    sudo rm -f "$state_file"
  fi
  rm -rf "$work"
}
trap cleanup EXIT

# The bundle evaluates the real Hjem module and builds its activation/state
# scripts. No handwritten manifest or manual positive-path symlink is used.
nix build --extra-experimental-features 'nix-command flakes' \
  --no-write-lock-file --print-build-logs .#verificationBundle \
  --out-link "$work/bundle"
bundle=$(readlink -f "$work/bundle")

sudo useradd --home-dir "$test_home" --create-home --shell /bin/bash "$test_user"
created_user=true
uid=$(id -u "$test_user")
sudo install -d -m 0755 /var/lib/hjem
sudo -u "$test_user" sh -c 'printf "preserve me\n" > /var/tmp/unitcheck/unrelated.txt'

as_user() {
  sudo -u "$test_user" env \
    XDG_RUNTIME_DIR="/run/user/$uid" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
    "$@"
}
stop_manager() {
  sudo systemctl stop "user@${uid}.service"
  sudo systemctl stop "user-runtime-dir@${uid}.service"
}
activate() {
  as_user "$bundle/$1/activate" "$test_user"
  # This is the same separate state-update phase used by the NixOS module.
  sudo "$bundle/$1/update-state" "$test_user"
  test "$(cat "$test_home/unrelated.txt")" = 'preserve me'
}
assert_links() {
  local snapshot=$1
  local primary="$test_home/.config/systemd/user/$unit"
  local wants="$test_home/.config/systemd/user/default.target.wants/$unit"
  local expected
  expected=$(readlink "$bundle/$snapshot/original-unit")
  test -L "$primary"
  test -L "$wants"
  test "$(readlink "$primary")" = "$expected"
  test "$(readlink "$wants")" = "$expected"
  cmp "$primary" "$bundle/$snapshot/original-unit"
  grep -q '^ExecStart=' "$primary"
}
start_and_expect() {
  local expected=$1
  # Fresh user-manager startup reaches default.target by itself. Deliberately
  # never issue 'systemctl --user start syncthing.service' here.
  sudo systemctl start "user@${uid}.service"
  local ready=false
  for _ in $(seq 1 100); do
    if as_user systemctl --user is-active --quiet "$unit" &&
      test -f "$test_home/unit-marker"; then
      ready=true
      break
    fi
    sleep 0.1
  done
  "$ready"
  test "$(cat "$test_home/unit-marker")" = "$expected"
  test "$(as_user systemctl --user show "$unit" --property=ExecMainStatus --value)" = 0
  local active_timestamp
  active_timestamp=$(as_user systemctl --user show "$unit" --property=ActiveEnterTimestampMonotonic --value)
  [[ "$active_timestamp" =~ ^[1-9][0-9]*$ ]]
  as_user systemctl --user is-enabled "$unit"
  as_user systemctl --user cat "$unit"
}

activate v1
assert_links v1
start_and_expect v1
stop_manager

old_source=$(readlink "$test_home/.config/systemd/user/$unit")
activate v2
assert_links v2
test "$(readlink "$test_home/.config/systemd/user/$unit")" != "$old_source"
sudo -u "$test_user" rm "$test_home/unit-marker"
start_and_expect v2
stop_manager

activate v2
assert_links v2
sudo -u "$test_user" rm "$test_home/unit-marker"
start_and_expect v2
stop_manager

# Control: retain the package import but omit the wants-link recipe. Actual
# Hjem activation must remove its formerly managed link. No manual unlink.
activate no-wants
test -L "$test_home/.config/systemd/user/$unit"
test ! -e "$test_home/.config/systemd/user/default.target.wants/$unit"
test ! -L "$test_home/.config/systemd/user/default.target.wants/$unit"
sudo -u "$test_user" rm "$test_home/unit-marker"
sudo systemctl start "user@${uid}.service"
as_user systemctl --user is-active --quiet default.target
if as_user systemctl --user is-active --quiet "$unit"; then
  echo 'Package-only control unexpectedly auto-started the fixture.' >&2
  exit 1
fi
test ! -e "$test_home/unit-marker"
test "$(cat "$test_home/unrelated.txt")" = 'preserve me'
printf '%s\n' 'PASS: real Hjem activation, v1/v2 startup, idempotence, and no-wants control.'
