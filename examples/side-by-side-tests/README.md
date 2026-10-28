# Run older .NET tests with a newer SDK in a Conda environment

A newer SDK can compile an older target framework, but running its tests still requires a compatible runtime. This example builds `net8.0` with SDK **10.0.403** and runs two real MSTest tests on **.NET 8.0.33**, while retaining runtime **10.0.14**.

The workaround is a separate Microsoft installation inside the activated Conda environment. **It is not managed by Conda** and does not enable two versions of the same Conda package. Keep it separate from Conda's own `lib/dotnet`; select its `dotnet` executable explicitly. Adding a runtime to a different installation root does not combine the roots.

## Checked versions and scope

Checked on macOS 14 / Apple Silicon, with Conda 23.1.0, SDK 10.0.403, runtimes 10.0.14 and 8.0.33, Microsoft.NET.Test.Sdk 18.11.0, and MSTest 4.5.2. The SDK and runtime versions come from Microsoft's [10.0 release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json) and [8.0 release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/8.0/releases.json). They were the stable versions checked on October 28, 2026.

The commands below are for macOS arm64 and Bash. Other operating systems and architectures need their matching Microsoft downloads and environment-variable spelling; they were not checked here. This is a small test project, not a change to the feedstock's package naming.

## Create a dedicated environment and install the new SDK

Download this directory, open a shell where `conda activate` already works, and run these commands from this directory. The empty environment keeps the demonstration independent of existing Conda packages. An existing environment can instead contain this separate sidecar root, provided that root does not already hold another installation.

```bash
conda create --prefix "$PWD/.conda-env" --yes --no-default-packages --offline
conda activate "$PWD/.conda-env"
sidecar="$CONDA_PREFIX/.sidecar-dotnet"
mkdir -p "$sidecar"

curl --fail --location \
  https://dotnetcli.azureedge.net/dotnet/Sdk/10.0.403/dotnet-sdk-10.0.403-osx-arm64.tar.gz \
  --output dotnet-sdk-10.0.403-osx-arm64.tar.gz

expected_sdk_hash=5893c66b48ea3674c7da18501059d606e96f3672fabe4d5e41762e692c7c83df3ee0b2b9dc5a0786191da2dc413d7335158101c14c935ab217f31ac2529770f3
actual_sdk_hash=$(shasum -a 512 dotnet-sdk-10.0.403-osx-arm64.tar.gz | awk '{print $1}')
test "$actual_sdk_hash" = "$expected_sdk_hash" &&
  tar -xzf dotnet-sdk-10.0.403-osx-arm64.tar.gz -C "$sidecar" &&
  rm dotnet-sdk-10.0.403-osx-arm64.tar.gz

"$sidecar/dotnet" --list-sdks
"$sidecar/dotnet" --list-runtimes
```

The archive checksum is the SHA512 value in Microsoft's versioned release metadata. Stop if the comparison fails. The initial runtime list should include `Microsoft.NETCore.App 10.0.14` and no `8.0.33`. Microsoft documents this [manual installation into a separate root](https://learn.microsoft.com/en-us/dotnet/core/install/macos#install-manually).

## Build first, then observe the missing runtime

This shell function only supplies environment variables to each explicit executable invocation. It does not change the shell's `PATH`, global .NET installation, or Conda-owned files. CLI state and downloaded NuGet packages stay in this example's directory.

```bash
run_dotnet() {
  env -u DOTNET_ROLL_FORWARD -u DOTNET_ROLL_FORWARD_TO_PRERELEASE \
    DOTNET_ROOT="$sidecar" DOTNET_ROOT_ARM64="$sidecar" \
    DOTNET_CLI_HOME="$PWD/.cli-state" NUGET_PACKAGES="$PWD/.nuget-packages" \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 \
    DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
    DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=0 \
    DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=true \
    "$sidecar/dotnet" "$@"
}

run_dotnet --version
run_dotnet restore tests/Sample.Tests/Sample.Tests.csproj \
  --configfile NuGet.Config --locked-mode
run_dotnet build tests/Sample.Tests/Sample.Tests.csproj --no-restore
run_dotnet test tests/Sample.Tests/Sample.Tests.csproj --no-build --no-restore
```

`--version` should report `10.0.403`, and the build should succeed. This first test command is expected to fail: its testhost requests `Microsoft.NETCore.App`, version `8.0.33`, and finds only 10.0.14. A successful build alone does not demonstrate that tests ran.

`global.json` pins the SDK. The test project pins its runtime and disables runtime roll-forward for this demonstration, so running the tests on .NET 10 cannot satisfy it. The real runtime test also asserts `Environment.Version.Major == 8`.

## Add the older runtime to that same root

Microsoft's installer supports keeping the newer non-versioned host files when adding an older runtime. The runtime-only option does not install an older SDK.

```bash
curl --fail --location https://dot.net/v1/dotnet-install.sh \
  --output dotnet-install.sh

bash dotnet-install.sh \
  --runtime dotnet --version 8.0.33 --architecture arm64 --os osx \
  --install-dir "$sidecar" --no-path --skip-non-versioned-files \
  --azure-feed https://dotnetcli.azureedge.net/dotnet \
  --keep-zip --zip-path dotnet-runtime-8.0.33-osx-arm64.tar.gz

expected_runtime_hash=0be37b64ea1f49651bbaa3dd08e89476919ceb98bd6b39d28883439c16c1d9cbcccf5cf01f67c913095e9f23235dc621125a551a6e736be4ebddbf060eb82758
actual_runtime_hash=$(shasum -a 512 dotnet-runtime-8.0.33-osx-arm64.tar.gz | awk '{print $1}')
test "$actual_runtime_hash" = "$expected_runtime_hash"
rm dotnet-runtime-8.0.33-osx-arm64.tar.gz

run_dotnet --version
run_dotnet --list-runtimes
run_dotnet test tests/Sample.Tests/Sample.Tests.csproj --no-build --no-restore \
  --logger 'trx;LogFileName=runtime.trx' --results-directory TestResults
```

The SDK should still be 10.0.403; the runtime list should now include both 8.0.33 and 10.0.14. The final command should execute **two tests, both passing**. Open `TestResults/runtime.trx` to see the test's captured output:

```text
Test process runtime: .NET 8.0.33
Environment.Version: 8.0.33
```

The other test exercises a small library that counts nonempty lines. This verifies an actual built library and test execution, rather than an empty test run. In the checked run, temporarily removing only the 8.0.33 runtime made the test command fail again; restoring it made both tests pass. Existing SDK/host files and Conda metadata remained unchanged.

## Apply the approach to your project

Use your project's target framework, supported runtime version, and test dependencies. Keep the newer SDK and the required runtime in the **same** sidecar root, invoke that root's host, and set the applicable `DOTNET_ROOT_<ARCH>` for child apphosts. Do not copy these files into a Conda-managed installation or rely on a different `dotnet` earlier in `PATH`. For ASP.NET Core tests, an appropriate `aspnetcore` runtime may also be needed; this example uses only `Microsoft.NETCore.App`.

Conda will not update this sidecar. Maintain its security updates separately and update the version pins and checksums together when changing this example. Microsoft's [version selection guide](https://learn.microsoft.com/en-us/dotnet/core/versions/selection), [environment variable reference](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-environment-variables#dotnet_root-dotnet_rootx86-dotnet_root_x86-dotnet_root_x64), and [installer options](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-install-script) explain the relevant behavior.

## Optional coffee

This example is free to use. If it helped and you would like to buy me a coffee, a small contribution is welcome, with no obligation:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
