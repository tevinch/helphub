import assert from "node:assert/strict";
import test from "node:test";
import { ics } from "calendar-link";
import ICAL from "ical.js";
import { withCalendarProductId } from "./calendar-product-id.mjs";

const originalProductId = "-//AnandChowdhary//calendar-link//EN";
const productId = "-//Field Notes//Schedule Export//EN";

const timedEvent = {
  title: "Planning café",
  start: "2027-01-11T09:00:00Z",
  end: "2027-01-11T09:30:00Z",
  uid: "planning-2027-01-11@example.com",
  description: "First line\nSecond line",
  location: "Room B",
  organizer: { name: "Calendar Desk", email: "calendar@example.com" },
  rRule: "FREQ=WEEKLY;COUNT=3",
  url: "https://example.com/planning?view=week#details",
  status: "CONFIRMED",
};

function calendarText(href) {
  return decodeURIComponent(href.slice(href.indexOf(",") + 1));
}

function parseCalendar(text) {
  return new ICAL.Component(ICAL.parse(text));
}

test("exports the selected product ID and preserves the recurring event", async () => {
  const href = ics(timedEvent);
  const before = calendarText(href);
  const response = await fetch(withCalendarProductId(href, productId));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /^text\/calendar/);
  const after = await response.text();
  const expected = before.replace(
    `\r\nPRODID:${originalProductId}\r\n`,
    `\r\nPRODID:${productId}\r\n`,
  );
  assert.notEqual(expected, before);
  assert.deepEqual(Buffer.from(after), Buffer.from(expected));

  const calendar = parseCalendar(after);
  assert.equal(calendar.getAllProperties("prodid").length, 1);
  assert.equal(calendar.getFirstPropertyValue("prodid"), productId);
  const entry = calendar.getFirstSubcomponent("vevent");
  assert.equal(entry.getFirstPropertyValue("summary"), timedEvent.title);
  assert.equal(entry.getFirstPropertyValue("uid"), timedEvent.uid);
  assert.equal(entry.getFirstPropertyValue("dtstart").toString(), "2027-01-11T09:00:00Z");
  assert.equal(entry.getFirstPropertyValue("dtend").toString(), "2027-01-11T09:30:00Z");
  assert.equal(entry.getFirstPropertyValue("rrule").toString(), timedEvent.rRule);
  assert.equal(entry.getFirstPropertyValue("description"), timedEvent.description);
  assert.equal(entry.getFirstPropertyValue("url"), timedEvent.url);
  assert.equal(entry.getFirstPropertyValue("organizer"), "MAILTO:calendar@example.com");
  assert.equal(entry.getFirstPropertyValue("status"), timedEvent.status);
  const occurrences = new ICAL.Event(entry).iterator();
  assert.deepEqual(
    [occurrences.next().toString(), occurrences.next().toString(), occurrences.next().toString()],
    ["2027-01-11T09:00:00Z", "2027-01-18T09:00:00Z", "2027-01-25T09:00:00Z"],
  );
  assert.equal(occurrences.next(), undefined);
});

test("preserves date-only values and replaces a previously customized ID", () => {
  const href = ics({
    title: "Library closed",
    start: "2027-01-12",
    end: "2027-01-13",
    allDay: true,
    uid: "library-closed-2027-01-12@example.com",
  });
  const first = withCalendarProductId(href, productId);
  const otherId = "-//Library Desk//Hours//EN";
  const second = withCalendarProductId(first, otherId);
  const text = calendarText(second);
  assert.equal(
    text,
    calendarText(href).replace(`\r\nPRODID:${originalProductId}\r\n`, `\r\nPRODID:${otherId}\r\n`),
  );
  const calendar = parseCalendar(text);
  assert.equal(calendar.getFirstPropertyValue("prodid"), otherId);
  assert.equal(calendar.getFirstSubcomponent("vevent").getFirstPropertyValue("summary"), "Library closed");
  // calendar-link emits these values without the explicit VALUE=DATE parameter.
  assert.ok(text.includes("\r\nDTSTART:20270112\r\nDTEND:20270113\r\n"));
  assert.ok(text.includes("\r\nX-MICROSOFT-CDO-ALLDAYEVENT:TRUE\r\n"));
});

test("escapes TEXT punctuation and folds a long UTF-8 product ID without losing characters", () => {
  const href = ics(timedEvent);
  const unicodeId = `-//${"資料🗓️".repeat(10)}, East; West\\Tools//Schedule//EN`;
  const next = calendarText(withCalendarProductId(href, unicodeId));
  const calendar = parseCalendar(next);
  assert.equal(calendar.getFirstPropertyValue("prodid"), unicodeId);
  const headerLines = next.split("\r\nBEGIN:VEVENT\r\n")[0].split("\r\n").slice(2);
  assert.ok(headerLines.length > 1);
  assert.ok(headerLines.slice(1).every((line) => line.startsWith(" ")));
  assert.ok(headerLines.every((line) => Buffer.byteLength(line) <= 75));
  assert.match(headerLines.join(""), /\\,/);
  assert.match(headerLines.join(""), /\\;/);
  assert.match(headerLines.join(""), /\\\\/);
  const afterFold = withCalendarProductId(withCalendarProductId(href, unicodeId), productId);
  assert.equal(
    calendarText(afterFold),
    calendarText(href).replace(
      `\r\nPRODID:${originalProductId}\r\n`,
      `\r\nPRODID:${productId}\r\n`,
    ),
  );
});

test("rejects empty IDs and raw line breaks before making a replacement", () => {
  const href = ics(timedEvent);
  for (const invalidId of ["", "   ", "example\r\nX-WRONG:yes", "example\nrest", "example\rrest"]) {
    assert.throws(() => withCalendarProductId(href, invalidId), /product ID/i);
  }
});

test("rejects a different URL and an unexpected calendar header", () => {
  assert.throws(() => withCalendarProductId("https://example.com/calendar.ics", productId), /data URL/i);
  const malformedHref = "data:text/calendar;charset=utf8," + encodeURIComponent(
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n",
  );
  assert.throws(() => withCalendarProductId(malformedHref, productId), /PRODID/);
  const duplicateHref = "data:text/calendar;charset=utf8," + encodeURIComponent(
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:first\r\nPRODID:second\r\nBEGIN:VEVENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n",
  );
  assert.throws(() => withCalendarProductId(duplicateHref, productId), /PRODID/);
});
