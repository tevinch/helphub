# Rough SVG with React 19.0

`react-rough-fiber` 0.0.8 can render with **React 19.0.9 and react-reconciler 0.31.0**. Pin the reconciler explicitly; installing its latest version brings a different renderer interface.

This example addresses the `resolveEventTimeStamp is not a function` and `trackSchedulerEvent is not a function` errors reported in [react-rough-fiber #15](https://github.com/Bowen7/react-rough-fiber/issues/15). It uses the published library unchanged.

## Run the example

Use Node.js 22.12 or newer; validation used Node.js 24.21.0.

```sh
npm ci --ignore-scripts
npm run dev
```

Open the local URL printed by Vite. Change the circle twice, add and remove the rectangle, then hide and restore the drawing. “Unmount example” removes the whole React root; reload the page to start again.

The complete application is in [src/main.jsx](src/main.jsx). It uses `RoughSVG` with ordinary React-created SVG children and React StrictMode.

## Apply the version choice to an existing React 19.0 app

```sh
npm install --save-exact react@19.0.9 react-dom@19.0.9 react-reconciler@0.31.0 react-rough-fiber@0.0.8
npm ls react react-dom react-reconciler react-rough-fiber
```

Keep React and React DOM on the same version, and keep a single React installation. Commit the resulting lockfile.

This is a verified **React 19.0** configuration. It does not establish support for React 19.1, 19.2 or 19.3. If your app needs one of those minor lines, this example does not supply that compatibility.

## Why the pin matters

The library's [installation guide](https://github.com/Bowen7/react-rough-fiber/blob/f3a6158675954db00a6857d40aaf3d3e9e5fa5f2/README.md#installation) leaves `react-reconciler` unpinned. Its [published 0.0.8 renderer](https://github.com/Bowen7/react-rough-fiber/blob/f3a6158675954db00a6857d40aaf3d3e9e5fa5f2/packages/react-rough-fiber/src/renderer.ts) includes React 19 handling but does not implement the hooks named in the reported errors. React documents that the [reconciler's host interface changes between releases](https://github.com/react/react/blob/v19.0.9/packages/react-reconciler/README.md).

`react-reconciler` 0.31.0 declares React `^19.0.0` as its peer dependency. React [19.0.9](https://github.com/react/react/releases/tag/v19.0.9) is the tested patch release for that minor line. An unbounded install currently selects reconciler 0.34.0; the same example with React/React DOM 19.3.1 and that reconciler reproduced both reported errors.

## Verify

```sh
npx playwright install chromium
npm test
npm run build
```

If Google Chrome is already installed, `PLAYWRIGHT_CHANNEL=chrome npm test` uses it instead.

The browser test checks visible generated SVG paths, changed geometry and color, updated text, repeated changes, shape insertion/removal, remounting and complete root removal. It also fails on browser errors. Validation used software-operated headless Chrome; the original reporter's project and human manual validation were not available.

## License

The example source is MIT licensed. React Rough Fiber and its dependencies retain their own licenses.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
