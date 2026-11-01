# A Linux `no_std` entry point using libc

This small example builds a `#![no_std]`, `#![no_main]` executable with a custom `_start` on **x86_64 GNU/Linux**. It calls `libc::write`, prints one fixed line, and terminates through `libc::_exit`.

It addresses two separate failures from [this question](https://github.com/rust-lang/libc/discussions/5683): an unresolved `exit` symbol, and a host build script crashing after receiving `-nostartfiles`.

## Build and run

Use a native x86_64 GNU/Linux machine with glibc, a C linker, Rust 1.99.1, Python 3 and GNU binutils (`nm` and `readelf`). The dependency is pinned to libc 0.2.191. This is a consumer example; it does not patch libc.

From this directory:

```sh
rustup toolchain install 1.99.1 --profile minimal
env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS -u CARGO_BUILD_RUSTFLAGS \
  -u CARGO_BUILD_TARGET -u CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS \
  rustup run 1.99.1 cargo build --locked --release --target x86_64-unknown-linux-gnu
./target/x86_64-unknown-linux-gnu/release/linux-libc-entry
```

Expected stdout, followed by exit status 0:

```text
Hello from no_std and libc.
```

Existing `RUSTFLAGS` or `CARGO_ENCODED_RUSTFLAGS` override target flags in Cargo config; the command clears those settings for this invocation. Keep the explicit `--target`, even when it matches the host. It prevents target rustflags from also being used to compile host build scripts and procedural macros.

## The two relevant settings

```toml
# Cargo.toml
[dependencies]
libc = { version = "=0.2.191", default-features = false }
```

libc 0.2.191 is already a `no_std` crate. Its feature named `std` does not add a Rust `std` dependency; it tells libc that actual Rust `std` supplies the native library links. A `no_std` executable does not supply those links. Disabling the default feature enables this release's GNU/Linux native-library link declarations, including `c`, which resolves `libc::exit`, `write` and `_exit`. An explicit native C-library link is another option; the example does not need both.

```toml
# .cargo/config.toml
[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "link-arg=-nostartfiles"]
```

`-nostartfiles` omits CRT startup objects. It does not itself request `-lc`. GNU/Linux's dynamic target does not need `target-feature=-crt-static` here. These details are specific to this target and libc release; upcoming libc 1.0 is a separate API/version line.

`build.rs` is deliberately an ordinary Rust program using `std`. It writes a small witness into Cargo's build output. The checks require both this script and libc's own host build script to have executed successfully.

## Entry and panic checks

The kernel enters `_start` directly rather than calling it as a C function. A small naked assembly shim aligns the stack before calling the Rust body. That body never returns. This example does not read arguments or environment variables.

The program only writes a fixed, bounded message and exits. A short or failed write produces status 1. Skipping CRT initialization is not a recipe for arbitrary libc use: allocation, stdio, exit callbacks, constructors, threading and a complete C runtime are outside this example. For a normal application that needs those facilities, keep normal CRT startup and use a C-compatible `main`.

`panic = "abort"` selects the panic strategy; it does **not** prove that Rust cannot panic. Here the panic handler refers to the intentionally undefined symbol `rust_panic_is_reachable_in_this_build`. A retained panic path makes linking fail. Enable the deliberate probe to see the failure:

```sh
env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS -u CARGO_BUILD_RUSTFLAGS \
  -u CARGO_BUILD_TARGET -u CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS \
  rustup run 1.99.1 cargo build --locked --release \
  --target x86_64-unknown-linux-gnu --features panic-probe
```

This checks reachability in the resulting artifact. It is not a general proof about undefined behavior, foreign library internals, untested build settings or arbitrary application code.

## Complete checks

```sh
rustup run 1.99.1 python3 check.py
```

The checks use isolated temporary copies, including paths with spaces, and remove their build outputs afterward. They require:

- The original default-feature/no-native-link configuration to fail with an unresolved `exit`, while host build scripts still run.
- Global `RUSTFLAGS=-C link-arg=-nostartfiles` without `--target` to fail when a host build script starts. Core dumps are disabled for this negative control.
- Both debug and release executables to print the exact line three times in separate processes, with empty stderr and status 0.
- An ELF entry address matching `_start`, a native `libc.so.6` dependency, and imports of `write` and `_exit`.
- Output to `/dev/full` to return status 1.
- The deliberate reachable-panic probe to fail at link in both profiles.

These are scripted native-process checks. The script refuses macOS, non-x86_64 hosts and non-glibc Linux rather than reporting a pass for another platform.

References: [Cargo rustflags and host/target separation](https://doc.rust-lang.org/cargo/reference/config.html#buildrustflags), [libc 0.2.191 feature definitions](https://github.com/rust-lang/libc/blob/0.2.191/Cargo.toml), [its Unix native link declarations](https://github.com/rust-lang/libc/blob/0.2.191/src/unix/mod.rs), [Rust naked assembly](https://doc.rust-lang.org/reference/inline-assembly.html), [GNU libc termination details](https://sourceware.org/glibc/manual/latest/html_node/Termination-Internals.html).

## Optional coffee

This example is free to use. If it saved you time and you would like to buy me a coffee, a contribution is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
