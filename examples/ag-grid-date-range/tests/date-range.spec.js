import { expect, test } from '@playwright/test';

test('rejects reversed dates and applies corrections in the same filter', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.clock.setFixedTime(new Date(2026, 10, 15, 12));
  await page.addInitScript(() => {
    window.reportedInvalid = [];
    document.addEventListener('invalid', event => {
      window.reportedInvalid.push(event.target.value);
    }, true);
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open date filter' }).click();

  const fields = page.locator('input[data-input]:visible');
  const from = fields.nth(0);
  const to = fields.nth(1);
  const visibleNames = page.getByRole('gridcell').filter({ hasText: /^(Early|Middle|Late|Last)$/ });
  const model = page.getByRole('status');
  const expectVisibleNames = names => expect.poll(async () => (await visibleNames.allTextContents()).sort()).toEqual([...names].sort());
  const pick = async (input, day) => {
    await input.click();
    await page.locator(`.flatpickr-calendar.open .flatpickr-day[aria-label="November ${day}, 2026"]`).click();
    await expect(input).toHaveValue(`${String(day).padStart(2, '0')}/11/2026`);
  };
  const expectRange = async (fromDay, toDay, names) => {
    await expect(model).toContainText(`2026-11-${String(fromDay).padStart(2, '0')}`);
    await expect(model).toContainText(`2026-11-${String(toDay).padStart(2, '0')}`);
    await expectVisibleNames(names);
  };

  await expect(fields).toHaveCount(2);
  await expect(from).toHaveAttribute('placeholder', 'dd/mm/yyyy');
  await expect(to).toHaveAttribute('placeholder', 'dd/mm/yyyy');
  await expectVisibleNames(['Early', 'Middle', 'Late', 'Last']);
  await pick(from, 12);
  await pick(to, 24);
  await expectRange(12, 24, ['Middle', 'Late']);
  const originalModel = await model.textContent();

  await pick(to, 8);
  await expect(to).toHaveAttribute('aria-invalid', 'true');
  await expect(from).not.toHaveAttribute('aria-invalid', 'true');
  expect(await to.evaluate(input => input.validity.customError)).toBe(true);
  expect(await to.evaluate(input => input.validationMessage.length)).toBeGreaterThan(0);
  await expect(to).toHaveCSS('outline-color', 'rgb(180, 35, 24)');
  await expect(to).toHaveCSS('outline-style', 'solid');
  await expect.poll(() => page.evaluate(() => window.reportedInvalid)).toContain('08/11/2026');
  await expect(model).toHaveText(originalModel);
  await expectVisibleNames(['Middle', 'Late']);

  await from.focus();
  await expect(from).toHaveAttribute('aria-invalid', 'true');
  await expect(to).not.toHaveAttribute('aria-invalid', 'true');
  await to.focus();
  await expect(to).toHaveAttribute('aria-invalid', 'true');

  await pick(to, 14);
  await expect(to).not.toHaveAttribute('aria-invalid', 'true');
  expect(await to.evaluate(input => input.validity.customError)).toBe(false);
  await expectRange(12, 14, ['Middle']);
  const correctedModel = await model.textContent();

  await pick(from, 20);
  await expect(from).toHaveAttribute('aria-invalid', 'true');
  await expect(to).not.toHaveAttribute('aria-invalid', 'true');
  expect(await from.evaluate(input => input.validity.customError)).toBe(true);
  await expect(model).toHaveText(correctedModel);
  await expectVisibleNames(['Middle']);

  await pick(from, 14);
  await expect(from).not.toHaveAttribute('aria-invalid', 'true');
  await expectRange(14, 14, ['Middle']);
  await expect(model).not.toContainText('2026-11-12');

  await page.getByRole('button', { name: 'Clear date' }).nth(0).click();
  await expect(from).toHaveValue('');
  await expect(model).toHaveText('No date filter');
  await expectVisibleNames(['Early', 'Middle', 'Late', 'Last']);
  await pick(to, 27);
  await pick(from, 21);
  await expectRange(21, 27, ['Late', 'Last']);
  expect(errors).toEqual([]);
});
