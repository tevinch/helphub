# Put Fastfetch memory and swap on one row

Use Fastfetch's native `Command` module to join the output of its Memory and Swap modules. The rest of the outer display, including its logo and following modules, keeps its normal layout.

This recipe uses a POSIX shell and `paste`. It was checked with Fastfetch **2.71.0 on macOS arm64**. The original question did not specify an operating system; this is not a Windows shell recipe, and Linux has not been tested here.

Download [config.jsonc](config.jsonc) into an empty directory and run:

```sh
/bin/sh -c 'command -v fastfetch && command -v paste'
fastfetch -c ./config.jsonc
```

The first command checks that both programs are available to the noninteractive shell used by Command. A shell alias for `fastfetch` is insufficient; use an installed executable in `PATH`, or replace `fastfetch` inside `text` with its quoted absolute path.

Illustrative output; the values depend on your system:

```text
Memory: 4.00 GiB / 8.00 GiB (50%) Swap: 1.00 GiB / 4.00 GiB (25%)
Next: The next module stays on its own row
```

## Add it to an existing configuration

Replace the separate `memory` and `swap` entries in your existing `modules` array with this one entry. Keep your other entries and logo configuration:

```jsonc
{
  "type": "command",
  "key": " ",
  "text": "fastfetch -c none --logo none --pipe true -s Memory:Swap | paste -s -d ' ' -",
  "useOutput": "stdout",
  "splitLines": false
}
```

The `Next` entry in the downloadable example just demonstrates the following row; replace it with your next normal module. The example's `"logo": null` disables its logo for a small standalone demonstration. You do not need to add that setting to your own configuration.

The child Fastfetch invocation selects only Memory and Swap. `-c none` prevents it from loading your default configuration again, which would otherwise risk recursion after you adopt this entry as your default. `--logo none` suppresses the child's logo, and `--pipe true` gives plain text. `paste` joins those two lines with a space. A one-space `key` hides the outer Command label, and `splitLines: false` keeps its output together.

This starts one extra Fastfetch process and one `paste` process each time the outer display runs.

The [official README](https://github.com/fastfetch-cli/fastfetch/blob/2.71.0/README.md#q-i-want-feature-a--b--c-will-fastfetch-support-it) recommends Command for custom functionality and [documents hiding a key with a space](https://github.com/fastfetch-cli/fastfetch/blob/2.71.0/README.md#q-how-do-i-hide-a-key). Command's fields are in the [2.71.0 schema](https://github.com/fastfetch-cli/fastfetch/blob/2.71.0/doc/json_schema.json).

## Formatting and available width

The child uses its own default Memory/Swap formatting and units. Custom keys, formats, units and colors from your outer configuration are not inherited. For custom keys, formats or units, put just the two modules and their display settings in a separate child configuration and replace `-c none` with its quoted absolute path. Keep that child file free of this Command entry and set its logo to `null`. The retained `--pipe true` still makes the child's output plain text.

This combines the two summary modules only. The row needs enough terminal width beside your logo; a wider logo or larger values can require more columns. It saves one information row, but cannot establish that an entire unseen configuration fits on one screen.

## Verification

Scripted native checks used the official 2.71.0 macOS universal release, verified against its published SHA-256. In an 80-column, 24-row PTY, the supplied configuration was run twice without a logo and twice with a two-character-wide, two-line text logo. Each run displayed Memory and Swap on one row, with the following module on the next row. Captured pipe output and loading the example as an isolated default configuration were also checked.

An external process trace verified one successful child invocation with the exact `-c none --logo none --pipe true -s Memory:Swap` arguments per run. Ordinary separate Memory/Swap entries failed the one-row check, and hardcoded output without a child invocation failed the execution check. These are software-operated checks of this example, not confirmation from the original requester.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The guide and configuration are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
