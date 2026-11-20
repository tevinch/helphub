import { writeFile } from "node:fs/promises";
import { ics } from "calendar-link";
import { withCalendarProductId } from "./calendar-product-id.mjs";

const event = {
  title: "Planning session",
  start: "2027-01-11T09:00:00Z",
  end: "2027-01-11T09:30:00Z",
  uid: "planning-2027-01-11@example.com",
  rRule: "FREQ=WEEKLY;COUNT=3",
};

const href = withCalendarProductId(ics(event), "-//Field Notes//Schedule Export//EN");
const response = await fetch(href);
const outputPath = process.argv[2] ?? "example.ics";

await writeFile(outputPath, new Uint8Array(await response.arrayBuffer()));
console.log(`Wrote ${outputPath}`);
