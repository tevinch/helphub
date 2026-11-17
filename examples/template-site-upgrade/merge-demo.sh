#!/bin/sh
# Offline synthetic Git histories. Never run this against an existing site.
set -eu
export LC_ALL=C
test "$#" -eq 1 || { echo 'usage: sh merge-demo.sh NEW_DIRECTORY' >&2; exit 2; }
if test -e "$1" || test -L "$1"; then
  echo 'Refusing an existing destination; choose a new directory.' >&2
  exit 2
fi
# These settings apply only to this process and the new disposable repositories.
unset GIT_DIR GIT_COMMON_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY
unset GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT
unset GIT_CONFIG GIT_EXTERNAL_DIFF GIT_DIFF_OPTS
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ATTR_NOSYSTEM=1
export GIT_TERMINAL_PROMPT=0 GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no
export GIT_AUTHOR_NAME=Tevinch GIT_AUTHOR_EMAIL=tevin.chang@live.com
export GIT_COMMITTER_NAME=Tevinch GIT_COMMITTER_EMAIL=tevin.chang@live.com
export GIT_AUTHOR_DATE=2026-11-18T00:00:00+00:00 GIT_COMMITTER_DATE=2026-11-18T00:00:00+00:00
umask 077
mkdir -p "$1"
root=$(cd "$1" && pwd)
mkdir "$root/evidence" "$root/empty-template"
upstream="$root/upstream"
site="$root/site"
wrong="$root/wrong-baseline"
g() {
  repo=$1
  shift
  git -c core.hooksPath=/dev/null -c core.autocrlf=false \
    -c commit.gpgSign=false -c tag.gpgSign=false -C "$repo" "$@"
}
init() {
  mkdir "$1"
  g "$1" init -q --template="$root/empty-template" -b main
  g "$1" config user.name Tevinch
  g "$1" config user.email tevin.chang@live.com
}
commit() { g "$1" add --all; g "$1" commit -qm "$2"; }
checkpoint() { g "$1" rev-parse HEAD > "$root/evidence/$2"; }
git --version > "$root/evidence/git-version.txt"

init "$upstream"
mkdir -p "$upstream/_includes" "$upstream/_layouts" "$upstream/.github/workflows"
cat > "$upstream/about.md" <<'EOF'
# Starter page
Replace this with your own content.
EOF
cat > "$upstream/_config.yml" <<'EOF'
title: Starter
url: https://example.com
baseurl: ""
enable_news: true
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
EOF
printf '%s\n' '<main class="starter-page">{{ content }}</main>' > "$upstream/_layouts/page.html"
printf '%s\n' '<a href="{{ item.url }}">{{ item.title }}</a>' > "$upstream/_includes/card.html"
printf '%s\n' 'name: Starter pages' 'on: workflow_dispatch' > "$upstream/.github/workflows/pages.yml"
commit "$upstream" 'Synthetic tagged starter'
checkpoint "$upstream" P
g "$upstream" tag v1.0
printf '%s\n' 'Copied from an untagged default-branch commit.' > "$upstream/source-note.txt"
commit "$upstream" 'Synthetic between-release starter change'
checkpoint "$upstream" S
S=$(cat "$root/evidence/S")

# "Use this template" copies files into an independent initial commit.
init "$site"
g "$upstream" archive "$S" | (cd "$site" && tar -xf -)
commit "$site" 'Create site from template files'
checkpoint "$site" G
cat > "$site/about.md" <<'EOF'
# My research
Keep this personal page and its original URL.
EOF
sed -e 's/title: Starter/title: My research/' \
    -e 's|https://example.com|https://example.org|' \
    -e 's|baseurl: ""|baseurl: /notes|' \
    -e 's/enable_news: true/enable_news: false/' \
    "$upstream/_config.yml" > "$site/_config.yml"
printf '%s\n' '<main class="personal-page">{{ content }}</main>' > "$site/_layouts/page.html"
cat > "$site/.github/workflows/pages.yml" <<'EOF'
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
commit "$site" 'Customize site content configuration layout and workflow'
checkpoint "$site" L
L=$(cat "$root/evidence/L")
g "$site" remote add upstream "$upstream"
g "$site" fetch -q upstream main
g "$site" fetch -q upstream tag v1.0
if g "$site" merge-base HEAD "$S" > "$root/evidence/before-merge-base.txt"; then
  echo 'Expected independent site and source histories.' >&2; exit 1
fi
if g "$site" merge --no-ff --no-commit "$S" > "$root/evidence/no-bridge.log" 2>&1; then
  echo 'Expected refusal before joining histories.' >&2; exit 1
else
  test "$?" -eq 128
fi
test "$(g "$site" rev-parse HEAD)" = "$L"
test -z "$(g "$site" status --porcelain)"

# S is known from the copy in this fixture; it is not guessed from a release.
g "$site" merge -s ours --allow-unrelated-histories --no-ff --no-commit "$S" \
  > "$root/evidence/bridge.log" 2>&1
