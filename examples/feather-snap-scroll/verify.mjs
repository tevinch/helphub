import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const directory = path.resolve(process.argv[2] || fileURLToPath(new URL('.', import.meta.url)));
const types = {'.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.css':'text/css', '.json':'application/json'};
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const filename = path.resolve(directory, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!filename.startsWith(directory + path.sep)) throw new Error('Outside example');
    const body = await readFile(filename);
    response.writeHead(200, {'Content-Type':types[path.extname(filename)] || 'application/octet-stream'});
    response.end(body);
  } catch {
    response.writeHead(404);
    response.end('Not found');
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
let browser;
const report = {checks:[], steps:[]};
try {
  browser = await chromium.launch({headless:true});
  report.browser = browser.version();
  const page = await browser.newPage({viewport:{width:1000,height:720}, reducedMotion:'no-preference'});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    window.samples = [];
    const sample = time => {
      window.samples.push({time, y:scrollY});
      requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  });
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector('nav a'));
  assert.deepEqual(errors, [], 'Example did not load cleanly');
  await page.waitForFunction(() => window.FeatherScroll?.instances.length === 1);
  report.loadedFeatherCount = await page.evaluate(() => window.FeatherScroll.instances.length);
  await page.fill('#notes', 'Keep this existing note.');
  const targets = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('.panel')].map(element => [element.id, element.getBoundingClientRect().top + scrollY - 72])));

  async function settled(expected) {
    await page.waitForFunction(target => {
      const samples = window.samples;
      const last = samples.at(-1);
      if (!last) return false;
      const recent = samples.filter(sample => sample.time >= last.time - 350);
      return recent.length > 10 && recent.at(-1).time - recent[0].time > 300 && recent.every(sample => Math.abs(sample.y - target) < 2);
    }, expected, {timeout:7000});
  }

  async function navigate(id) {
    const before = await page.evaluate(() => ({y:scrollY, index:samples.length}));
    await page.locator(`nav a[href="#${id}"]`).click();
    await settled(targets[id]);
    const result = await page.evaluate(start => ({y:scrollY, samples:samples.slice(start), status:document.querySelector('#status').textContent}), before.index);
    assert.ok(Math.abs(result.y - targets[id]) < 2, 'Navigation did not reach the target with header offset');
    assert.equal(result.status, `Arrived at ${id}.`);
    const intermediate = result.samples.filter(sample => Math.abs(sample.y - before.y) > 5 && Math.abs(sample.y - targets[id]) > 5);
    assert.ok(intermediate.length >= 4, 'Programmatic navigation jumped instead of animating');
    report.steps.push({type:'anchor', id, target:targets[id], before:before.y, after:result.y, intermediateFrames:intermediate.length});
  }

  // The original operation is asserted before inspecting implementation details.
  await navigate('middle');
  report.checks.push('actual anchor reaches target with offset and remains there');
  const setup = await page.evaluate(async () => {
    const {scroll, snap} = await import('/example.js');
    window.snapEvents = [];
    for (const [name, type] of [['onSnapStart','start'], ['onSnapComplete','complete']]) {
      const previous = snap.options[name];
      snap.options[name] = value => {
        snapEvents.push({type, time:performance.now(), y:scrollY, value:value.value});
        previous?.(value);
      };
    }
    return {sameInstance:snap.lenis === scroll.lenis, featherCount:scroll.constructor.instances.length, points:snap.elements.size, duration:snap.options.duration, debounce:snap.options.debounce, behavior:getComputedStyle(document.documentElement).scrollBehavior, snapType:getComputedStyle(document.documentElement).scrollSnapType};
  });
  assert.equal(setup.sameInstance, true);
  assert.equal(setup.featherCount, 1);
  assert.ok(setup.points > 0, 'No snap points were registered');
  assert.ok(setup.duration > 0, 'No snap duration was configured');
  assert.equal(setup.debounce, 200);
  assert.equal(setup.behavior, 'auto');
  assert.equal(setup.snapType, 'none');
  report.setup = setup;

  async function wheel(delta, id) {
    const before = await page.evaluate(() => ({y:scrollY, index:samples.length, events:snapEvents.length}));
    await page.mouse.move(900,500);
    await page.mouse.wheel(0,delta);
    await settled(targets[id]);
    const result = await page.evaluate(start => ({y:scrollY, samples:samples.slice(start.index), events:snapEvents.slice(start.events)}), before);
    const start = result.events.find(event => event.type === 'start');
    const complete = result.events.find(event => event.type === 'complete');
    assert.ok(start && complete, 'Real wheel movement did not complete a snap');
    assert.ok(Math.abs(complete.value - targets[id]) < 2, 'Snap chose a different section');
    const elapsed = complete.time - start.time;
    assert.ok(elapsed >= 900 && elapsed < 2500, `Snap timing was ${elapsed}ms`);
    const intermediate = result.samples.filter(sample => sample.time > start.time && sample.time < complete.time && Math.abs(sample.y - start.y) > 3 && Math.abs(sample.y - targets[id]) > 3);
    assert.ok(intermediate.length >= 8, 'Snap did not visibly progress through multiple native positions');
    assert.ok(Math.abs(result.y - targets[id]) < 2, 'Final native wheel/snap location is wrong');
    report.steps.push({type:'wheel', delta, id, target:targets[id], before:before.y, after:result.y, elapsed, intermediateFrames:intermediate.length, events:result.events});
  }
  await wheel(550,'end');
  await wheel(-550,'middle');
  await navigate('intro');
  await wheel(550,'middle');
  await navigate('end');
  assert.equal(await page.inputValue('#notes'), 'Keep this existing note.');
  assert.equal(await page.locator('#ordinary-content').textContent(), 'This ordinary paragraph stays in the document.');
  assert.deepEqual(errors, []);
  report.checks.push('forward and reverse wheel snaps complete gradually', 'another anchor and repeated wheel interaction stay usable', 'unrelated existing content retained', 'no browser errors');

  const reduced = await browser.newPage({viewport:{width:1000,height:720}, reducedMotion:'reduce'});
  await reduced.goto(base);
  await reduced.locator('nav a[href="#middle"]').click();
  await reduced.waitForFunction(() => document.querySelector('#status').textContent === 'Arrived at middle.');
  const reducedState = await reduced.evaluate(async () => {
    const {snap, scroll} = await import('/example.js');
    return {stopped:snap.isStopped, smoothWheel:scroll.lenis.options.smoothWheel, y:scrollY, target:document.querySelector('#middle').getBoundingClientRect().top + scrollY - 72};
  });
  assert.equal(reducedState.stopped, true);
  assert.equal(reducedState.smoothWheel, false);
  assert.ok(Math.abs(reducedState.y - reducedState.target) < 2);
  report.reducedMotion = reducedState;
  report.checks.push('reduced motion uses immediate navigation and native wheel behavior');
  console.log(`PASS ${report.checks.length} behavior checks; ${report.steps.length} completed anchor/wheel operations; Chromium ${report.browser}`);
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
  if (process.env.EVIDENCE_FILE) await writeFile(process.env.EVIDENCE_FILE, JSON.stringify(report,null,2));
}
