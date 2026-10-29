# Call C++ functions from Sere

This small application connects two C++ functions to a Sere module through typed `extern "C"` declarations. It shows the complete source layout, native build setting and executable call for Sere 0.2.2 on Windows x64.

## Build and run

Download the official [Sere 0.2.2 Windows x64 portable ZIP](https://github.com/Sere-Language/sere/releases/tag/0.2.2) and extract the complete bundle. Keep its compiler, runtime and standard library together. The release bundles its native toolchain; this example does not require building the compiler or installing a separate C++ toolchain.

The published portable archive SHA256 is:

```text
f55ad803922380dc6b5db0cf6036d3bfc05be18bbbc7725257f29bf869320bbb
```

You can compare your downloaded ZIP with `Get-FileHash -Algorithm SHA256`. From this example's directory, open PowerShell, set the compiler path to your extracted bundle and run:

```powershell
$sere = (Resolve-Path 'C:\tools\Sere-0.2.2\bin\sere.exe').Path
& $sere --version
& $sere build
if ($LASTEXITCODE -ne 0) { throw 'Sere build failed' }
& .\bin\native_math_example.exe
if ($LASTEXITCODE -ne 0) { throw 'Native example failed' }
```

Adjust the example compiler path to the actual extracted location. Use a terminal without another Sere project environment activated. Expected program output:

```text
42
-5
42
```

## How the files connect

| File | Purpose |
| --- | --- |
| `libs/native/numbers.cpp` | Defines `example_add` and `example_twice` with C linkage and `int32_t` arguments/results. |
| `libs/native_math.sere` | Gives those exact native symbols Sere names, argument lists and `i32` results. The declarations have no body. |
| `src/main.sere` | Imports the module and calls both functions, including a negative input. |
| `sere.toml` | Sets the entry file and requests an eager native build with `[build] native = true`. |

For example, this declaration binds the Sere name `add` to the C symbol `example_add`:

```sere
extern "C" "example_add"
def add(left: i32, right: i32) -> i32
```

The C++ definition's name, argument order, widths and return type must match that declaration. `extern "C"` prevents C++ name mangling. The manifest's native setting requests compilation of the loose C++ source under `libs/native/` before the Sere application is compiled. Sere 0.2.2 also discovers and builds a `native/` directory beside an imported module, then links its artifacts. For this layout, importing `libs/native_math.sere` discovers `libs/native/` even with `native = false`; that flag is not an off switch for imported native code.

These functions demonstrate a primitive interface with fixed inputs whose arithmetic fits signed 32-bit integers. Strings, objects, ownership, callbacks and C++ exceptions crossing the boundary need a separate interface design. The boxed module registration API is not needed here. For distributing a `.slib`, follow the official library guide; packing and consuming a package are outside this application's check.

## Check the complete workflow

In PowerShell 7, from this directory:

```powershell
.\Verify.ps1 -CompilerPath $sere
```

The check uses the supplied 0.2.2 compiler in five independent temporary projects:

1. Remove the C++ source and require an actual missing-symbol build failure.
2. Remove both C-linkage declarations and require a missing-symbol build failure.
3. Build the complete application, run its produced executable, and require exactly `42`, `-5`, `42` with exit code zero.
4. Repeat the complete build and run in another fresh project.
5. Set `native = false`, then require the same actual program output and exit code, checking import-time native discovery.

Only the four source inputs are copied, so an earlier build's archives and executables cannot satisfy a check. Your original application stays untouched. The script temporarily clears the documented Sere project/stdlib environment overrides, gives each case its own process temporary directory, restores the previous environment values on exit, and removes only its own temporary files. Its final JSON lists the cases that actually completed; a failed build, wrong output or unexpected successful source/linkage omission stops the check.

This is a Windows x64 / Sere 0.2.2 verification target. Other compiler versions and platforms need their own native integration check.

References: [typed extern extensions](https://github.com/Sere-Language/sere/blob/0.2.2/docs/extending.md#8-add-a-native-extension-library), [native library layout](https://github.com/Sere-Language/sere/blob/0.2.2/docs/libraries.md#native-code), [manifest settings](https://github.com/Sere-Language/sere/blob/0.2.2/docs/sere-toml.md#native), and the official [native C++](https://github.com/Sere-Language/sere/blob/0.2.2/examples/native_add.cpp) / [Sere binding](https://github.com/Sere-Language/sere/blob/0.2.2/examples/native_add.sere) examples. Sere and its portable bundle retain their upstream license.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
