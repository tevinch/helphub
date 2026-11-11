# Compact diagnostic messages in Helix

Helix's older diagnostic display draws a box over the text at your cursor. In a small split, a long file-wide warning can cover the code you need to edit. You can temporarily switch that box to a compact end-of-line message, keep editing at the same position, and switch back afterward.

This uses existing settings in **Helix 25.07.1**. It changes presentation across buffers and views; diagnostics remain active. It is a two-way presentation toggle, with a second action to restore the display.

## Check your current display

Run these commands in Helix:

```text
:get end-of-line-diagnostics
:get inline-diagnostics.cursor-line
:get inline-diagnostics.other-lines
```

Continue with this recipe only when **all three return `"disable"`** and the diagnostic box is drawn over your text. These are the older renderer's settings. If any value differs, keep your existing settings: this toggle does not remember an arbitrary prior value, and it will not remove an already-enabled multiline inline display.

## Uncover the code, edit, and restore

Run:

```text
:set end-of-line-diagnostics hint
```

The large box is replaced by one truncated diagnostic line after the code. The cursor stays in place. Edit and save normally; diagnostics remain available in the diagnostic picker (`Space`, then `d`), with your configured gutter and highlighting settings preserved.

To restore the older display, run:

```text
:set end-of-line-diagnostics disable
```

These runtime changes do not rewrite your configuration file. Restoring the older display can make its box appear again at the same diagnostic. This does not dismiss one diagnostic until the cursor moves or restore the display automatically.

## Optional shortcut

For the checked starting settings above, the same command alternates between the two presentations:

```text
:toggle end-of-line-diagnostics disable hint
```

[keymap.toml](./keymap.toml) binds it to F8 in normal mode. Choose an unassigned key in your own setup. Merge the entry into your existing `[keys.normal]` table; do not add a second copy of that table or replace the rest of your config. Save and run `:config-reload`. **After reloading, rerun all three checks above before the first toggle:** the settings on disk may differ from the runtime values you checked earlier.

In normal mode, press the chosen key to uncover the code, then press it again to restore the older presentation. The shortcut persists; the presentation changes happen at runtime.

## Verification

Native scripted validation on Helix 25.07.1 / macOS arm64 used a local diagnostic fixture and a 120×40 terminal split into two views. The long warning initially covered the target text. The shortcut revealed it without moving the cursor; all three fixture diagnostics remained in the picker. Two successive edits were saved, each followed by restoring the older display. The source outside the edited character, configuration file, unrelated editor option and existing shortcut were preserved. The language server independently received the open, both changes and both saves. Omitting the toggle left the target covered.

This verifies the older-renderer workflow described here. The original requester's installed version, configuration and use of this recipe are unknown.

To repeat the fixture check on macOS or Linux with Python 3.11+ and an installed Helix, run from this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python verify.py --helix /path/to/hx
```

The check creates an isolated temporary home/project and retains terminal screens, file results and language-server events in the printed output directory. It uses the authored [fixture server](./fixture_lsp.py), with no external server or user configuration. For a downloaded Helix archive, keep its runtime beside `hx`, or add `--runtime /path/to/runtime`. `--output /new/directory` selects an evidence directory and refuses existing nonempty directories. Add `--omit-toggle` for the negative control: it must exit with a failed target-visibility check because the old box still covers the text.

References: [diagnostic display settings](https://docs.helix-editor.com/editor.html#editorinline-diagnostics-section), [runtime commands](https://docs.helix-editor.com/commands.html#typable-commands), [key remapping](https://docs.helix-editor.com/remapping.html), and [the 25.07.1 renderer switch](https://github.com/helix-editor/helix/blob/25.07.1/helix-term/src/ui/editor.rs#L211).

## Optional coffee

If this helped, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
