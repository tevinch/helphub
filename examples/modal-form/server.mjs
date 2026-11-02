import http from 'node:http';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { itemSchema, initialDocument } from './schema.mjs';

const dataFile = resolve(process.env.MODAL_FORM_DATA_FILE ?? '.data/item.json');
await mkdir(dirname(dataFile), { recursive: true });
try { await readFile(dataFile); }
catch (error) {
  if (error.code !== 'ENOENT') throw error;
  await writeFile(dataFile, JSON.stringify(initialDocument, null, 2));
}

const files = new Map([
  ['/', ['dist/index.html', 'text/html']],
  ['/app.js', ['dist/app.js', 'text/javascript']],
  ['/style.css', ['dist/style.css', 'text/css']],
]);
const server = http.createServer(async (request, response) => {
  response.setHeader('Cache-Control', 'no-store');
  try {
    if (request.url === '/api/item') {
      response.setHeader('Content-Type', 'application/json');
      if (request.method === 'GET') {
        response.end(await readFile(dataFile));
        return;
      }
      if (request.method === 'POST') {
        const chunks = [];
        let bytes = 0;
        for await (const part of request) {
          bytes += part.length;
          if (bytes > 16384) { response.writeHead(413).end(); return; }
          chunks.push(part);
        }
        const body = Buffer.concat(chunks, bytes).toString('utf8');
        const result = itemSchema.safeParse(JSON.parse(body));
        if (!result.success) {
          response.writeHead(422).end(JSON.stringify({ error: 'Invalid item.' }));
          return;
        }
        const current = JSON.parse(await readFile(dataFile, 'utf8'));
        const saved = { ...current, item: { ...current.item, ...result.data }, revision: current.revision + 1 };
        await writeFile(`${dataFile}.tmp`, JSON.stringify(saved, null, 2));
        await rename(`${dataFile}.tmp`, dataFile);
        response.end(JSON.stringify(saved));
        return;
      }
      response.writeHead(405).end();
      return;
    }
    const file = files.get(request.url);
    if (!file || request.method !== 'GET') { response.writeHead(404).end(); return; }
    response.setHeader('Content-Type', file[1]);
    response.end(await readFile(file[0]));
  } catch (error) {
    console.error(error.message);
    response.writeHead(500).end(JSON.stringify({ error: 'Could not save.' }));
  }
});
server.listen(Number(process.env.PORT ?? 4173), '127.0.0.1', () => {
  console.log(`http://127.0.0.1:${server.address().port}`);
});
