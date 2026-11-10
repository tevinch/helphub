const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const os = require('node:os');

const sourceGarden = path.resolve(process.argv[2] || '');
if (!process.argv[2] || !fs.existsSync(path.join(sourceGarden, '.eleventy.js')) ||
    !fs.existsSync(path.join(sourceGarden, 'node_modules/@11ty/eleventy/cmd.cjs'))) {
  throw new Error('Usage: node verify.cjs /path/to/clean-installed-digitalgarden-1.96.0');
}
const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'navigation-check-'));
const garden = path.join(sandbox, 'garden');
fs.cpSync(sourceGarden, garden, { recursive: true, filter: (name) =>
  !['node_modules', '.git', 'dist'].includes(path.basename(name)) });
fs.symlinkSync(path.join(sourceGarden, 'node_modules'), path.join(garden, 'node_modules'), 'dir');
const result = [];

const { parse } = require(path.join(garden, 'node_modules/node-html-parser'));
const notes = [
  ['Journal/A old.md', 'Old', '/journal/old/', '2024-12-31T23:59:00Z'],
  ['Journal/B later local.md', 'Later local', '/journal/local/', '2026-11-05T01:00:00+03:00'],
  ['Journal/C newer UTC.md', 'Newer UTC', '/journal/utc/', '2026-11-04T23:00:00Z'],
  ['Journal/D newest.md', 'Newest', '/journal/newest/', '2026-11-06T00:00:00Z'],
  ['Journal/E tied.md', 'Tied', '/journal/tied/', '2026-11-04T23:00:00Z'],
  ['Journal/F missing.md', 'Missing', '/journal/missing/', null],
  ['Journal/G invalid.md', 'Invalid', '/journal/invalid/', 'not-a-date'],
  ['Journal/Z pinned.md', 'Pinned', '/journal/pinned/', '2020-01-01T00:00:00Z', 'pinned: true'],
  ['Journal/Hidden.md', 'Hidden', '/journal/hidden/', '2030-01-01T00:00:00Z', 'hideInFiletree: true'],
  ['Journal/Archive/Old.md', 'Archive old', '/archive/old/', '2020-01-01T00:00:00Z'],
  ['Journal/Archive/New.md', 'Archive new', '/archive/new/', '2026-01-01T00:00:00Z'],
  ['Reference/Note 10.md', 'Reference 10', '/reference/10/', '2030-01-01T00:00:00Z'],
  ['Reference/Note 2.md', 'Reference 2', '/reference/2/', '2020-01-01T00:00:00Z'],
  ['Projects/Log/A old.md', 'Log old', '/log/old/', '2020-01-01T00:00:00Z'],
  ['Projects/Log/Z new.md', 'Log new', '/log/new/', '2026-01-01T00:00:00Z'],
  ['No tree.md', 'Tree disabled', '/tree-disabled/', '2026-01-01T00:00:00Z', 'dgShowFileTree: false'],
];

function prepare() {
  for (const [file, title, url, created, extra = ''] of notes) {
    const target = path.join(garden, 'src/site/notes', file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, `---\ntitle: ${JSON.stringify(title)}\npermalink: ${JSON.stringify(url)}\n${created === null ? '' : `created: ${JSON.stringify(created)}\n`}noteIcon: "🌱"\n${extra}\n---\nContent remains: **${title}**.\n`);
  }
  fs.writeFileSync(path.join(garden, '.env'), 'SITE_NAME_HEADER=Date Order Fixture\nSITE_BASE_URL=https://example.invalid\nBASE_THEME=dark\ndgHomeLink=true\ndgShowFileTree=true\ndgShowInlineTitle=true\ndgEnableSearch=true\nSHOW_CREATED_TIMESTAMP=true\n');
  for (const [slot, content] of [['beforeTitle', 'Existing before-title content'], ['afterTitle', 'Existing after-title content']]) {
    const target = path.join(garden, 'src/site/_includes/components/user/filetree', slot, 'existing.njk');
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, `<p class="existing-${slot}">${content}</p>`);
  }
}

function build(label) {
  const start = performance.now();
  const result = spawnSync(process.execPath, ['node_modules/@11ty/eleventy/cmd.cjs'], {
    cwd: garden, encoding: 'utf8', env: { ...process.env, ELEVENTY_ENV: 'dev' },
  });
  if (result.status !== 0) process.stderr.write(result.stdout + result.stderr);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  return Math.round(performance.now() - start);
}

function rowsFor(doc, name) {
  const label = doc.querySelectorAll('.foldername').find((el) => el.text.trim() === name);
  assert.ok(label, `Folder ${name} must render`);
  const folder = label.parentNode.parentNode;
  return folder.childNodes.filter((el) => el.classList?.contains('filelist'))
    .map((el) => el.childNodes.find((child) => child.tagName === 'DIV')).filter(Boolean).map((entry) => {
    return entry.classList.contains('folder')
      ? `folder:${entry.querySelector('.foldername').text.trim()}`
      : entry.querySelector('a.filename').text.trim();
  });
}

