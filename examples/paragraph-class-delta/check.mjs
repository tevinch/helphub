import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const control = process.env.CONTROL || '';
const browser = await chromium.launch({ headless: true });
let server;
const evidence = { browser: browser.version(), control, rounds: [] };

async function snapshot(page) {
  return page.evaluate(() => ({
    text: window.quill.getText(),
    delta: JSON.parse(JSON.stringify(window.quill.getContents())),
    lines: window.quill.getLines().map((line) => ({
      tag: line.domNode.tagName,
      text: line.domNode.textContent,
      classes: [...line.domNode.classList].sort(),
      list: line.domNode.getAttribute('data-list'),
    })),
  }));
}

async function roundTrip(page, expectedClasses) {
  const before = await snapshot(page);
  await page.evaluate(() => {
    window.previousEditor = window.quill;
    window.previousRoot = window.quill.root;
  });
  await page.locator('#export').click();
  const saved = JSON.parse(await page.locator('#saved-json').inputValue());
  assert.deepEqual(saved, before.delta, 'Export must really save this editor Delta');
  await page.locator('#clear').click();
  assert.deepEqual((await snapshot(page)).delta, { ops: [{ insert: '\n' }] }, 'Clear must really empty the document');
  await page.locator('#restore').click();
  const independent = await page.evaluate(() => ({
    freshEditor: window.quill !== window.previousEditor,
    oldRootDisconnected: !window.previousRoot.isConnected,
  }));
  const restored = await snapshot(page);
  evidence.rounds.push({ before, saved, independent, restored });
  assert.equal(independent.freshEditor, true, 'Restore must create a new Quill instance');
  assert.equal(independent.oldRootDisconnected, true, 'Restore must replace the old editable root');
  assert.deepEqual(restored.delta, saved, 'All serialized marks and line attributes must survive');
  for (const op of saved.ops.filter((op) => op.attributes?.customKey)) {
    assert.equal(op.insert, '\n', 'This block format must be serialized on the line newline');
    assert.equal(['a', 'b'].includes(op.attributes.customKey), true);
  }
  assert.equal(restored.text, before.text, 'Text must survive');
  assert.deepEqual(restored.lines.slice(2), before.lines.slice(2), 'Ordinary, heading and list neighbors must survive');
  assert.deepEqual(restored.lines.slice(0, 2).map((line) => line.classes.filter((name) => name.startsWith('class-'))), expectedClasses,
    'Paragraph classes must survive editing, JSON export, clear and fresh restore');
  return restored;
}

async function domOnlyFixture(page) {
  await page.setContent(`<!doctype html><html lang="en"><meta charset="utf-8"><title>Paragraph class control</title>
    <button id="export">Export JSON</button><button id="clear">Clear editor</button>
    <button id="restore">Restore in new editor</button><div id="host"><div id="editor"></div></div>
    <textarea id="saved-json"></textarea></html>`);
  await page.addStyleTag({ path: fileURLToPath(new URL('./node_modules/quill/dist/quill.snow.css', import.meta.url)) });
  await page.addScriptTag({ path: fileURLToPath(new URL('./node_modules/quill/dist/quill.js', import.meta.url)) });
  await page.evaluate(() => {
    const options = { theme: 'snow', modules: { toolbar: [['bold']] }, formats: ['customKey', 'bold', 'align', 'header', 'list'] };
    window.quill = new Quill('#editor', options);
    window.quill.setContents([
      { insert: 'Alpha', attributes: { bold: true } }, { insert: '\n', attributes: { customKey: 'a' } },
      { insert: 'Beta' }, { insert: '\n', attributes: { customKey: 'b', align: 'center' } },
      { insert: 'Ordinary\nHeading' }, { insert: '\n', attributes: { header: 2 } },
      { insert: 'List item' }, { insert: '\n', attributes: { list: 'bullet' } },
    ]);
    // Reproduce the original DOM-only approach.  This is a negative control.
    window.quill.root.children[0].classList.add('class-a');
    window.quill.root.children[1].classList.add('class-b');
    window.quill.update();
    document.querySelector('#export').onclick = () => {
      document.querySelector('#saved-json').value = JSON.stringify(window.quill.getContents());
    };
    document.querySelector('#clear').onclick = () => window.quill.setText('');
    document.querySelector('#restore').onclick = () => {
      const contents = JSON.parse(document.querySelector('#saved-json').value);
      window.quill.disable();
      const container = document.createElement('div');
      document.querySelector('#host').replaceChildren(container);
      window.quill = new Quill(container, options);
      window.quill.setContents(contents);
    };
  });
}

