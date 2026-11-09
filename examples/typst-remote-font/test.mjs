import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { resolve, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
await assert.doesNotReject(access(resolve(root, 'example.mjs')), 'the browser custom-font example must exist');
const mime = { '.mjs': 'text/javascript', '.js': 'text/javascript', '.html': 'text/html', '.wasm': 'application/wasm' };
const server = createServer(async (req, res) => {
  const path = resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname === '/' ? '/index.html' : new URL(req.url, 'http://localhost').pathname));
  if (!path.startsWith(resolve(root) + '/')) { res.writeHead(403).end(); return; }
  try { res.setHeader('Content-Type', mime[extname(path)] || 'application/octet-stream'); res.end(await readFile(path)); }
  catch { res.writeHead(404).end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
try {
  const page = await browser.newPage();
  const errors = [], responses = [], warnings = [];
  page.on('console', m => { if(m.type() === 'warning') warnings.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (/\.wasm|NotoSansSC-Regular\.otf/.test(r.url())) responses.push({ url: r.url(), status: r.status() }); });
  await page.goto(url);
  assert.equal(await page.evaluate(async () => typeof (await import('@myriaddreamin/typst.ts')).$typst.preloadRemoteFonts), 'undefined', 'the original instance method does not exist');
  await page.locator('#status').filter({ hasText: 'Rendered' }).waitFor({timeout: 90000});
  const initial = await page.locator('#preview').innerHTML();
  assert.ok(initial.includes('<svg'), 'compiler vector data must be rendered into SVG');
  assert.ok(await page.locator('#preview use').count() > 5, 'visible text must have real glyph uses');
  assert.equal(await page.locator('#diagnostics').textContent(), '[]', 'actual compiler diagnostics must be empty');
  assert.equal(responses.filter(r => r.url.includes('NotoSansSC-Regular.otf') && r.status === 200).length, 1, 'native font hook must fetch the exact custom font');
  assert.equal(responses.filter(r => r.url.endsWith('.wasm') && r.status === 200).length, 2, 'compiler and renderer WASM must both load');
  const originalGlyphs = await page.locator('#preview use').evaluateAll(nodes => [...new Set(nodes.map(n => n.getAttribute('href') || n.getAttribute('xlink:href')))]);
  const original = await page.locator('#source').inputValue();
  const extended = original + '\n\u4f60\u597d\uff0c\u4e16\u754c\u3002';
  await page.locator('#source').fill(extended);
  await page.getByRole('button', { name: 'Render' }).click();
  await page.locator('#status').filter({ hasText: 'Rendered 2' }).waitFor();
  assert.ok(await page.locator('#preview use').count() > 15, 'added non-Latin text must render additional glyphs');
  const extendedGlyphs = await page.locator('#preview use').evaluateAll(nodes => [...new Set(nodes.map(n => n.getAttribute('href') || n.getAttribute('xlink:href')))]);
  assert.ok(extendedGlyphs.length >= originalGlyphs.length + 4, 'non-Latin characters must use distinct glyph outlines, not repeated missing-character boxes');
  assert.equal(await page.locator('#diagnostics').textContent(), '[]');
  await page.locator('#source').fill(extended + '\nSecond document edit.');
  await page.getByRole('button', { name: 'Render' }).click();
  await page.locator('#status').filter({ hasText: 'Rendered 3' }).waitFor();
  assert.notEqual(await page.locator('#preview').innerHTML(), initial, 'second edit must produce changed SVG');
  assert.equal(await page.locator('#source').inputValue(), extended + '\nSecond document edit.', 'original content must remain after repeated compilation');
  assert.deepEqual(errors, [], 'no browser runtime errors');
  await page.screenshot({path: resolve(root, '../typst-render.png'), fullPage: true});
  console.log(JSON.stringify({ mode:'software-operated Chromium', renders:3, diagnostics:[], responses, errors, warnings }));

  const negative = await browser.newPage();
  const negativeResponses = [];
  negative.on('response', r => { if (r.url().includes('NotoSansSC')) negativeResponses.push(r.url()); });
  await negative.route('**/example.mjs', async route => {
    const response = await route.fetch();
    const originalModule = await response.text();
    const omitted = originalModule.replace('loadFonts([FONT_URL], { assets: false })', 'loadFonts([], { assets: false })');
    assert.notEqual(omitted, originalModule, 'negative control must really remove the font');
    await route.fulfill({response, body: omitted});
  });
  await negative.goto(url);
  await negative.locator('#status').filter({hasText:/Rendered|Compile failed/}).waitFor({timeout:90000});
  const negativeGlyphs = await negative.locator('#preview use').count();
  assert.equal(negativeResponses.length, 0, 'font omission must not fetch a cached/default replacement');
  assert.equal(negativeGlyphs, 0, 'without fonts the returned SVG has no text glyphs');
  assert.throws(() => assert.ok(negativeGlyphs > 5), 'the normal glyph acceptance must reject missing text even when diagnostics are empty');
  console.log(JSON.stringify({negativeGlyphs, negativeFontRequests: negativeResponses.length, negativeDiagnostics: await negative.locator('#diagnostics').textContent()}));
  console.log('PASS: actual custom font, compiler, renderer, second edit, and font omission negative control');
} finally { await browser.close(); await new Promise(r => server.close(r)); }
