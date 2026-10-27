# Require meaningful Quill content on submit

Read the full document with `quill.getContents()` in your form's submit handler. An empty Quill document still contains a final newline, and an empty code block adds formatting to a newline. Neither is meaningful input. `getLength()` or nonempty editor HTML cannot decide this.

[content.mjs](content.mjs) supplies a small predicate. It accepts a non-whitespace text insert, including real code, or an explicitly accepted embed type:

```js
import { hasMeaningfulContent } from './content.mjs';

form.addEventListener('submit', event => {
  const delta = quill.getContents();
  if (!hasMeaningfulContent(delta)) {
    event.preventDefault();
    error.textContent = 'Enter text or add an image before submitting.';
    error.hidden = false;
    return;
  }
  // Continue your existing submission with this unchanged Delta.
});
```

Connect this to your actual form and error element. Keep your existing Quill formats, toolbar, registry and read-only settings. The complete example in [app.mjs](app.mjs) also handles accessibility, JSON submission, visible acknowledgement, failure and retry.

## Content policy

| Document | This example |
| --- | --- |
| Empty document, blank lines, spaces, tabs or nonbreaking spaces | Reject |
| Empty code block, including several blank code lines | Reject |
| Non-whitespace text or code | Accept |
| Registered, allowed image embed with no text | Accept |
| Other embed types alone | Reject unless explicitly added to the accepted set |

Images count here because a form may legitimately accept an image-only answer. `getText()` omits embeds, so `quill.getText().trim()` would reject that document. If your form requires text, make that policy explicit:

```js
hasMeaningfulContent(quill.getContents(), new Set()); // Text required
```

For another meaningful embed, register and allow it in your editor normally, then include its blot name in the set passed to the predicate. The predicate does not register formats or change their permissions. Only the built-in image embed is exercised by this demo.

Whitespace follows JavaScript's `trim()` definition. Invisible characters outside that definition are not filtered. This is required-content validation, not a content-quality filter. Pass a **full document Delta**, not the incremental change Delta from a `text-change` event. The check does not modify text, attributes, line formats or embeds.

## Run the complete form

Use Node20 or newer:

```sh
npm ci
npm start
```

Open <http://127.0.0.1:3000>. Submit the blank editor to see the error. Use the code-block toolbar button and submit the empty block: the error remains. Type code and submit again: the local server acknowledges the exact Delta and the page displays it. Clear and refill the editor to repeat the operation.

The demo enables bold, italic, code-block and image formats. The toolbar uses Quill's ordinary code-block format without a syntax-highlighting dependency. Images already present in the document are accepted and preserved. The local server acknowledges submissions in memory; it does not store them across restarts. Replace the example endpoint with your application's submission/storage flow and apply the same required-content policy there.

## Verify the flow

```sh
npx playwright install chromium
npm test
```

The check creates its own local server and temporary browser context. It exercises real form-button clicks, a toolbar-created empty code block, native keyboard input, visible errors and actual HTTP requests/responses. An observer outside the submit handler verifies that invalid documents send no POST, while accepted requests and acknowledgements contain exactly the editor's full Delta.

It also clears/refills and submits repeatedly, preserves bold/italic/code-block data, accepts an image-only document under the stated policy, keeps a disabled editor disabled, then stops the local endpoint and verifies visible failure plus successful retry without erasing content. Native configuration and submit-event observations ensure the checks cannot pass merely because a callback was never called.

Verified with Quill2.0.3, Node24.19.0 and Chromium156.0.8078.4 on macOS arm64 using scripted browser checks. The original requester's application and a human manual session were not tested. This example uses Quill's public APIs; it does not patch Quill.

References: [Quill content API](https://quilljs.com/docs/api#content), [Delta embeds and line formatting](https://quilljs.com/docs/delta), [supported formats](https://quilljs.com/docs/formats), [original question](https://github.com/slab/quill/discussions/4742).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
