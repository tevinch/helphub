import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { chromium } from 'playwright';

// Removing validation or performing preparation separately in each callback
// must break the externally observed lifecycle and saved-payload assertions.
function withDeadline(promise, operation) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Timed out waiting for ${operation}`)), 5000);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

const server = spawn(process.execPath, ['server.mjs'], {
  env: { ...process.env, PORT: '0' }, stdio: ['ignore', 'pipe', 'inherit'],
});
let browser;
const report = [];
try {
  const url = await withDeadline(new Promise((resolve, reject) => {
    let output = '';
    server.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/LISTEN=(http:\/\/127\.0\.0\.1:\d+)/);
      if (match) resolve(match[1]);
    });
    server.once('exit', code => reject(new Error(`Server exited ${code}`)));
  }), 'the local server to start');
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(url);
  const form = page.locator('[data-form="first"]');
  const input = form.getByRole('textbox', { name: 'JSON document' });
  const submit = form.getByRole('button', { name: 'Save document' });
  const events = async name => JSON.parse(await page.locator(`[data-events="${name}"]`).textContent());
  const receipts = async () => (await fetch(`${url}/api/documents`)).json();

  // Pause, then continue a real POST to observe native isSubmitting behavior.
  let releasePost;
  let reachedPost;
  const postGate = new Promise(resolve => { releasePost = resolve; });
  const postSeen = new Promise(resolve => { reachedPost = resolve; });
  let holdNextPost = true;
  await page.route('**/api/documents', async route => {
    if (route.request().method() === 'POST' && holdNextPost) {
      holdNextPost = false;
      reachedPost();
      await postGate;
    }
    await route.continue();
  });
  await input.fill('{"title":"First document","pages":2}');
  await submit.click();
  await withDeadline(postSeen, 'the first native submission POST');
  assert.equal(await input.isDisabled(), true, 'native isSubmitting must disable editing during the save');
  assert.equal(await submit.isDisabled(), true, 'native isSubmitting must prevent another submit');
  releasePost();
  await form.getByRole('status').filter({ hasText: 'Saved document 1' }).waitFor();
  let trace = await events('first');
  assert.equal(trace.filter(x => x.step === 'prepare').length, 1,
    'one successful submission must prepare once, shared by validation and submit');
  assert.deepEqual(trace.map(x => x.step), ['prepare', 'validate', 'submit', 'saved']);
  assert.equal(trace.find(x => x.step === 'submit').samePrepared, true,
    'native validator and submit must use the same prepared object identity');
  assert.deepEqual(await receipts(), [{ id: 1, source: 'first', document: { title: 'First document', pages: 2 } }]);
  assert.equal(await input.inputValue(), '{"title":"First document","pages":2}');
  assert.equal(await input.isDisabled(), false);
  report.push('valid input: native validation, same prepared object, pending-save guard, real persisted HTTP receipt');

  await input.fill('{"title":"","pages":2}');
  await submit.click();
  await form.getByRole('alert').filter({ hasText: 'title must be a non-empty string' }).waitFor();
  trace = await events('first');
  assert.equal(trace.filter(x => x.step === 'prepare').length, 2);
  assert.equal(trace.filter(x => x.step === 'validate').length, 2);
  assert.equal(trace.filter(x => x.step === 'submit').length, 1);
  assert.equal((await receipts()).length, 1, 'invalid prepared data must not be saved');
  assert.equal(await input.inputValue(), '{"title":"","pages":2}');
  report.push('invalid prepared data: native error, preserved text, no submit or HTTP write');

  await input.fill('{broken');
  await submit.click();
  await form.getByRole('alert').filter({ hasText: 'Enter valid JSON' }).waitFor();
  trace = await events('first');
  assert.equal(trace.filter(x => x.step === 'prepare').length, 3);
  assert.equal(trace.filter(x => x.step === 'validate').length, 3);
  assert.equal(trace.filter(x => x.step === 'submit').length, 1);
  assert.equal((await receipts()).length, 1);
  assert.equal(await input.inputValue(), '{broken');
  report.push('preparation failure: recoverable native error and no saved document');

  await input.fill('{"title":"Revised document","pages":4}');
  await submit.click();
  await form.getByRole('status').filter({ hasText: 'Saved document 2' }).waitFor();
  trace = await events('first');
  assert.equal(trace.filter(x => x.step === 'prepare').length, 4);
  assert.equal(trace.filter(x => x.step === 'validate').length, 4);
  assert.equal(trace.filter(x => x.step === 'submit').length, 2);
  assert.ok(trace.filter(x => x.step === 'submit').every(x => x.samePrepared));
  assert.equal(await form.getByRole('alert').count(), 0);
  assert.deepEqual(await receipts(), [
    { id: 1, source: 'first', document: { title: 'First document', pages: 2 } },
    { id: 2, source: 'first', document: { title: 'Revised document', pages: 4 } },
  ]);
  report.push('changed input retry: new preparation, cleared native error, new payload, old receipt retained');

  await form.getByRole('button', { name: 'Rerender example' }).click();
  await submit.click();
  await form.getByRole('status').filter({ hasText: 'Saved document 3' }).waitFor();
  trace = await events('first');
  assert.equal(trace.filter(x => x.step === 'prepare').length, 4,
    'unchanged input must reuse the last result across ordinary rerenders');
  assert.equal(trace.filter(x => x.step === 'validate').length, 5);
  assert.equal(trace.filter(x => x.step === 'submit').length, 3);
  assert.equal(trace.filter(x => x.step === 'submit').at(-1).samePrepared, true,
    'the latest submission after rerender must reuse its validated prepared object');
  assert.deepEqual(await receipts(), [
    { id: 1, source: 'first', document: { title: 'First document', pages: 2 } },
    { id: 2, source: 'first', document: { title: 'Revised document', pages: 4 } },
    { id: 3, source: 'first', document: { title: 'Revised document', pages: 4 } },
  ]);
  report.push('unchanged repeated submit after rerender: reused preparation and complete new HTTP save');

  const second = page.locator('[data-form="second"]');
  await second.getByRole('textbox', { name: 'JSON document' }).fill('{"title":"Revised document","pages":4}');
  await second.getByRole('button', { name: 'Save document' }).click();
  await second.getByRole('status').filter({ hasText: 'Saved document 4' }).waitFor();
  assert.deepEqual((await events('second')).map(x => x.step), ['prepare', 'validate', 'submit', 'saved']);
  assert.equal((await events('second')).find(x => x.step === 'submit').samePrepared, true);
  assert.equal((await events('first')).filter(x => x.step === 'prepare').length, 4);
  assert.deepEqual((await receipts()).at(-1), { id: 4, source: 'second', document: { title: 'Revised document', pages: 4 } });
  report.push('two mounted forms: independent preparation/cache and separate saved receipt');

  assert.deepEqual(errors, [], 'browser must not report uncaught application errors');
  console.log(JSON.stringify({ browser: await browser.version(), checks: report, passed: report.length }, null, 2));
} finally {
  await browser?.close();
  if (server.exitCode === null && server.signalCode === null) {
    const exited = once(server, 'exit');
    server.kill('SIGTERM');
    await exited;
  }
}
