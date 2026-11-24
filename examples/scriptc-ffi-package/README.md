# Ship a scriptc FFI library in an npm package

Bundle the TypeScript declaration, FFI manifest, and target-specific static archive in the same npm package. The consumer imports the declared function by name and passes the installed manifest to `scriptc build --ffi`.

This example targets Linux ARM64 with glibc. Extract `scriptc-0.4.16-linux-arm64-gnu.tar.gz` and put its `bin` directory on `PATH`. You also need Node.js 24 with npm, `clang`, `ar`, and the target system headers and libraries used by the linker. [Scriptc 0.4.16 release](https://github.com/vercel-labs/scriptc/releases/tag/v0.4.16) · [Platform support](https://scriptc.dev/docs/platforms)

## Pack the library and build the consumer

Run these commands from this example directory.

```sh
cd package
clang -c native.c -o native.o
ar rcs libnative_math.a native.o
npm pack --ignore-scripts --offline --pack-destination ..

cd ../consumer
npm install --ignore-scripts --offline --no-audit --no-fund --no-package-lock ../example-native-math-0.0.0.tgz
manifest=$(node -p 'require.resolve("example-native-math/ffi.json")')
scriptc build main.ts --ffi "$manifest" -o demo
./demo
```

The executable prints the C function's results for `4` and `-1.5`.

```text
14
-2.5
```

## Adapt the package to your library

- Set `"scriptc": { "source": true }` to compile the installed TypeScript source. The `scriptc` export condition selects `index.ts`, which declares the function's signature. The consumer calls that declaration directly by the name in the manifest. [TypeScript packages and export conditions](https://scriptc.dev/docs/dependencies#packages-that-ship-typescript-source)
- Export `./ffi.json` so the consumer can resolve the manifest from the installed package. The linker resolves `./libnative_math.a` relative to that manifest. Keep both files in the package and pass the resolved manifest path on each executable build. The example uses `"private": true` so it can be packed and installed locally without publishing it. If you publish your own package to a registry, give it your own name and version and remove that setting. [FFI manifest fields](https://scriptc.dev/docs/ffi#manifest-fields)
- Build and package an archive for the consumer's target. The sample's npm metadata limits installation to Linux ARM64 glibc. For another target, update that metadata and build a matching archive. The archive is linked at build time. On a compatible target system, the executable runs outside the project directory without Node.js or `node_modules`. It still uses the target system libraries, including glibc in this example. [FFI boundary rules](https://scriptc.dev/docs/ffi#boundary-rules-and-current-limits)

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
