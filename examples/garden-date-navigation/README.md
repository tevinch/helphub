# Sort selected garden folders by creation date

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

2. Copy the `menuChildren` macro from [filetree.njk](filetree.njk) above your existing `menuItem` macro. Keep your own navigation markup and styles.

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

Checked against Digital Garden template **1.96.0**, Eleventy **3.1.2** and Nunjucks **3.2.4**, with the current Digital Garden plugin **2.103.0** used as the source for exported-date behavior.

To repeat the scripted check with Node 22, prepare a clean disposable checkout of template tag `1.96.0`, install its locked dependencies, and run:

```sh
node verify.cjs /absolute/path/to/digitalgarden
```

[verify.cjs](verify.cjs) makes its own temporary source copy, adds synthetic notes and removes that copy when finished. It builds the real template, checks selected and nested folders, untouched natural alphabetical order, UTC offsets, ties, missing dates, pins, hidden notes, per-note settings, existing navigation content, icons, active links and every generated article. It changes a date and rebuilds. The original alphabetical template and an omitted date index must both fail the chronology assertions.

The local template's existing 409 tests passed. A separate software-operated Chrome check followed three note links and used the mobile menu at widths 1280 and 390 pixels. Forestry.md account access and the requester's own garden were not tested; no adoption is claimed.

Navigation markup is adapted from [Ole Eskild Steensen's MIT-licensed template](https://github.com/oleeskild/digitalgarden/blob/1.96.0/src/plugins/dg-filetree/templates/filetree.njk). Its copyright notice is retained in [LICENSE](LICENSE).

## Optional coffee

If this saved you some time, you're welcome to buy me a coffee. It's entirely optional; the example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
