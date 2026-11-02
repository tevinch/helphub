import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import http from 'node:http';

const original = {
  item: { id: 'sample-item', title: 'Weekly plan', color: 'blue',
    notes: 'Keep this existing note.\nSecond line: café ☕.', extra: { retained: 'Keep this item property.' } },
  settings: { density: 'comfortable', retained: 'Keep this setting.' },
  revision: 0,
};
let browser;
before(async () => {
  browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}),
  });
  console.log(`Browser ${browser.version()}; Node ${process.version}`);
});
after(async () => { await browser?.close(); });

async function app(run, options = {}, initial = original) {
  const directory = await mkdtemp(join(tmpdir(), 'modal-form-'));
  const dataFile = join(directory, 'item.json');
  await writeFile(dataFile, JSON.stringify(initial));
  const server = spawn(process.execPath, ['server.mjs'], {
    env: { ...process.env, PORT: '0', MODAL_FORM_DATA_FILE: dataFile },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const url = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Loopback server did not start')), 8000);
    server.stdout.on('data', data => {
      const match = data.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
    server.on('error', reject);
    server.stderr.on('data', data => process.stderr.write(data));
  });
  const context = await browser.newContext({ viewport: { width: 1000, height: 900 }, ...options });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== url) return route.abort();
    return route.continue();
  });
  try {
    await page.goto(url);
    await run(page, async () => JSON.parse(await readFile(dataFile, 'utf8')), url);
    assert.deepEqual(errors, [], 'No browser exceptions');
  } finally {
    await context.close();
    server.kill();
    await new Promise(resolve => server.once('exit', resolve));
    await rm(directory, { recursive: true, force: true });
  }
}

async function until(check, message) {
  for (let i = 0; i < 100; i++) {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.fail(message);
}
async function open(page) {
  await page.getByRole('button', { name: 'Edit item', exact: true }).click({ timeout: 2000 });
  await page.getByLabel('Title', { exact: true }).waitFor();
  await until(() => page.getByLabel('Title', { exact: true }).evaluate(e => e === document.activeElement), 'Native opening focus lands on title');
}
async function formState(page) {
  return page.locator('form').evaluate(form => ({
    values: [...new FormData(form)],
    errors: [...form.querySelectorAll('[data-field-error]')].map(e => e.textContent),
    boxes: [...form.querySelectorAll('[data-layout]')].map(e => {
      const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height];
    }),
  }));
}
function sameLayout(actual, expected) {
  actual.forEach((box, i) => box.forEach((v, j) => assert.ok(Math.abs(v - expected[i][j]) < 0.6, 'Field geometry stays fixed')));
}
async function exit(page, mechanism) {
  if (mechanism === 'Escape') await page.keyboard.press('Escape');
  else if (mechanism === 'backdrop') await page.mouse.click(20, 20);
  else await page.getByRole('button', { name: mechanism, exact: true }).click();
}
async function verifyExit(page, mechanism, read, visibleError = false, fromRadio = false) {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('x');
  if (visibleError) {
    await page.keyboard.press('Tab');
    await until(async () => (await page.locator('#title-error').innerText()).includes('3'), 'Normal blur must show error');
    await page.getByLabel('Title', { exact: true }).focus();
  }
  if (fromRadio) await page.getByRole('radio', { name: 'Red', exact: true }).click();
  const before = await formState(page);
  await page.evaluate(() => {
    window.exitFrames = [];
    const frame = () => {
      const form = document.querySelector('form');
      if (!form) return;
      window.exitFrames.push({ state: document.querySelector('[role="dialog"]').dataset.state,
        values: [...new FormData(form)],
        errors: [...form.querySelectorAll('[data-field-error]')].map(e => e.textContent),
        boxes: [...form.querySelectorAll('[data-layout]')].map(e => {
          const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height];
        }),
      });
      requestAnimationFrame(frame);
    };
    frame();
  });
  await exit(page, mechanism);
  if (await page.locator('[role="dialog"][data-state="closed"]').count()) {
    const during = await formState(page);
    assert.deepEqual(during.values, before.values, 'Exit must retain current draft');
    assert.deepEqual(during.errors, before.errors, 'Exit must not add or clear validation errors');
    sameLayout(during.boxes, before.boxes);
  }
  await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 2000 });
  const frames = await page.evaluate(() => window.exitFrames);
  assert.ok(frames.length > 0, 'Exit observer must actually run');
  if (!await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)) {
    assert.ok(frames.filter(frame => frame.state === 'closed').length > 1,
      'Independent observer must capture the actual animated closed phase');
  }
  for (const frame of frames) {
    assert.deepEqual(frame.values, before.values, 'Every observed exit frame retains the draft');
    assert.deepEqual(frame.errors, before.errors, 'No late validation/reset flash during exit');
    sameLayout(frame.boxes, before.boxes);
  }
  await until(() => page.getByRole('button', { name: 'Edit item', exact: true }).evaluate(e => e === document.activeElement), 'Native close returns focus to trigger');
  assert.deepEqual(await read(), original, 'Cancel/close leaves saved content/settings intact');
}

