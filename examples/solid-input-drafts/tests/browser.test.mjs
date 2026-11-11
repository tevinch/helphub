import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';

let browser;
let server;
let origin;
before(async () => {
  server = spawn(process.execPath, ['server.mjs'], {
    env: { ...process.env, PORT: '0' }, stdio: ['ignore', 'pipe', 'inherit'],
  });
  origin = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Server did not start')), 8000);
    server.on('error', reject);
    server.stdout.on('data', data => {
      const match = data.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timeout); resolve(match[0]); }
    });
  });
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}),
  });
  console.log(`Browser ${browser.version()}; Node ${process.version}`);
});
after(async () => {
  await browser?.close();
  if (server && server.exitCode === null) {
    server.kill();
    await new Promise(resolve => server.once('exit', resolve));
  }
});

async function withPage(run) {
  const context = await browser.newContext({ viewport: { width: 860, height: 1000 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === origin
    ? route.continue() : route.abort());
  try {
    await page.goto(origin);
    await run(page);
    assert.deepEqual(errors, [], 'No browser exceptions');
  } finally { await context.close(); }
}

// Real editing, rather than writing input.value without an input event.
async function typeValue(input, value) {
  await input.click();
  await input.press('ControlOrMeta+A');
  await input.press('Backspace');
  if (value) await input.pressSequentially(value);
}
async function toggle(page, disabled) {
  await page.getByRole('button', { name: 'Toggle draft disabled', exact: true }).click();
  assert.equal(await page.locator('#draft').isDisabled(), disabled);
}

test('original four variants: only two reactive properties together reset the edited DOM value', async () => withPage(async page => {
  for (const [id, value] of [['one', '21'], ['two', '22'], ['three', '23'], ['four', '24']]) {
    await typeValue(page.locator(`#${id}`), value);
  }
  assert.equal(await page.locator('#original-state').textContent(), '11', 'Typing alone never wrote to the original signal');
  await page.getByRole('button', { name: 'CLICK ME', exact: true }).click();
  assert.deepEqual(await page.locator('#original input').evaluateAll(inputs => inputs.map(e => e.disabled)), [true, true, true, true]);
  assert.deepEqual(await page.locator('#original input').evaluateAll(inputs => inputs.map(e => e.value)), ['11', '22', '23', '24']);
  await page.getByRole('button', { name: 'CLICK ME', exact: true }).click();
  assert.deepEqual(await page.locator('#original input').evaluateAll(inputs => inputs.map(e => e.disabled)), [false, false, false, false]);
  assert.deepEqual(await page.locator('#original input').evaluateAll(inputs => inputs.map(e => e.value)), ['11', '22', '23', '24']);
}));

// Removing the event-to-signal writeback breaks this workflow.
test('typed draft survives repeated real disable/enable cycles, then continued editing and submit', async () => withPage(async page => {
  const draft = page.locator('#draft');
  await typeValue(draft, '21');
  // This retention assertion must fail against the missing-writeback baseline.
  await toggle(page, true);
  assert.equal(await draft.inputValue(), '21', 'Disabling must retain the current typed draft');
  assert.equal(await page.locator('#draft-state').textContent(), '"21"', 'Signal state independently contains the edit');
  await toggle(page, false);
  for (const value of ['32', '43', '-7.5']) {
    await typeValue(draft, value);
    assert.equal(await page.locator('#draft-state').textContent(), JSON.stringify(value));
    await toggle(page, true);
    assert.equal(await draft.inputValue(), value);
    await toggle(page, false);
    assert.equal(await draft.inputValue(), value);
  }
  await typeValue(draft, '54');
  await page.getByRole('button', { name: 'Read submitted value', exact: true }).click();
  assert.equal(await page.locator('#submitted').textContent(), '"54"', 'FormData receives the final continued edit');
  assert.equal(await page.locator('#original-state').textContent(), '11', 'The usable example owns separate state');
}));

test('empty number draft stays empty through toggles and can be edited and submitted again', async () => withPage(async page => {
  const draft = page.locator('#draft');
  await page.evaluate(() => {
    window.observedInputs = 0;
    document.addEventListener('input', event => {
      if (event.target.id === 'draft') window.observedInputs++;
    });
  });
  await typeValue(draft, '');
  assert.ok(await page.evaluate(() => window.observedInputs > 0), 'Independent native input-event observer was reached');
  assert.equal(await page.locator('#draft-state').textContent(), '""', 'The signal received the actual empty edit');
  for (let cycle = 0; cycle < 3; cycle++) {
    await toggle(page, true);
    assert.equal(await draft.inputValue(), '');
    await toggle(page, false);
    assert.equal(await draft.inputValue(), '');
  }
  await page.getByRole('button', { name: 'Read submitted value', exact: true }).click();
  assert.equal(await page.locator('#submitted').textContent(), '""');
  await typeValue(draft, '65');
  await page.getByRole('button', { name: 'Read submitted value', exact: true }).click();
  assert.equal(await page.locator('#submitted').textContent(), '"65"');
}));

test('programmatic signal update reaches the disabled DOM input and remains after re-enabling', async () => withPage(async page => {
  await toggle(page, true);
  await page.getByRole('button', { name: 'Set draft to 42', exact: true }).click();
  assert.equal(await page.locator('#draft-state').textContent(), '"42"');
  assert.equal(await page.locator('#draft').inputValue(), '42');
  await toggle(page, false);
  await typeValue(page.locator('#draft'), '73');
  await page.getByRole('button', { name: 'Read submitted value', exact: true }).click();
  assert.equal(await page.locator('#submitted').textContent(), '"73"');
}));
