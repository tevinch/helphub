const calendarPrefix = "data:text/calendar;charset=utf8,";
const calendarHeader = /^(BEGIN:VCALENDAR\r\nVERSION:2\.0\r\n)PRODID:[^\r\n]*(?:\r\n[ \t][^\r\n]*)*\r\n(?=BEGIN:VEVENT\r\n)/u;
const encoder = new TextEncoder();

function foldContentLine(text) {
  const lines = [];
  let line = "";
  let lineBytes = 0;

  for (const character of text) {
    const characterBytes = encoder.encode(character).length;
    if (lineBytes + characterBytes > 75) {
      lines.push(line);
      line = " ";
      lineBytes = 1;
    }
    line += character;
    lineBytes += characterBytes;
  }

  lines.push(line);
  return lines.join("\r\n");
}

export function withCalendarProductId(calendarHref, productId) {
  if (!calendarHref.startsWith(calendarPrefix)) {
    throw new TypeError("Expected the calendar data URL returned by calendar-link ics().");
  }

  if (!productId.trim() || /[\u0000-\u001f\u007f]/u.test(productId)) {
    throw new TypeError("The product ID must be a non-empty line without control characters.");
  }

  const calendar = decodeURIComponent(calendarHref.slice(calendarPrefix.length));
  const header = calendarHeader.exec(calendar);
  if (!header) {
    throw new Error("Expected the calendar-link PRODID in the VCALENDAR header.");
  }

  const escapedId = productId.replace(/[\\,;]/gu, (character) => "\\" + character);
  const productLine = foldContentLine(`PRODID:${escapedId}`);
  const updated = header[1] + productLine + "\r\n" + calendar.slice(header[0].length);
  return calendarPrefix + encodeURIComponent(updated);
}
