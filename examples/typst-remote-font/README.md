# Typst remote font example

Load a custom OTF font before compiling a document in the browser. This example uses the public API in typst.ts **0.7.0**, the current stable release checked on 2026-11-09.

`preloadRemoteFonts` is a named export, not a method on `$typst`. It is deprecated in favor of the named `loadFonts` export. For an npm application:

```js
import { $typst, loadFonts } from '@myriaddreamin/typst.ts';

$typst.setCompilerInitOptions({
  getModule: () => '/assets/typst_ts_web_compiler_bg.wasm',
  beforeBuild: [loadFonts(['/assets/MyFont.otf'])],
});
```

Set these options **before** calling `getCompiler()`, `svg()`, `pdf()`, or another operation that initializes the compiler. Keep the JavaScript package, compiler WASM and renderer WASM on matching versions. Use the font's internal family name in Typst, for example:

```typst
#set text(font: "Noto Sans SC")
Hello, Typst!
```

The alternative already suggested in [the font discussion](https://github.com/Myriad-Dreamin/typst.ts/discussions/902) is `$typst.use(TypstSnippet.preloadFonts([fontUrl]))`, with `TypstSnippet` imported from `@myriaddreamin/typst.ts/contrib/snippet`. Both configure the compiler before its first use.

## Run

```sh
cd examples/typst-remote-font
npm ci --ignore-scripts
npm start
```

Open [the local example](http://127.0.0.1:8123). It loads the font, compiles the initial document and shows its SVG. Edit the document and press **Render** to compile again.

The browser import map supports this standalone example without a bundler. In a bundled application, use the ordinary package import above and your bundler's documented way to copy or locate the matching WASM files. This example's Node server is for local development.

`example.mjs` passes `{ assets: false }` so the example uses only the chosen font. Normal applications can omit this option to keep default font assets, or supply additional text, math and style fonts. The Noto Sans SC Regular file does not cover every font/style a full template might request. It also does not install missing Typst packages or template files.

The sample font comes from [Noto CJK](https://github.com/notofonts/noto-cjk), pinned at revision `f8d157532fbfaeda587e826d4cd5b21a49186f7c`. The OTF is fetched at runtime and is not included here. Its checked SHA-256 is `faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9` (8,331,336 bytes). A production application can host its own copy under the font's license. Font and WASM URLs must be reachable from the browser; cross-origin hosts must allow CORS.

## Verification

```sh
# Install a Playwright browser if you do not already have Chrome:
npx playwright install chromium
CHROME_PATH="/path/to/chrome" npm test
```

On macOS, the test defaults to the usual Google Chrome path. Alternatively, set `CHROME_PATH` to the executable supplied by your Playwright installation.

Software-operated Chromium checks cover the real compiler and renderer WASM, the actual remote font request, visible Latin and non-Latin glyphs, two edits followed by repeated compilation, and exact source preservation. A negative control removes the font from the initializer in a fresh browser context: it fetches no font and yields zero text glyphs, which the normal acceptance check rejects. Empty compiler diagnostics alone are insufficient to establish that text rendered.

The stable package emits two WASM initialization deprecation warnings with its documented `getModule` form. The checked document produces no compiler diagnostics and no browser page errors. This is a standalone consumer check; it does not establish that any particular application or template has been validated or adopted.

References: [font usage question](https://github.com/Myriad-Dreamin/typst.ts/issues/903), [stable named exports](https://github.com/Myriad-Dreamin/typst.ts/blob/v0.7.0/packages/typst.ts/src/index.mts), [stable font initializer](https://github.com/Myriad-Dreamin/typst.ts/blob/v0.7.0/packages/typst.ts/src/options.init.mts), [official browser guide](https://myriad-dreamin.github.io/typst.ts/cookery/guide/all-in-one.html).

## Optional coffee

This example is free to use. If it saves you time, buying me a coffee is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
