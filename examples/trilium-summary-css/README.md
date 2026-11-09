# Trilium summary backgrounds

Give the summaries below note titles a pale yellow background in the Grid view of Trilium's Note List. The summary element is `.note-book-content`; `.note-book-card-content` does not match it in **Trilium 0.107.0**.

```css
.note-list.grid-view .note-book-card > .note-book-content {
    background-color: #fff3a6;
}
```

The header containing the title is a separate sibling, so this rule changes only the summary container's background. It leaves the title, card border, text color, spacing and click handling alone. Change the hex value to choose another color.

## Apply it

1. Insert a child note using **Code → Custom CSS**. Alternatively, create a Code note, select CSS as its language, and add the `#appCss` label.
2. Paste the rule from [summary.css](./summary.css) into that note.
3. Refresh Trilium with **Ctrl+Shift+R**, as the [custom CSS guide](https://github.com/TriliumNext/Trilium/blob/v0.107.0/docs/User%20Guide/User%20Guide/Theme%20development/Custom%20app-wide%20CSS.md) requires. Editing an app CSS note does not immediately update the page.
4. Open a parent with child text notes in **Grid** view. The summaries should be yellow, and clicking a summary should still open its note.

Keep any other rules in your existing CSS note. To undo this change, remove only this rule and refresh again. The selector is scoped to Grid view and does not target other Note List layouts or note editors.

## Verification

The included check uses the [official browser app](https://app.triliumnotes.org) in a fresh local database, and requires its runtime to report stable version **0.107.0**. It creates two text notes with existing HTML, installs a real CSS note with `#appCss`, and reloads the app. It checks the original selector as a negative control, both yellow summaries, unchanged title/card styles, two actual summary clicks opening the full editable notes, exact stored HTML preservation, and restoration after removing the rule. Coverage is the standard light theme; other custom CSS can affect the cascade.

```sh
cd examples/trilium-summary-css
npm ci --ignore-scripts
npx playwright install chromium
CHROME_PATH="/path/to/chrome" npm test
```

Set `CHROME_PATH` to your Chrome or Playwright Chromium executable. On macOS, the test defaults to `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. A screenshot is written to `artifacts/summary.png`.

All fixture mutations use Trilium's explicit `standaloneApi.localFetch` transport to its browser-local SQLite worker. The test blocks non-GET/HEAD requests seen by its browser route, records blocked host telemetry, and checks that no `/api/` requests reach that route. Trilium's required service worker remains enabled; this is a routed-request audit, not a blanket network guarantee. These are software-operated Chromium checks, not desktop or human manual validation.

References: [original question](https://github.com/orgs/TriliumNext/discussions/12539), [stable card markup](https://github.com/TriliumNext/Trilium/blob/v0.107.0/apps/client/src/widgets/collections/legacy/ListOrGridView.tsx), [stable card styles](https://github.com/TriliumNext/Trilium/blob/v0.107.0/apps/client/src/widgets/collections/legacy/ListOrGridView.css).

## Optional coffee

This example is free to use. If it saves you time, buying me a coffee is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
