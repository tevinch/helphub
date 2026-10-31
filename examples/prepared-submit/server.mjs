import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname } from 'node:path';

// Local demonstration only: receipts last until this process stops.
const receipts = [];
const root = resolve(fileURLToPath(new URL('./dist/', import.meta.url)));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
const server = createServer(async (request, response) => {
  try {
    const path = new URL(request.url, 'http://localhost').pathname;
    if (path === '/api/documents' && request.method === 'GET') {
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify(receipts));
    } else if (path === '/api/documents' && request.method === 'POST') {
      let body = '';
      for await (const chunk of request) body += chunk;
      const { source, document } = JSON.parse(body);
      const receipt = { id: receipts.length + 1, source, document };
      receipts.push(receipt);
      response.writeHead(201, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify(receipt));
    } else if (request.method === 'GET') {
      const file = resolve(root, `.${path === '/' ? '/index.html' : path}`);
      if (!file.startsWith(`${root}/`)) { response.writeHead(404); response.end(); return; }
      response.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
      response.end(await readFile(file));
    } else { response.writeHead(405); response.end(); }
  } catch {
    if (!response.headersSent) response.writeHead(400);
    response.end('Request could not be processed');
  }
});
server.listen(Number(process.env.PORT || 4173), '127.0.0.1', () => {
  console.log(`LISTEN=http://127.0.0.1:${server.address().port}`);
});
