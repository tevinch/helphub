# Math headings and legends for Chart.js

Chart.js draws ordinary text on its canvas. Dollar delimiters do not make its built-in title or legend render LaTeX, and there is no native `AllowLatexExpression` option.

This example puts the chart heading and dataset legend in HTML and renders their formulas with KaTeX. The legend follows Chart.js's documented HTML-legend sample: its `afterUpdate` hook uses the built-in label generator, colors, dataset indices and visibility state. Formula buttons work with the mouse, Enter and Space. The second series starts hidden.

## Run

Use Node **22.12 or newer**. The checked runtime was Node 22.23.5.

```sh
npm ci
npm start
```

Open the local address printed by the server. All JavaScript, CSS and KaTeX fonts are served from the installed packages.

The locked dependencies are Chart.js **4.6.1**, KaTeX **0.19.1** and Playwright **1.65.1** for browser checks. No framework or build step is needed.

## Use it in your chart

Keep the HTML heading and legend containers outside the dedicated, relatively positioned canvas parent, as shown in [index.html](index.html). Load KaTeX's CSS and JavaScript plus Chart.js, then copy [math-labels.js](math-labels.js) and its plugin configuration from [main.js](main.js):

```js
options: {
  plugins: {
    title: {display: false},
    legend: {display: false},
    'math-labels': {
      headingID: 'math-heading',
      legendID: 'math-legend',
      heading: String.raw`\sqrt{cos(x^2)} + se(x^2)`,
    },
  },
},
plugins: [mathLabels],
```

The plugin array belongs at the chart configuration's top level; its settings belong under `options.plugins`. The hook renders the external heading and legend after the actual chart updates. Supply a readable `accessibleLabel` on each dataset for its toggle button, alongside its formula `label`.

The standalone page includes [style.css](style.css). For an existing site, copy its `#math-legend` layout/button rules and the `.swatch`, `.formula`, `.is-hidden` and focus styles. Scope the shared `button` and `button:focus-visible` rules to `#math-legend button` so they do not restyle other controls. The swatches need the CSS display, size and border-style rules to show their native colors; the hidden-state rules mark a hidden series.

Pass the TeX source directly to KaTeX without `$` delimiters. The original `\sqrt{cos(x^2)} + se(x^2)` is preserved exactly, including `se`; the example does not reinterpret or evaluate it. Its plotted points are illustrative data, independent of the formula strings.

The **Update example** button changes the heading, formulas and sample values for the same two datasets through `chart.update()`. Existing visibility choices remain intact, and the refreshed legend retains keyboard focus. This example is scoped to line-chart dataset labels and same-series updates.

## Limits

“Series title” here means the dataset's legend label. This does not add labels painted along each curve, rich math tooltips or a new Chart.js option. Native canvas tooltips still display the formula source as ordinary text.

The math heading and legend are outside the canvas. `chart.toBase64Image()` and other canvas-only PNG exports therefore omit them.

KaTeX provides HTML and MathML output. Browser checks verify their presence and visible layout.

## Verify

```sh
npx playwright install chromium
npm test
```

For an existing compatible Chromium installation, set `CHROME_EXECUTABLE_PATH` to its executable. Set `EVIDENCE_DIR` to save screenshots. The script starts a temporary loopback server and closes its test browser afterward.

[verify.mjs](verify.mjs) checks the original formula in the heading and first legend label, the expected formulas in both series labels, MathML roots/exponents, actual font requests, visible geometry at 390 and 1100 pixels, rendered chart points and colors, initial hidden state, repeated mouse/keyboard toggles, and three title/label/data updates followed by continued interaction. It also requires the acceptance checks to fail when math, heading or series rendering is omitted, the plugin does not run, or a click is mapped to the wrong dataset.

The legend is adapted from Chart.js's [HTML legend example](https://github.com/chartjs/Chart.js/blob/v4.6.1/docs/samples/legend/html.md), with its MIT notice preserved in [LICENSE](LICENSE). See the official [HTML title guidance](https://github.com/chartjs/Chart.js/blob/v4.6.1/docs/configuration/title.md), [responsive container requirements](https://github.com/chartjs/Chart.js/blob/v4.6.1/docs/configuration/responsive.md), [dataset visibility API](https://github.com/chartjs/Chart.js/blob/v4.6.1/docs/developers/api.md) and [KaTeX rendering API](https://katex.org/docs/api).

## Optional coffee

If this saved you some time, you're welcome to buy me a coffee. It's entirely optional; the example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
