# CLI11 configuration from standard input

On a POSIX system with a readable `/dev/stdin`, CLI11 can read standard input through its normal configuration-file option:

```cpp
app.set_config("--config_file");
```

Then pass `--config_file /dev/stdin`. This keeps the ordinary priority: **command line > configuration > environment > defaults**. There is one normal parse.

The included example also accepts `--config_file -` with one public transformer:

```cpp
app.set_config("--config_file")
    ->transform(CLI::Transformer({{"-", "/dev/stdin"}}));
```

`Transformer` changes the exact `-` input and leaves other paths unchanged. A file literally named `-` remains accessible as `./-`.

## Build and try it

Use the official [CLI11 2.7.2 headers](https://github.com/CLIUtils/CLI11/tree/v2.7.2/include). For example, with a local checkout:

```sh
git clone --depth 1 --branch v2.7.2 https://github.com/CLIUtils/CLI11.git
c++ -std=c++11 -I CLI11/include example.cpp -o example
```

The following values are demonstration data. Pipe configuration into the literal path first:

```sh
printf 'value=40\nconfig_only=41\n' |
  env CLI11_CONFIG_EXAMPLE_VALUE=90 ./example --config_file /dev/stdin
```

Expected output:

```json
{"value":40,"config_only":41,"untouched":30}
```

The shorter spelling gives the same result:

```sh
printf 'value=40\nconfig_only=41\n' |
  env CLI11_CONFIG_EXAMPLE_VALUE=90 ./example --config_file -
```

Command-line values still win:

```sh
printf 'value=40\nconfig_only=41\n' |
  env CLI11_CONFIG_EXAMPLE_VALUE=90 ./example --config_file - --value 60
```

```json
{"value":60,"config_only":41,"untouched":30}
```

A named file uses the same parser and precedence:

```sh
printf 'value=40\nconfig_only=41\n' > settings.toml
env CLI11_CONFIG_EXAMPLE_VALUE=90 ./example --config_file settings.toml
```

If configuration omits `value`, its environment value is used. If both omit it, the initialized default is 10. The example rejects unknown configuration fields and validates `value` in the range 0–100.

## Why the parse order matters

Calling `parse_from_stream` after command-line parsing is complete lets environment values fill empty options first. A later stream parse then leaves those options alone, putting configuration below environment. Passing `/dev/stdin` through `set_config` reads the input at CLI11's normal configuration stage.

Keep the rest of your application's option definitions, validators and callbacks. Replace the separate filename option and post-parse stream read with the configuration option above. If the filename is needed after parsing, use `app.get_config_ptr()->as<std::string>()`; a transformed dash is reported as `/dev/stdin`.

## Scope and checks

This is a POSIX recipe using a filesystem path to standard input. It was compiled and run on macOS arm64 with AppleClang 15.0.0, C++11 and official CLI11 2.7.2. Linux was not run, and this example does not provide a Windows stdin path. It reads stdin once; do not consume the same input earlier in the application.

Run the bounded checks with Python 3 and the same headers:

```sh
python3 verify.py CLI11/include
```

The 16 checks run real subprocesses and cover defaults, environment fallback, named files, literal stdin, dash stdin, CLI overrides, fresh repeated input, an unchanged `./-` path, native validation/file errors, and help with stdin held open. Each successful invocation must print exactly one completed application record. A compiled variant with the dash transform removed must reject the same dash input.

## References

- [Configuration files and stream parsing](https://cliutils.github.io/CLI11/book-config.html)
- [Transforming validators](https://github.com/CLIUtils/CLI11/tree/v2.7.2#transforming-validators)
- [Stable parse and configuration implementation](https://github.com/CLIUtils/CLI11/blob/v2.7.2/include/CLI/impl/App_inl.hpp)
- [Original question](https://github.com/CLIUtils/CLI11/discussions/1442)

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`

