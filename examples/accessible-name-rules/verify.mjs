import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { chromium } from 'playwright';

const require = createRequire(import.meta.url);
const rules = ['aria-command-name', 'button-name', 'link-name'];
const expectedRaw = {
  'aria-command-name': ['#raw-div'],
  'button-name': ['#raw-button'],
  'link-name': ['#raw-link'],
};
const expectedNamed = {
  'aria-command-name': ['#named-div'],
  'button-name': ['#named-button'],
  'link-name': ['#named-link'],
};
const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const browser = await chromium.launch({ headless: true });
const reports = [];
try {
  for (const packageName of ['axe-core-reported', 'axe-core']) {
    const page = await browser.newPage();
    try {
      await page.setContent(html);
      await page.addScriptTag({ path: require.resolve(`${packageName}/axe.min.js`) });
      const before = await page.locator('main').innerHTML();
      const result = await page.evaluate(async (ids) => {
        const scan = selector => axe.run(document.querySelector(selector), {
          runOnly: { type: 'rule', values: ids },
        });
        return { version: axe.version, original: await scan('#original'), named: await scan('#named') };
      }, rules);
      const targets = entries => Object.fromEntries(entries.map(entry => [
        entry.id, entry.nodes.flatMap(node => node.target).sort(),
      ]));
      assert.deepEqual(targets(result.original.violations), expectedRaw);
      assert.equal(result.original.incomplete.length, 0);
      assert.deepEqual(result.named.violations, [], 'Named controls still fail a naming rule');
      assert.equal(result.named.incomplete.length, 0);
      assert.deepEqual(targets(result.named.passes), expectedNamed, 'Each named control must be checked');
      assert.equal(await page.locator('main').innerHTML(), before, 'The scan changed the fixture');
      const again = await page.evaluate(ids => axe.run(document.querySelector('#named'), {
        runOnly: { type: 'rule', values: ids },
      }), rules);
      assert.deepEqual(targets(again.passes), expectedNamed);
      assert.deepEqual(again.violations, []);
      reports.push({ version: result.version, violations: targets(result.original.violations), passes: targets(result.named.passes) });
    } finally { await page.close(); }
  }
} finally { await browser.close(); }
console.log(JSON.stringify({ scope: 'Three accessible-name rules only', reports }, null, 2));