test('1. Existing content, constraints, native focus and one named color value', async () => app(async (page, read) => {
  await open(page);
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), original.item.title);
  assert.equal(await page.locator('[data-retained-note]').innerText(), original.item.notes);
  assert.equal(await page.getByRole('radio', { name: 'Blue', exact: true }).getAttribute('aria-checked'), 'true');
  assert.equal(await page.getByRole('dialog').getAttribute('aria-labelledby') !== null, true);
  assert.equal(await page.getByLabel('Title', { exact: true }).getAttribute('minlength'), '3');
  assert.equal(await page.getByLabel('Title', { exact: true }).getAttribute('maxlength'), '80');
  assert.deepEqual((await formState(page)).values.filter(([k]) => k === 'notes'), [['notes', original.item.notes]]);
  await until(() => page.getByLabel('Title', { exact: true }).evaluate(e => e === document.activeElement), 'Native opening focus lands on title');
  assert.deepEqual((await formState(page)).values.filter(([k]) => k === 'color'), [['color', 'blue']]);
  assert.deepEqual(await read(), original);
}));

test('2. onBlur validation and onInput revalidation remain enabled, including the radio proxy', async () => {
  await app(async page => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('x');
  assert.equal(await page.locator('#title-error').innerText(), '');
  await page.keyboard.press('Tab');
  await until(async () => (await page.locator('#title-error').innerText()).includes('3'), 'Blur should display native schema error');
  await page.getByLabel('Title', { exact: true }).fill('Corrected title');
  await until(async () => (await page.locator('#title-error').innerText()) === '', 'Input should clear touched error');
  });
  await app(async page => {
    await open(page);
    await page.keyboard.press('Tab');
    await until(() => page.getByRole('radio', { name: 'Red', exact: true }).evaluate(e => e === document.activeElement), 'Native Tab enters first radio when no value is selected');
    await page.keyboard.press('Shift+Tab');
    await until(async () => (await page.locator('#color-error').innerText()).includes('Choose red or blue'),
      'Ordinary group departure must validate its synthetic blur despite null relatedTarget');
    await page.getByRole('radio', { name: 'Red', exact: true }).click();
    await until(async () => (await page.locator('#color-error').innerText()) === '', 'Radio input revalidation must clear its error');
  }, {}, { ...original, item: { ...original.item, color: 'old-color' } });
});

