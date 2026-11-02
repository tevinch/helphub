# Reject unmatched command-line arguments

Cxxopts **3.3.1** distinguishes unknown options from tokens without a positional mapping. This example accepts named options only. It checks `result.unmatched()` before printing help or formatting a labelled integer.

| Input | Native parser result | This example |
| --- | --- | --- |
| `--label tasks --number 7` | Recognised options | Prints `tasks: 7` |
| `--unknown` or `-z` | Exception by default | Diagnostic on stderr, exit 2 |
| `extra` | Unmatched positional token | Diagnostic on stderr, exit 2 |
| `-- --unknown` | Literal token after the separator, unmatched here | Diagnostic on stderr, exit 2 |

`--` ends option parsing; it does not require an application to accept the remaining tokens. This example deliberately has no positional arguments. `--help extra` also fails before help is printed.

## Build and run

Use a C++17 compiler, Python 3, `curl` and `shasum`. From this directory, download the pinned official header into a temporary build directory, verify its SHA-256 and compile:

```sh
set -eu
unmatched_build_dir="$(mktemp -d)"
mkdir "$unmatched_build_dir/include"
curl -fL 'https://raw.githubusercontent.com/jarro2783/cxxopts/v3.3.1/include/cxxopts.hpp' -o "$unmatched_build_dir/include/cxxopts.hpp"
printf '%s  %s\n' '80c35bb692f44a4cae5fc47f3a2dbe7138fa268f26340f5ab556d8fd07edbb6d' "$unmatched_build_dir/include/cxxopts.hpp" | shasum -a 256 -c -
c++ -std=c++17 -Wall -Wextra -pedantic -I "$unmatched_build_dir/include" main.cpp -o "$unmatched_build_dir/label-number"
python3 verify.py "$unmatched_build_dir/label-number"
"$unmatched_build_dir/label-number" --label tasks --number 7
```

The final command prints:

```text
tasks: 7
```

The default invocation prints `value: 0`. `-l` and `-n` are the short forms; `--help` or `-h` prints usage. Invalid integers, missing values, unknown options and unmatched tokens produce no formatted output.

## Apply the policy after parsing

The relevant part of [main.cpp](./main.cpp) is:

```cpp
const auto result = options.parse(argc, argv);

if (!result.unmatched().empty())
{
  // Report the unexpected tokens and return before help or application work.
  return 2;
}
```

Keep Cxxopts' default unknown-option rejection. Calling `options.allow_unrecognised_options()` explicitly permits unknown options and puts them in `unmatched()`; that permissive mode is unnecessary for this policy.

If your CLI intentionally accepts a positional input, register it before parsing instead:

```cpp
options.add_options()
  ("input", "Input file", cxxopts::value<std::string>());
options.parse_positional({"input"});
```

Mapped positional values are consumed into the declared option. Decide what any remaining unmatched tokens mean for your application. There is no separate strict-positional flag used here, and the example does not modify `argv` or the library.

## Verification and limits

`verify.py` runs six test groups against the binary you provide. They check exact completed formatting, defaults, short options, help, native parse errors, extra ordinary tokens and literal tokens after `--`. Rejected invocations must exit 2 with a diagnostic and empty stdout, including when help was requested.

Verified with Cxxopts 3.3.1 and C++17 on macOS 14.6 / Apple silicon, using Python 3.12.4. Other platforms and compilers have not been verified. These are native command-line checks; they do not establish that an unprovided application's arguments or configuration behave identically.

If a default-configured `--unknown` still parses successfully in your program, compare the exact argument list, installed Cxxopts version, registered options and any `allow_unrecognised_options()` call. This example is an application policy, not a library bug fix.

- [Official 3.3.1 unrecognised-arguments guidance](https://github.com/jarro2783/cxxopts/tree/v3.3.1#unrecognised-arguments)
- [Official positional-arguments guidance](https://github.com/jarro2783/cxxopts/tree/v3.3.1#positional-arguments)
- [Related usage question](https://github.com/jarro2783/cxxopts/issues/517)

## Optional coffee

This example is free. If it saves you time, buying me a coffee is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
