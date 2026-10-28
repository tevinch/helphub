# Put extras beside Igir game folders

Use Igir's `--dir-game-subdir always` to create a folder for each game, then copy extra files into that folder with an explicit Python manifest. Protect those extra directories when running Igir's `clean` command again.

This small example addresses the Python follow-up in [Igir discussion #2561](https://github.com/emmercm/igir/discussions/2561). The existing answer already explains the native game-folder flag. The addition here is explicit placement without guessing which platform owns a title, and a repeatable check of the cleaning exclusions.

## Layout and manifest

```text
roms/
  gb/
    Shared Title (USA)/
      Shared Title (USA).zip
      manual/
        My notes.txt
      patch/
        My patch.ips
```

For example, save this as `extras.json`, with the source files beside it in `extras/`:

```json
[
  {
    "source": "extras/My notes.txt",
    "platform": "gb",
    "game": "Shared Title (USA)",
    "kind": "manual"
  },
  {
    "source": "extras/My patch.ips",
    "platform": "gb",
    "game": "Shared Title (USA)",
    "kind": "patch"
  }
]
```

`platform` is the actual output folder, and `game` is the exact folder Igir produced from the DAT. The helper does not search by title; you choose the platform and exact game folder explicitly. Multiple entries may use the same kind directory. Allowed kinds are `dlc`, `hack`, `manual`, `mod`, `patch`, `update`, `demo`, `translation`, `prototype`, `walkthrough`, `soundtrack`, `cheat`, and `screenshot`, following [RomM's folder guide](https://docs.romm.app/5.4.0/getting-started/folder-structure/).

With Python 3.10 or newer, preview the complete manifest, then apply it:

```sh
python3 place_extras.py extras.json /absolute/path/to/roms
python3 place_extras.py extras.json /absolute/path/to/roms --apply
```

The default prints a JSON plan and changes no files or directories. Every game folder must already exist. Sources must stay inside the manifest's directory; destination paths must stay inside the specified output root. Internal symlinks are followed when resolving the printed plan; redirects outside that root are refused. Review the resolved source and target paths before applying. The helper checks the entire manifest before copying. It compares existing files in bounded chunks, skips identical bytes, refuses different existing files and duplicate targets, and creates new files exclusively. It does not delete files, apply patches, or scan a collection to infer matches. Keep the source and output folders unchanged by other processes during a run. Filesystem failures after copying starts can leave earlier successful copies in place; rerunning safely skips those identical files.

## Keep extras through another clean

Keep your current DATs, inputs, filters, preferences and `--overwrite-invalid`. Add `--dir-game-subdir always` and cleaning exclusions for the extra directories. This is an additive change to your existing command, not a replacement for your selection settings.

The following is a **Bash argument fragment** for the output setting and exclusion; append it to your existing `zip copy test clean` command. `ROMS` must be an absolute path to the platform-folder root:

```sh
ROMS="/absolute/path/to/roms"
# Append these options to your existing Igir command:
# --output "$ROMS/{romm}" --dir-game-subdir always \
# --clean-exclude "$ROMS/*/*/{cheat,demo,dlc,hack,manual,mod,patch,prototype,screenshot,soundtrack,translation,update,walkthrough}/**"
```

The quoted braces and wildcards are passed to Igir, which expands the glob. They protect files inside all listed kind directories at `platform/game/kind/`, including existing files omitted from the manifest. Other content needs its own exclusion. Use Igir's glob escaping if your root path itself contains glob metacharacters. Review an initial `--clean-dry-run -v` before enabling cleaning on an existing collection. A separate `--clean-backup /absolute/path/to/backup` moves cleaned **files** to that folder; it does not disable Igir's separate empty-directory recycling. See the [native cleaning rules](https://igir.io/output/cleaning/) and [game-folder option](https://igir.io/output/path-options/#append-the-game-name).

Igir's `--patch` applies patches to matching input files. If you only want to place raw patch files for RomM, copy them as `kind: "patch"`; remove `--patch` only when that was its intended purpose. This example does not apply patches or verify RomM's server/UI behavior.

## Run the text-only example

The dependency is pinned to **Igir 5.8.0**, a stable release. Use a supported Node.js version (`^22.22.2`, `^24.15.0`, or `>=26.0.0`); the checks used macOS, Node 24.22.1, and Python 3.12.4. Python uses only its standard library. From this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 -m unittest discover -p test_place_extras.py
python3 verify.py "checks with spaces"
```

The verification directory must not already exist. The runner generates its own DATs and short original text payloads. It downloads no game content and uses no ROMs, BIOS files, real patches, emulator, or RomM server. It invokes the installed native CLI and saves each command and its output beside the fixture.

The completed check covers:

- Three actual ZIPs containing four text files, including a two-file game and the same title on two platforms.
- Sixteen explicitly placed extras across all thirteen kinds, with a second file in one kind directory.
- Fifteen additional unlisted files preserved alongside the mapped extras through two repeated `zip copy test clean` cycles. Unprotected stale files actually move to the backup; every input and DAT keeps its original bytes.
- The retained `--no-demo` filter excludes a separate synthetic demo record. This fixture does not validate every possible 1G1R preference.
- Default planning, repeated identical placement, conflicts, missing game folders, duplicate mappings, path escapes and symlink escapes.
- Six controls that deliberately omit Python placement, native `clean`, the extras exclusions, native `zip`, native `copy`, or native `test`. Each omission must be detected. The no-exclusions control retains exact fixture anchor files so cleaning the extras does not empty those directories.

First creation requires native `testing zip` / `test passed` evidence for each ZIP and independent ZIP-entry byte checks. On repeated runs, Igir may select an existing output as its input and skip writer verification. The runner preserves that behavior, then calls the separate read-only native `test` command on the output archives and independently checks every ZIP entry again. The read-only command logs raw archive-file tests; it is distinct from first creation's ZIP-content test. Neither native source nor runtime is patched.

These are scripted filesystem checks, not RomM UI or human manual testing. Igir performs a registry version check even with local inputs; this is not an offline execution claim. The runner disables Igir's persistent cache and gives it a fixture-local temporary directory, which Igir removes at exit. The helper and fixture scripts are MIT licensed; Igir remains a separate [GPL-3.0 dependency](https://github.com/emmercm/igir/blob/v5.8.0/LICENSE).

## Optional coffee

The example is free. If it saves you some time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
