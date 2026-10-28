import assert from 'node:assert/strict';
import { once } from 'node:events';
import { chromium } from 'playwright';
import { createExampleServer } from './server.mjs';

const { server, requests } = createExampleServer();
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true });
const results = [];

try {
  for (const version of ['2.0.11', '4.0.0']) {
    const context = await browser.newContext();
    context.setDefaultTimeout(5000);
    const page = await context.newPage();
    const errors = [];
    const actualPosts = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    page.on('request', request => {
      if (request.method() === 'POST') actualPosts.push({
        path: new URL(request.url()).pathname,
        fields: Object.fromEntries(new URLSearchParams(request.postData())),
      });
    });
    await page.goto(`${origin}/?version=${version}`);
    assert.equal(await page.evaluate(() => htmx.version), version);
    assert.equal(await page.locator('#city').getAttribute('data-country'), '');
    const start = requests.length;

    async function choose(label, group, country) {
      const previous = requests.length;
      const response = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/cities/${group}` &&
        response.request().method() === 'POST');
      await page.getByLabel(label, { exact: true }).check();
      assert.equal((await response).status(), 200);
      await page.waitForFunction(({ group, country }) =>
        document.getElementById(group)?.dataset.country === country,
      { group, country });
      await page.waitForLoadState('networkidle');
      assert.equal(requests.length, previous + 1, 'one real request per changed country');
      const last = requests.at(-1);
      assert.equal(last.path, `/cities/${group}`);
      assert.equal(last.fields[group === 'city' ? 'country' : 'shipping_country'], country);
    }

    await choose('France', 'city', 'fr');
    assert.deepEqual(await page.locator('#city option').allTextContents(), ['Choose a city', 'Paris', 'Lyon']);
    await page.locator('#city').selectOption('lyon');
    await page.getByLabel('Notes').fill('Keep this text across country changes.');
    await page.getByLabel('Other field').fill('unrelated input');
    await page.waitForLoadState('networkidle');
    assert.equal(requests.length, start + 1, 'an unrelated input must not reload a city');
    assert.equal(await page.locator('#city').inputValue(), 'lyon');

    await choose('Germany', 'city', 'de');
    assert.deepEqual(await page.locator('#city option').allTextContents(), ['Choose a city', 'Berlin', 'Hamburg']);
    await page.locator('#city').selectOption('hamburg');
    assert.equal(await page.getByLabel('Notes').inputValue(), 'Keep this text across country changes.');
    assert.equal(await page.locator('#shipping_city').getAttribute('data-country'), '');

    await page.evaluate(() => {
      const item = document.createElement('li');
      item.innerHTML = '<div><label><input type="radio" name="country" value="be"> Belgium</label></div>';
      document.querySelector('[data-source="city"]').append(item);
    });
    await choose('Belgium', 'city', 'be');
    assert.deepEqual(await page.locator('#city option').allTextContents(), ['Choose a city', 'Brussels', 'Antwerp']);
    await page.locator('#city').selectOption('brussels');

    await choose('Shipping Germany', 'shipping_city', 'de');
    assert.equal(await page.locator('#city').inputValue(), 'brussels');
    assert.equal(await page.locator('#city').getAttribute('data-country'), 'be');
    await page.locator('#shipping_city').selectOption('hamburg');
    const beforeSelect = requests.length;
    await page.locator('#shipping_city').selectOption('berlin');
    await page.getByLabel('Other field').fill('unrelated edit again');
    await page.waitForLoadState('networkidle');
    assert.equal(requests.length, beforeSelect, 'selecting a city or editing another field must not reload');

    await choose('France', 'city', 'fr');
    await page.locator('#city').selectOption('paris');
    await choose('Germany', 'city', 'de');
    await page.locator('#city').selectOption('berlin');
    await choose('France', 'city', 'fr');
    await page.locator('#city').selectOption('lyon');
    await page.getByLabel('Notes').fill('Final edited note');
    const beforeSubmit = requests.length;
    await Promise.all([
      page.waitForURL(`${origin}/submit`),
      page.getByRole('button', { name: 'Submit form' }).click(),
    ]);
    assert.equal(requests.length, beforeSubmit + 1);
    const submitted = JSON.parse(await page.locator('#result').textContent());
    assert.deepEqual(submitted, {
      country: 'fr', city: 'lyon', shipping_country: 'de',
      shipping_city: 'berlin', notes: 'Final edited note', other: 'unrelated edit again',
    });
    assert.deepEqual(requests.at(-1).fields, submitted);
    assert.deepEqual(actualPosts, requests.slice(start));
    assert.deepEqual(errors, [], 'no JavaScript or CSP errors');
    results.push({ version, cityRequests: requests.length - start - 1, submission: submitted, errors });
    await context.close();
  }
  console.log(JSON.stringify({ status: 'PASS', results }, null, 2));
} finally {
  await browser.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
