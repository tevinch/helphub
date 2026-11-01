import { test, expect } from '@playwright/test';
const times = page => page.locator('.react-datepicker-time__input input[type="time"]');
async function open(page) {
  await page.locator('#range').click();
  await expect(times(page)).toHaveCount(2);
}
async function setTimes(page, start, end) {
  await open(page);
  await times(page).nth(0).fill(start);
  await times(page).nth(1).fill(end);
}
async function pickDay(page, dayLabel) {
  await page.getByRole('gridcell', { name: dayLabel, exact: true }).click();
}
async function submit(page, start, end) {
  await page.getByRole('heading', { level: 1 }).click();
  await page.getByRole('button', { name: 'Use range', exact: true }).click();
  await expect(page.locator('#result')).toContainText(`"start": "${start}"`);
  await expect(page.locator('#result')).toContainText(`"end": "${end}"`);
}
test('independent times survive repeated range selection, validation, clearing and submit', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await setTimes(page, '10:30', '16:00');
  await submit(page, '2026-11-03T10:30', '2026-11-03T16:00');
  await open(page);
  await expect(times(page).nth(0)).toHaveValue('10:30');
  await expect(times(page).nth(1)).toHaveValue('16:00');
  await pickDay(page, 'Choose Wednesday, November 4th, 2026');
  await expect(page.locator('#validation')).toHaveText('Choose a start and an end.');
  await pickDay(page, 'Choose Thursday, November 5th, 2026');
  await setTimes(page, '12:00', '08:00');
  await submit(page, '2026-11-04T12:00', '2026-11-05T08:00');
  await open(page);
  await pickDay(page, 'Choose Friday, November 6th, 2026');
  await pickDay(page, 'Choose Friday, November 6th, 2026');
  await setTimes(page, '10:30', '08:00');
  await expect(page.locator('#validation')).toHaveText('End must be after start.');
  await expect(page.getByRole('button', { name: 'Use range', exact: true })).toBeDisabled();
  await expect(times(page).nth(0)).toHaveValue('10:30');
  await expect(times(page).nth(1)).toHaveValue('08:00');
  await times(page).nth(1).fill('11:00');
  await submit(page, '2026-11-06T10:30', '2026-11-06T11:00');
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.locator('#validation')).toHaveText('Choose a start and an end.');
  await expect(page.getByRole('button', { name: 'Use range', exact: true })).toBeDisabled();
  await open(page);
  await pickDay(page, 'Choose Saturday, November 7th, 2026');
  await pickDay(page, 'Choose Sunday, November 8th, 2026');
  await setTimes(page, '23:00', '01:00');
  await submit(page, '2026-11-07T23:00', '2026-11-08T01:00');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
