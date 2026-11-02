import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';

const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.mjs', ['app.mjs', 'text/javascript; charset=utf-8']],
  ['/style.css', ['style.css', 'text/css; charset=utf-8']],
  ['/dist/schema.js', ['dist/schema.js', 'text/javascript; charset=utf-8']],
  ['/vendor/valibot.js', ['node_modules/valibot/dist/index.mjs', 'text/javascript; charset=utf-8']],
]);
const server = createServer(async (request, response) => {
  const file = files.get(new URL(request.url, 'http://127.0.0.1').pathname);
  if (!file || !['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(404).end('Not found');
    return;
  }
  try {
    const contents = await readFile(new URL(file[0], import.meta.url));
    response.writeHead(200, { 'Content-Type': file[1], 'Cache-Control': 'no-store' });
    response.end(request.method === 'HEAD' ? undefined : contents);
  } catch {
    response.writeHead(500).end('Run npm ci and npm run build first.');
  }
});
server.listen(Number(process.env.PORT ?? 4173), '127.0.0.1', () => {
  console.log(`Open http://127.0.0.1:${server.address().port}`);
});
