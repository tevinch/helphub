#!/bin/sh
# Read-only checks for the disposable source-sync example.
set -eu
export LC_ALL=C
unset GIT_DIR GIT_COMMON_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY
unset GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT
unset GIT_CONFIG GIT_EXTERNAL_DIFF GIT_DIFF_OPTS
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ATTR_NOSYSTEM=1
test "$#" -eq 1 || { echo 'usage: sh verify-demo.sh DEMO_DIRECTORY' >&2; exit 2; }
root=$(cd "$1" && pwd)
test -d "$root/site/.git" || { echo 'FAIL: demo site is missing' >&2; exit 1; }
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
g() { git -c core.hooksPath=/dev/null -C "$root/site" "$@"; }
check_file() {
  cat > "$scratch/expected"
  cmp "$scratch/expected" "$root/site/$1" || { echo "FAIL: $1 content" >&2; exit 1; }
}

# Literal expected results, independent of the fixture's merge implementation.
check_file about.md <<'EOF'
# My research
Keep this personal page and its original URL.
EOF
check_file _config.yml <<'EOF'
title: My research
url: https://example.org
baseurl: /notes
enable_news: false
language: en
timezone: UTC
markdown: kramdown
highlighter: rouge
permalink: pretty
collections:
  projects:
    output: true
defaults:
  - scope:
      path: ""
    values:
      layout: page
feed_limit: 10
EOF
check_file _layouts/page.html <<'EOF'
<main class="personal-page" aria-label="Page content">{{ content }}</main>
EOF
check_file _includes/card.html <<'EOF'
<a href="{{ item.url | relative_url }}">{{ item.title | escape }}</a>
<p>{{ item.description | escape }}</p>
EOF
check_file .github/workflows/pages.yml <<'EOF'
name: Personal pages
on: workflow_dispatch
permissions:
  contents: read
jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Keep the site's reviewed build command"
EOF
check_file notes/source-updates.md <<'EOF'
First source update applied.
EOF

for name in P S G L BRIDGE U1 U2 U3 M1 M2 M3; do
  test -s "$root/evidence/$name" || { echo "FAIL: missing checkpoint $name" >&2; exit 1; }
done
P=$(cat "$root/evidence/P"); S=$(cat "$root/evidence/S")
G=$(cat "$root/evidence/G"); L=$(cat "$root/evidence/L")
BRIDGE=$(cat "$root/evidence/BRIDGE")
U1=$(cat "$root/evidence/U1"); U2=$(cat "$root/evidence/U2"); U3=$(cat "$root/evidence/U3")
M1=$(cat "$root/evidence/M1"); M2=$(cat "$root/evidence/M2"); M3=$(cat "$root/evidence/M3")
test "$(g rev-parse "$G^{tree}")" = "$(g rev-parse "$S^{tree}")"
test "$(g rev-parse "$L^{tree}")" != "$(g rev-parse "$S^{tree}")"
test "$(g rev-list --parents -n 1 "$G")" = "$G"
if g merge-base "$G" "$S" > /dev/null; then echo 'FAIL: template copy inherited history' >&2; exit 1; fi
test "$(g rev-parse 'upstream/main')" = "$U3"
test "$(g merge-base "$BRIDGE" "$U1")" = "$S"
test "$(g rev-parse "$BRIDGE^{tree}")" = "$(g rev-parse "$L^{tree}")"
test "$(g rev-list --parents -n 1 "$BRIDGE")" = "$BRIDGE $L $S"
test "$(g rev-list --parents -n 1 "$M1")" = "$M1 $BRIDGE $U1"
test "$(g rev-list --parents -n 1 "$M2")" = "$M2 $M1 $U2"
test "$(g rev-list --parents -n 1 "$M3")" = "$M3 $M2 $U3"
g show "$M1:_includes/card.html" > "$scratch/actual"
printf '%s\n' '<a href="{{ item.url | relative_url }}">{{ item.title | escape }}</a>' > "$scratch/expected"
cmp "$scratch/expected" "$scratch/actual"
g show "$M1:notes/source-updates.md" > "$scratch/actual"
printf '%s\n' 'First source update applied.' > "$scratch/expected"
cmp "$scratch/expected" "$scratch/actual"
g show "$M2:_layouts/page.html" > "$scratch/actual"
printf '%s\n' '<main class="personal-page" aria-label="Page content">{{ content }}</main>' > "$scratch/expected"
cmp "$scratch/expected" "$scratch/actual"
test "$(g merge-base "$M1" "$U2")" = "$U1"
test "$(g merge-base "$M2" "$U3")" = "$U2"
test "$(g rev-parse HEAD)" = "$M3"
test "$(g rev-list --count --first-parent "$L..$M3")" -eq 4
test "$(g rev-list --count "$S..$U3")" -eq 3
test -z "$(g tag --points-at "$S")"
test "$(g rev-parse v1.0)" = "$P"
test -z "$(g status --porcelain)"
test -z "$(g ls-files -u)"
if g rev-parse --verify MERGE_HEAD > /dev/null 2>&1; then echo 'FAIL: merge unfinished' >&2; exit 1; fi

# The deliberately conflicting merge must actually have happened.
test "$(cat "$root/evidence/conflict-status")" = '1'
test "$(cat "$root/evidence/abort-head")" = "$M1"
test "$(cat "$root/evidence/abort-tree")" = "$(g rev-parse "$M1^{tree}")"
test "$(cat "$root/evidence/repeat-head")" = "$M3"
test "$(cat "$root/evidence/repeat-tree")" = "$(g rev-parse "$M3^{tree}")"
printf '%s\n' '<main class="starter-page">{{ content }}</main>' > "$scratch/expected"
cmp "$scratch/expected" "$root/evidence/conflict-base.html"
printf '%s\n' '<main class="personal-page">{{ content }}</main>' > "$scratch/expected"
cmp "$scratch/expected" "$root/evidence/conflict-ours.html"
printf '%s\n' '<main class="starter-page" aria-label="Page content">{{ content }}</main>' > "$scratch/expected"
cmp "$scratch/expected" "$root/evidence/conflict-theirs.html"

# Joining the wrong, newer baseline falsely acknowledges a skipped source fix.
printf '%s\n' '<a href="{{ item.url }}">{{ item.title }}</a>' > "$scratch/expected"
cmp "$scratch/expected" "$root/wrong-baseline/_includes/card.html"
test ! -e "$root/wrong-baseline/notes/source-updates.md"
test "$(git -C "$root/wrong-baseline" merge-base HEAD "$U2")" = "$U2"
test "$(cat "$root/evidence/wrong-before")" = "$(cat "$root/evidence/wrong-after")"

test "$(g log --format='%an <%ae>|%cn <%ce>' | sort -u)" = 'Tevinch <tevin.chang@live.com>|Tevinch <tevin.chang@live.com>'
echo 'PASS: three completed source merges, explicit conflict resolution, exact custom files, ancestry, abort, repeat and wrong-baseline control'
