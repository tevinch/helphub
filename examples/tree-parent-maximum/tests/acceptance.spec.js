import { test, expect } from '@playwright/test';

const tree = page => page.getByRole('tree', { name: 'Project files' });
const panel = page => page.getByRole('region', { name: 'Bounded files panel' });
const frames = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
async function visibleActive(page, expected) {
  await frames(page);
  const result = await tree(page).evaluate(el => {
    const active = el.ownerDocument.getElementById(el.getAttribute('aria-activedescendant'));
    const panel = el.closest('[aria-label="Bounded files panel"]');
    const a = active?.getBoundingClientRect(), p = panel.getBoundingClientRect();
    return { text: active?.textContent, visible: !!a && a.top >= p.top + panel.clientTop - 1 && a.bottom <= p.top + panel.clientTop + panel.clientHeight + 1 };
  });
  if (expected) expect(result.text).toContain(expected);
  expect(result.visible, JSON.stringify(result)).toBe(true);
}
async function stableOutside(page) {
  return page.evaluate(() => ({ page: window.scrollY, other: document.querySelector('#other-panel').scrollTop, sentinel: document.querySelector('#sentinel').getBoundingClientRect().top }));
}

test('pointer workflow preserves the same 100 nodes, selection and parent maximum', async ({ page }) => {
  await page.goto('/');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(1);
  expect(await panel(page).evaluate(el => el.clientHeight)).toBeLessThan(400);
  const outside = await stableOutside(page);
  await page.getByRole('button', { name: 'Expand all' }).click();
  await expect(tree(page).getByRole('treeitem')).toHaveCount(100);
  expect(await panel(page).evaluate(el => ({ max: getComputedStyle(el).maxHeight, height: el.clientHeight, overflows: el.scrollHeight > el.clientHeight }))).toEqual({ max: '400px', height: 400, overflows: true });
  await panel(page).evaluate(el => { el.scrollTop = el.scrollHeight; });
  await tree(page).getByText('File 099', { exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  await expect(tree(page).getByRole('treeitem', { selected: true })).toContainText('File 099');
  await page.getByRole('button', { name: 'Collapse all' }).click();
  await expect(tree(page).getByRole('treeitem')).toHaveCount(1);
  await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  await page.getByRole('button', { name: 'Expand all' }).click();
  for (const max of [180, 400]) {
    await page.getByRole('button', { name: `Maximum ${max}px` }).click();
    expect(await panel(page).evaluate(el => el.clientHeight)).toBe(max);
    await expect(tree(page).getByRole('treeitem')).toHaveCount(100);
    await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
    await panel(page).evaluate(el => { el.scrollTop = el.scrollHeight; });
    await tree(page).getByText('File 097', { exact: true }).click();
    await expect(page.getByRole('status')).toHaveText('Selected key: file-097');
    await tree(page).getByText('File 099', { exact: true }).click();
    await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  }
  const disabled = tree(page).getByRole('treeitem').filter({ hasText: 'File 098 (disabled)' });
  await expect(disabled).toHaveAttribute('aria-disabled', 'true');
  await disabled.getByText('File 098 (disabled)', { exact: true }).click({ force: true });
  await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  const longTitle = tree(page).getByText('File 050 — configuration for the shared internationalization resources and development documentation', { exact: true });
  await longTitle.scrollIntoViewIfNeeded();
  expect(await longTitle.evaluate(el => { const p = el.closest('[aria-label="Bounded files panel"]'); return el.getBoundingClientRect().right <= p.getBoundingClientRect().right && el.getBoundingClientRect().width > 0; })).toBe(true);
  expect(await stableOutside(page)).toEqual(outside);
  await expect(page.getByRole('tree', { name: 'Reference files' }).getByText('Reference leaf', { exact: true })).toBeVisible();
});

test('native keyboard interaction reveals the active item and continues after resize', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Expand all' }).click();
  const outside = await stableOutside(page);
  await tree(page).focus();
  await tree(page).press('End');
  await visibleActive(page, 'File 099');
  await tree(page).press('Enter');
  await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  await expect(tree(page).getByRole('treeitem', { selected: true })).toContainText('File 099');
  await tree(page).press('ArrowUp');
  await visibleActive(page, 'File 098 (disabled)');
  await tree(page).press('Enter');
  await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  await tree(page).press('Home');
  await visibleActive(page, 'Project');
  await tree(page).press('ArrowLeft');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(1);
  await tree(page).press('ArrowRight');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(100);
  await tree(page).press('ArrowDown');
  await visibleActive(page, 'Group 01');
  await tree(page).press('ArrowLeft');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(92);
  await tree(page).press('ArrowRight');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(100);
  await page.getByRole('button', { name: 'Expand all' }).click();
  await tree(page).focus();
  await tree(page).press('Home');
  for (let i = 0; i < 99; i++) { await tree(page).press('ArrowDown'); await visibleActive(page); }
  await visibleActive(page, 'File 099');
  for (let i = 0; i < 99; i++) { await tree(page).press('ArrowUp'); await visibleActive(page); }
  await visibleActive(page, 'Project');
  for (const max of [180, 400]) {
    await page.getByRole('button', { name: `Maximum ${max}px` }).click();
    await tree(page).focus();
    await tree(page).press('End');
    await visibleActive(page, 'File 099');
    await tree(page).press('Enter');
    await expect(page.getByRole('status')).toHaveText('Selected key: file-099');
  }
  expect(await stableOutside(page)).toEqual(outside);
});

test('initial selected focus reveals offscreen item; focus-away cancels queued scrolling', async ({ page }) => {
  await page.goto('/?selected=file-099&expanded=all');
  await expect(tree(page).getByRole('treeitem')).toHaveCount(100);
  expect(await panel(page).evaluate(el => el.scrollTop)).toBe(0);
  await tree(page).focus();
  await visibleActive(page, 'File 099');
  await tree(page).press('Home');
  await visibleActive(page, 'Project');
  const outside = await stableOutside(page);
  const before = await panel(page).evaluate(el => el.scrollTop);
  // Both events happen before a queued animation frame can run.
  const activeBeforeBlur = await tree(page).evaluate(async el => {
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', code: 'End', keyCode: 35, which: 35, bubbles: true }));
    // Let React commit the native key update without yielding to a frame.
    await Promise.resolve();
    const active = el.ownerDocument.getElementById(el.getAttribute('aria-activedescendant'));
    const text = active?.textContent;
    document.querySelector('#focus-away').focus({ preventScroll: true });
    return text;
  });
  expect(activeBeforeBlur).toBe('File 099');
  await frames(page);
  expect(await panel(page).evaluate(el => el.scrollTop)).toBe(before);
  expect(await stableOutside(page)).toEqual(outside);
  await expect(page.getByRole('button', { name: 'Outside focus' })).toBeFocused();
  await tree(page).focus();
  await visibleActive(page, 'File 099');
  await tree(page).press('Home');
  await visibleActive(page, 'Project');
});
