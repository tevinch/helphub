# Restore the project after dependency cooking

If a Rust executable exits successfully without running your application after adding `cargo-chef`, check what the builder copies after `cargo chef cook`.

`cook` creates dummy source files **and** prepared `Cargo.toml`/`Cargo.lock` files. In version 0.1.78, local package versions in those prepared files are set to `0.0.1`. Copying only `src` leaves that prepared metadata in place. If the copied source files are older than the cooked executable, Cargo can also consider the dummy executable fresh.

Restore the complete project before the final build, as in the [official Docker example](https://github.com/LukeMathWalker/cargo-chef/tree/v0.1.78#how-to-use):

```dockerfile
RUN cargo chef cook --release --recipe-path recipe.json
COPY . .
RUN cargo build --release --locked --bin sample
```

Use a `.dockerignore` that excludes `target` and `.git`. Keep the same Rust version and working directory for cooking and building. If you copy selected files instead, include the original manifests, lockfile, source files, build scripts, Cargo configuration and local dependencies that your project actually needs.

Touching only `src/main.rs` can force recompilation, but it still leaves the prepared manifest and lockfile behind. Restoring the real files also preserves package versions and other project metadata.

## Run the comparison

This directory contains a tiny binary that prints its package version, plus Docker targets for each comparison. It uses Rust `1.98.1`, cargo-chef `0.1.78` and Alpine `3.24`.

```sh
docker build --target restored -t source-copy-example .
docker run --rm source-copy-example
# application started (version 0.1.0)
```

Run the complete comparison with:

```sh
sh verify.sh
```

The script uses a temporary copy of this example. It checks the silent source-only case, the touch-only case with the prepared `0.0.1` version, the restored application and a second build after changing the application's message. The builder compares both restored files with the planner's originals. The repeated build must report a cached cooking layer and run the updated message. The script removes its temporary files and final test image tags afterward. Docker's reusable build cache remains.

A scripted native stage comparison on macOS, using Cargo `1.98.1` and cargo-chef `0.1.78`, reproduced the two negative cases and verified that the complete restore prints `0.1.0` with byte-identical original manifest and lockfile.

This demonstrates the build pattern on the included program. It doesn't establish the cause of a different service's failure without its build details.

Sources: [dummy project generation](https://github.com/LukeMathWalker/cargo-chef/blob/v0.1.78/src/skeleton/mod.rs), [local package version masking](https://github.com/LukeMathWalker/cargo-chef/blob/v0.1.78/src/skeleton/version_masking.rs).

## Optional coffee

This example is free. If it saved you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
