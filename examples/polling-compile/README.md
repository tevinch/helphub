# Polling compilation for Typst

If your filesystem does not deliver usable change events, run this small launcher instead of `typst watch`. It uses Notify's explicit `PollWatcher` with content comparison, then runs ordinary `typst compile` after a save. Changes to imported files and data assets also trigger compilation.

The launcher is an external command. The watcher selected inside an existing Typst executable stays the same.

## Run the example

Install [Rust](https://www.rust-lang.org/tools/install) 1.85 or newer and the [Typst CLI](https://github.com/typst/typst/releases). Start in this example's repository directory:

```sh
cargo build --locked
mkdir -p "example/output"
./target/debug/polling-compile \
  "example/source" \
  "main document.typ" \
  "example/output/main document.pdf"
```

Open the PDF, edit a sentence in `example/source/main document.typ`, and save. The PDF rebuilds. Repeat with `parts/chapter.typ` or `data.json`; their updated text appears in the PDF too. Your PDF viewer may need a refresh after the file changes.

Press **Ctrl+C** in the terminal to stop. There is no compilation timeout: a running compiler is allowed to finish. A source change received while it runs causes a follow-up compilation, without cancelling the current one. A Typst syntax error leaves the last successful PDF in place; fix the source and save to try again.

## Use your own document

The three arguments are:

1. The existing source directory to watch recursively.
2. The input file, relative to that source directory.
3. The output PDF, relative to the directory where you start the launcher, or an absolute path. Create its parent directory first.

Keep the output outside the source directory, preferably in a sibling directory. The launcher rejects output inside the watched tree and rejects output-file symlinks. This prevents compilation output from causing another rebuild.

Paths with spaces stay separate arguments; no shell is used to run Typst. To select a specific Typst executable:

```sh
TYPST="/path with spaces/typst" ./target/debug/polling-compile \
  "/path/to/document source" "main.typ" "/path/to/output/main.pdf"
```

The source root is also passed to Typst as `--root`. Keep the imports, images, local fonts and data whose changes should trigger rebuilds inside it. There is no extension filter: hidden files and non-`.typ` assets are included. Events under `.git` and `vendor` are ignored; `.gitignore` and `.ignore` are not read. Symlink targets and files outside the selected source root are not watched. Typst's package cache and system font directories are outside this watch scope.

Typst's environment is inherited. Local font files still need to be configured for Typst, for example with `TYPST_FONT_PATHS="/absolute/path/to/document source/fonts"`; putting them in the watched root does not register them as fonts by itself. If your usual compilation needs extra CLI flags, add them to the `Command` argument list in `compile` before building this source example.

Content comparison reads and hashes files every 200 ms, including files whose events are subsequently ignored. Choose a small document directory; keep large vendor trees and generated files outside it. Adjust the interval in `src/main.rs` if that I/O cost is too high. Polling detects the latest content seen during a scan; it does not promise to observe every transient intermediate write.

## Why compare contents?

Notify's [configuration](https://docs.rs/notify/8.2.1/notify/struct.Config.html#method.with_compare_contents) supports content hashing specifically for filesystems with unreliable metadata. This example constructs `PollWatcher` directly and sets `compare_contents(true)`. It can therefore detect a same-size edit even when the file's modification time is preserved.

The watch is registered before the initial compilation. Its callback sends events to a channel while the main thread runs the compiler serially. Pending changes are coalesced and compiled after the current run finishes. No custom file scanner or native-watcher override is involved.

## Checks and limits

The native checks used Notify **8.2.1**, Typst **0.15.1**, Rust **1.98.1** and macOS arm64. They inspected actual PDF text after repeated same-size edits with preserved modification times, atomic saves, an import, a hidden import and a JSON asset. They also checked edits during the initial and later busy Typst compilations, syntax-error recovery followed by another edit, and output changes that caused no rebuild. Disabling content comparison in an omission-control build left the old PDF after the preserved-time edit.

The original container/VM/9p setup has **not** been tested. The checks establish the explicit polling and compilation behavior on the platform above; the receiving filesystem still needs to make changed file contents visible to the process. Linux and Windows have not been run for this example.

To repeat the positive checks on a POSIX system, use Python 3 with [`pypdf`](https://pypi.org/project/pypdf/) installed, and a new results directory:

```sh
python3 -m pip install pypdf
python3 check.py \
  --poll-compile ./target/debug/polling-compile \
  --typst /path/to/typst \
  --evidence check-results
```

The checker creates disposable files, runs the real compiler, and saves logs and representative PDFs in the chosen results directory. Its waits are bounded; it stops its own process group on failure. The busy-compile check requires the provided computation to last long enough for an edit; it fails clearly if the machine finishes it first. `--control-compile` optionally accepts a separate build with `compare_contents(false)` for the omission control.

## Optional coffee

This example is free. If it saves you time, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
