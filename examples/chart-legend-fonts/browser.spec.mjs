import { test, expect } from '@playwright/test';
const inspect = page => page.evaluate(() => {
  const c = Chart.getChart(document.getElementById('chart'));
  return { visible: [c.isDatasetVisible(0), c.isDatasetVisible(1)],
    data: c.data.datasets.map(d => [...d.data]), rendered: [c.getDatasetMeta(0).data.length, c.getDatasetMeta(1).data.length] };
});
test('canvas item font fields are ignored by the actual canvas legend', async ({ page }) => {
  await page.addInitScript(() => {
    window.legendTextCalls = [];
    const native = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function(text, ...args) {
      if (text === 'Number 1' || text === 'Number 2') window.legendTextCalls.push({ text, font: this.font, color: this.fillStyle });
      return native.call(this, text, ...args);
    };
  });
  await page.goto('/canvas-control.html');
  await expect.poll(() => page.evaluate(() => legendTextCalls.length)).toBeGreaterThanOrEqual(2);
  const calls = await page.evaluate(() => legendTextCalls);
  const first = calls.find(c => c.text === 'Number 1');
  const second = calls.find(c => c.text === 'Number 2');
  expect(first.font).toBe(second.font);
  expect(first.color).not.toBe(second.color);
  expect((await inspect(page)).rendered).toEqual([6, 6]);
});
test('per-label fonts retain native pointer and keyboard visibility behavior across updates', async ({ page }) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  const first = page.getByRole('button', { name: 'Number 1', exact: true });
  const second = page.getByRole('button', { name: 'Number 2', exact: true });
  await expect(first).toHaveCount(1); await expect(second).toHaveCount(1);
  await expect(first).toHaveCSS('font-size', '20px'); await expect(first).toHaveCSS('font-style', 'italic');
  await expect(first).toHaveCSS('font-weight', '700'); await expect(first).toHaveCSS('font-family', 'Arial, sans-serif');
  await expect(second).toHaveCSS('font-size', '12px'); await expect(second).toHaveCSS('font-family', 'Georgia, serif');
  const initial = await inspect(page); expect(initial.rendered).toEqual([6, 6]);
  await first.click(); await expect(first).toHaveAttribute('aria-pressed', 'false');
  expect((await inspect(page)).visible).toEqual([false, true]);
  await expect(first).toHaveCSS('text-decoration-line', 'line-through');
  await page.getByRole('button', { name: 'Update data' }).click();
  const changed = await inspect(page); expect(changed.visible).toEqual([false, true]);
  expect(changed.data).toEqual(initial.data.map(row => row.map(v => v + 1)));
  await first.click(); expect((await inspect(page)).visible).toEqual([true, true]);
  await second.focus(); await second.press('Space'); await expect(second).toBeFocused();
  await expect(second).toHaveAttribute('aria-pressed', 'false'); expect((await inspect(page)).visible).toEqual([true, false]);
  await second.press('Enter'); await expect(second).toHaveAttribute('aria-pressed', 'true');
  expect((await inspect(page)).visible).toEqual([true, true]);
  await first.click(); await first.click(); expect((await inspect(page)).visible).toEqual([true, true]);
  expect((await inspect(page)).data).toEqual(changed.data);
  await expect(first).toHaveCSS('font-size', '20px'); await expect(second).toHaveCSS('font-size', '12px');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => Chart.getChart(document.getElementById('chart')).destroy());
  await expect(page.locator('#legend .legend-list')).toHaveCount(0);
  await expect(page.locator('#legend-note')).toHaveText('Both datasets contain six points.');
  expect(errors).toEqual([]);
});
