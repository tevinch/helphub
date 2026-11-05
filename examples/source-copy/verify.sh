#!/bin/sh
set -eu

project=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
workspace=$(mktemp -d "${TMPDIR:-/tmp}/source-copy.XXXXXX")
image="source-copy-check-$$"
trap 'rm -rf "$workspace"; docker image rm "$image:source-only" "$image:touch-only" "$image:restored" "$image:updated" >/dev/null 2>&1 || true' EXIT HUP INT TERM
cp -R "$project/." "$workspace/"

# Build contexts commonly contain source files older than the cooking step.
# Keep this case deterministic without editing the original project files.
touch -t 202001010000 "$workspace/Cargo.toml" "$workspace/Cargo.lock" "$workspace/src/main.rs"

docker build --progress plain --target source-only -t "$image:source-only" "$workspace"
output=$(docker run --rm "$image:source-only")
test -z "$output"
printf '%s\n' 'PASS: copying only src reuses the silent dummy executable.'

docker build --progress plain --target touch-only -t "$image:touch-only" "$workspace"
output=$(docker run --rm "$image:touch-only")
test "$output" = 'application started (version 0.0.1)'
printf '%s\n' 'PASS: touching only src recompiles with the prepared package version 0.0.1.'

docker build --progress plain --target restored -t "$image:restored" "$workspace"
output=$(docker run --rm "$image:restored")
test "$output" = 'application started (version 0.1.0)'
printf '%s\n' 'PASS: restoring the real project runs application version 0.1.0.'

sed 's/application started/application updated/' "$workspace/src/main.rs" > "$workspace/src/main.rs.new"
mv "$workspace/src/main.rs.new" "$workspace/src/main.rs"
if ! docker build --progress plain --target restored -t "$image:updated" "$workspace" > "$workspace/updated-build.log" 2>&1; then
    cat "$workspace/updated-build.log"
    exit 1
fi
cat "$workspace/updated-build.log"
awk '/\[cooked .*RUN cargo chef cook/ {step=$1} $1 == step && $2 == "CACHED" {found=1} END {exit !found}' "$workspace/updated-build.log"
output=$(docker run --rm "$image:updated")
test "$output" = 'application updated (version 0.1.0)'
printf '%s\n' 'PASS: a source edit reuses the cooking layer and runs the updated application.'