test('3. A single native radio click from an invalid text field changes value without moving its target', async () => app(async page => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('x');
  const radio = page.getByRole('radio', { name: 'Red', exact: true });
  const box = await radio.boundingBox();
  const point = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  await until(async () => (await page.locator('#title-error').innerText()).includes('3'), 'Pointerdown blur validates title');
  const after = await radio.boundingBox();
  assert.ok(Math.abs(box.y - after.y) < 0.6, 'Error must not move radio between down and up');
  await page.mouse.up();
  await until(async () => (await radio.getAttribute('aria-checked')) === 'true', 'The single click must commit its value');
  assert.deepEqual((await formState(page)).values.filter(([k]) => k === 'color'), [['color', 'red']]);
  await page.keyboard.down('ArrowRight');
  try {
    await until(async () => (await page.getByRole('radio', { name: 'Blue', exact: true }).getAttribute('aria-checked')) === 'true', 'Native held arrow navigation selects next radio');
  } finally { await page.keyboard.up('ArrowRight'); }
}));

test('4. X and Cancel preserve the exit snapshot and restore native trigger focus', async () => app(async (page, read) => {
  await verifyExit(page, 'Close editor', read);
  await verifyExit(page, 'Cancel', read, true);
}));

test('5. Escape and backdrop close from native/composite focus without error or layout changes', async () => app(async (page, read) => {
  await verifyExit(page, 'Escape', read);
  await verifyExit(page, 'backdrop', read, false, true);
  await verifyExit(page, 'backdrop', read);
}));

test('6. Invalid submission retains values, focuses the visible invalid field and permits correction', async () => app(async (page, read) => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('x');
  await page.getByRole('radio', { name: 'Red', exact: true }).click();
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await until(() => page.getByLabel('Title', { exact: true }).evaluate(e => e === document.activeElement), 'Invalid submit focuses visible field');
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'x');
  assert.deepEqual((await formState(page)).values.filter(([k]) => k === 'color'), [['color', 'red']]);
  assert.deepEqual(await read(), original);
  await page.getByLabel('Title', { exact: true }).fill('Corrected after submit');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await until(async () => (await read()).revision === 1, 'Correction must actually persist');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
}));

test('7. Async save is acknowledged before close, then persisted summary/reopen/second save complete', async () => app(async (page, read, url) => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('First saved title');
  await page.getByRole('radio', { name: 'Red', exact: true }).click();
  let release;
  const barrier = new Promise(resolve => { release = resolve; });
  await page.route(`${url}/api/item`, async route => {
    if (route.request().method() === 'POST') await barrier;
    await route.continue();
  });
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.getByRole('button', { name: 'Saving…', exact: true }).waitFor();
  assert.equal(await page.getByRole('dialog').count(), 1, 'Must stay open before acknowledgement');
  assert.deepEqual(await read(), original, 'No pretend local save before server write');
  release();
  await until(async () => (await read()).revision === 1, 'Actual server save must run');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  assert.match(await page.locator('[data-summary]').innerText(), /First saved title/);
  await until(() => page.getByRole('button', { name: 'Edit item', exact: true }).evaluate(e => e === document.activeElement), 'Save returns native trigger focus');
  await open(page);
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'First saved title');
  assert.equal(await page.getByRole('radio', { name: 'Red', exact: true }).getAttribute('aria-checked'), 'true');
  await page.getByLabel('Title', { exact: true }).fill('Second saved title');
  await page.getByRole('radio', { name: 'Blue', exact: true }).click();
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await until(async () => (await read()).revision === 2, 'Second real save must run');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  const stored = await read();
  assert.deepEqual(stored, { ...original, item: { ...original.item, title: 'Second saved title', color: 'blue' }, revision: 2 });
  assert.match(await page.locator('[data-summary]').innerText(), /Second saved title/);
  await page.reload();
  await open(page);
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), stored.item.title);
  assert.equal(await page.locator('[data-retained-note]').innerText(), original.item.notes);
}));

test('8. Failed request leaves a usable draft and permits real retry; reduced-motion exit works', async () => app(async (page, read, url) => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('Retried title');
  await page.route(`${url}/api/item`, route => route.request().method() === 'POST'
    ? route.fulfill({ status: 503, body: 'Temporarily unavailable' }) : route.continue());
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Could not save' }).waitFor();
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Retried title');
  assert.deepEqual(await read(), original);
  await page.unroute(`${url}/api/item`);
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await until(async () => (await read()).revision === 1, 'Retry actually persists');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  await open(page);
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Retried title');
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
}, { reducedMotion: 'reduce' }));

