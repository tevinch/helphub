# Bringing routine upstream commits into a template-based site

You can use ordinary Git merges for periodic starter-source updates, including commits between releases. First establish a shared ancestor with the **source commit whose files your site copied**, then merge newer source commits normally. That source commit can be an untagged default-branch commit.

This is a native Git workflow for your own site repository. It is separate from al-folio's dependency/override upgrade commands. Git merges combine file changes; you still review the result, resolve conflicts and build your site.

## Establish the source baseline once

Save your work and make a backup. Start with a clean worktree in your **site repository**, on a review branch:

~~~sh
git status --short
git switch -c source-sync-baseline
git remote -v
~~~

If an `upstream` remote does not already exist:

~~~sh
git remote add upstream https://github.com/alshedivat/al-folio.git
~~~

If it exists, verify its URL with `git remote get-url upstream`. Then fetch the source history and confirm the upstream default branch:

~~~sh
git fetch upstream
git remote show upstream
~~~

The commands below use `upstream/main`. Substitute the observed default branch if it differs.

Let `SOURCE_COPY` be the **verified source commit**, not the nearest release tag or today's `upstream/main`. Replace the placeholder before running:

~~~sh
SOURCE_COPY=REPLACE_WITH_VERIFIED_COPIED_COMMIT
SOURCE_COPY=$(git rev-parse --verify "$SOURCE_COPY^{commit}")
TARGET=$(git rev-parse --verify 'upstream/main^{commit}')
git merge-base --is-ancestor "$SOURCE_COPY" "$TARGET"
git diff "$SOURCE_COPY" HEAD --
~~~

Review that last comparison as your site-specific changes. The ancestry check must succeed; stop if the source history no longer contains the expected baseline.

For a site with independent template history, create a one-time merge whose tree stays exactly as it is:

~~~sh
BEFORE_TREE=$(git rev-parse 'HEAD^{tree}')
git merge --no-ff --no-commit -s ours --allow-unrelated-histories "$SOURCE_COPY"
git diff --cached --exit-code
git diff --exit-code
git write-tree
~~~

The two diffs should be empty, and `git write-tree` should print `BEFORE_TREE`'s value (`printf '%s\n' "$BEFORE_TREE"`). If they do not, stop and inspect or run `git merge --abort`. Once verified:

~~~sh
git commit -m "Record reviewed starter source $SOURCE_COPY"
git merge-base HEAD "$TARGET"
~~~

