# Paragraph classes that survive Quill Delta saves

Register a native block `ClassAttributor` to make a paragraph class part of Quill's document model. A class added directly to a DOM node is absent from `getContents()` and cannot be restored from that Delta.

This example uses Quill **2.0.3**, keeps the exact DOM classes `class-a` and `class-b`, and stores their suffixes as `customKey: "a"` and `customKey: "b"`.

## The native configuration

Register the format before constructing the editor:

```js
const { ClassAttributor, Scope } = Quill.import('parchment');
const ParagraphClass = new ClassAttributor('customKey', 'class', {
  scope: Scope.BLOCK,
  whitelist: ['a', 'b'],
});
Quill.register(ParagraphClass);

const quill = new Quill('#editor', {
  formats: ['customKey', 'bold', 'align', 'header', 'list'],
});

quill.setContents({
  ops: [
    { insert: 'hello', attributes: { bold: true } },
    { insert: '\n', attributes: { customKey: condition ? 'a' : 'b' } },
  ],
});
```

`condition` is your application state. The class prefix is `class`, so value `a` produces `class-a`; passing the full string `class-a` as the value would not match this whitelist. Keep the block attribute on the **newline**, or update an existing line with:

```js
quill.formatLine(0, 1, 'customKey', 'b');
```

Reserve the `class-` prefix for this format. Parchment replaces classes belonging to the same prefix when the value changes, so unrelated classes should use another prefix. This example supports the two declared values, rather than arbitrary class names. Use the Parchment instance returned by `Quill.import('parchment')` so registration uses the same instance as the editor. This example uses Quill's default registry.

If your editor has a `formats` allowlist, add `customKey` **alongside your existing allowed formats**. Registration does not override that restriction. An editor that excludes `customKey` will discard it, and unrelated disallowed formats stay disallowed.

## Run the example

Requires Node.js 20 or later:

```sh
npm ci --ignore-scripts
npm start
```

Open [the local example](http://127.0.0.1:3000). Only the editor's installed Quill files and this example are served locally.

1. Edit the first two colored paragraphs. The third paragraph, heading and bullet item demonstrate neighboring content and existing formats.
2. Select **Export JSON**. The saved Delta includes the class values on the newline operations.
3. Select **Clear editor**, then **Restore in new editor**. The content and classes are restored into a fresh Quill instance.
4. Select **Toggle first paragraph A / B**, export again, clear and restore again. The old class is replaced, and you can keep editing after restoration.

The saved JSON is an in-page snapshot. Add your own storage/API call where `getContents()` is serialized; this example does not supply a persistence service.

## Check the workflow

```sh
npx playwright install chromium
npm test
```

The check uses real Chromium keyboard input and a toolbar click, then three export→clear→fresh-editor restore cycles. It checks actual saved JSON, paragraph DOM classes, a different editor instance, the disconnected old editable root, continued editing, existing bold/alignment/header/list formatting and the ordinary paragraph. Separate editors check the `formats` restriction and the declared values.

Native whitelist behavior is deliberate: an unknown value on imported content is dropped; an attempted unknown replacement leaves an existing allowed value unchanged. Pass `false` to remove the format. No Block subclass, Quill source patch or direct editor-class mutation is used in the working example.

The test writes `preview.png`. Set `EVIDENCE` to a JSON file path to retain its observations. The DOM-only approach is available as an expected-failing control with `CONTROL=dom-only npm test`; `no-registration`, `inline-scope` and `reuse-editor` also test essential parts of the workflow.

References: [Quill customization](https://quilljs.com/docs/customization), [Delta line formatting](https://quilljs.com/docs/delta#line-formatting), [Parchment attributors](https://github.com/slab/parchment#attributors), [original usage question](https://github.com/slab/quill/discussions/4725).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
