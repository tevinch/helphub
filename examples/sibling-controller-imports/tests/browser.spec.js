import { test, expect } from '@playwright/test';

test('sibling controller imports complete repeated actions and survive reload', async ({ page }) => {
  const errors = [];
  const assets = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(request.url()));
  page.on('response', response => {
    if (response.url().includes('/assets/')) assets.push({ url: response.url(), status: response.status() });
  });
  await page.goto('/');
  await expect(page.getByTestId('existing-content')).toHaveText('Existing app content');
  for (let run = 0; run < 2; run++) {
    await expect(page.getByTestId('api-status')).toHaveText('API controller connected');
    await expect(page.getByTestId('grid-status')).toHaveText('Grid controller connected');
    await page.getByRole('button', { name: 'Add API row' }).click();
    await page.getByRole('button', { name: 'Add API row' }).click();
    await expect(page.getByTestId('api-result')).toHaveText('API uses grid: 2 rows');
    await page.getByRole('button', { name: 'Add grid row' }).click();
    await expect(page.getByTestId('grid-result')).toHaveText('Grid: 1 row');
    if (run === 0) await page.reload();
  }
  expect(errors).toEqual([]);
  expect(assets.length).toBeGreaterThan(3);
  expect(assets.every(asset => asset.status === 200)).toBe(true);
  expect(assets.every(asset => new URL(asset.url).origin === 'http://127.0.0.1:8967')).toBe(true);
});