The merge base should now be `SOURCE_COPY`. The commit records that source ancestry while retaining all existing site files. It does **not** install any newer upstream changes. Git documents the distinction between the [`ours` strategy and `-X ours`](https://git-scm.com/docs/git-merge#_merge_strategies); they are different operations.

Use this history join only once for the reviewed baseline. Using `-s ours` for a later update would declare its commits merged while discarding their file changes.

## Merge each newer source revision normally

Work on a review branch from your current site, with a clean worktree. Fetch and pin the target so the review and merge use the same commit:

~~~sh
git fetch upstream
TARGET=$(git rev-parse --verify 'upstream/main^{commit}')
BASE=$(git merge-base HEAD "$TARGET")
git log --oneline "HEAD..$TARGET"
git diff "$BASE" "$TARGET" --
git diff "$BASE" HEAD --
git merge --no-ff --no-commit "$TARGET"
~~~

The comparisons show upstream changes and your site's changes since their common ancestor. After the one-time join, do not add `--allow-unrelated-histories` or `-s ours` to routine merges. If history unexpectedly diverges or upstream was rewritten, stop and investigate rather than inventing another baseline.

An ordinary merge applies compatible changes automatically. A clean merge can still change or delete files, introduce sample content or alter settings, so review the **whole staged diff**, including workflows and files without conflicts:

~~~sh
git diff --cached HEAD --
git status --short
~~~

If there are conflicts, Git stops with a nonzero status. List them, then inspect each file's common base, your version and the incoming version:

~~~sh
git diff --name-only --diff-filter=U
git show :1:_config.yml
git show :2:_config.yml
git show :3:_config.yml
~~~

The `_config.yml` commands apply if that file conflicted; use the actual conflicted path. For an add/add conflict there may be no base stage. Edit the combined result deliberately: retain your URL/baseurl, content, explicit feature settings and intended layout/workflow customizations while incorporating the relevant upstream changes. Avoid accepting an entire side merely to remove markers.

Stage only reviewed resolutions, then check the final result:

~~~sh
git add _config.yml
git diff --name-only --diff-filter=U
git diff --cached --check
git diff --cached HEAD --
~~~

Use your actual resolved paths with `git add`; the unresolved-path list must be empty. If you want to stop before committing, `git merge --abort` returns to the pre-merge state when the worktree was clean at the start. [`--no-ff --no-commit`](https://git-scm.com/docs/git-merge#Documentation/git-merge.txt---no-commit) provides a review stop even when a fast-forward would otherwise be possible.

If the reviewed merge changes dependencies, resolve them deliberately with Bundler as described in the [release-upgrade guide](README.md). Then build and preview the customized site, check its existing routes/content and enabled/disabled features, and review any workflow changes. Keep build-generated or lockfile changes under review too. Commit the completed source merge after those checks:

~~~sh
JEKYLL_ENV=production bundle exec jekyll build
git status --short
git commit -m "Merge reviewed starter source $TARGET"
~~~

Use your usual preview command and deployment review before publishing. The next update repeats this section. The new common ancestor will reflect the last merged upstream revision, and Git will combine subsequent changes from there.

## If the copied commit is unknown

[GitHub template generation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) creates independent history. The template's default branch can contain commits between releases; a gem version, creation date or nearby tag does not establish the copied source.

An untouched initial template commit can help: after fetching source history, compare its tree with candidate upstream commits:

~~~sh
git log --reverse --first-parent --oneline
git diff --exit-code INITIAL_TEMPLATE_COMMIT CANDIDATE_SOURCE_COMMIT --
~~~

Substitute the actual commits. An empty diff establishes identical tracked trees. Check that the initial snapshot is complete and unedited; multiple upstream commits can also have the same tree, so an exact copy date/commit may remain ambiguous. Comparing only your currently customized tree does not recover lost provenance.

If you cannot establish a trustworthy copied baseline, do **not** substitute the latest source into the ours merge. First reconcile your current site against a chosen source revision file by file, including intentionally retained and deferred changes. Record that revision as an intentionally reviewed baseline only after that reconciliation. That initial review cannot safely be skipped. Future updates can then use ordinary merges from the recorded baseline.

`git log HEAD..upstream/main` lists commits not in the site's ancestry. It does not prove every upstream file or feature is installed: local overrides and explicit merge decisions can retain different contents. Keep meaningful exceptions in the review record.

## Run the offline example

Requires Git 2.28+ and a POSIX shell with standard `tar`, `sed`, `cmp` and `mktemp`. From this directory, choose a new destination:

~~~sh
sh merge-demo.sh /tmp/source-sync-example
sh verify-demo.sh /tmp/source-sync-example
~~~

The script refuses an existing destination. It creates synthetic upstream and site repositories with no network access, and does not edit your site or global Git configuration. It demonstrates an untagged baseline, an unchanged-tree history join, three completed native source merges, explicit conflict resolution, abort/retry, and a repeated no-op merge. Verification checks actual final contents and ancestry, including preservation of custom content, URL/baseurl, a disabled feature, layout choices and workflow bytes.

A separate deliberately incorrect-baseline control shows how a later ours merge can falsely acknowledge missing changes. Its stale files are expected; it is not the workflow to adopt.

This is a scripted Git demonstration on text fixtures. It does not build al-folio, execute GitHub Actions or validate the requester's unavailable site. The existing release rehearsal covers its separately stated Bundler/Jekyll checks.
