# js-yaml with a classic script tag

js-yaml **5.5.0** publishes a ready-made browser UMD build. You can use it in a plain HTML page without running Browserify or Docker:

```html
<script src="https://cdn.jsdelivr.net/npm/js-yaml@5.5.0/dist/browser/js-yaml.umd.min.js"></script>
<script>
  const value = jsyaml.load('greeting: hello');
  console.log(value.greeting); // hello
  console.log(jsyaml.dump(value)); // greeting: hello, followed by a newline
</script>
```

The global name in the official UMD build is **`jsyaml`**, including the lowercase letters. Your own `browserify -s YAML` bundle would choose a different global name. These two ordinary script tags run in order; keep your code after the library and do not add `async` to the first tag.

## Try it

Open [index.html](index.html) in a modern browser. It loads the sample into a JavaScript value and writes it back to YAML. Edit the source and select **Load and dump YAML**. Invalid YAML shows its parse error and clears the previous results; correcting the input lets you continue.

For an offline page, save the official [browser UMD file](https://cdn.jsdelivr.net/npm/js-yaml@5.5.0/dist/browser/js-yaml.umd.min.js) beside `index.html`, preserve its license notice, and change only the library tag to:

```html
<script src="./js-yaml.umd.min.js"></script>
```

That local version also works when opened directly from disk. The `.mjs` files are for ES modules; `dist/js-yaml.cjs.js` is for CommonJS. Neither is the classic browser UMD file shown here.

## Version and scope

The official [package exports](https://github.com/nodeca/js-yaml/blob/5.5.0/package.json) expose the browser build, and the [build script](https://github.com/nodeca/js-yaml/blob/5.5.0/support/build-dist.mjs) sets its global name to `jsyaml`. The library's [usage guide](https://github.com/nodeca/js-yaml/blob/5.5.0/docs/usage.md) documents `load()` and `dump()`.

The example was checked with the exact official 5.5.0 UMD file in Chromium 156.0.8078.4, including repeated conversion, malformed input and recovery, a missing library, an incorrect global name, and an offline local-file copy. The CDN file matched the official npm package byte for byte. These are scripted browser checks; the original application and human manual testing were not performed. This example changes no js-yaml code. The online version needs access to the CDN; sites whose content policy blocks inline scripts should move the second script into their own allowed JavaScript file.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
