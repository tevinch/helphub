import test from 'node:test';
import assert from 'node:assert/strict';
import { validateRange, localStamp } from './range.mjs';

test('each local endpoint retains its own date and time', () => {
  assert.equal(localStamp(new Date(2026, 10, 3, 10, 30)), '2026-11-03T10:30');
  assert.equal(localStamp(new Date(2026, 10, 4, 8)), '2026-11-04T08:00');
});
test('both endpoints are required and invalid Date is rejected', () => {
  assert.equal(validateRange(null, new Date()), 'Choose a start and an end.');
  assert.equal(validateRange(new Date(), null), 'Choose a start and an end.');
  assert.equal(validateRange(new Date('bad'), new Date()), 'Choose a start and an end.');
});
test('ordering uses the full instant, including same-day times', () => {
  const start = new Date(2026, 10, 3, 10, 30);
  assert.equal(validateRange(start, new Date(2026, 10, 3, 10)), 'End must be after start.');
  assert.equal(validateRange(start, new Date(start)), 'End must be after start.');
  assert.equal(validateRange(start, new Date(2026, 10, 3, 16)), '');
  assert.equal(validateRange(start, new Date(2026, 10, 4, 8)), '');
});
