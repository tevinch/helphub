import { test, expect } from '@playwright/test';

// This catches an incompatible reconciler or a missed render/update/remount:
// the expected paths, color, geometry and text must change in the real DOM.
test('renders, updates repeatedly, remounts and unmounts rough SVG on React 19', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  await page.goto('/');
  const svg = page.getByRole('img', { name: 'Editable rough shapes' });
  await expect(svg).toBeVisible();
  const blue = svg.locator('path[stroke="#2563eb"]');
  await expect(blue).toHaveCount(1);
  const originalPath = await blue.getAttribute('d');
  await expect(svg.locator('text')).toHaveText('Small blue circle');

  await page.getByRole('button', { name: 'Change circle' }).click();
  const orange = svg.locator('path[stroke="#c2410c"]');
  await expect(orange).toHaveCount(1);
  await expect(orange).not.toHaveAttribute('d', originalPath);
  await expect(svg.locator('text')).toHaveText('Large orange circle');

  await page.getByRole('button', { name: 'Change circle' }).click();
  await expect(blue).toHaveCount(1);
  await expect(blue).toHaveAttribute('d', originalPath);
  await expect(svg.locator('text')).toHaveText('Small blue circle');

  await page.getByRole('button', { name: 'Add rectangle' }).click();
  await expect(svg.locator('path[stroke="#15803d"]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Remove rectangle' }).click();
  await expect(svg.locator('path[stroke="#15803d"]')).toHaveCount(0);

  await page.getByRole('button', { name: 'Hide drawing' }).click();
  await expect(svg).toHaveCount(0);
  await page.getByRole('button', { name: 'Show drawing' }).click();
  await expect(svg).toBeVisible();
  await expect(blue).toHaveCount(1);
  await expect(svg.locator('text')).toHaveText('Small blue circle');

  await page.screenshot({ path: 'test-results/rough-svg.png' });
  await page.getByRole('button', { name: 'Unmount example' }).click();
  await expect(page.locator('#root')).toBeEmpty();
  expect(errors).toEqual([]);
});
