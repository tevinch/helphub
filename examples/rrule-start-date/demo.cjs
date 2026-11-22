const { fromTextWithStart } = require("./recurrence.cjs");

const input = "every Monday starts on 2026-12-14 until 2027-01-04";
const rule = fromTextWithStart(input);

console.log(input);
console.log(rule.toString());
for (const occurrence of rule.all()) {
  console.log(occurrence.toISOString().slice(0, 10));
}
