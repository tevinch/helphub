const assert = require("node:assert/strict");
const test = require("node:test");
const { datetime, RRule, rrulestr } = require("rrule");
const { fromTextWithStart } = require("./recurrence.cjs");

const pattern = "every Monday until 2027-01-04";
const monday = "2026-12-14";
const dates = ["2026-12-14", "2026-12-21", "2026-12-28", "2027-01-04"];

function occurrenceDates(rule) {
  return rule.all().map((date) => date.toISOString().slice(0, 10));
}

test("native text accepts until but does not populate DTSTART from a start clause", () => {
  const native = RRule.parseText(pattern);
  assert.ok(Number.isFinite(native.until.getTime()));
  assert.equal(RRule.parseText("every Monday starts on 2026-12-14").dtstart, undefined);
});

test("a separate start includes the first and last Monday with no dates outside the bounds", () => {
  const rule = fromTextWithStart(pattern, monday);
  assert.deepEqual(occurrenceDates(rule), dates);
  assert.equal(rule.before(datetime(2026, 12, 14)), null);
  assert.equal(rule.after(datetime(2027, 1, 4)), null);
});

test("both placements of the start clause preserve the complete schedule", () => {
  const sentences = [
    "every Monday starts on 2026-12-14 until 2027-01-04",
    "every Monday until 2027-01-04 starts on 2026-12-14",
  ];
  for (const sentence of sentences) {
    assert.deepEqual(occurrenceDates(fromTextWithStart(sentence)), dates);
  }
});

test("serialization preserves DTSTART, UNTIL, and the resulting occurrences", () => {
  const rule = fromTextWithStart("every Monday starts on 2026-12-14 until 2027-01-04");
  const serialized = rule.toString();
  assert.equal(
    serialized,
    "DTSTART:20261214T000000Z\nRRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20270104T000000Z",
  );
  assert.deepEqual(occurrenceDates(rrulestr(serialized)), dates);
});

test("repeated scheduling with a Tuesday start runs from the next matching Monday", () => {
  assert.deepEqual(occurrenceDates(fromTextWithStart(pattern, monday)), dates);
  assert.deepEqual(occurrenceDates(fromTextWithStart(pattern, "2026-12-15")), dates.slice(1));
  assert.deepEqual(occurrenceDates(fromTextWithStart(pattern, "2027-01-05")), []);
  assert.deepEqual(occurrenceDates(fromTextWithStart(pattern, monday)), dates);
});

test("count-based recurrence keeps its count and accepts a real leap day", () => {
  const rule = fromTextWithStart("every day starts on 2028-02-29 for 2 times");
  assert.equal(rule.origOptions.count, 2);
  assert.deepEqual(occurrenceDates(rule), ["2028-02-29", "2028-03-01"]);
});

test("an ISO end date is also calendar-checked and cannot follow a count", () => {
  assert.throws(() => fromTextWithStart("every Monday until 2027-02-30", monday), /valid calendar date/);
  assert.throws(() => fromTextWithStart("every Monday for 3 times until 2027-01-04", monday), /one end clause/);
});

test("rejects a missing, malformed, or impossible start date", () => {
  assert.throws(() => fromTextWithStart(pattern), /YYYY-MM-DD/);
  assert.throws(() => fromTextWithStart(pattern, "2026/12/14"), /YYYY-MM-DD/);
  assert.throws(() => fromTextWithStart(pattern, "2026-02-29"), /calendar date/);
  assert.throws(() => fromTextWithStart("every Monday starts on December 14"), /YYYY-MM-DD/);
});

test("rejects duplicate dates and misplaced or intersecting clauses", () => {
  const sentence = "every Monday starts on 2026-12-14 until 2027-01-04";
  assert.throws(() => fromTextWithStart(sentence, monday), /only one start date/);
  assert.throws(() => fromTextWithStart(sentence + " starts on 2026-12-21"), /only one start date/);
  assert.throws(() => fromTextWithStart("starts on 2026-12-14 every Monday"), /starts on/);
  assert.throws(() => fromTextWithStart("every week starts on 2026-12-14 on Monday"), /starts on/);
  assert.throws(() => fromTextWithStart("every Monday for 3 times starts on 2026-12-14 until 2027-01-04"), /one end clause/);
});

test("rejects input the native parser cannot turn into a rule", () => {
  assert.throws(() => fromTextWithStart("gibberish", monday), /recurrence pattern/);
});
