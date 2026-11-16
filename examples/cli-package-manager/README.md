# When shadcn init cannot find pnpm

`spawn pnpm ENOENT` at the dependency-installation step means that the CLI tried to execute `pnpm` and could not find it in its child process environment. Launching shadcn through `npx` does not force dependency installation to use npm: shadcn detects the project's package manager separately.

This addresses the error reported in [shadcn-ui/ui#12648](https://github.com/shadcn-ui/ui/issues/12648). That report does not include the project's package-manager declarations, lockfiles, Node version or intended manager. Choose the case that matches the project; what selected pnpm and whether the reporter can adopt the solution remain unconfirmed.

## Check the app's intended package manager

Run from the Laravel app root. Inspect `package.json` (`packageManager` and `devEngines.packageManager`), the app's lockfile, and workspace files or lockfiles in parent directories. Check the package manager and version expected by that project or workspace.

The [current CLI](https://ui.shadcn.com/docs/cli) has no `init --pm` option. A downgrade does not make a missing executable available. shadcn 4.23.0 requires Node 20.18.1 or newer; the reporter's Node version is unknown.

### The project uses pnpm

Make the project's compatible pnpm version available to the same invocation as shadcn. For example, these pinned commands use npm's documented [`exec --package` facility](https://docs.npmjs.com/cli/v12/commands/npm-exec/):

```sh
npm exec --yes --package=shadcn@4.23.0 --package=pnpm@12.21.0 -- shadcn init
npm exec --yes --package=shadcn@4.23.0 --package=pnpm@12.21.0 -- shadcn add switch
```

`12.21.0` is the pnpm version used in the example below. Use the version compatible with your own project, rather than changing its declared major version to match the example. These commands provide executables for that invocation without a global installation or shell-profile change.

If a failed init already wrote configuration or CSS, review those changes before retrying. The isolated fixture below uses `--force` because its official starter already has `components.json`; it is not a general instruction to overwrite an existing app's configuration.

### The project uses npm

Keep its npm lockfile and check whether contrary app or workspace metadata selected pnpm. Run init at the actual app root after resolving that mismatch according to the project's intended manager:

```sh
npm exec --yes --package=shadcn@4.23.0 -- shadcn init
npm exec --yes --package=shadcn@4.23.0 -- shadcn add switch
```

The independent npm fixture below uses the starter's existing `package-lock.json`. It initialized with npm even with a synthetic `pnpm-lock.yaml` one directory above it. That case does not reproduce the reported error, and adding a parent pnpm lockfile alone is not a reliable explanation for the report. Do not delete a workspace lockfile or silently migrate a pnpm project to npm.

## A separate pnpm 12 build-script condition

After providing pnpm, the isolated pnpm fixture reached a different error: `ERR_PNPM_IGNORED_BUILDS` for esbuild 0.25.12. That is a build-script decision, not an executable lookup failure.

For this fixture only, `pnpm-workspace.yaml` explicitly denies esbuild's postinstall script using the [documented build settings](https://pnpm.io/settings/build#allowbuilds):

```yaml
allowBuilds:
  esbuild: false
```

pnpm's default strict checks stay enabled. The platform package `@esbuild/darwin-arm64@0.25.12` supplied the binary used by the actual client and SSR builds. This denial is only appropriate when the installed platform package provides what the build needs; it is not a general fix for dependencies that require their install script. No build-script approval is part of this example.

## Reproduce the component check

The fixture is the official [Laravel React starter v1.0.1](https://github.com/laravel/react-starter-kit/tree/53720687617d62d0813775970439e22fc9518487), commit `53720687617d62d0813775970439e22fc9518487`. It preserves the starter's Vite configuration, Laravel plugin, Inertia client entry and SSR entry. This historical release is an explicit fixture choice, not a claim about the latest Laravel starter or the reporter's version.

Use a fresh local copy of that starter for each manager case. The pnpm copy declares `"packageManager": "pnpm@12.21.0"` and the denial above; the npm copy keeps its original npm lockfile. The pnpm declaration is synthetic fixture intent, not information supplied by the reporter.

In the pnpm copy, initialize and add the component:

```sh
npm exec --yes --package=shadcn@4.23.0 --package=pnpm@12.21.0 -- shadcn init --defaults --template laravel --base radix --yes --force --no-reinstall --no-monorepo
npm exec --yes --package=shadcn@4.23.0 --package=pnpm@12.21.0 -- shadcn add switch --yes
```

For the npm copy, use the same flags while omitting `--package=pnpm@12.21.0`. The forced fixture initialization updates existing configuration, CSS and the starter's Button component. Existing application pages are retained.

Copy [ComponentCheck.tsx](./ComponentCheck.tsx) into the app as `resources/js/pages/component-check.tsx`. It imports the real generated Switch, displays its state, supports reset, and retains a separate text draft while the switch is used. Then run the starter's own build:

```sh
npm run build:ssr
```

That script builds both the client and SSR assets. [make-check-page.mjs](./make-check-page.mjs) creates a static Inertia page envelope that loads the actual built client entry and its CSS:

```sh
node /path/to/cli-package-manager/make-check-page.mjs /path/to/laravel-app
python3 -m http.server 4173 --bind 127.0.0.1 --directory /path/to/laravel-app/public
```

Open `http://127.0.0.1:4173/component-check.html`. This is an isolated client check, not a served PHP/Laravel application. Authentication, backend routes, database work and SSR request handling are outside its scope.

For software-operated browser checks, install this directory's development dependency with `npm install`, then use an installed Google Chrome:

```sh
npm run check -- http://127.0.0.1:4173/component-check.html
```

The check requires the real Switch to render, toggle by pointer and Space, reset, and remain usable while the text draft is preserved. It fails on page errors. Re-run `shadcn add switch --yes`, rebuild the starter and repeat the browser check to verify the next normal operation.

## Validation scope

Native CLI commands and software-operated browser checks passed with shadcn 4.23.0, npm 10.7.0, pnpm 12.21.0 and Chrome 157.0.8103.52:

| Fixture | Init | Add and repeat add | Client and SSR asset builds | Switch browser interaction |
| --- | --- | --- | --- | --- |
| Declared pnpm project, pnpm absent | `spawn pnpm ENOENT` at dependency installation | Not reached | Not reached | Not reached |
| Same project, scoped pnpm plus the explicit script denial above | Passed | Passed; repeated add retains the component | Passed before and after repeated add | Passed after repeated add and rebuild |
| Independent npm project with its original npm lockfile | Passed with pnpm absent | Passed; repeated add retains the component | Passed before and after repeated add | Passed after repeated add and rebuild |

All 11 original starter pages remained byte-identical; the original Vite configuration and client/SSR entry files were retained. The test machine runs macOS 14.6 with Node 24.19.0; macOS 12.7.6 Monterey and the original user's project have not been tested. These are native CLI and software-operated client-browser checks, not human manual validation or a PHP/Laravel server test.

## Optional coffee

This guide and example are free. If they save you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