try {
  const page = await browser.newPage({ viewport: { width: 1080, height: 850 } });
  if (control === 'dom-only') {
    await domOnlyFixture(page);
  } else {
    const { createDemoServer } = await import('./server.mjs');
    server = createDemoServer();
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    if (control === 'no-registration' || control === 'inline-scope') {
      await page.route('**/paragraph-format.js', async (route) => {
        const response = await route.fetch();
        let source = await response.text();
        source = control === 'no-registration'
          ? source.replace('Quill.register(ParagraphClass);', '// registration deliberately omitted')
          : source.replace('scope: Scope.BLOCK', 'scope: Scope.INLINE');
        await route.fulfill({ response, body: source });
      });
    }
    if (control === 'reuse-editor') {
      await page.route('**/app.js', async (route) => {
        const response = await route.fetch();
        const source = (await response.text()).replace(
          'createEditor(JSON.parse(saved.value));',
          'window.quill.setContents(JSON.parse(saved.value));',
        );
        await route.fulfill({ response, body: source });
      });
    }
    await page.goto(base);
    await page.waitForFunction(() => window.quill);
  }
  assert.equal(await page.evaluate(() => Quill.version), '2.0.3');
  evidence.initial = await snapshot(page);
  evidence.registration = await page.evaluate(() => {
    const { Scope } = Quill.import('parchment');
    const block = window.quill.scroll.query('customKey', Scope.BLOCK_ATTRIBUTE);
    return {
      blockRegistered: !!block,
      inlineRegistered: !!window.quill.scroll.query('customKey', Scope.INLINE_ATTRIBUTE),
      keyName: block?.keyName,
      whitelist: block?.whitelist,
    };
  });
  // Real keyboard input and a real formatting toolbar click.
  await page.locator('.ql-editor').click();
  await page.evaluate(() => window.quill.setSelection(5, 0));
  await page.keyboard.type('!');
  await page.evaluate(() => window.quill.setSelection(7, 4));
  await page.locator('button.ql-bold').click();
  assert.equal((await snapshot(page)).text, 'Alpha!\nBeta\nOrdinary\nHeading\nList item\n');
  assert.equal(await page.locator('.ql-editor p').nth(0).locator('strong').innerText(), 'Alpha!');
  assert.equal(await page.locator('.ql-editor p').nth(1).locator('strong').innerText(), 'Beta');
  let restored = await roundTrip(page, [['class-a'], ['class-b']]);
  assert.deepEqual(evidence.registration, {
    blockRegistered: true, inlineRegistered: false, keyName: 'class', whitelist: ['a', 'b'],
  }, 'The actual editor registry must contain the native block attributor');
  assert.equal(restored.delta.ops.some((op) => op.attributes?.customKey === 'a'), true);
  assert.equal(restored.delta.ops.some((op) => op.attributes?.customKey === 'b'), true);
  assert.equal(restored.delta.ops.some((op) => op.attributes?.align === 'center'), true);
  assert.equal(restored.delta.ops.some((op) => op.attributes?.header === 2), true);
  assert.equal(restored.delta.ops.some((op) => op.attributes?.list === 'bullet'), true);
  for (const classes of [[['class-b'], ['class-b']], [['class-a'], ['class-b']]]) {
    const before = await snapshot(page);
    await page.locator('#toggle').click();
    const changed = await snapshot(page);
    assert.equal(changed.text, before.text);
    assert.deepEqual(changed.lines.slice(1), before.lines.slice(1));
    assert.deepEqual(changed.lines[0].classes.filter((name) => name.startsWith('class-')), classes[0]);
    restored = await roundTrip(page, classes);
  }
  await page.evaluate(() => window.quill.setSelection(6, 0));
  await page.keyboard.type('?');
  assert.equal((await snapshot(page)).text.startsWith('Alpha!?\n'), true, 'Restored editor must remain editable');
  if (control !== 'dom-only') {
    evidence.restrictions = await page.evaluate(async () => {
      const { FORMAT_NAME } = await import('./paragraph-format.js');
      const make = (formats) => {
        const node = document.createElement('div');
        document.body.append(node);
        return new Quill(node, { modules: { toolbar: false }, formats });
      };
      const restricted = make(['bold']);
      restricted.setContents([{ insert: 'Keep', attributes: { bold: true, italic: true } }, { insert: '\n', attributes: { [FORMAT_NAME]: 'a' } }]);
      const restrictedResult = { delta: restricted.getContents(), html: restricted.root.innerHTML };
      const invalid = make([FORMAT_NAME, 'bold']);
      invalid.setContents([{ insert: 'Invalid', attributes: { bold: true } }, { insert: '\n', attributes: { [FORMAT_NAME]: 'class-a' } }]);
      const fullClassImported = { delta: invalid.getContents(), html: invalid.root.innerHTML };
      invalid.setContents([{ insert: 'Invalid', attributes: { bold: true } }, { insert: '\n', attributes: { [FORMAT_NAME]: 'unknown' } }]);
      const invalidImported = { delta: invalid.getContents(), html: invalid.root.innerHTML };
      invalid.formatLine(0, 1, FORMAT_NAME, 'a');
      invalid.formatLine(0, 1, FORMAT_NAME, 'unknown');
      const invalidChange = { delta: invalid.getContents(), html: invalid.root.innerHTML };
      invalid.formatLine(0, 1, FORMAT_NAME, false);
      const removed = { delta: invalid.getContents(), html: invalid.root.innerHTML };
      restricted.disable();
      invalid.disable();
      restricted.container.remove();
      invalid.container.remove();
      return { restrictedResult, fullClassImported, invalidImported, invalidChange, removed };
    });
    const { restrictedResult, fullClassImported, invalidImported, invalidChange, removed } = evidence.restrictions;
    assert.deepEqual(restrictedResult.delta, { ops: [{ insert: 'Keep', attributes: { bold: true } }, { insert: '\n' }] });
    assert.equal(restrictedResult.html.includes('class-a'), false);
    assert.equal(fullClassImported.html.includes('class-a'), false);
    assert.equal(JSON.stringify(fullClassImported.delta).includes('customKey'), false);
    assert.equal(invalidImported.html.includes('class-'), false);
    assert.equal(JSON.stringify(invalidImported.delta).includes('customKey'), false);
    assert.equal(invalidChange.html.includes('class-a'), true, 'Invalid replacement leaves the existing allowed class unchanged');
    assert.equal(removed.html.includes('class-'), false);
    evidence.final = await snapshot(page);
    await page.screenshot({ path: process.env.SCREENSHOT || 'preview.png', fullPage: true });
  }
  evidence.pass = true;
  console.log('PASS: native paragraph classes survive real editing and three fresh-editor JSON restores; host restrictions preserved.');
} catch (error) {
  evidence.pass = false;
  evidence.error = error.message;
  throw error;
} finally {
  if (process.env.EVIDENCE) await writeFile(process.env.EVIDENCE, JSON.stringify(evidence, null, 2));
  await browser.close();
  if (server) await new Promise((resolve) => server.close(resolve));
}
