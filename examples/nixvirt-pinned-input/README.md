# Choose nixpkgs for a legacy NixVirt import

NixVirt's upstream `default.nix` returns outputs using its own locked inputs. It does not accept a `pkgs` or `nixpkgs` override argument. To select another package source without a fork, put the input relationship in a small caller-owned flake, then expose that caller through `flake-compat`.

**Verified:** the [native bootstrap check](https://github.com/tevinch/helphub/actions/runs/44128760654) and [retained-lock check](https://github.com/tevinch/helphub/actions/runs/44130540251) passed with Nix 2.35.6 on Ubuntu 24.04 (`x86_64-linux`). Both real imports, generated XML, package derivation, repeated evaluation and the absent-`follows` control passed their acceptance checks. The retained lock's SHA256 stayed `574831a1e53c3257838661a55fe0aea473010a46ed8238bef520bb205c532845`. These were software-operated evaluation checks; no virtual machine was created or run, and adoption in the original application remains unverified.

## The caller files

Keep this directory's `flake.nix`, `default.nix` and included `flake.lock` together. Use the committed lock as provided; no lock generation is needed for these pins. The important relationship in `flake.nix` is:

```nix
inputs.NixVirt = {
  url = "github:AshleyYakeley/NixVirt/b9489f0e4b1cef1d5fe5dcc48f705c1cdfc9e7a8";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

The caller's `nixpkgs` input pins the NixOS 26.05 channel revision `b349185bb79c7cf7ad8ea8c097931730bf473c71`. `default.nix` reads the caller's lock and loads its graph with pinned upstream `flake-compat`. It does not rewrite NixVirt's files or lock.

NixVirt source commit `b9489f0…` is an **unreleased source revision**. The current FlakeHub/tag release, `0.6.0`, does not contain the upstream `default.nix` entrypoint discussed here. The source revision is pinned deliberately; this example does not track a moving `master` branch. Check compatibility with your own package choices before using a different pin.

Only regenerate the lock when intentionally changing a pinned input. Update the expected revisions in `verify.py` for that change, then run from this directory with a modern Nix installation:

```sh
nix --extra-experimental-features 'nix-command flakes' --option allow-import-from-derivation false flake lock path:.
```

Review the new lock, keep it under version control and rerun the checks below. Lock generation uses modern flake commands even though the consumer can use an ordinary `import`. No Nix 2.3 compatibility test has been performed here.

Then an ordinary expression can use the caller's outputs:

```nix
let
  caller = import ./default.nix;
in
caller.nixvirt.lib.volume.getXML {
  name = "fixture-volume";
  capacity = { count = 1; unit = "MiB"; };
}
```

This produces a volume XML description. It does not create a storage volume or start a virtual machine. The example is scoped to `x86_64-linux`, matching this NixVirt source's package outputs.

## Check the actual import

Requirements: Nix, Python 3 and network access to the public pinned sources. No Python packages are needed.

```sh
python3 -m unittest -v test_verifier.py
python3 verify.py
```

The second command evaluates `consumer.nix` with the real Nix evaluator. It checks:

- The original upstream import reports its locked 24.11 source, while the caller and NixVirt's transitive input both report the selected 26.05 source and exact revision. The package sets' actual `lib.version` strings are `24.11pre-git` and `26.05pre-git`; exact revision and source-path comparisons establish their identities.
- The selected and transitive input paths are identical. Printing only the caller's version would not establish this.
- NixVirt actually generates the requested XML, which Python parses and checks independently.
- NixVirt's `writeXML` derivation matches `writeTextFile` from the selected package set. XML generation alone does not depend on nixpkgs and cannot prove the input was selected.
- A second evaluation returns the same evidence without changing the lock.
- A separate caller with `follows` removed gets a fresh valid lock, evaluates successfully, and then fails the same dependency acceptance checks.

The verifier works in temporary directories and leaves this source directory unchanged. With the included lock it reports `lockMode: "committed"` and validates those bytes with updates disabled. If a lock is absent, it instead generates a temporary lock and prints it in the `generatedLock` JSON field with `lockMode: "bootstrap"`; that mode does not retain a lock in the source directory. Both modes passed for the files provided here.

Only source fetching, lock generation and evaluation are performed. Import-from-derivation is disabled; no derivation is built, no module is activated and no libvirt helper is run. The original 24.11 input is a comparison fixture, not a recommendation for a current installation.

## References

- [NixVirt's documented input relationship](https://github.com/AshleyYakeley/NixVirt/blob/b9489f0e4b1cef1d5fe5dcc48f705c1cdfc9e7a8/README.md)
- [The upstream compatibility entrypoint](https://github.com/AshleyYakeley/NixVirt/blob/b9489f0e4b1cef1d5fe5dcc48f705c1cdfc9e7a8/default.nix)
- [Pinned flake-compat usage](https://github.com/nix-community/flake-compat/blob/38fd3954cf65ce6faf3d0d45cd26059e059f07ea/README.md)
- [Nix input overrides and follows](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-flake.html#flake-inputs)

## Optional coffee

This example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
