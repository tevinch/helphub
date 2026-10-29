import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const mode = process.argv[2] || 'green';
assert(['baseline', 'green', 'missing-loader', 'missing-menu', 'resume'].includes(mode));
const base = process.env.MAILFLOW_TEST_URL || 'http://127.0.0.1:18080';
const output = process.env.VERIFY_OUTPUT_DIR || './verification-results';
const password = process.env.MAILFLOW_TEST_PASSWORD;
assert(password && password.length >= 16, 'supply an ephemeral test password');
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ locale: 'en-US', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(20000);
page.setDefaultNavigationTimeout(30000);
const report = { mode, checks: [], localeResponses: [], preferenceWrites: [], pageErrors: [] };
page.on('pageerror', error => report.pageErrors.push(error.message));
page.on('response', response => {
  if (/\/assets\/da-[^/]+\.js(?:\?|$)/.test(response.url())) {
    report.localeResponses.push({ url: new URL(response.url()).pathname, status: response.status() });
  }
  if (response.url().endsWith('/api/auth/preferences') && response.request().method() === 'PATCH') {
    const data = response.request().postDataJSON();
    report.preferenceWrites.push({ status: response.status(), language: data?.language ?? null });
  }
});
function checked(name) { report.checks.push(name); }
async function api(path, options) {
  const response = await context.request.fetch(base + '/api' + path, { ...options, headers: { 'X-Requested-With': 'MailFlow' } });
  assert(response.ok(), `${path}: HTTP ${response.status()}`);
  return response.json();
}
async function preferences() { return api('/auth/preferences'); }
async function until(predicate, message) {
  const end = Date.now() + 15000;
  while (Date.now() < end) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 150));
  }
  assert.fail(message);
}
async function openLanguageSettings(translated = false) {
  await page.getByText('tevinch', { exact: true }).last().click();
  await page.getByText(translated ? 'Danish test: Settings' : 'Settings', { exact: true }).last().click();
  await page.getByRole('button', { name: translated ? 'Danish test: Appearance' : 'Appearance', exact: true }).click();
  await page.getByRole('button', { name: translated ? 'Danish test: Language & Font' : 'Language & Font', exact: true }).click();
  await page.getByRole('button', { name: 'English', exact: true }).waitFor();
  checked('native-language-settings-open');
}
async function choose(code, label, translated) {
  const saved = page.waitForResponse(response => response.url().endsWith('/api/auth/preferences')
    && response.request().method() === 'PATCH' && response.request().postDataJSON()?.language === code);
  await page.getByRole('button', { name: label, exact: true }).click();
  await page.getByText(translated ? 'Danish test: Choose the display language for the interface'
    : 'Choose the display language for the interface', { exact: true }).waitFor();
  assert.equal((await saved).status(), 200);
  await until(async () => (await preferences()).language === code, `server did not save ${code}`);
  assert.equal(await page.evaluate(() => document.documentElement.lang), code);
  assert.equal(await page.evaluate(() => localStorage.getItem('mailflow_language')), code);
  checked(`native-selection-and-server-save-${code}`);
}
let exitCode = 0;
try {
  const endpoint = mode === 'baseline' ? '/auth/register' : '/auth/login';
  const auth = await api(endpoint, { method: 'POST', data: { username: 'Tevinch', password } });
  assert.equal(auth.user.username, 'tevinch');
  checked(mode === 'baseline' ? 'native-ephemeral-registration' : 'native-test-login');
  if (mode !== 'resume') {
    await api('/auth/preferences', { method: 'PATCH', data: { language: 'en', fontSize: '110' } });
  } else {
    assert.equal((await preferences()).language, 'da');
  }
  await page.goto(base, { waitUntil: 'networkidle' });
  await openLanguageSettings(mode === 'resume');
  if (mode === 'resume') {
    await page.getByText('Danish test: Choose the display language for the interface', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => localStorage.getItem('mailflow_language')), 'da');
    checked('native-locale-survives-container-restart-and-new-browser');
  } else {
    const available = await page.getByRole('button', { name: 'Danish', exact: true }).count();
    if (!available) {
      report.failureStage = 'danish-selector-missing';
      exitCode = 42;
      throw new Error('Danish is absent from the native language menu');
    }
    if (mode === 'missing-loader') {
      await page.getByRole('button', { name: 'Danish', exact: true }).click();
      await until(async () => (await preferences()).language === 'da', 'da selection was not saved');
      assert.equal(await page.evaluate(() => document.documentElement.lang), 'da');
      assert.equal(await page.getByText('Choose the display language for the interface', { exact: true }).count(), 1);
      assert.equal(await page.getByText('Danish test: Choose the display language for the interface', { exact: true }).count(), 0);
      assert.equal(report.localeResponses.length, 0);
      report.failureStage = 'danish-strings-not-loaded';
      exitCode = 43;
      throw new Error('Saved da without its loader keeps English strings');
    }
    await choose('da', 'Danish', true);
    await until(() => report.localeResponses.some(item => item.status === 200), 'no actual da chunk HTTP 200');
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.evaluate(() => document.documentElement.lang), 'da');
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.evaluate(() => document.documentElement.lang), 'da');
    assert.equal(await page.evaluate(() => localStorage.getItem('mailflow_language')), 'da');
    checked('server-preference-restores-da-after-local-storage-clear');
    await openLanguageSettings(true);
    await choose('en', 'English', false);
    await choose('da', 'Danish', true);
    checked('repeated-English-Danish-switching');
  }
  assert.equal((await preferences()).fontSize, '110');
  assert.deepEqual(await api('/accounts'), []);
  assert.deepEqual(report.pageErrors, []);
  checked('unrelated-font-preference-preserved-and-no-mail-account');
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = error.message;
  if (!exitCode) exitCode = 1;
} finally {
  await writeFile(`${output}/${mode}.json`, JSON.stringify(report, null, 2) + '\n');
  await page.screenshot({ path: `${output}/${mode}.png`, fullPage: true }).catch(() => {});
  await browser.close();
}
console.log(JSON.stringify({ mode, status: report.status, checks: report.checks, failureStage: report.failureStage }));
process.exitCode = exitCode;
