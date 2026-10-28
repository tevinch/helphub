import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { createDemoServer } from './server.mjs';

const { server, requests } = createDemoServer();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = 'http://127.0.0.1:' + server.address().port;
let browser;
try {
  browser = await chromium.launch({ headless: true });
  for (const version of ['2.0.11', '4.0.0']) {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    const errors = [];
    const posts = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (request.method() === 'POST') posts.push(request);
    });
    await page.addInitScript(() => {
      window.cspViolations = [];
      window.settledSwaps = 0;
      document.addEventListener('securitypolicyviolation', event =>
        window.cspViolations.push({ directive: event.violatedDirective, blocked: event.blockedURI }));
      for (const name of ['htmx:afterSettle', 'htmx:after:settle']) {
        document.addEventListener(name, () => window.settledSwaps++);
      }
    });
    const response = await page.goto(base + '/?version=' + version);
    assert.equal(response.headers()['content-security-policy'],
      "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'self'; base-uri 'none'; form-action 'self'");
    await page.waitForFunction(expected => window.htmx?.version === expected, version);
    assert.equal(await page.locator('#error').textContent(), '');
    assert.equal(requests.length, 0);
    const postal = page.locator('#postal_code');
    const country = page.locator('#country');
    async function waitPost(action, expectedReason) {
      const before = requests.length;
      const beforeSettle = await page.evaluate(() => window.settledSwaps);
      const rendered = page.waitForResponse(r => r.url().endsWith('/postal') && r.request().method() === 'POST');
      await action();
      await rendered;
      await page.waitForFunction(count => document.querySelector('#postal-row').dataset.sequence === String(count), before + 1);
      await page.waitForFunction(count => window.settledSwaps > count, beforeSettle);
      assert.equal(requests.length, before + 1);
      assert.equal(requests.at(-1).reason, expectedReason);
      assert.equal(posts.at(-1).headers()['x-postal-reason'], expectedReason);
    }
    await waitPost(() => country.fill('CA'), 'refresh');
    assert.equal(await page.locator('#error').textContent(), '', 'country refresh must not validate empty postal code');
    assert.match(await page.locator('#hint').textContent(), /A1A 1A1/);
    await waitPost(async () => { await postal.focus(); await page.locator('#notes').focus(); }, 'validate');
    assert.match(await page.locator('#error').textContent(), /required/);
    await waitPost(async () => { await postal.fill('K1A 0B1'); await page.locator('#notes').focus(); }, 'validate');
    assert.equal(await page.locator('#error').textContent(), '');
    assert.equal(await postal.inputValue(), 'K1A 0B1');
    await waitPost(() => country.fill('FR'), 'refresh');
    assert.equal(await page.locator('#error').textContent(), '');
    assert.match(await page.locator('#hint').textContent(), /five digits/);
    assert.equal(await postal.inputValue(), 'K1A 0B1');
    await waitPost(async () => { await postal.focus(); await page.locator('#notes').focus(); }, 'validate');
    assert.match(await page.locator('#error').textContent(), /format/);
    await waitPost(async () => { await postal.fill('75001'); await page.locator('#notes').focus(); }, 'validate');
    assert.equal(await page.locator('#error').textContent(), '');
    await page.locator('#notes').fill('Keep this note');
    const submitted = page.waitForResponse(r => r.url().endsWith('/submit') && r.request().method() === 'POST');
    await page.locator('button[type=submit]').click();
    await submitted;
    await page.waitForFunction(() => document.querySelector('#submission').textContent.includes('Saved'));
    assert.deepEqual(requests.at(-1), { route: '/submit', country: 'FR', postal: '75001', notes: 'Keep this note', valid: true });
    assert.equal(await page.locator('#notes').inputValue(), 'Keep this note');
    assert.equal(await page.locator('tr > :not(th):not(td)').count(), 0, 'table rows must keep valid cell boundaries');
    assert.equal(await page.locator('[hx-nonce],[hx-vals],[hx-on],[onclick]').count(), 0);
    assert.deepEqual(await page.evaluate(() => window.cspViolations), []);
    assert.deepEqual(errors, []);
    // Verify policy enforcement after the ordinary flow has no violations.
    await page.evaluate(() => {
      const script = document.createElement('script');
      script.textContent = 'window.inlineProbeRan = true';
      document.head.append(script);
    });
    await page.waitForFunction(() => window.cspViolations.some(event => event.blocked === 'inline'));
    assert.equal(await page.evaluate(() => window.inlineProbeRan), undefined);
    await page.route('**/csp-probe.js', route => route.fulfill({
      contentType: 'text/javascript',
      body: 'try { new Function("return 7")(); window.evalProbeRan = true; } catch (error) { window.evalProbeError = error.name; }'
    }));
    await page.addScriptTag({ url: base + '/csp-probe.js' });
    await page.waitForFunction(() => window.cspViolations.some(event => event.blocked === 'eval'));
    assert.equal(await page.evaluate(() => window.evalProbeRan), undefined);
    assert.equal(await page.evaluate(() => window.evalProbeError), 'EvalError');
    const forced = await page.request.post(base + '/submit', {
      form: { country: 'FR', postal_code: '', notes: 'Keep this note' },
      headers: { 'X-Postal-Reason': 'refresh' }
    });
    assert.equal(forced.status(), 200);
    assert.match(await forced.text(), /not saved/);
    assert.equal(requests.at(-1).valid, false);
    assert.equal(posts.length, 7, 'six actual field updates and one complete form submission');
    console.log(JSON.stringify({ version, fieldPOSTs: 6, finalPOSTs: 1, finalFieldsChecked: true, ordinaryFlowCspViolations: [], inlineAndEvalProbesBlocked: true, errors }));
    requests.length = 0;
    await page.close();
  }
  console.log('PASS: refresh, validation, repeated row replacement and final submission in both versions.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
