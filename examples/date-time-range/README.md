# Independent start and end times in a date range

In react-datepicker **9.1.0**, use `selectsRange` with **`showTimeInput`**. The calendar then has separate **Time (Start)** and **Time (End)** inputs. Each updates its corresponding endpoint.

`showTimeSelect` displays one time list. If you need to edit both times directly in one range calendar, the two-input mode is the existing API to use. This answers [the range-time question](https://github.com/Hacker0x01/react-datepicker/discussions/6084) using the current package; it does not change an older installed version.

The essential configuration is:

```jsx
const [[start, end], setRange] = useState([
  new Date(2026, 10, 3, 9),
  new Date(2026, 10, 3, 17),
]);

<DatePicker
  selected={start}
  startDate={start}
  endDate={end}
  onChange={setRange}
  selectsRange
  showTimeInput
  allowSameDay
  dateFormat="yyyy-MM-dd HH:mm"
  shouldCloseOnSelect={false}
/>
```

Select the start and end dates first, then edit the two times. These are native time inputs, so their appearance follows the browser and operating system. Do not also set `showTimeSelect` for this example.

## Run the complete form

Use Node **20 or newer**. From this directory:

```sh
npm ci
npm start
```

Open `http://127.0.0.1:4176`. Choose different times and select **Use range** to see both submitted values. The runnable source is [app.jsx](app.jsx); [range.mjs](range.mjs) validates the complete endpoints before submission. A missing endpoint or an end at/before the start blocks submission without silently changing either selection. Changing dates clears the previous submitted result.

The form uses local JavaScript `Date` values. Its displayed result deliberately has **no time zone or UTC offset**. For storage or communication across zones, decide the intended zone and conversion policy separately. DST gaps and repeated local times require that policy; they are outside this example. The example is not a booking backend.

## Check

```sh
npx playwright install chromium
npm test
npm run build
```

The three Node tests cover local formatting, missing/invalid values and full date/time ordering. The two Chromium runs use 1280px and 375px viewports. They edit the actual start/end time inputs, submit different same-day times, select a new date range, submit an overnight interval, reject a reversed same-day interval, correct it, clear the range, and select/submit again. Reopening the popup checks that both time values persist. These are scripted browser checks; the original application and requester adoption have not been verified.

Current first-party references: [single range example](https://github.com/Hacker0x01/react-datepicker/blob/644f2f512d2efcc83885811b0faa3de7fc111350/docs-site/src/examples/ts/selectsRange.tsx), [range time-input rendering](https://github.com/Hacker0x01/react-datepicker/blob/644f2f512d2efcc83885811b0faa3de7fc111350/src/calendar.tsx), [endpoint time handling](https://github.com/Hacker0x01/react-datepicker/blob/644f2f512d2efcc83885811b0faa3de7fc111350/src/index.tsx).

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, a contribution is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
