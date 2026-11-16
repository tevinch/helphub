import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const target = process.argv[2];
assert(target, 'Pass the URL of the component check page.');

const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(target, { waitUntil: 'networkidle' });

    const control = page.getByRole('switch', { name: 'Notifications' });
    const draft = page.getByRole('textbox', { name: 'Draft' });
    const status = page.getByRole('status');
    await control.waitFor();
    assert.equal(await control.getAttribute('aria-checked'), 'false');
    assert.equal(await draft.inputValue(), 'Existing page content');

    await draft.fill('Keep this draft while using the switch');
    await control.click();
    assert.equal(await control.getAttribute('aria-checked'), 'true');
    assert.equal(await status.textContent(), 'Notifications: on');
    await page.getByRole('button', { name: 'Reset switch' }).click();
    assert.equal(await control.getAttribute('aria-checked'), 'false');
    assert.equal(await draft.inputValue(), 'Keep this draft while using the switch');

    await control.focus();
    await page.keyboard.press('Space');
    assert.equal(await control.getAttribute('aria-checked'), 'true');
    await control.click();
    assert.equal(await control.getAttribute('aria-checked'), 'false');
    assert.equal(await draft.inputValue(), 'Keep this draft while using the switch');
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({
        browser: await browser.version(),
        rendered: true,
        pointerToggle: true,
        reset: true,
        keyboardToggle: true,
        continuedInteraction: true,
        draftPreserved: true,
        pageErrors: errors,
    }, null, 2));
} finally {
    await browser.close();
}
