# Different fonts for individual legend labels

For a line chart in Chart.js **4.6.1**, use an HTML legend when each dataset label needs its own font. The canvas legend's `labels.font` is shared. Flat font properties or a nested `font` object returned by `generateLabels` do not give individual `LegendItem`s separate fonts.

This example renders **Number 1** in 20px bold italic Arial and **Number 2** in 12px regular Georgia, using system fallback fonts if needed. The two lines remain on the same chart. Each legend item is a native button: pointer clicks, Space and Enter hide/show the corresponding dataset. `aria-pressed` and a strikethrough reflect visibility, and keyboard focus survives chart updates.

## Run

Use Node **20 or newer**. From this directory:

```sh
npm ci
npm start
```

Open `http://127.0.0.1:4177`. Toggle the labels, select **Update data**, and toggle again. A hidden dataset stays hidden when its values change; no data points are removed by a visibility toggle.

## Use in another line chart

Copy [legend.mjs](legend.mjs) and the `.legend-list`/`.legend-swatch` rules from [style.css](style.css). Create a container and a separate plugin instance for each chart:

```js
import { createHtmlLegend } from './legend.mjs';

const legend = createHtmlLegend(document.getElementById('legend'), index =>
  index === 0
    ? { font: 'italic 700 20px Arial, sans-serif', color: '#c22020' }
    : { font: 'normal 400 12px Georgia, serif', color: '#17652f' }
);

// In the Chart configuration:
// options.plugins.legend.display = false
// plugins = [legend]
```

[main.mjs](main.mjs) contains the complete configuration. The plugin uses the built-in label generator for dataset labels, colors and hidden state, then applies ordinary CSS to each button. Labels use `textContent`. Calling `chart.destroy()` removes only the list created by this plugin and preserves other container content.

The style callback receives the dataset index. This example keeps the original two **line** datasets and their string colors. It also fits dataset-based bar charts. Pie/doughnut legends toggle individual data items and require a different visibility handler; this snippet does not implement that behavior. If you replace the system fonts with web fonts, load those fonts before judging their appearance.

## Checks

```sh
npx playwright install chromium
npm test
```

Four Chromium checks run at 1280px and 375px widths. The negative control in [canvas-control.html](canvas-control.html) sends both flat and nested font fields through `generateLabels`; instrumentation records the fonts used by actual canvas `fillText` calls while still invoking the native drawing method. The labels retain the same canvas font despite the distinct requested fonts.

The working-page checks verify actual computed font styles, six rendered points per line, pointer/keyboard toggling, focus, updated values, preserved data and visibility, repeated toggling, cleanup and layout width. These are scripted browser checks, not confirmation from the original application or requester.

First-party references: [legend configuration and LegendItem interface](https://www.chartjs.org/docs/latest/configuration/legend.html), [HTML legend example](https://www.chartjs.org/docs/latest/samples/legend/html.html), [4.6.1 canvas legend drawing](https://github.com/chartjs/Chart.js/blob/76d8cf895a7485dc838c90ef37e2bc9d9e388fcb/src/plugins/plugin.legend.js). Original [per-label font question](https://github.com/chartjs/Chart.js/discussions/12156).

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, a contribution is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
