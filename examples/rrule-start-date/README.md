# Set a start date when parsing RRule text

RRule 2.8.1 accepts `until` in its English text parser. Supply the start as the `dtstart` option. An explicit start anchors the recurrence and sets its earliest possible occurrence. If the start falls on a Tuesday and the rule repeats on Mondays, the first occurrence is the following Monday. [RRule text parsing and date options](https://github.com/jkbrzt/rrule#natural-language-text-methods)

## Separate date fields

Parse the repeat pattern and pass the dates as options. The `datetime()` helper takes a one-based month and creates a UTC date. Use explicit date options when you already have date fields in your form.

```js
const { datetime, RRule } = require("rrule");

const rule = new RRule({
  ...RRule.parseText("every Monday"),
  dtstart: datetime(2026, 12, 14),
  until: datetime(2027, 1, 4),
});
```

## One text field

[recurrence.cjs](recurrence.cjs) shows how an application can recognize one `starts on YYYY-MM-DD` clause and pass the other recurrence text to RRule. These inputs produce the same schedule:

```text
every Monday starts on 2026-12-14 until 2027-01-04
every Monday until 2027-01-04 starts on 2026-12-14
```

You can also call `fromTextWithStart("every Monday until 2027-01-04", "2026-12-14")`. The example interprets an explicit `YYYY-MM-DD` start and a final ISO date-only `until` clause at midnight UTC. This preserves the last matching date across local time zones. It also accepts native count clauses such as `every day starts on 2028-02-29 for 2 times`. Other pattern text follows the library's limited English parser. Preview the actual dates before saving user-entered rules. Use `between()` with a finite date range for an open-ended rule. [RRule recurrence queries](https://github.com/jkbrzt/rrule#rruleprototypebetweenafter-before-incfalse--iterator)

Run the example with Node.js 18 or newer.

```sh
npm ci
npm start
npm test
```

The demo prints:

```text
every Monday starts on 2026-12-14 until 2027-01-04
DTSTART:20261214T000000Z
RRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20270104T000000Z
2026-12-14
2026-12-21
2026-12-28
2027-01-04
```

The tests read the actual dates, repeat the calculation with different starts, and use `rrulestr()` to load the serialized rule. Keep the serialized rule or the original text and date fields when saving it.

## Optional coffee

If this example saved you time and you'd like to buy me a coffee, contributions are entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
