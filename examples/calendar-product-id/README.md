# Set the product ID of a calendar-link export

In calendar-link 2.11.7, `ics(event)` returns a calendar data URL with a fixed `PRODID`. If your app publishes the download, you can set its product ID on the exported calendar. Pass the generated URL through [calendar-product-id.mjs](calendar-product-id.mjs) before serving or downloading it.

```js
import { ics } from "calendar-link";
import { withCalendarProductId } from "./calendar-product-id.mjs";

const event = {
  title: "Planning session",
  start: "2027-01-11T09:00:00Z",
  end: "2027-01-11T09:30:00Z",
  uid: "planning-2027-01-11@example.com",
};

const href = withCalendarProductId(
  ics(event),
  "-//Field Notes//Schedule Export//EN",
);
```

Use `href` as the URL for your calendar download link. Choose a stable identifier for the application publishing the file. The helper takes the data URL from this version of `ics()`, replaces its calendar-level `PRODID`, and preserves the other calendar fields byte for byte after decoding. It escapes iCalendar text punctuation and folds long product IDs on UTF-8 character boundaries. The ID must be a single non-empty line. [calendar-link exporter](https://github.com/AnandChowdhary/calendar-link/blob/v2.11.7/src/index.ts#L213-L326) · [iCalendar product identifier](https://www.rfc-editor.org/rfc/rfc5545.html#section-3.7.3)

## Try it

Run these commands from this example directory with Node.js 18 or later.

```sh
npm ci
npm test
npm run example -- example.ics
```

Open `example.ics` as text to see `PRODID:-//Field Notes//Schedule Export//EN`. Import the file into a calendar app to see the recurring Planning session at 09:00 UTC, three Mondays starting January 11, 2027. The test suite fetches the data URL and reads the recurring event and its three occurrences with ical.js. It checks all-day dates as raw lines because calendar-link 2.11.7 omits `VALUE=DATE` on those fields.

## Optional coffee

If this example saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
