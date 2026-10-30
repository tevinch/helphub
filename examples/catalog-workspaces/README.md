# Bun catalog updates with npm-check-updates

If the root `package.json` only has `workspaces` and `catalog`, plain `ncu` can print **No dependencies**. Catalog discovery runs in workspace mode:

```sh
ncu --workspaces       # preview catalog and workspace updates
ncu -u --workspaces    # apply the reviewed updates
bun install           # update installed packages and bun.lock
```

Use a current npm-check-updates release. This example pins **23.1.1** and uses its existing CLI; it adds no updater or library patch. `--workspaces` also scans member manifests, and the root is included by default. The default target includes major upgrades. Review the preview first; add `--target minor` to both ncu commands if you want to stay within each dependency’s current major version.

## Run the example

Requirements: Node.js satisfying `^22.22.2 || ^24.15.0 || >=26.0.0`, npm 10 or later, and Bun. The checks below used Node **24.21.0** and Bun **1.4.4**.

From this directory:

```sh
npm ci --ignore-scripts
cd workspace
bun install --ignore-scripts

# The root has no ordinary dependencies; this prints "No dependencies".
node ../node_modules/npm-check-updates/build/cli.js

# Preview, then apply using the same native workspace option.
node ../node_modules/npm-check-updates/build/cli.js --workspaces
node ../node_modules/npm-check-updates/build/cli.js -u --workspaces

bun install --ignore-scripts
bun run check
```

The root keeps the three member paths `apps/ui-shares`, `apps/web` and `apps/desktop`. The first two report the installed Svelte and TypeScript versions through their `catalog:` references. The third checks an existing content file. Run the preview again: there should be no further upgrades until a newer registry version appears.

`--ignore-scripts` avoids dependency lifecycle scripts in this demonstration. Real projects may require their own documented install/build steps after reviewing compatibility.

## Verify preservation and repeated use

From the example directory, with Bun on `PATH`:

```sh
npm test
```

The two command-level checks cover the supplied top-level catalog layout, plus Bun’s object-form `workspaces` with a named catalog. Each check runs plain ncu, a workspace preview, apply, real Bun installation, the root’s `bun run --filter '*' check`, and repeated preview/apply/use. It verifies that preview changes no bytes, apply matches the preview, unrelated settings and member content stay unchanged, and the installed member versions match the updated catalog.

These are scripted checks on the included fixture, not validation of your project. The commands query the public npm registry, so available versions change over time. The example does not establish compatibility between newly selected major versions; use your project’s own tests before accepting them.

## References

- [npm-check-updates workspace options](https://github.com/raineorshine/npm-check-updates#options)
- [Released 23.1.1 catalog discovery](https://github.com/raineorshine/npm-check-updates/blob/161014ec672069303ce6595a4b8663f1245c0db9/src/lib/getAllPackages.ts)
- [Bun workspaces](https://bun.com/docs/pm/workspaces)
- [Bun catalogs](https://bun.com/docs/pm/catalogs)

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
