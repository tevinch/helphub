const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const { createHash } = require('node:crypto');

function verifyScale(sourceGarden, templateFile, noteCount = 200) {
  sourceGarden = path.resolve(sourceGarden);
  templateFile = path.resolve(templateFile);
  assert.equal(Number(process.versions.node.split('.')[0]), 22, 'Use Node 22, matching the template engine requirement');
  assert.ok(Number.isInteger(noteCount) && noteCount >= 100, 'Scale fixture needs at least 100 notes');
  assert.ok(fs.existsSync(path.join(sourceGarden, 'node_modules/@11ty/eleventy/cmd.cjs')), 'Supply a clean installed Digital Garden 1.96.0');
  const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'navigation-scale-'));
  const garden = path.join(sandbox, 'garden');
  fs.cpSync(sourceGarden, garden, { recursive: true, filter: name =>
    !['node_modules', '.git', 'dist'].includes(path.basename(name)) });
  fs.symlinkSync(path.join(sourceGarden, 'node_modules'), path.join(garden, 'node_modules'), 'dir');
  const { parse } = require(path.join(sourceGarden, 'node_modules/node-html-parser'));
  const results = [];
  const hostHash = createHash('sha256').update(fs.readFileSync(path.join(garden, '.eleventy.js'))).digest('hex');
  const evidenceDir = process.env.NAVIGATION_EVIDENCE_DIR;
  if (evidenceDir) fs.mkdirSync(evidenceDir, { recursive: true });
  const plugin = path.join(garden, 'src/plugins/date-ordered-navigation');
  const templatePath = path.join(plugin, 'filetree.njk');
  const root = path.join(garden, 'src/site/notes');
  try {
    for (const entry of fs.readdirSync(root)) {
      if (!['notes.json', 'notes.11tydata.js'].includes(entry)) fs.rmSync(path.join(root, entry), { recursive: true, force: true });
    }
    for (let i = 0; i < noteCount; i++) {
      const folder = i < noteCount * .6 ? 'Journal' : i < noteCount * .8 ? 'Reference' : 'Projects/Log';
      const name = `Note ${String(i).padStart(5, '0')}`;
      const target = path.join(root, folder, name + '.md');
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, `---\ntitle: ${name}\npermalink: /note-${i}/\ncreated: "${new Date(Date.UTC(2020, 0, 1 + i)).toISOString()}"\nnoteIcon: "🌱"\n${i === noteCount - 1 ? 'dgShowFileTree: false\n' : ''}---\nPreserved ${name}.\n${i === 0 ? '\n<span class="production-minifier-proof" style="color: rgb(255, 0, 0); margin: 0px 0px 0px 0px;">Compression marker</span>\n\n| left | right |\n| --- | --- |\n| A | B |\n' : ''}`);
    }
    fs.writeFileSync(path.join(garden, '.env'), 'SITE_NAME_HEADER=Scale Fixture\nSITE_BASE_URL=https://example.invalid\nBASE_THEME=dark\ndgHomeLink=true\ndgShowFileTree=true\ndgShowInlineTitle=true\ndgEnableSearch=true\nSHOW_CREATED_TIMESTAMP=true\n');
    fs.mkdirSync(plugin, { recursive: true });
    fs.copyFileSync(path.join(__dirname, 'garden-plugin.json'), path.join(plugin, 'garden-plugin.json'));
    fs.writeFileSync(path.join(garden, 'src/plugins/plugins.json'), JSON.stringify({ plugins: {
      'dg-filetree': { enabled: false }, 'date-ordered-navigation': { enabled: true },
    } }));
    const native = fs.readFileSync(path.join(garden, 'src/plugins/dg-filetree/templates/filetree.njk'), 'utf8');
    const candidate = fs.readFileSync(templateFile, 'utf8');
    function build(label, text, timeout) {
      fs.rmSync(path.join(garden, 'dist'), { recursive: true, force: true });
      fs.writeFileSync(templatePath, text);
      const start = performance.now();
      const run = spawnSync(process.execPath, ['node_modules/@11ty/eleventy/cmd.cjs'], {
        cwd: garden, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024, timeout,
        env: { ...process.env, ELEVENTY_ENV: 'prod', UV_THREADPOOL_SIZE: '16', NODE_OPTIONS: '--max-old-space-size=3072' },
      });
      const buildMs = Math.round(performance.now() - start);
      if (evidenceDir) fs.writeFileSync(path.join(evidenceDir, `scale-${noteCount}-${label}.log`), run.stdout + run.stderr);
      assert.equal(run.status, 0, `${label}: full production build did not complete within ${timeout}ms (${run.error?.code || run.signal || run.status}); elapsed ${buildMs}ms\n${run.stderr}`);
      const dist = path.join(garden, 'dist');
      const html = fs.readFileSync(path.join(dist, 'note-0/index.html'), 'utf8');
      const doc = parse(html);
      const nav = doc.querySelector('nav.filetree-sidebar');
      assert.ok(nav, 'The navigation must actually render');
      const hrefs = nav.querySelectorAll('a.filename').map(a => a.getAttribute('href'));
      assert.equal(hrefs.length, noteCount);
      assert.equal(new Set(hrefs).size, noteCount);
      for (let i = 0; i < noteCount; i++) {
        assert.ok(hrefs.includes(`/note-${i}/`), `Navigation retains note ${i}`);
        assert.ok(fs.readFileSync(path.join(dist, `note-${i}/index.html`), 'utf8').includes(`Preserved Note ${String(i).padStart(5, '0')}.`), `Article ${i} completed`);
      }
      const journal = doc.querySelectorAll('.foldername').find(el => el.text.trim() === 'Journal').parentNode.parentNode;
      const journalLinks = journal.querySelectorAll('a.filename').map(a => a.getAttribute('href'));
      const journalEnd = Math.ceil(noteCount * .6);
      const referenceEnd = Math.ceil(noteCount * .8);
      assert.deepEqual(journalLinks, Array.from({ length: journalEnd }, (_, i) => `/note-${label === 'native' ? i : journalEnd - 1 - i}/`), 'Every selected Journal link has the expected order');
      const reference = doc.querySelectorAll('.foldername').find(el => el.text.trim() === 'Reference').parentNode.parentNode;
      assert.deepEqual(reference.querySelectorAll('a.filename').map(a => a.getAttribute('href')), Array.from({ length: referenceEnd - journalEnd }, (_, i) => `/note-${journalEnd + i}/`), 'Untouched Reference keeps its natural order');
      const log = doc.querySelectorAll('.foldername').find(el => el.text.trim() === 'Log').parentNode.parentNode;
      assert.deepEqual(log.querySelectorAll('a.filename').map(a => a.getAttribute('href')), Array.from({ length: noteCount - referenceEnd }, (_, i) => `/note-${label === 'native' ? referenceEnd + i : noteCount - 1 - i}/`), 'Every nested selected Log link has the expected order');
      assert.ok(doc.querySelector('main .table-wrapper table'), 'The native HTML table transformation ran');
      const compressionProof = doc.querySelector('.production-minifier-proof');
      assert.ok(compressionProof, 'Inline compression fixture remains present');
      assert.equal(compressionProof.getAttribute('style'), 'color:red;margin:0', 'Native production minifier transforms inline style');
      const disabled = parse(fs.readFileSync(path.join(dist, `note-${noteCount - 1}/index.html`), 'utf8'));
      assert.equal(disabled.querySelector('nav.filetree-sidebar'), null, 'Per-note filetree=false remains respected');
      assert.ok(disabled.querySelector('.navbar-actions .search-button'));
      assert.equal(createHash('sha256').update(fs.readFileSync(path.join(garden, '.eleventy.js'))).digest('hex'), hostHash, 'Host configuration remains unchanged');
      const row = { label, notes: noteCount, selectedNotes: Math.ceil(noteCount * .6) + noteCount - Math.ceil(noteCount * .8), buildMs, htmlBytes: Buffer.byteLength(html), navBytes: Buffer.byteLength(nav.outerHTML), completedArticles: noteCount, sourceSHA256: createHash('sha256').update(text).digest('hex') };
      results.push(row);
      return row;
    }
    const nativeResult = build('native', native, 600000);
    // Relative to the same fixture on this machine, with room for startup noise.
    const candidateResult = build('date-ordered', candidate, Math.max(15000, nativeResult.buildMs * 3));
    return { mode: 'scripted full production builds; synthetic data; no Forestry account', node: process.version, template: '1.96.0', hostSHA256: hostHash, results, candidateToNativeRatio: candidateResult.buildMs / nativeResult.buildMs };
  } finally {
    fs.rmSync(sandbox, { recursive: true, force: true });
  }
}

module.exports = { verifyScale };
if (require.main === module) {
  if (!process.argv[2]) throw new Error('Usage: node verify-scale.cjs /path/to/clean-installed-digitalgarden-1.96.0 [template.njk] [note-count]');
  console.log(JSON.stringify(verifyScale(process.argv[2], process.argv[3] || path.join(__dirname, 'filetree.njk'), Number(process.argv[4] || 200)), null, 2));
}
