const test = require('node:test');
const assert = require('node:assert/strict');
const run = require('../open-folder-comparison.js');

class MarkdownView {}
function context(folder = 'Compare', names = ['Note 10.md', 'Note 2.md', 'Alpha.md']) {
  const origin = { id: 'original' };
  let scroll = { top: 2342, left: 12 };
  const view = Object.assign(new MarkdownView(), { file: { parent: { path: folder } }, leaf: origin, editor: { getScrollInfo: () => ({ ...scroll }), scrollTo(left, top) { scroll = { left, top }; } } });
  const files = names.map(name => ({ name, path: folder ? `${folder}/${name}` : name, parent: { path: folder } }));
  files.push({ name: 'Nested.md', path: `${folder}/Nested/Nested.md`, parent: { path: `${folder}/Nested` } });
  files.push({ name: 'Unrelated.md', path: 'Other/Unrelated.md', parent: { path: 'Other' } });
  const opened = [], notices = [];
  let currentView = view;
  let active = origin;
  const workspace = {
    getActiveViewOfType(type) { assert.equal(type, MarkdownView); return currentView; },
    setActiveLeaf(leaf, options) { assert.equal(options.focus, true); active = leaf; scroll = { top: 0, left: 0 }; },
    createLeafBySplit(anchor, direction, before) {
      const leaf = { id: `new-${opened.length}`, async openFile(file, options) {
        opened.push({ file: file.path, anchor: anchor.id, leaf: leaf.id, direction, before, options });
      } };
      active = leaf; // Native split creation activates the new pane.
      return leaf;
    },
  };
  return { app: { workspace, vault: { getMarkdownFiles: () => files } },
    obsidian: { MarkdownView, Notice: class { constructor(text) { notices.push(text); } } },
    opened, notices, origin, view, files, activeLeaf: () => active, scrollInfo: () => ({ ...scroll }), setView(value) { currentView = value; } };
}

test('opens only immediate Markdown children in numeric filename order, in successive right splits with focus off', async () => {
  const ctx = context();
  await run(ctx);
  assert.deepEqual(ctx.opened.map(x => x.file), ['Compare/Alpha.md', 'Compare/Note 2.md', 'Compare/Note 10.md']);
  assert.deepEqual(ctx.opened.map(x => x.anchor), ['original', 'new-0', 'new-1']);
  assert.ok(ctx.opened.every(x => x.direction === 'vertical' && x.before === false && x.options.active === false));
  assert.equal(ctx.notices.length, 0);
});

test('resolves the current folder on every invocation, including the vault root', async () => {
  const ctx = context('', ['Root 20.md', 'Root 3.md']);
  await run(ctx);
  assert.deepEqual(ctx.opened.map(x => x.file), ['Root 3.md', 'Root 20.md']);
  ctx.opened.length = 0;
  ctx.view.file.parent.path = 'Other';
  await run(ctx);
  assert.deepEqual(ctx.opened.map(x => x.file), ['Other/Unrelated.md']);
});

test('an absent active Markdown view changes no layout and permits a later valid run', async () => {
  const ctx = context();
  ctx.setView(null);
  await run(ctx);
  assert.equal(ctx.opened.length, 0);
  assert.equal(ctx.notices.length, 1);
  assert.match(ctx.notices[0], /Markdown note/i);
  ctx.setView(ctx.view);
  await run(ctx);
  assert.equal(ctx.opened.length, 3);
});

test('the macro promise waits for each real file opening to complete', async () => {
  const ctx = context('Compare', ['One.md', 'Two.md']);
  const opened = [];
  let release;
  ctx.app.workspace.createLeafBySplit = () => ({ async openFile(file) {
    opened.push(file.name);
    if (opened.length === 1) await new Promise(resolve => { release = resolve; });
  } });
  let done = false;
  const pending = run(ctx).then(() => { done = true; });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(opened, ['One.md']);
  assert.equal(done, false);
  release();
  await pending;
  assert.deepEqual(opened, ['One.md', 'Two.md']);
  assert.equal(done, true);
});

test('restores the original pane after host split creation activates new panes', async () => {
  const ctx = context();
  await run(ctx);
  assert.equal(ctx.activeLeaf(), ctx.origin);
});

test('restores nonzero editor scroll offsets after returning to the starting pane', async () => {
  const ctx = context();
  const before = ctx.scrollInfo();
  await run(ctx);
  assert.deepEqual(ctx.scrollInfo(), before);
});
