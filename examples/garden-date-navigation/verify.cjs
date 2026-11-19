const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const os = require('node:os');

assert.equal(Number(process.versions.node.split('.')[0]), 22, 'Use Node 22, matching the template engine requirement');
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
  ['Journal/Archive/Old.md', 'Archive old', '/archive/old/', '2030-01-01T00:00:00Z'],
  ['Journal/Archive/New.md', 'Archive new', '/archive/new/', '2020-01-01T00:00:00Z'],
  ['Reference/Note 10.md', 'Reference 10', '/reference/10/', '2030-01-01T00:00:00Z'],
  ['Reference/Note 2.md', 'Reference 2', '/reference/2/', '2020-01-01T00:00:00Z'],
  ['Projects/Log/A old.md', 'Log old', '/log/old/', '2020-01-01T00:00:00Z'],
  ['Projects/Log/Z new.md', 'Log new', '/log/new/', '2026-01-01T00:00:00Z'],
  ['JournalExtra/Note 10.md', 'Extra 10', '/extra/10/', '2030-01-01T00:00:00Z'],
  ['JournalExtra/Note 2.md', 'Extra 2', '/extra/2/', '2020-01-01T00:00:00Z'],
  ['No tree.md', 'Tree disabled', '/tree-disabled/', '2026-01-01T00:00:00Z', 'dgShowFileTree: false'],
];

function prepare() {
  for (const [file, title, url, created, extra = ''] of notes) {
    const target = path.join(garden, 'src/site/notes', file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, `---\ntitle: ${JSON.stringify(title)}\npermalink: ${JSON.stringify(url)}\n${created === null ? '' : `created: ${JSON.stringify(created)}\n`}noteIcon: "🌱"\n${extra}\n---\nContent remains: **${title}**.\n\n<span class="production-minifier-proof" style="color: rgb(255, 0, 0); margin: 0px 0px 0px 0px;">Compression marker</span>\n\n| left | right |\n| --- | --- |\n| A | B |\n`);
  }
  fs.writeFileSync(path.join(garden, '.env'), 'SITE_NAME_HEADER=Date Order Fixture\nSITE_BASE_URL=https://example.invalid\nBASE_THEME=dark\ndgHomeLink=true\ndgShowFileTree=true\ndgShowInlineTitle=true\ndgEnableSearch=true\nSHOW_CREATED_TIMESTAMP=true\n');
  for (const [slot, content] of [['beforeTitle', 'Existing before-title content'], ['afterTitle', 'Existing after-title content']]) {
    const target = path.join(garden, 'src/site/_includes/components/user/filetree', slot, 'existing.njk');
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, `<p class="existing-${slot}">${content}</p>`);
  }
}

