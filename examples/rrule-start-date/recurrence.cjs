const { RRule } = require("rrule");

const dateFormat = /^[1-9]\d{3}-\d{2}-\d{2}$/;
const dateAndEnding = /^(\S+)(?:\s+((?:(?:un)?til|for)\s+\S.*))?$/is;
const endingInPattern = /\b(?:(?:un)?til|for)\s/i;
const isoUntilClause = /\s+(?:un)?til\s+(\d{4}-\d{2}-\d{2})$/i;

function parseCalendarDate(value, label) {
  if (typeof value !== "string" || !dateFormat.test(value)) {
    throw new SyntaxError(`Enter a ${label} date in YYYY-MM-DD format.`);
  }
  const date = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value) {
    throw new RangeError(`The ${label} date must be a valid calendar date.`);
  }
  return date;
}

function fromTextWithStart(text, separateStartDate) {
  let pattern = text.trim();
  let startDate = separateStartDate;
  const parts = pattern.split(/\bstarts\s+on\b/i);

  if (parts.length > 2 || (parts.length === 2 && separateStartDate !== undefined)) {
    throw new SyntaxError("Provide only one start date.");
  }

  if (parts.length === 2) {
    const prefix = parts[0].trim();
    const match = dateAndEnding.exec(parts[1].trim());
    if (!prefix || !match) {
      throw new SyntaxError("Put starts on YYYY-MM-DD after the recurrence pattern.");
    }
    const [, date, ending] = match;
    if (ending && endingInPattern.test(prefix)) {
      throw new SyntaxError("Provide only one end clause.");
    }
    pattern = ending ? `${prefix} ${ending}` : prefix;
    startDate = date;
  }

  const dtstart = parseCalendarDate(startDate, "start");
  const isoUntil = isoUntilClause.exec(pattern);
  if (isoUntil) {
    pattern = pattern.slice(0, isoUntil.index);
    if (endingInPattern.test(pattern)) {
      throw new SyntaxError("Provide only one end clause.");
    }
  }
  const options = RRule.parseText(pattern);
  if (!options) {
    throw new SyntaxError("Enter an English recurrence pattern, such as every Monday.");
  }
  if (isoUntil) {
    // Treat an ISO date-only bound as UTC in both the start and end clauses.
    options.until = parseCalendarDate(isoUntil[1], "end");
  }
  return new RRule({ ...options, dtstart });
}

module.exports = { fromTextWithStart };
