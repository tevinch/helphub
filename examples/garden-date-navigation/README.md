# Sort selected garden folders by creation date

**Performance correction, November 19, 2026:** The previous template's record-preparation loop emitted a large whitespace-only text node. Compressing that output made complete Eleventy production builds much slower as folders grew. The corrected macro suppresses that unused whitespace; its sorting, links and HTML structure stay the same. Preserve every `{%-` and `-%}` marker when copying the macro.

The requester [reported a 30-minute Forestry.md build failure](https://github.com/oleeskild/obsidian-digital-garden/issues/855#issuecomment-6835701186) and later [reported that the default file tree builds in 3–6 minutes](https://github.com/oleeskild/obsidian-digital-garden/issues/855#issuecomment-6990852595). The local checks below reproduce a substantial inefficiency in the published recipe. The exact deployed template and Forestry account were not available, so this does not establish that the requester's full build has been restored.

Keep the normal file-tree order everywhere except the folders you choose. Inside those folders, notes appear newest first while their links, titles, icons and child objects remain intact.

This uses Nunjucks' built-in `groupby` and `sort` filters, plus Digital Garden's existing `dateToZulu` filter. It requires no new JavaScript filter, build hook or change to the managed site's core files.

## Use your existing custom navigation template

The reference is based on the navigation template shipped with [Digital Garden 1.96.0](https://github.com/oleeskild/digitalgarden/tree/1.96.0). If you already have a custom navigation plugin, keep its registration and make these changes only in its `.njk` file:

1. Add these declarations before its `menuItem` macro:

   ```njk
   {% set newestFirstFolders = ["Journal", "Projects/Log"] %}
   {% set navigationNotesByUrl = (collections.note or []) | groupby("url") %}
   ```

   Use the folder paths shown in the generated tree, with matching capitalization and no leading or trailing slash. A folder name is an exact match: `Journal` does not also select `Journal/Archive`.

2. Copy the `menuChildren` macro, including its whitespace-control hyphens, from [filetree.njk](filetree.njk) above your existing `menuItem` macro. Keep your own navigation markup and styles.

3. In `menuItem`'s folder branch, replace the loop that calls `menuItem` for each child with:

   ```njk
   {{ menuChildren(fileOrFolder, step+1, currentPath) }}
   ```

   These parameter names match the shipped template. If your custom template renamed them, use its equivalent folder object, depth and current folder path.

4. Rebuild and open a note. Check both a selected folder and an untouched folder, then follow a note link. Change one note's creation date and rebuild to check the new order.

The full [filetree.njk](filetree.njk) is also a complete reference navigation template. The accompanying [garden-plugin.json](garden-plugin.json) is an optional registration example for a new custom navigation plugin; an existing plugin only needs the template edits above. A new registration should claim the `navigation` region, declare `noteSettings: ["dgShowFileTree"]`, and replace the enabled `dg-filetree` provider using the site's normal plugin controls.

## Where the dates come from

The generated `filetree` objects do not contain creation dates. The template indexes the original `collections.note` entries by their URL, finds the matching `note.data.created`, and sorts records containing the actual `child` object:

```njk
{% set row = {name: name, child: child, created: created} %}
```

`sort(true, false, "created")` sorts those records by their normalized date. No child object is serialized or reconstructed. `safe` marks text as safe HTML; it does not parse JSON.

Dates are normalized to UTC before sorting, so different UTC offsets compare correctly. Pinned notes keep priority, then child folders keep their normal order, then unpinned notes are sorted. Equal dates preserve the existing relative order. Notes with missing or unparseable creation dates go last within their pinned or unpinned group. Hidden notes stay hidden, and a note's `dgShowFileTree: false` setting still uses the normal navbar.

The published notes need an actual `created` property, for example:

```yaml
created: "2026-11-05T09:30:00+08:00"
```

Use an explicit UTC offset or `Z`; offset-free date-times follow the build host’s timezone.

If it is absent, check the Digital Garden plugin's created-timestamp export setting and republish the affected notes. A configured custom timestamp key supplies that value; otherwise the plugin exports the vault file's creation time. This recipe does not substitute an Eleventy build or checkout date for the missing creation time.

## Verification

Checked against Digital Garden template **1.96.0**, Eleventy **3.1.2**, Nunjucks **3.2.4** and Node **22.23.5**. Digital Garden plugin **2.103.0** supplies the exported-date behavior. The correction changes only whitespace controls in the macro's data-preparation section; it adds no JavaScript filter, hook or host configuration change.

With Node 22 and a clean disposable checkout of template tag `1.96.0` with its locked dependencies installed, run:

```sh
node verify.cjs /absolute/path/to/digitalgarden
```

[verify.cjs](verify.cjs) copies that checkout into a temporary directory and removes the copy afterward. It runs complete Eleventy production builds on an **18-note** correctness fixture, including the native HTML transformations and compression. It checks selected and nested folders, an untouched similarly named folder, natural alphabetical order, UTC offsets, ties, missing dates, pins, hidden notes, note settings, existing navigation slots, icons, active links and every generated article. It edits a date, adds and deletes a note, and rebuilds after each operation. It also turns the global file-tree setting off and back on. The default alphabetical template, a missing date index and omitted custom registration must fail their respective checks. A development build must fail the independent inline-style compression check; the final production build must pass it.

The default run also compares the stock and corrected templates on the same **200-note** synthetic garden, with **160 notes in selected folders**. [verify-scale.cjs](verify-scale.cjs) allows up to ten minutes for the stock baseline, then requires the corrected build to finish within three times that measured duration, with a 15-second minimum allowance for startup variation. It verifies completed articles, navigation links, sorting, the disabled-note fallback and actual native production transformations. This is a local regression guard, not a Forestry build-time guarantee.

For a larger synthetic comparison:

```sh
node verify-scale.cjs /absolute/path/to/digitalgarden ./filetree.njk 1000
```

Additional local fixtures put a small Markdown table in each of **1,000 notes**, with no images. Each stock/corrected pair used identical content, settings and native production transformations:

| Selected notes | Stock template | Corrected template | Final navigation size, both templates |
| --- | ---: | ---: | ---: |
| 120 (12%) | 268.1 s | 238.6 s | 216,007 bytes |
| 800 (80%, stress case) | 175.2 s | 260.5 s | 215,992 bytes |

Both corrected builds completed all 1,000 articles and navigation checks. An earlier stress attempt reached its four-minute local cap before finishing; the completed rerun used a budget of three times the stock measurement. Machine load affects these timings, so they establish bounded completion on these fixtures rather than a universal speedup.

The bundled verifier and the 1,000-note measurements cover the complete Eleventy production stage; theme fetching and the separate site Sass command are outside their scope. A separate **200-note, 24-selected-note** fixture passed the complete `npm run build` command, a changed-date rebuild, CSS delivery and software-operated desktop/mobile navigation checks. That fixture used the native dark base with no external theme configured. These checks use synthetic content.

The requester [confirmed the sort worked in their Forestry build](https://github.com/oleeskild/obsidian-digital-garden/issues/855#issuecomment-7022932115). They reported 5 minutes 48 seconds for a build with the custom file tree, 4 minutes 35 seconds after editing frontmatter, and 2 minutes 14 seconds with the stock file tree. These are timings from their site; compare both templates on your own content if build time matters.

Navigation markup is adapted from [Ole Eskild Steensen's MIT-licensed template](https://github.com/oleeskild/digitalgarden/blob/1.96.0/src/plugins/dg-filetree/templates/filetree.njk). Its copyright notice is retained in [LICENSE](LICENSE).

## Optional coffee

If this saved you some time, you're welcome to buy me a coffee. It's entirely optional; the example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
