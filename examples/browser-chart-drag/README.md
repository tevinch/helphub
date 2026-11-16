# Browser chart drag

A complete Recharts selection example and a Vitest browser test that presses, drags through intermediate categories, and releases. The test checks the completed visible range, actual chart callbacks, a second selection, and reverse dragging.

The chart preserves the 800 × 400 dimensions, seven `a`–`g` data points, axes, grid, tooltip, and line used in [Recharts discussion #6178](https://github.com/recharts/recharts/discussions/6178). The selection logic and tests here are a standalone consumer example to adapt. The original application's selection code and full test suite are unavailable; this example does not establish that they are fixed.

## Run

Use Node 22.12 or newer. The exact tested runtime was Node 24.19.0.

```sh
npm ci --ignore-scripts
npx playwright install chromium
npm test
npm run build
npm run dev
```

If Google Chrome is already installed, use it without downloading Chromium:

```sh
CHROME_CHANNEL=chrome npm test
```

Playwright starts a separate browser with a temporary profile. It does not use your signed-in Chrome profile. On Windows PowerShell, set `$env:CHROME_CHANNEL = 'chrome'` before running `npm test`.

Direct dependencies are pinned and the lockfile includes transitive versions. The tested chart package is Recharts **3.10.1**, confirmed as npm's stable release on November 16, 2026. React 19.1.0 and Vitest / `@vitest/browser` 3.2.4 retain the reported reproduction's versions. Vite 7.3.8, Playwright 1.62.1, and TypeScript 5.8.3 complete this tested setup. These are reproducibility pins, not a claim that every dependency is the newest release.

## Why the sequence matters

A press-only DOM event does not first populate the chart's hover state. In this setup its `onMouseDown` callback has unavailable active fields. Even dispatching a DOM mouse move and press synchronously in one task leaves no opportunity for the default animation-frame hover update to finish.

The passing sequence uses Playwright's native mouse input through [Vitest browser commands](https://v3.vitest.dev/guide/browser/commands):

1. Read a rendered category tick and the SVG's native browser bounds.
2. Move to the starting category, then wait for both its actual `onMouseMove` observation and visible tooltip label.
3. Press the left button and independently verify that `onMouseDown` ran.
4. Move through each intermediate category with the button held, waiting for each callback and tooltip update.
5. Release, then assert the completed visible selection and exact down/move/up observations.

There is no preliminary click. The tests use real timers and browser geometry. They do not access Recharts' store, call the selection handlers directly, or set selection state from a test.

[`ChartRange.tsx`](src/ChartRange.tsx) keeps the draft endpoints in a ref. Down starts the draft, held-button moves update its endpoint, and up completes the selection only when the release payload agrees with the last observed endpoint. The highlight uses `ReferenceArea`; the original series and axis settings remain intact. The optional `onEvent` observer reports actual chart callbacks separately from the selection state. It normalizes unavailable fields to `null` and category indices to numbers.

[`ChartRange.test.tsx`](test/ChartRange.test.tsx) verifies:

- `b (1) → e (4)`, then `a (0) → c (2)`, then reverse `f (5) → d (3)`.
- Held-button intermediate moves, exact release endpoints, the visible final range, and highlight bounds.
- All seven points, the line path, axes, and grid remain after the repeated gestures.
- A press without hover has unavailable active fields.
- Synchronous DOM hover and press without waiting still have unavailable active fields.
- A native drag without release leaves no completed selection.

The positive gesture tests use native Playwright input. The two timing controls deliberately use DOM events in the same real browser to characterize press-only and same-task test arrangements. They do not demonstrate that every native move followed immediately by press fails; that sequence can race a rendering frame.

## Scope and limitations

Validation was scripted browser testing in headless Chrome, plus TypeScript checking and a production build. It was not human manual testing, original-project adoption, jsdom validation, or cross-browser coverage. The production build emits Vite's bundle-size advisory for this single-page chart example.

This example covers a mouse gesture that stays within the chart. It does not implement out-of-chart pointer capture, touch selection, keyboard range selection, zooming, or the original application's unavailable selection behavior. Adapt the consumer handlers and acceptance assertions to those requirements when needed. If your suite uses fake timers, account for the animation-frame scheduling described in the [Recharts 3.10.1 testing guidance](https://github.com/recharts/recharts/blob/v3.10.1/test/README.md); this example uses real timers throughout.

The [public LineChart API](https://recharts.github.io/en-US/api/LineChart/) documents the chart's mouse callbacks and event throttling. This example leaves the default chart settings intact.

## Optional coffee

The example is free. If it saved you time and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
