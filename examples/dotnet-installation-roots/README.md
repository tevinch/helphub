# Compare .NET installation roots

Compare package records, shell command locations and each host's SDK list to establish where .NET SDK versions are installed.

This guide uses [requester-reported output](https://github.com/dotnet/sdk/issues/56867#issuecomment-6540816236) from Ubuntu 26.04 and the [earlier package/environment inventory](https://github.com/dotnet/sdk/issues/56867#issuecomment-6540510916). The migration explanation comes from documentation and source for the reported `dotnetup` preview, `0.3.0-preview.1.26519.1+36b4e922df82e6d764fb847cb8ec2995f14700d0`.

## Inspect without changing installations

In Bash, inspect the package records and the host selected by your shell:

```sh
dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package} ${Version}\n' 'dotnet*' 'aspnetcore*'
type -a dotnet
dotnet --info
```

The [dpkg status columns](https://manpages.ubuntu.com/manpages/resolute/man1/dpkg-query.1.html#commands) distinguish installed packages (`ii`) from unknown/not-installed entries (`un`). An `un` entry without a version does not establish an installed SDK. [`type -a`](https://manpages.ubuntu.com/manpages/noble/man1/bash.1.html#shell-builtin-commands) lists matching command locations; repeated paths are not additional installations.

Compare the executable paths actually reported. These are the paths from this case; use your own reported paths if they differ:

```sh
realpath -e -- "$HOME/.local/share/dotnetup/dotnet/dotnet" /usr/bin/dotnet /bin/dotnet
"$HOME/.local/share/dotnetup/dotnet/dotnet" --list-sdks
/usr/bin/dotnet --list-sdks
```

[`realpath -e`](https://manpages.ubuntu.com/manpages/noble/man1/realpath.1.html) resolves existing paths to canonical locations. Calling each host explicitly avoids ambiguous shell selection. [`--list-sdks`](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet#options-for-displaying-environment-information-and-available-commands) lists SDKs for the invoked host's architecture.

## Interpret the reported result

The reported `/usr/bin/dotnet` and `/bin/dotnet` both resolve to `/usr/lib/dotnet/dotnet`. The user-local executable resolves to a different location. With the home directory shortened to `~`:

| Installation root | SDK versions listed by its host |
| --- | --- |
| `~/.local/share/dotnetup/dotnet` | 10.0.114, 10.0.403 |
| `/usr/lib/dotnet` | 10.0.114 |

SDK 10.0.114 therefore exists in two distinct roots. SDK 10.0.403 is listed in the user-local root, and the earlier `dotnet --info` selected that version. The earlier package output records `dotnet-sdk-10.0` version `10.0.114-0ubuntu1~26.04.1` as installed. Package status alone is not a per-file integrity or ownership check.

For this exact preview, the [installation-root documentation](https://github.com/dotnet/sdk/blob/36b4e922df82e6d764fb847cb8ec2995f14700d0/documentation/general/dotnetup/concepts/how-dotnetup-works.md#installation-roots) describes the user-local dotnetup root, and the [migration workflow](https://github.com/dotnet/sdk/blob/36b4e922df82e6d764fb847cb8ec2995f14700d0/src/Installer/dotnetup.Library/Commands/Shared/MigrationWorkflow.cs#L127) creates installation requests targeting the selected root. This supports explaining the separate inventories. The reported current state cannot reconstruct any earlier deletion or restoration of files.

The demonstrated evidence is the requester's command output plus inspection of the version-matched first-party sources. It is scoped to those reported paths and host architecture, rather than every possible installation on a machine. The commands above only inspect; choosing or removing an installation is a separate decision.

Free to use under the MIT license. See [LICENSE](../../LICENSE).

## Optional coffee

This guide is free to use. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
