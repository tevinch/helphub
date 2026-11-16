import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const app = path.resolve(process.argv[2] || '.');
const manifest = JSON.parse(await readFile(path.join(app, 'public/build/manifest.json'), 'utf8'));
const entry = manifest['resources/js/app.tsx'];
assert(entry?.isEntry && entry.file, 'Build the Laravel starter client entry first.');
const styles = new Set();
const seen = new Set();
function collect(key) {
    if (seen.has(key)) return;
    seen.add(key);
    const chunk = manifest[key];
    assert(chunk, `Missing manifest entry: ${key}`);
    for (const css of chunk.css || []) styles.add(css);
    for (const imported of chunk.imports || []) collect(imported);
}
collect('resources/js/app.tsx');
const page = JSON.stringify({
    component: 'component-check', props: {}, url: '/component-check.html', version: null,
}).replaceAll('&', '&amp;').replaceAll("'", '&#39;').replaceAll('<', '&lt;');
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Isolated client component check</title>
${[...styles].map((css) => `<link rel="stylesheet" href="/build/${css}">`).join('\n')}
</head><body><div id="app" data-page='${page}'></div>
<script type="module" src="/build/${entry.file}"></script></body></html>
`;
await writeFile(path.join(app, 'public/component-check.html'), html);
console.log(JSON.stringify({ clientEntry: entry.file, styles: [...styles], html: 'public/component-check.html' }));
