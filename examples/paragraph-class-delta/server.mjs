import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const files = new Map([
  ['/', ['index.html', 'text/html']],
  ['/index.html', ['index.html', 'text/html']],
  ['/app.js', ['app.js', 'text/javascript']],
  ['/paragraph-format.js', ['paragraph-format.js', 'text/javascript']],
  ['/styles.css', ['styles.css', 'text/css']],
  ['/node_modules/quill/dist/quill.js', ['node_modules/quill/dist/quill.js', 'text/javascript']],
  ['/node_modules/quill/dist/quill.snow.css', ['node_modules/quill/dist/quill.snow.css', 'text/css']],
]);

export function createDemoServer() {
  return createServer(async (request, response) => {
    const pathname = new URL(request.url, 'http://127.0.0.1').pathname;
    const entry = files.get(pathname);
    if (request.method !== 'GET' || !entry) {
      response.writeHead(404).end('Not found');
      return;
    }
    try {
      const data = await readFile(new URL(entry[0], import.meta.url));
      response.writeHead(200, { 'Content-Type': `${entry[1]}; charset=utf-8` }).end(data);
    } catch {
      response.writeHead(500).end('Unable to read example file. Run npm ci first.');
    }
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3000);
  createDemoServer().listen(port, '127.0.0.1', () => {
    console.log(`Open http://127.0.0.1:${port}`);
  });
}