function build(label) {
  fs.rmSync(path.join(garden, 'dist'), { recursive: true, force: true });
  const syncedRoot = path.join(garden, 'src/site/_includes/plugins');
  fs.rmSync(syncedRoot, { recursive: true, force: true });
  const start = performance.now();
  const result = spawnSync(process.execPath, ['node_modules/@11ty/eleventy/cmd.cjs'], {
    cwd: garden, encoding: 'utf8', timeout: 120000, maxBuffer: 32 * 1024 * 1024, env: { ...process.env, ELEVENTY_ENV: label === 'dev-minifier-control' ? 'dev' : 'prod', NODE_ENV: label === 'dev-minifier-control' ? 'development' : 'production' },
  });
  if (process.env.NAVIGATION_EVIDENCE_DIR) {
    fs.mkdirSync(process.env.NAVIGATION_EVIDENCE_DIR, { recursive: true });
    fs.writeFileSync(path.join(process.env.NAVIGATION_EVIDENCE_DIR, `small-${label}.log`), result.stdout + result.stderr);
  }
  if (result.status !== 0) process.stderr.write(result.stdout + result.stderr);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const synced = path.join(syncedRoot, 'date-ordered-navigation/filetree.njk');
  const compiledStyle = path.join(garden, 'dist/plugins/date-ordered-navigation/fixture.css');
  if (label === 'missing-registration') {
    assert.equal(fs.existsSync(synced), false);
    assert.equal(fs.existsSync(compiledStyle), false);
  } else {
    assert.equal(fs.readFileSync(synced, 'utf8'), fs.readFileSync(templatePath, 'utf8'), 'Native before-hook synchronized the exact custom template');
    assert.equal(fs.readFileSync(compiledStyle, 'utf8'), '.navigation-fixture{color:#123456}', 'Native after-hook compiled the disposable fixture style');
  }
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

function assertProductionCompression(doc) {
  const proof = doc.querySelector('.production-minifier-proof');
  assert.ok(proof, 'Inline compression fixture remains present');
  assert.equal(proof.getAttribute('style'), 'color:red;margin:0', 'Native production minifier transforms inline style');
}

function inspect(label, changed = false, added = false) {
  const file = path.join(garden, 'dist/journal/utc/index.html');
  const doc = parse(fs.readFileSync(file, 'utf8'));
  assert.equal(doc.querySelector('nav.filetree-sidebar h1').text.trim(), 'Date Order Fixture');
  if (label !== 'native') assert.ok(doc.querySelector('template[data-navigation-fixture="date-order"]'), 'Custom navigation provider must run');
  assert.deepEqual(rowsFor(doc, 'Journal'), [
    'Pinned', 'folder:Archive', ...(added ? ['Added'] : []), ...(changed
      ? ['Old', 'Newest', 'Newer UTC', 'Tied', 'Later local', 'Missing', 'Invalid']
      : ['Newest', 'Newer UTC', 'Tied', 'Later local', 'Old', 'Missing', 'Invalid']),
  ], 'Selected Journal chronology');
  assert.deepEqual(rowsFor(doc, 'Reference'), ['Reference 2', 'Reference 10']);
  assert.deepEqual(rowsFor(doc, 'Archive'), ['Archive new', 'Archive old']);
  assert.deepEqual(rowsFor(doc, 'JournalExtra'), ['Extra 2', 'Extra 10']);
  assert.deepEqual(rowsFor(doc, 'Log'), ['Log new', 'Log old']);
  assert.ok(doc.querySelector('main .table-wrapper table'), 'Native table transformation ran');
  assertProductionCompression(doc);
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
const templateSource = fs.readFileSync(path.join(__dirname, 'filetree.njk'), 'utf8');
// Fixture-only marker proves the registered provider rendered; it is not part of the recipe.
const template = '<template data-navigation-fixture="date-order"></template>\n' + templateSource;
try {
  // These are synthetic notes in a disposable source copy. Your supplied directory is read-only.
  fs.rmSync(path.join(garden, 'src/site/notes'), { recursive: true, force: true });
  fs.mkdirSync(path.join(garden, 'src/site/notes'), { recursive: true });
  fs.copyFileSync(path.join(sourceGarden, 'src/site/notes/notes.json'), path.join(garden, 'src/site/notes/notes.json'));
  fs.copyFileSync(path.join(sourceGarden, 'src/site/notes/notes.11tydata.js'), path.join(garden, 'src/site/notes/notes.11tydata.js'));
  prepare();
  fs.mkdirSync(plugin, { recursive: true });
  const fixtureManifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'garden-plugin.json'), 'utf8'));
  fixtureManifest.styles = ['fixture.scss'];
  fs.writeFileSync(path.join(plugin, 'garden-plugin.json'), JSON.stringify(fixtureManifest));
  fs.writeFileSync(path.join(plugin, 'fixture.scss'), '.navigation-fixture { color: #123456; }');
  fs.writeFileSync(path.join(garden, 'src/plugins/plugins.json'), JSON.stringify({ plugins: {
    'dg-filetree': { enabled: false }, 'date-ordered-navigation': { enabled: true },
  } }));
  // Start from the native template under the same custom-plugin registration.
  fs.copyFileSync(path.join(garden, 'src/plugins/dg-filetree/templates/filetree.njk'), templatePath);
  let buildMs = build('native');
  assert.throws(() => inspect('native'), /Selected Journal chronology/);
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
  notes.push(['Journal/Y added.md', 'Added', '/journal/added/', '2050-01-01T00:00:00Z']);
  prepare();
  // prepare writes the original fixture too; retain the earlier creation-date edit.
  fs.writeFileSync(oldNote, fs.readFileSync(oldNote, 'utf8').replace('2024-12-31T23:59:00Z', '2040-01-01T00:00:00Z'));
  buildMs = build('added');
  inspect('added', true, true);
  result.push({ operation: 'add note and rebuild, retaining changed date and all article bodies', status: 'passed', buildMs });
  notes.pop();
  fs.rmSync(path.join(garden, 'src/site/notes/Journal/Y added.md'));
  buildMs = build('deleted');
  inspect('deleted', true);
  assert.equal(fs.existsSync(path.join(garden, 'dist/journal/added/index.html')), false, 'Fresh build removes deleted article output');
  const deletedDoc = parse(fs.readFileSync(path.join(garden, 'dist/journal/utc/index.html'), 'utf8'));
  assert.equal(deletedDoc.querySelectorAll('a.filename').some(a => a.getAttribute('href') === '/journal/added/'), false, 'Deleted note leaves navigation');
  result.push({ operation: 'delete added note and rebuild without stale navigation or article', status: 'passed', buildMs });
  const envPath = path.join(garden, '.env');
  const enabledEnv = fs.readFileSync(envPath, 'utf8');
  fs.writeFileSync(envPath, enabledEnv.replace('dgShowFileTree=true', 'dgShowFileTree=false'));
  buildMs = build('global-disabled');
  for (const [, title, url] of notes) {
    const output = fs.readFileSync(path.join(garden, 'dist', url, 'index.html'), 'utf8');
    const doc = parse(output);
    assert.equal(doc.querySelector('nav.filetree-sidebar'), null, 'Respect global filetree=false');
    assert.ok(doc.querySelector('.navbar-actions .search-button'), 'Retain fallback search');
    assert.ok(output.includes(`Content remains: <strong>${title}</strong>`));
  }
  result.push({ operation: 'global filetree=false, all articles and fallback search remain', status: 'passed', buildMs });
  fs.writeFileSync(envPath, enabledEnv);
  buildMs = build('global-restored');
  inspect('global-restored', true);
  result.push({ operation: 'restore global setting and repeat chronology/navigation', status: 'passed', buildMs });
  const missingIndex = template.replace(/\{% set navigationNotesByUrl = .*? %\}/,
    '{% set navigationNotesByUrl = {} %}');
  assert.notEqual(missingIndex, template);
  fs.writeFileSync(templatePath, missingIndex);
  buildMs = build('missing-index');
  assert.throws(() => inspect('missing-index', true), /Selected Journal chronology/);
  result.push({ operation: 'missing date-index negative control', status: 'failed as required', buildMs });
  fs.writeFileSync(templatePath, template);
  fs.writeFileSync(path.join(garden, 'src/plugins/plugins.json'), JSON.stringify({ plugins: {
    'dg-filetree': { enabled: true }, 'date-ordered-navigation': { enabled: false },
  } }));
  buildMs = build('missing-registration');
  const withoutProvider = parse(fs.readFileSync(path.join(garden, 'dist/journal/utc/index.html'), 'utf8'));
  assert.throws(() => assert.ok(withoutProvider.querySelector('template[data-navigation-fixture="date-order"]'), 'Custom navigation provider must run'), /Custom navigation provider must run/);
  result.push({ operation: 'omitted custom registration fails the independent provider marker', status: 'failed as required', buildMs });
  fs.writeFileSync(path.join(garden, 'src/plugins/plugins.json'), JSON.stringify({ plugins: {
    'dg-filetree': { enabled: false }, 'date-ordered-navigation': { enabled: true },
  } }));
  buildMs = build('dev-minifier-control');
  const uncompressed = parse(fs.readFileSync(path.join(garden, 'dist/journal/utc/index.html'), 'utf8'));
  assert.equal(uncompressed.querySelector('.production-minifier-proof').getAttribute('style'), 'color: rgb(255, 0, 0); margin: 0px 0px 0px 0px;');
  assert.throws(() => assertProductionCompression(uncompressed), /Native production minifier transforms inline style/);
  result.push({ operation: 'development build fails the independent production compression marker', status: 'failed as required', buildMs });
  buildMs = build('restored');
  inspect('restored', true);
  result.push({ operation: 'restore exact template and rebuild', status: 'passed', buildMs });
  assert.equal(fs.readFileSync(templatePath, 'utf8'), template);
  const scale = process.argv.includes('--small-only') ? null : require('./verify-scale.cjs').verifyScale(sourceGarden, path.join(__dirname, 'filetree.njk'), 200);
  console.log(JSON.stringify({ template: '1.96.0', node: process.version, mode: 'scripted full production Eleventy builds', notes: notes.length, result, scale }, null, 2));
} finally {
  fs.rmSync(sandbox, { recursive: true, force: true });
}
