import http from 'node:http';
import fs from 'node:fs/promises';
const assets = {
  '/': ['index.html', 'text/html'], '/canvas-control.html': ['canvas-control.html', 'text/html'],
  '/main.mjs': ['main.mjs', 'text/javascript'], '/legend.mjs': ['legend.mjs', 'text/javascript'],
  '/style.css': ['style.css', 'text/css'],
  '/chart.js': ['node_modules/chart.js/dist/chart.umd.min.js', 'text/javascript'],
};
http.createServer(async (req, res) => {
  const asset = assets[new URL(req.url, 'http://localhost').pathname];
  if (!asset) { res.writeHead(404); res.end('Not found'); return; }
  res.setHeader('Content-Type', asset[1] + '; charset=utf-8');
  try { res.end(await fs.readFile(new URL(asset[0], import.meta.url))); }
  catch { res.writeHead(500); res.end('Unable to read page'); }
}).listen(4177, '127.0.0.1', () => console.log('http://127.0.0.1:4177'));
