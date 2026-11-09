#!/usr/bin/env bash
set -euo pipefail

brew_command="${MYSQL_PATH_BREW:-$(command -v brew || true)}"
if [[ -z "$brew_command" || ! -x "$brew_command" ]]; then
  printf '%s\n' 'Homebrew was not found. Set MYSQL_PATH_BREW to its executable.' >&2
  exit 1
fi
brew_command="$(cd "$(dirname "$brew_command")" && pwd)/$(basename "$brew_command")"

printf 'Architecture: %s\n' "$(uname -m)"
"$brew_command" --version
printf 'Homebrew prefix: %s\n' "$("$brew_command" --prefix)"
client_prefix="$("$brew_command" --prefix --installed mysql-client)"
client_binary="$client_prefix/bin/mysql"
if [[ ! -x "$client_binary" ]]; then
  printf 'Installed prefix has no executable client: %s\n' "$client_binary" >&2
  exit 1
fi
printf 'Client prefix: %s\n' "$client_prefix"
"$brew_command" list --versions mysql-client
"$client_binary" --version

check_dir="$(mktemp -d "${TMPDIR:-/tmp}/mysql-path-check.XXXXXX")"
trap 'rm -rf "$check_dir"' EXIT

MYSQL_PATH_BREW="$brew_command" MYSQL_PATH_EXPECTED="$client_binary" \
  PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/zsh -f -c '
    set -eu
    if command -v mysql; then
      print -u2 "The clean baseline unexpectedly finds mysql."
      exit 1
    fi
    client_prefix="$("$MYSQL_PATH_BREW" --prefix --installed mysql-client)"
    export PATH="$client_prefix/bin:$PATH"
    rehash
    [[ "$(command -v mysql)" == "$MYSQL_PATH_EXPECTED" ]]
    mysql --version
    mysql --version
    print "Current shell: PASS"
  '

printf '%s\n' 'export MYSQL_PATH_EXISTING_CONTENT=preserved' > "$check_dir/.zshrc"
printf '%s\n' 'Existing data stays here.' > "$check_dir/existing-data.txt"
cp "$check_dir/.zshrc" "$check_dir/original.zshrc"
cp "$check_dir/existing-data.txt" "$check_dir/original-data.txt"
cat >> "$check_dir/.zshrc" <<'PROFILE'
export PATH="$(brew --prefix mysql-client)/bin:$PATH"
PROFILE

ZDOTDIR="$check_dir" MYSQL_PATH_BREW="$brew_command" MYSQL_PATH_EXPECTED="$client_binary" \
  PATH="$(dirname "$brew_command"):/usr/bin:/bin:/usr/sbin:/sbin" /bin/zsh -d -i -c '
    set -eu
    [[ "$MYSQL_PATH_EXISTING_CONTENT" == preserved ]]
    [[ "$(command -v mysql)" == "$MYSQL_PATH_EXPECTED" ]]
    mysql --version
    print "New interactive shell: PASS"
  '
head -n 1 "$check_dir/.zshrc" > "$check_dir/preserved.zshrc"
cmp "$check_dir/original.zshrc" "$check_dir/preserved.zshrc"
cmp "$check_dir/original-data.txt" "$check_dir/existing-data.txt"

if "$brew_command" --prefix --installed mysql-path-check-missing-formula > "$check_dir/missing.out" 2> "$check_dir/missing.err"; then
  printf '%s\n' 'The missing-formula installed check unexpectedly succeeded.' >&2
  exit 1
fi
[[ ! -s "$check_dir/missing.out" ]]
printf '%s\n' 'Missing formula: PASS' 'Existing startup content and data: PASS' 'All checks passed.'
