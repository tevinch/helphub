# Keep date range validation with a custom AG Grid picker

AG Grid 36.2.0 and 36.3.0 can validate an `inRange` filter with a custom Flatpickr input. Put `ag-input-field-input` on each visible `<input data-input>` so the date-filter wrapper can set its native validation message and `aria-invalid`. Keep forwarding selected dates through `onDateChange` and input focus through `onFocusIn`.

```jsx
<input
  type="text"
  data-input
  className="ag-input-field-input"
  onFocus={() => onFocusIn?.()}
/>
```

The class is a compatibility detail of these AG Grid releases. If the picker creates a different visible input, the wrapper needs to find that input inside the custom component. The [AG Grid date wrapper](https://github.com/ag-grid/ag-grid/blob/release-36.3.0/packages/ag-grid-community/src/filter/provided/date/dateCompWrapper.ts) shows where the class is used.

Flatpickr makes the field read-only by default. With that default you can show an error outline based on `aria-invalid`, as this example's CSS does. Use `allowInput: true` if you also want the browser to report native validation errors and support typing. Keep `ag-custom-component-popup` on the calendar so selecting a calendar day leaves the filter open.

## Run the example

Use Node.js 22.12 or newer.

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite and select **Open date filter**. Navigate both calendars to November 2026. Select November 12 to 24 for a range showing Middle and Late. Change the end to November 8 to see the invalid state while the old rows stay visible. Change it to November 14 to clear the error and see only Middle.

## Verify

```sh
npx playwright install chromium
npm test
```

The browser test opens the production build, operates both calendars, and checks the error outline, native `invalid` event, `aria-invalid`, applied range and visible rows. It also checks correction, an inclusive one-day range, clearing and applying a new range. The package lock uses the `ag-grid-community` and `ag-grid-react` packages at 36.3.0, with Flatpickr 4.6.13. The same interaction was also checked with AG Grid 36.2.0.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
