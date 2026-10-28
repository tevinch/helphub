# A TypeScript story with Sharpee

Sharpee's author CLI can scaffold a TypeScript project. Use `--ts`; plain `init` creates a Chord `.story` project instead.

This example uses Sharpee **5.5.0**, TypeScript **5.9.3**, and Node.js **22+**. It has two connected rooms and a brass key you can take and drop. The story is written entirely in [`src/index.ts`](src/index.ts).

## Run this example

From this directory:

```sh
npm ci --ignore-scripts
npm exec -- sharpee build
npm exec -- sharpee play
```

Try these commands at the game's prompt:

```text
look
take brass key
inventory
north
look
south
drop brass key
inventory
look
/quit
```

You start in the Study. Taking the key puts it in your inventory; after dropping it, `inventory` is empty and `look` shows it in the room again. North leads to the Hall and south returns to the Study.

## Scaffold your own project

No global installation or Sharpee repository clone is required:

```sh
npm exec --yes --ignore-scripts --package=@sharpee/devkit@5.5.0 -- sharpee init quiet-study --ts
cd quiet-study
```

Answer the title, package name, author and description prompts. Use a new or empty target directory. The TypeScript scaffold creates `src/index.ts`, `package.json` and `tsconfig.json`; it does not create a `.story` source file.

There are two version-specific details before playing a 5.5.0 TypeScript starter:

1. Use `"type": "commonjs"` in `package.json`. This example keeps `module` and `moduleResolution` set to `NodeNext` in `tsconfig.json`. The emitted story is then CommonJS, which works with this version's terminal loader.
2. Use the world/player lifecycle in this example's `src/index.ts`: `initializeWorld` creates and places the player with `ActorTrait({ isPlayable: true })`; `createPlayer` returns that existing entity. The engine initializes the world **before** calling `createPlayer`, so calling `world.getPlayer()` during world initialization is too early. Exit keys use `Direction.NORTH` and `Direction.SOUTH`.

For a complete starter, copy this example's `package.json`, `package-lock.json`, `tsconfig.json` and `src/index.ts` into your newly generated project, then run the three commands above. Adjust the package name, `author`, `sharpee` metadata and story `config` to describe your own story.

The unmodified 5.5.0 starter compiled in the checked environment but did not complete terminal loading. This example includes the configuration and story initialization needed for the playable route; it does not modify installed Sharpee packages. Its generated README also describes Chord, so use the TypeScript commands here for this project.

## Edit, rebuild, play again

Change the Study's description in `src/index.ts`, for example to:

```ts
description: 'A blue notebook rests in the study. The hall is north.',
```

Then rebuild and start a new session:

```sh
npm exec -- sharpee build
npm exec -- sharpee play
```

`look` now shows your changed description. `play` reads the compiled story in `dist/`, so source changes need a rebuild. `npm run build` runs only TypeScript's compiler; the `sharpee build` command also creates the `.sharpee` story bundle.

Keep mutable story state inside `createStory()`, so a new game receives a fresh world and player.

## Scope and checks

The terminal workflow was checked on macOS with Node.js 22.23.4 using the real CLI: native scaffold, clean dependency installation, build, room movement, take/inventory/drop, repeated movement and an edited description appearing after rebuilding. These are software-operated checks of this example, not a test of another project's configuration.

No Chord source or Chord authoring step is needed. The official devkit still installs `@sharpee/chord` as an internal dependency; this is not a dependency tree without that package. No browser client, publishing, save/restore or deployment is included in the checked workflow. In the checked Node.js 18.20.4 environment, `init` failed at UUID generation, so this guide uses Node.js 22+.

The source follows the published [devkit scaffold](https://www.npmjs.com/package/@sharpee/devkit/v/5.5.0) and the engine's world-first player initialization contract. [Sharpee's source](https://github.com/ChicagoDave/sharpee) is available under MIT. Dependency installation reported an upstream `glob@10.5.0` deprecation; installation scripts were disabled in the checked path.

## Optional coffee

This example is free. If it saved you some time and you'd like to buy me a coffee, a small contribution is welcome. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
