# Image size checks for Quill

Apply one image file-size limit to Quill's image button, pasted image files and dropped image files. This runnable Quill **2.0.3** example also handles HTML clipboard images, preserves selected text when a paste is entirely rejected, and checks image data before exporting Delta JSON.

The demo accepts PNG/JPEG images up to **102,400 bytes each (100 KiB)**, including the exact boundary. Larger files show a visible message and leave the document untouched when no acceptable file remains.

## Run

```sh
npm ci
npm start
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Insert an image with the toolbar, clipboard or file drop. Continue editing, choose **Export Delta JSON**, then **Restore in second editor** and continue editing there.

For the checks, use Node.js 20 or newer and a Playwright Chromium installation:

```sh
npx playwright install chromium
npm test
```

Dependencies are pinned in `package-lock.json`: Quill 2.0.3 and Playwright 1.64.1. The checks ran with Node.js 22.23.4 and Chromium 156.0.8078.4 on macOS. File selection used the browser's native chooser; clipboard and drop checks used synthetic browser events carrying actual `File` objects. Physical OS clipboard and drag operations were not tested.

## Use in your editor

[image-limits.mjs](image-limits.mjs) attaches the controls once, **after Quill initializes**. This keeps existing HTML and images intact:

```js
const policy = {
  maxBytes: 102400,
  mimetypes: ['image/png', 'image/jpeg'],
};

const quill = new Quill('#editor', {
  theme: 'snow',
  modules: { uploader: { mimetypes: policy.mimetypes } },
});

installImageLimits(quill, {
  ...policy,
  notify(message) { document.querySelector('#status').textContent = message; },
});
```

Use the same MIME list in Quill's uploader and the policy. Allowed files go through Quill's original uploader handler, which preserves its registered formats and uses a user-source update. The controls respect disabled/read-only editors and never enable a format excluded by the host.

The default handler reads accepted files as data URLs. If your application already provides an upload handler, install the controls after that handler is configured. The controls delegate only accepted files to it; test its own asynchronous behavior and server responses separately.

## HTML paste and existing content

A file-handler check alone misses HTML clipboard images. Quill routes file-only pastes and a single image accompanied by files through its uploader; other HTML goes through the clipboard converter.

The added `IMG` matcher checks decoded data-URL bytes. New URL-only images are rejected with a visible message because their byte size is unavailable locally. The controls do not fetch those URLs. Supported text and formatting in a mixed paste are preserved.

For an entirely rejected HTML-image paste, a capture-phase listener prevents Quill's normal paste operation before it deletes the selected text. Empty paragraphs left by a rejected image are treated as an empty paste. Normal text-only pastes and the native file routes continue through Quill.

Existing images are retained when controls are attached. [image-policy.mjs](image-policy.mjs) also provides `auditDelta(delta, policy)`. Run it before your export or upload pipeline. It reports oversized or unknown-size image sources without changing the editor:

```js
const delta = quill.getContents();
const issues = auditDelta(delta, policy);
if (issues.length) {
  showMessage(issues.map(issue => issue.reason).join('; '));
} else {
  const json = JSON.stringify(delta);
  // Continue with your application's export/upload pipeline.
}
```

The demo preserves the last successful JSON export if a later export is blocked. Remove or replace a reported image explicitly, then export again. Programmatic `insertEmbed`/`setContents` calls do not pass through user-entry controls, so the final audit is necessary. Other custom embeds and application-specific import paths need their own policy.

File size is the original byte count; base64 JSON is larger. These checks cover declared MIME types and byte sizes. Keep your server's size limit and image validation in its ingestion path. This example ends at local JSON export and restore; it does not send images to a server.

## Verification

The browser check exercises all three original routes with small, exact-limit and oversized images. It observes native events, uploader entries and `FileReader` calls, then checks actual image DOM, Delta data, selection preservation and visible feedback. It also covers HTML-only and mixed-content paste, remote/malformed source rejection, existing content, format restrictions, disabled editors, the final export audit, JSON restore into a second editor and continued editing with another insertion.

References: [original question](https://github.com/slab/quill/discussions/4780), [uploader source](https://github.com/slab/quill/blob/v2.0.3/packages/quill/src/modules/uploader.ts), [clipboard source](https://github.com/slab/quill/blob/v2.0.3/packages/quill/src/modules/clipboard.ts), [clipboard matchers](https://quilljs.com/docs/modules/clipboard), [Quill settings](https://quilljs.com/docs/configuration), [File/Blob byte size](https://developer.mozilla.org/en-US/docs/Web/API/Blob/size).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
