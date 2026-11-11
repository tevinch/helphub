import http from 'node:http';
import { readFile } from 'node:fs/promises';

const files = new Map([
  ['/', ['dist/index.html', 'text/html; charset=utf-8']],
  ['/main.js', ['dist/main.js', 'text/javascript; charset=utf-8']],
]);
const server = http.createServer(async (request, response) => {
  const file = files.get(new URL(request.url, 'http://localhost').pathname);
  if (!file) { response.writeHead(404); response.end('Not found'); return; }
  try {
    const body = await readFile(file[0]);
    response.writeHead(200, { 'Content-Type': file[1], 'Cache-Control': 'no-store' });
    response.end(body);
  } catch {
    response.writeHead(500); response.end('Build the example first with npm run build');
  }
});
server.listen(Number(process.env.PORT ?? 4173), '127.0.0.1', () => {
  console.log(`http://127.0.0.1:${server.address().port}`);
});
