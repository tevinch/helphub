# Updating a site created from the al-folio template

Keep your site's files and review the starter changes between releases. Updating gems and reconciling starter files are separate jobs: `bundle update` cannot copy new configuration or workflows into your repository.

This guide uses released **v1.1 → v1.2**. It includes a disposable example that builds a customized site with the real released gems. It does not migrate an unseen site automatically.

## 1. Establish what you have

Make a backup and work on a branch in your own repository. Commit or otherwise save your existing changes first.

A GitHub template copy has independent history. “Generated from” identifies the template, but does not prove which release you copied. Your site's creation date and current gem versions cannot establish that either.

If you recorded the starter tag or commit, compare that source with your target release. If the original source is unknown, record it as **unknown**: review your current files against a chosen release, record which changes you accept or keep, and use that review as your future baseline. Do not infer that every upstream change is installed.

For a pre-v1 site, use the official [pre-v1 migration instructions](https://github.com/alshedivat/al-folio/blob/v1.2/docs/INSTALL.md#older-pre-v1-installs). That is a larger migration than this example.

## 2. Review the starter changes

Read the [v1.2 release notes](https://github.com/alshedivat/al-folio/releases/tag/v1.2) and [v1.1…v1.2 source comparison](https://github.com/alshedivat/al-folio/compare/v1.1...v1.2).

The reviewed documentation does not specify an automatic starter-source sync for template copies. Adding a remote alone does not supply the shared ancestry that a normal fork merge uses. This example reviews selected source changes explicitly.

Keep old and new release snapshots **outside your site's directory**. No upstream remote or unrelated-history merge is needed. For each relevant file, compare:

- old starter → new starter: what the release changed;
- old starter → your file: what your site changed.

The example saves both release snapshots. A native comparison is:

```sh
git diff --no-index -- releases/v1.1/_config.yml releases/v1.2/_config.yml
```

Exit status 1 means differences were found. Review the result, then edit your site's file. Do not replace its entire `_config.yml`, `Gemfile` or deployment workflow.

| File | What needs a decision |
| --- | --- |
| `Gemfile` | Update selected exact pins; preserve your own dependencies. |
| `_config.yml` | Add relevant new settings and plugin activation; preserve URL/baseurl, content settings and explicit disabled features. |
| `Gemfile.lock` | Let Bundler resolve your edited Gemfile. Do not copy another site's lockfile blindly. |
| `.github/workflows/` | Review relevant build changes against your runner, permissions and custom jobs. Upstream demo tests are not your site tests. |
| Content, data, bibliography, images | Keep your files. Upstream sample posts and screenshots are not required upgrade steps. |
| Local layouts/includes/Sass | Review against the installed owning gem; see step 4. |

## 3. Update gems deliberately

The v1.2 release uses exact pins. Plain `bundle update` honors the old pins, so a v1.1 site's core remains 1.0.12.

For these two v1.2 updates, edit your existing Gemfile:

```ruby
gem "al_folio_core", "= 1.0.15"
gem "al_cookie", "= 1.0.1"
```

The release also introduces three optional plugins. Decide which you want; a plugin requires **both** its Gemfile entry and its `plugins:` entry in `_config.yml`. The rehearsal opts into `al_rtl` 1.0.0 to verify that new source wiring executes. It leaves email protection and notebook integration disabled.

Then run:

```sh
bundle install
bundle exec ruby -e 'puts Gem.loaded_specs.fetch("al_folio_core").version'
bundle exec ruby -e 'puts Gem.loaded_specs.fetch("al_cookie").version'
```

For this release, expect **1.0.15** and **1.0.1**. A successful install alone does not establish those versions.

## 4. Audit and review local overrides

```sh
bundle exec al-folio upgrade audit
bundle exec al-folio upgrade overrides audit
bundle exec al-folio upgrade overrides diff _layouts/page.liquid
```

Use the path of an actual override in your site. The diff compares it with the installed gem's file; status 1 means it differs. Preserve your intended customization while incorporating relevant upstream changes. Then acknowledge that specific reviewed file:

```sh
bundle exec al-folio upgrade overrides accept _layouts/page.liquid
bundle exec al-folio upgrade overrides audit --fail-on-stale
bundle exec al-folio upgrade report
```

Commit `.al-folio-overrides.yml` with your reviewed changes. Do not use `accept --all` to silence findings without reviewing them.

The CLI's optional `upgrade apply --safe` performs specific codemods. It does not synchronize starter source, discover your original template release, change exact gem pins, or prove your site builds.

## 5. Build, preview and record the review

```sh
JEKYLL_ENV=production bundle exec jekyll build
bundle exec jekyll serve
```

Use your existing `baseurl` when opening the preview. Check home, custom routes, images, CSS, intentional layout changes and any features you use. Confirm disabled features remain disabled. Keep your current deployment workflow until you have reviewed and tested its changes.

Record the old source if known, the reviewed target tag/commit, accepted changes, local exceptions and deferred files in your repository. A starter tag and the installed gem versions describe different things. The rehearsal's `.starter-source.json` is one small example of such a record; it is not an al-folio CLI feature.

The documented support venue is [al-folio GitHub Discussions](https://github.com/alshedivat/al-folio/discussions). The reviewed documentation does not list an official Discord.

## Run the disposable example

Requires Python 3.10+, Git, Ruby 3.3 and Bundler, internet access to GitHub/RubyGems, and at least 2 GiB free disk space. Native gem compilation may need your platform's development tools.

```sh
python3 rehearse.py /tmp/template-upgrade-example
python3 verify.py /tmp/template-upgrade-example
```

Choose a **new directory**. The script refuses an existing destination, downloads five text files per release from pinned commits, and creates only a synthetic site. It runs native Bundler, upgrade CLI and Jekyll commands. It creates independent local Git history with no remote; it does not deploy, run GitHub Actions or touch your real site.

The example checks that plain `bundle update` leaves old pins; upgrades selected gems and starter settings; activates the new optional plugin; reviews a single intentional override; and builds the existing custom pages, data and image. It preserves URL/baseurl, explicit feature settings, bibliography and custom workflow bytes. Logs, source diffs, installed versions and preservation hashes remain in the output directory.

Preview it with `bundle exec jekyll serve` from the generated `site/`, using the same `BUNDLE_PATH` if set. Open `http://127.0.0.1:4000/notes/`, follow the guide link, and check `/notes/direction/`. The direction page uses `lang: ar` to exercise the released RTL plugin; the other pages keep the site's language.

This is a minimal synthetic upgrade rehearsal, not a build of every upstream demo feature or a validation of your own customized site. Workflow files are preserved and compared; GitHub Actions are not executed.

Source: [al-folio](https://github.com/alshedivat/al-folio) and its released plugin gems, MIT licensed. Downloaded source retains the upstream LICENSE in each release snapshot. The local page layout and fixture content in this example are separate customizations.

## Optional coffee

The guide and example are free. If they helped, an optional contribution is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