function inspect(label, changed = false) {
  const file = path.join(garden, 'dist/journal/utc/index.html');
  const doc = parse(fs.readFileSync(file, 'utf8'));
  assert.equal(doc.querySelector('nav.filetree-sidebar h1').text.trim(), 'Date Order Fixture');
  assert.deepEqual(rowsFor(doc, 'Journal'), [
    'Pinned', 'folder:Archive', ...(changed
      ? ['Old', 'Newest', 'Newer UTC', 'Tied', 'Later local', 'Missing', 'Invalid']
      : ['Newest', 'Newer UTC', 'Tied', 'Later local', 'Old', 'Missing', 'Invalid']),
  ]);
  assert.deepEqual(rowsFor(doc, 'Reference'), ['Reference 2', 'Reference 10']);
  assert.deepEqual(rowsFor(doc, 'Archive'), ['Archive new', 'Archive old']);
  assert.deepEqual(rowsFor(doc, 'Log'), ['Log new', 'Log old']);
  assert.equal(doc.querySelectorAll('a.filename').some((a) => a.text.trim() === 'Hidden'), false);
  const current = doc.querySelector('.notelink.active-note a');
  assert.equal(current.getAttribute('href'), '/journal/utc/');
  assert.equal(current.getAttribute('data-note-icon'), '🌱');
  assert.ok(doc.querySelector('nav.filetree-sidebar .existing-beforeTitle'));
  assert.ok(doc.querySelector('nav.filetree-sidebar .existing-afterTitle'));
  assert.ok(doc.querySelector('.filetree-sidebar .search-button'), 'Existing search slot remains');
  assert.equal(doc.querySelector('main .human-date').getAttribute('data-date'), '2026-11-04T23:00:00Z', 'Page timestamp remains unchanged');
  const disabled = parse(fs.readFileSync(path.join(garden, 'dist/tree-disabled/index.html'), 'utf8'));
  assert.equal(disabled.querySelector('nav.filetree-sidebar'), null, 'Honor per-note filetree=false');
  assert.ok(disabled.querySelector('.navbar-actions .search-button'), 'Fallback navigation search slot remains');
  for (const [, title, url] of notes) {
    const output = fs.readFileSync(path.join(garden, 'dist', url, 'index.html'), 'utf8');
    assert.ok(output.includes(`Content remains: <strong>${title}</strong>`), `${title}: article content preserved`);
  }

}

const plugin = path.join(garden, 'src/plugins/date-ordered-navigation');
const templatePath = path.join(plugin, 'filetree.njk');
const template = fs.readFileSync(path.join(__dirname, 'filetree.njk'), 'utf8');
try {
  // These are synthetic notes in a disposable source copy. Your supplied directory is read-only.
  fs.rmSync(path.join(garden, 'src/site/notes'), { recursive: true, force: true });
  fs.mkdirSync(path.join(garden, 'src/site/notes'), { recursive: true });
  fs.copyFileSync(path.join(sourceGarden, 'src/site/notes/notes.json'), path.join(garden, 'src/site/notes/notes.json'));
  fs.copyFileSync(path.join(sourceGarden, 'src/site/notes/notes.11tydata.js'), path.join(garden, 'src/site/notes/notes.11tydata.js'));
  prepare();
  fs.mkdirSync(plugin, { recursive: true });
  fs.copyFileSync(path.join(__dirname, 'garden-plugin.json'), path.join(plugin, 'garden-plugin.json'));
  fs.writeFileSync(path.join(garden, 'src/plugins/plugins.json'), JSON.stringify({ plugins: {
    'dg-filetree': { enabled: false }, 'date-ordered-navigation': { enabled: true },
  } }));
  // Start from the native template under the same custom-plugin registration.
  fs.copyFileSync(path.join(garden, 'src/plugins/dg-filetree/templates/filetree.njk'), templatePath);
  let buildMs = build('native');
  assert.throws(() => inspect('native'), { code: 'ERR_ASSERTION' });
  result.push({ operation: 'native chronological-order negative control', status: 'failed as required', buildMs });
  fs.writeFileSync(templatePath, template);
  buildMs = build('custom');
  inspect('custom');
  result.push({ operation: 'custom template, full generated navigation and articles', status: 'passed', buildMs });
  const oldNote = path.join(garden, 'src/site/notes/Journal/A old.md');
  fs.writeFileSync(oldNote, fs.readFileSync(oldNote, 'utf8').replace('2024-12-31T23:59:00Z', '2040-01-01T00:00:00Z'));
  buildMs = build('changed');
  inspect('changed', true);
  result.push({ operation: 'change creation date and rebuild', status: 'passed', buildMs });
  const missingIndex = template.replace(/\{% set navigationNotesByUrl = .*? %\}/,
    '{% set navigationNotesByUrl = {} %}');
  assert.notEqual(missingIndex, template);
  fs.writeFileSync(templatePath, missingIndex);
  buildMs = build('missing-index');
  assert.throws(() => inspect('missing-index', true), { code: 'ERR_ASSERTION' });
  result.push({ operation: 'missing date-index negative control', status: 'failed as required', buildMs });
  fs.writeFileSync(templatePath, template);
  buildMs = build('restored');
  inspect('restored', true);
  result.push({ operation: 'restore exact template and rebuild', status: 'passed', buildMs });
  assert.equal(fs.readFileSync(templatePath, 'utf8'), template);
  console.log(JSON.stringify({ template: '1.96.0', mode: 'scripted full Eleventy builds', notes: notes.length, result }, null, 2));
} finally {
  fs.rmSync(sandbox, { recursive: true, force: true });
}