g "$site" diff --cached --exit-code
g "$site" commit -qm "Record reviewed copied source $S without changing site files"
checkpoint "$site" BRIDGE

# First ordinary update: a source fix, a new setting, and a new file.
printf '%s\n' '<a href="{{ item.url | relative_url }}">{{ item.title | escape }}</a>' > "$upstream/_includes/card.html"
printf '%s\n' 'feed_limit: 10' >> "$upstream/_config.yml"
mkdir "$upstream/notes"
printf '%s\n' 'First source update applied.' > "$upstream/notes/source-updates.md"
commit "$upstream" 'Synthetic source fix and new setting'
checkpoint "$upstream" U1
U1=$(cat "$root/evidence/U1")
g "$site" fetch -q --no-tags upstream main
g "$site" merge --no-ff --no-commit "$U1" > "$root/evidence/update-1.log" 2>&1
g "$site" diff --cached --check
g "$site" diff --cached > "$root/evidence/update-1.diff"
g "$site" commit -qm "Merge reviewed source update $U1"
checkpoint "$site" M1

# Second update deliberately changes the same line as the local layout.
printf '%s\n' '<main class="starter-page" aria-label="Page content">{{ content }}</main>' > "$upstream/_layouts/page.html"
commit "$upstream" 'Synthetic source accessibility improvement'
checkpoint "$upstream" U2
U2=$(cat "$root/evidence/U2")
g "$site" fetch -q --no-tags upstream main
if g "$site" merge --no-ff --no-commit "$U2" > "$root/evidence/update-2-first.log" 2>&1; then
  echo 'Expected an explicit layout conflict.' >&2; exit 1
else
  conflict_status=$?
  printf '%s\n' "$conflict_status" > "$root/evidence/conflict-status"
  test "$conflict_status" -eq 1
fi
test "$(g "$site" rev-parse MERGE_HEAD)" = "$U2"
test -n "$(g "$site" ls-files -u)"
g "$site" show :1:_layouts/page.html > "$root/evidence/conflict-base.html"
g "$site" show :2:_layouts/page.html > "$root/evidence/conflict-ours.html"
g "$site" show :3:_layouts/page.html > "$root/evidence/conflict-theirs.html"
g "$site" merge --abort
g "$site" rev-parse HEAD > "$root/evidence/abort-head"
g "$site" rev-parse 'HEAD^{tree}' > "$root/evidence/abort-tree"
test -z "$(g "$site" status --porcelain)"
if g "$site" merge --no-ff --no-commit "$U2" > "$root/evidence/update-2-retry.log" 2>&1; then
  echo 'Expected the same conflict on retry.' >&2; exit 1
else
  test "$?" -eq 1
fi
# Explicit resolution: preserve the local class AND take the source attribute.
printf '%s\n' '<main class="personal-page" aria-label="Page content">{{ content }}</main>' > "$site/_layouts/page.html"
g "$site" add _layouts/page.html
test -z "$(g "$site" ls-files -u)"
g "$site" diff --cached --check
g "$site" diff --cached > "$root/evidence/update-2-resolved.diff"
g "$site" commit -qm "Merge $U2 keeping local layout class and adding the source attribute"
checkpoint "$site" M2

# A later normal merge uses the newly recorded source ancestry.
printf '%s\n' '<p>{{ item.description | escape }}</p>' >> "$upstream/_includes/card.html"
commit "$upstream" 'Synthetic later card improvement'
checkpoint "$upstream" U3
U3=$(cat "$root/evidence/U3")
g "$site" fetch -q --no-tags upstream main
g "$site" merge --no-ff --no-commit "$U3" > "$root/evidence/update-3.log" 2>&1
g "$site" diff --cached --check
g "$site" commit -qm "Merge reviewed later source update $U3"
checkpoint "$site" M3
g "$site" merge --no-ff --no-commit "$U3" > "$root/evidence/repeat.log" 2>&1
g "$site" rev-parse HEAD > "$root/evidence/repeat-head"
g "$site" rev-parse 'HEAD^{tree}' > "$root/evidence/repeat-tree"
g "$site" log --all --graph --oneline --decorate=short > "$root/evidence/history.txt"

# Negative control: guessing a newer baseline suppresses real source changes.
init "$wrong"
g "$site" archive "$L" | (cd "$wrong" && tar -xf -)
commit "$wrong" 'Independent control site with old source files'
g "$wrong" remote add upstream "$upstream"
g "$wrong" fetch -q --no-tags upstream main
g "$wrong" merge -q -s ours --allow-unrelated-histories "$U2" \
  -m 'Incorrectly acknowledge a newer source without reconciling its changes'
g "$wrong" rev-parse HEAD > "$root/evidence/wrong-before"
g "$wrong" merge --no-ff --no-commit "$U2" > "$root/evidence/wrong-repeat.log" 2>&1
g "$wrong" rev-parse HEAD > "$root/evidence/wrong-after"
echo "Created disposable histories in $root"
echo 'Run verify-demo.sh on that directory to check the completed workflow.'
