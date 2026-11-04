# Open a folder’s notes for comparison

This QuickAdd macro opens the Markdown notes in the **current note’s folder** in separate right-hand panes. It reads the folder each time, so adding or renaming notes requires no script edits. Your starting note keeps focus, existing panes remain open, and note contents are unchanged.

## Set it up

1. Save the complete [open-folder-comparison.js](./open-folder-comparison.js) file as `Scripts/open-folder-comparison.js` inside your vault. Create `Scripts` if needed. Use a plain text editor, keep the `.js` extension, and include the first `module.exports = async ...` line and the closing `};`. The file belongs in a normal vault folder, outside `.obsidian`.
2. In **Settings → QuickAdd**, choose **New choice → Macro** and name it **Folder comparison**.
3. In the macro editor, find **User scripts**, click **Browse**, and select `Scripts/open-folder-comparison.js`. A command named `open-folder-comparison` should appear under **Commands**.
4. Enable **Add to command palette**, then use the editor’s back arrow to save the macro and close settings. Leave **Run on startup** off.
5. Open a Markdown note in the folder you want to compare. Open Obsidian’s command palette and run **QuickAdd: Folder comparison**.

No npm installation is needed to use the script. You can also assign the saved command a hotkey in Obsidian’s settings.

## What it opens

- Immediate Markdown files only. Notes in subfolders and attachments are excluded. Notes directly in the vault root also work.
- English filename order with numbers compared numerically: `Draft 2.md` comes before `Draft 10.md`. This is independent of File Explorer’s selected sort setting.
- A **new right-hand pane for every matching note**, including an additional copy of the starting note. Existing panes are retained. Running it again adds another set; it does not reuse or close previous comparison panes.

The script returns focus to the starting pane after creating the splits. Pane widths shrink as more notes open; widen the window or drag the dividers as needed. Without an active Markdown note, it shows a notice and leaves the layout unchanged.

## Why the complete file matters

QuickAdd loads a user script through its exported function. `await` belongs inside that async function; pasting only the loop can produce the “await is only valid in async functions” error. The [User Scripts guide](https://github.com/chhoumann/quickadd/blob/2.33.1/docs/src/content/docs/docs/UserScripts.md) describes this entry point.

The script uses Obsidian’s public `createLeafBySplit` API for actual splits and `openFile` with `active: false`. Split creation itself activates its new pane, so the script explicitly restores the original pane with `setActiveLeaf` at the end. See the [public Workspace API](https://github.com/obsidianmd/obsidian-api/blob/master/obsidian.d.ts).

## Checked behavior

Checked in the macOS desktop app with Obsidian **1.15.0** and QuickAdd **2.33.1**, using a saved Macro choice with a User Script step. Checks covered six changing folder notes, adding and renaming files, another folder, root notes, repeated runs, and recovery after an empty active tab. Separate pane bounds, original editor focus and selection, an unrelated existing pane, and unchanged file contents were checked.

The small supplementary Node tests can be run with `npm test` from this directory. Mobile and other version combinations have not been checked.

## Optional coffee

The example is free. If it helps, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
