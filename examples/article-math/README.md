# Equations that survive article editing and saving

This example carries a Quill equation through an article's full editing and reading flow. It keeps the existing paragraph array and text, link, image and pull-quote segment types, then adds a formula segment whose content is the TeX source.

It addresses the integration described in [NU Sci's article question](https://github.com/Northeastern-Science-Magazine/nusci-frontend/issues/219). The example runs locally with its own sample article and JSON file. It has not been deployed to that website or connected to its MongoDB database. The linked Google Doc's original equation was not available for verification.

## Run

Use Node.js 20 or newer.

```sh
npm ci --ignore-scripts
npm run build
npm start
```

Open [the local example](http://127.0.0.1:4178). Put the cursor in the article, enter TeX without dollar delimiters, and choose **Insert equation**. Click an equation in the editor to load its source, change it, and choose **Replace selected equation**. Save, then reopen the saved article.

For a separate display equation, put it on its own paragraph. A formula mixed with text stays inline. The **Read-only editor** setting disables editing and save controls.

For example:

```tex
P(v)=\frac{m v}{k_B T}\exp\left(-\frac{m v^2}{2k_B T}\right)
```

This is an illustrative expression, not a transcription of the unavailable document.

## Storage

A saved equation looks like this:

```json
{
  "articleContent": [
    [{ "contentType": "text", "content": "An existing paragraph." }],
    [{ "contentType": "formula", "content": "\\frac{a}{b}" }],
    [{ "contentType": "pull_quote", "content": "An existing quotation." }]
  ]
}
```

[content.mjs](./content.mjs) converts a complete native Quill Delta to this shape and back. It never extracts the generated KaTeX HTML, duplicated accessibility text, or a formula's rendered textContent. Text and link order, empty paragraphs and pull quotes remain separate. Adjacent identical text/link runs may be combined.

The example preserves supported images as URL segments. It rejects unsupported formats and mixed-content pull quotes before saving rather than silently discarding them. Its editor permits formula, link, blockquote and image formats. Extend the storage model and conversion deliberately if your application needs bold, lists or other formats.

## Integrating with NU Sci

There are three connected changes. Adding an equation button alone does not carry an equation through the existing save and reader paths.

1. Add `'formula'` to the frontend's `ArticleContentSegment.contentType` union. In the backend's [ArticleContent enum](https://github.com/Northeastern-Science-Magazine/nusci-backend/blob/95a94a450dde68d6bc3d57d58ae1199341e5cfd2/app/models/enums/articleContent.js), add `static Formula = new ArticleContent("formula");`. Both the existing Zod schema and Mongoose schema obtain their allowed values from `ArticleContent.listr()`, so the backend change is required before sending formula records. Existing records do not need conversion.
2. In ArticleInput, import KaTeX and its CSS before creating the editor. Quill's built-in formula format expects `window.katex`. Keep `modules={{ toolbar: false }}` if you want the existing toolbar behavior; [main.jsx](./main.jsx) shows separate insert/edit controls using public Quill methods. Use a complete Delta from `editor.getContents()` when submitting. ReactQuill's second onChange argument is only the incremental change, and its HTML output is not the formula's storage contract.
3. Replace the HTML-to-text-only conversion in ArticleSubmissionForm with the complete Delta mapping. Preserve the rest of articleData and the existing pull-quote insertion step. In ArticleTemplate, handle formula segments before the text/link fallback and render their TeX with KaTeX. Reverse the mapping when reopening an article for editing.

Deploy reader support and the backend enum before enabling formula authoring. Older readers that only understand text/link cannot render the new type. Keep application authentication, authorization, validation and existing deployment settings when integrating; the loopback file server is a local demonstration.

The current [backend accessor](https://github.com/Northeastern-Science-Magazine/nusci-backend/blob/95a94a450dde68d6bc3d57d58ae1199341e5cfd2/app/databaseAccessors/articleAccessor.js) calls `article.save()` without awaiting it. Await the database write before showing a successful save so a rejected formula cannot appear saved. The local server responds only after its JSON write completes.

A pasted Google Docs or Word equation needs conversion to TeX first. Enter its TeX source through the equation control, or paste an existing Quill formula with its native format. KaTeX supports a defined subset of TeX; invalid entered expressions show an error, and invalid saved expressions remain visible as source for correction.

## Verification

```sh
npx playwright install chromium
npm test
```

Five codec tests cover native formula mapping, complete edit round trips, image sources, unsupported-format rejection and storage validation. The Chromium check enters and edits a formula, saves through real HTTP to a temporary JSON file, reloads into a fresh editor, edits and saves again, and checks both typeset output and the on-disk TeX. It also checks existing text/link/pull-quote content, empty paragraphs, read-only behavior and rejected writes.

These are scripted tests and software-operated Chromium checks. They do not establish adoption in the original application. Versions are pinned to React 18.3.1, react-quill-new 3.8.3, Quill 2.0.3 and KaTeX 0.19.1.

References: [Quill formula format](https://quilljs.com/docs/formats/), [Quill content API](https://quilljs.com/docs/api/#getcontents), [ReactQuill controlled values](https://github.com/VaguelySerious/react-quill#using-deltas), [KaTeX rendering API](https://katex.org/docs/api).

## Optional coffee

This example is free. If it saves you time and you would like to buy me a coffee, an entirely optional contribution is welcome.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`

