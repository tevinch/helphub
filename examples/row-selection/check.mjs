import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = process.argv[2] ? path.resolve(process.argv[2]) : fileURLToPath(new URL('.', import.meta.url));
const server = await createServer({ root, server: { host: '127.0.0.1', port: 0 }, logLevel: 'error' });
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
  const page = await browser.newPage({ viewport: { width: 1100, height: 850 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}`);
  await page.locator('#selection-state').waitFor();
  const original = await page.locator('#source-data').textContent();
  const canvas = page.locator('canvas').first();
  const nativeModifier = await page.evaluate(() => /Mac/.test(navigator.platform) ? 'Meta' : 'Control');
  let operations = 0;

  async function read() {
    return JSON.parse(await page.locator('#selection-state').textContent());
  }
  async function expect(rows, columns = [], clearCurrent = false) {
    const actual = await read();
    assert.deepEqual(actual.rows, rows, `Selected rows after operation ${operations}`);
    assert.deepEqual(actual.columns, columns, `Selected columns after operation ${operations}`);
    if (clearCurrent) assert.equal(actual.current, null, `No stale cell rectangle after operation ${operations}`);
    assert.equal(await page.locator('#source-data').textContent(), original, 'Selection must preserve every source value');
    assert.deepEqual(errors, [], 'No uncaught application error');
  }
  async function point(col, row) {
    const box = await canvas.boundingBox();
    assert.ok(box, 'The actual grid canvas must be visible');
    return { x: box.x + (col < 0 ? 22 : 44 + col * 200 + 100), y: box.y + (row < 0 ? 18 : 36 + row * 34 + 17) };
  }
  async function click(col, row, modifiers = []) {
    const p = await point(col, row);
    for (const key of modifiers) await page.keyboard.down(key);
    await page.mouse.click(p.x, p.y);
    for (const key of [...modifiers].reverse()) await page.keyboard.up(key);
    operations++;
  }

  await expect([], [], true);
  await click(0, 1); await expect([1]);
  await click(0, 1, ['Control']); await expect([], [], true);
  await click(0, 1, ['Control']); await expect([1], [], true);
  await click(1, 4, ['Control']); await expect([1, 4], [], true);
  await click(0, 1, ['Control']); await expect([4], [], true);
  await click(1, 6, ['Shift']); await expect([1, 2, 3, 4, 5, 6]);
  assert.deepEqual((await read()).current.range, { x: 0, y: 1, width: 2, height: 6 });
  await click(0, 0, ['Control', 'Shift']); await expect([0, 1, 2, 3, 4, 5, 6]);
  await click(1, 3, ['Meta']); await expect([0, 1, 2, 4, 5, 6], [], true);
  await click(1, 3, ['Meta']); await expect([0, 1, 2, 3, 4, 5, 6], [], true);
  await click(0, 0); await expect([0]);
  const start = await point(0, 0); const end = await point(1, 3);
  await page.mouse.move(start.x, start.y); await page.mouse.down();
  await page.mouse.move(end.x, end.y, { steps: 12 }); await page.mouse.up(); operations++;
  await expect([0, 1, 2, 3]);
  assert.deepEqual((await read()).current.range, { x: 0, y: 0, width: 2, height: 4 }, 'Native drag geometry must remain');
  const secondStart = await point(0, 5); const secondEnd = await point(1, 6);
  await page.keyboard.down(nativeModifier);
  await page.mouse.move(secondStart.x, secondStart.y); await page.mouse.down();
  await page.mouse.move(secondEnd.x, secondEnd.y, { steps: 10 }); await page.mouse.up();
  await page.keyboard.up(nativeModifier); operations++;
  await expect([0, 1, 2, 3, 5, 6]);
  assert.deepEqual((await read()).current.rangeStack, [{ x: 0, y: 0, width: 2, height: 4 }], 'Existing disjoint native range must remain');
  await click(0, 2, ['Control']); await expect([0, 1, 3, 5, 6], [], true);
  await click(1, 5, ['Shift']); await expect([2, 3, 4, 5]);
  await click(-1, 6); await expect([6], [], true);
  await click(1, 7); await expect([7]);
  await click(1, 7, ['Control']); await expect([], [], true);
  await click(0, -1); await expect([], [0], true);
  await click(1, -1, [nativeModifier]); await expect([], [0, 1], true);
  await click(0, -1, [nativeModifier]); await expect([], [1], true);
  await click(-1, 6); await expect([6], [], true);
  await click(-1, 4, [nativeModifier]); await expect([4, 6], [], true);
  await click(-1, 6, [nativeModifier]); await expect([4], [], true);
  await page.keyboard.press('Escape'); operations++; await expect([], [], true);
  await click(0, 3); await expect([3]);
  await click(0, 3, ['Control']); await expect([], [], true);
  // Continue from row-only toggles into native additive dragging.
  await click(0, 0); await expect([0]);
  await click(0, 4, [nativeModifier]); await expect([0, 4], [], true);
  await click(0, 5, [nativeModifier, 'Shift']); await expect([0, 4, 5]);
  await page.keyboard.press('Alt+ArrowDown'); operations++; await expect([0, 4, 5]);
  await page.keyboard.press('Alt+ArrowDown'); operations++; await expect([0, 4, 5, 6]);
  await page.keyboard.press('Alt+ArrowUp'); operations++; await expect([0, 4, 5]);
  const continuedStart = await point(0, 6); const continuedEnd = await point(1, 7);
  await page.keyboard.down(nativeModifier);
  await page.mouse.move(continuedStart.x, continuedStart.y); await page.mouse.down();
  await page.mouse.move(continuedEnd.x, continuedEnd.y, { steps: 10 }); await page.mouse.up();
  await page.keyboard.up(nativeModifier); operations++;
  await expect([0, 4, 5, 6, 7]);
  await click(0, 4, [nativeModifier]); await expect([0, 5, 6, 7], [], true);
  const toggledStart = await point(0, 2); const toggledEnd = await point(1, 3);
  await page.keyboard.down(nativeModifier);
  await page.mouse.move(toggledStart.x, toggledStart.y); await page.mouse.down();
  await page.mouse.move(toggledEnd.x, toggledEnd.y, { steps: 10 }); await page.mouse.up();
  await page.keyboard.up(nativeModifier); operations++;
  await expect([0, 2, 3, 5, 6, 7]);
  await page.keyboard.press('Escape'); operations++; await expect([], [], true);
  await click(0, 1); await expect([1]);
  await page.keyboard.press('ArrowDown'); operations++; await expect([2]);
  await page.keyboard.press('Shift+ArrowDown'); operations++; await expect([2, 3]);
  await click(0, 0); await expect([0]);
  await click(0, 4, [nativeModifier]); await expect([0, 4], [], true);
  await click(-1, 6, [nativeModifier]); await expect([0, 4, 6], [], true);
  await click(-1, 0, [nativeModifier]); await expect([4, 6], [], true);
  await click(1, -1); await expect([], [1], true);
  await page.keyboard.press('Escape'); operations++; await expect([], [], true);
  await click(1, 7); await expect([7]);
  await click(0, 2); await expect([2]);
  console.log(`PASS: one complete native browser flow, ${operations} physical operations; Ctrl/Meta toggles, Shift, drag, headers, markers, Escape and all source values verified.`);
} finally {
  await browser?.close();
  await server.close();
}
