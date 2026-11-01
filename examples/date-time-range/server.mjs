import { build } from 'esbuild';
import http from 'node:http';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const here = fileURLToPath(new URL('.', import.meta.url));
await build({ entryPoints: [here + 'app.jsx'], bundle: true, outdir: here + 'dist',
  loader: { '.css': 'css' }, minify: true, define: { 'process.env.NODE_ENV': '"production"' } });
if (!process.argv.includes('--build')) {
  const assets = { '/': ['index.html', 'text/html'], '/app.js': ['dist/app.js', 'text/javascript'],
    '/app.css': ['dist/app.css', 'text/css'] };
  http.createServer(async (req, res) => {
    const file = assets[new URL(req.url, 'http://localhost').pathname];
    if (!file) { res.writeHead(404); res.end('Not found'); return; }
    res.setHeader('Content-Type', file[1] + '; charset=utf-8');
    try { res.end(await fs.readFile(here + file[0])); }
    catch { res.writeHead(500); res.end('Unable to read page'); }
  }).listen(4176, '127.0.0.1', () => console.log('http://127.0.0.1:4176'));
}
