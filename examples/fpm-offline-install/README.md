# Install an existing fpm build in a separate packaging step

Use the same compiler, build directory, profile, features, and flags in both commands. In fpm 0.14.0, `install --no-rebuild` calculates the expected artifact paths from those settings and stages the files it finds there.

For a project built with `-fPIC`, the second command needs that flag too.

```sh
fpm build --flag '-fPIC'
fpm install --no-rebuild --flag '-fPIC' --prefix "$PWD/debian/tmp/usr"
```

Use the staging prefix required by your package. For example, a debhelper package can call the same commands with shared settings in `override_dh_auto_build` and `override_dh_auto_install`. If your build sets `FPM_FFLAGS` instead of using `--flag`, set the same value for both phases. Keep the project sources, manifests, and build tree available to the install phase.

## Run the example

Copy these files into a scratch directory. With fpm 0.14.0 and GNU Fortran installed, run the following from the directory containing `fpm.toml`. The project uses a local path dependency in `vendor/message`. The extra macro makes the selected build visible when the installed program runs.

```sh
(
    export FPM_BUILD_DIR=build-packaging
    flags='-fPIC -DPIC_VARIANT'

    fpm build --flag "$flags"

    fpm install --list --flag "$flags"
    fpm install --list

    fpm install --no-rebuild --flag "$flags" --prefix "$PWD/stage/usr"
    ./stage/usr/bin/offline-demo
)
```

The program prints `PIC: 42`. The two lists show different executable paths. Right after the PIC build, the path printed by the matching command exists. The default path is only a candidate until you build the default variant. Run `fpm build` inside the same subshell to build that variant too. Its executable prints `baseline: 42` and the matching install command still stages the PIC variant.

## Read the paths and diagnose an offline failure

- fpm 0.14.0 names the output directories with the compiler's basename and a hexadecimal hash of the arguments used for that target. A single build can use multiple hashes. `--build-dir` or `FPM_BUILD_DIR` sets the parent output directory. Use `fpm install --list` with the original settings to find the install candidate.
- If the listed file is missing or belongs to a different build, compare the compiler, profile, enabled features, and Fortran, C, C++, and linker flags between phases. Also check that both phases use the same project directory and build root.
- `--no-rebuild` skips the compilation step. fpm still reads the manifest, resolves dependencies, and computes the target model. In fpm 0.14.0, even `--list` runs that model step. For offline packaging, ensure dependency sources and any required cache are already available. This example uses a path dependency supplied with the project. The same approach can work for dependencies vendored according to the package's source and licensing rules.

For the implementation details, see [install and target selection in fpm 0.14.0](https://github.com/fortran-lang/fpm/blob/v0.14.0/src/fpm/cmd/install.f90#L39-L85), [model dependency resolution](https://github.com/fortran-lang/fpm/blob/v0.14.0/src/fpm.f90#L119-L134), and [the build directory hash](https://github.com/fortran-lang/fpm/blob/v0.14.0/src/fpm_targets.f90#L1436-L1445).

## Verification

On Debian 13 ARM64 with GNU Fortran 14.2.0 and the published fpm 0.14.0 release, the matching install copied the exact PIC executable without invoking the compiler or changing the compiled files. The staged program ran successfully with networking disabled. With the local dependency manifest temporarily absent, install failed even though the executable was still present.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