test('9. An earlier save acknowledgement cannot close or overwrite a reopened draft', async () => app(async (page, read, url) => {
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('Earlier pending save');
  let release;
  const held = new Promise(resolve => { release = resolve; });
  let post = 0;
  await page.route(`${url}/api/item`, async route => {
    if (route.request().method() === 'POST' && ++post === 1) await held;
    await route.continue();
  });
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.getByRole('button', { name: 'Saving…', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  await open(page);
  await page.getByLabel('Title', { exact: true }).fill('Newer editing session');
  await page.getByRole('radio', { name: 'Red', exact: true }).click();
  release();
  await until(async () => (await read()).revision === 1, 'Earlier actual save completes');
  await until(async () => (await page.locator('[data-summary]').innerText()).includes('Earlier pending save'), 'Earlier acknowledgement updates canonical summary');
  assert.equal(await page.getByRole('dialog').count(), 1, 'Earlier acknowledgement must not close newer dialog');
  assert.equal(await page.getByRole('dialog').getAttribute('data-state'), 'open', 'Newer dialog must remain open, not merely mounted during exit');
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Newer editing session');
  assert.equal(await page.getByRole('radio', { name: 'Red', exact: true }).getAttribute('aria-checked'), 'true');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await until(async () => (await read()).revision === 2, 'Newer session must complete its own save');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  await open(page);
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Newer editing session');
  assert.equal(await page.getByRole('radio', { name: 'Red', exact: true }).getAttribute('aria-checked'), 'true');
  assert.deepEqual((await read()).settings, original.settings);
}));


test('10. UTF-8 split across HTTP chunks preserves content and the raw-byte limit', async () => app(async (_page, read, url) => {
  const submitted = { title: 'Café title ☕', color: 'red', notes: original.item.notes };
  const bytes = Buffer.from(JSON.stringify(submitted), 'utf8');
  async function post(parts) {
    return new Promise((resolve, reject) => {
      const request = http.request(`${url}/api/item`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
      }, response => {
        const chunks = [];
        response.on('data', chunk => chunks.push(chunk));
        response.once('end', () => resolve({ status: response.statusCode,
          body: Buffer.concat(chunks).toString('utf8') }));
        response.once('error', reject);
      });
      request.once('error', reject);
      request.write(parts[0]);
      // Send a valid multibyte character in separate real HTTP chunks.
      setTimeout(() => request.end(parts[1]), 40);
    });
  }
  for (const [index, split] of [bytes.indexOf(Buffer.from('é')) + 1,
    bytes.lastIndexOf(Buffer.from('é')) + 1].entries()) {
    assert.equal(bytes[split - 1], 0xc3);
    assert.equal(bytes[split], 0xa9);
    const response = await post([bytes.subarray(0, split), bytes.subarray(split)]);
    assert.equal(response.status, 200);
    const saved = JSON.parse(response.body);
    assert.deepEqual(saved.item, { ...original.item, ...submitted });
    assert.deepEqual(saved.settings, original.settings);
    assert.equal(saved.revision, index + 1);
    assert.deepEqual(await read(), saved, 'Independent persisted file retains complete Unicode');
  }
  const before = await read();
  const oversized = Buffer.from(JSON.stringify({ ...submitted, notes: 'é'.repeat(9000) }), 'utf8');
  assert.ok(oversized.length > 16384);
  const rejected = await post([oversized.subarray(0, 12000), oversized.subarray(12000)]);
  assert.equal(rejected.status, 413, 'The limit counts raw bytes before schema validation');
  assert.deepEqual(await read(), before, 'Oversized input leaves the saved record unchanged');
}));
