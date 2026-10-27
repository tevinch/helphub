import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { hasMeaningfulContent } from './content.mjs';

const files = new Map([
  ['/', ['index.html', 'text/html']],
  ['/app.mjs', ['app.mjs', 'text/javascript']],
  ['/content.mjs', ['content.mjs', 'text/javascript']],
  ['/node_modules/quill/dist/quill.js', ['node_modules/quill/dist/quill.js', 'text/javascript']],
  ['/node_modules/quill/dist/quill.snow.css', ['node_modules/quill/dist/quill.snow.css', 'text/css']],
]);

export function createDemoServer() {
  let number = 0;
  return createServer(async (request, response) => {
    if (request.method === 'POST' && request.url === '/submit') {
      try {
        let body = '';
        for await (const part of request) body += part;
        const delta = JSON.parse(body);
        if (!hasMeaningfulContent(delta)) {
          response.writeHead(422, { 'Content-Type': 'application/json' });
          response.end(JSON.stringify({ error: 'Content is required' }));
          return;
        }
        response.writeHead(200, { 'Content-Type': 'application/json' });
        response.end(JSON.stringify({ id: ++number, delta }));
      } catch {
        response.writeHead(400); response.end('Invalid JSON Delta');
      }
      return;
    }
    const file = files.get(request.url);
    if (request.method !== 'GET' || !file) { response.writeHead(404); response.end(); return; }
    try {
      const data = await readFile(new URL(file[0], import.meta.url));
      response.writeHead(200, { 'Content-Type': file[1] }); response.end(data);
    } catch { response.writeHead(500); response.end('Could not load example'); }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  createDemoServer().listen(3000, '127.0.0.1', () => {
    console.log('Open http://127.0.0.1:3000');
  });
}
