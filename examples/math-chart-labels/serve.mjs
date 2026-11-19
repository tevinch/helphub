import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const types = {'.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.css':'text/css', '.woff2':'font/woff2', '.woff':'font/woff', '.ttf':'font/ttf', '.json':'application/json'};
export async function startServer(port = 4173) {
  const server = http.createServer(async (req,res) => {
    try {
      const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      const file = path.resolve(root, '.' + (name === '/' ? '/index.html' : name));
      if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
      const data = await fs.readFile(file);
      res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream', 'Cache-Control':'no-store'}).end(data);
    } catch {res.writeHead(404).end();}
  });
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  return server;
}
if (path.resolve(process.argv[1] || '') === fileURLToPath(import.meta.url)) {
  const server = await startServer(Number(process.env.PORT || 4173));
  console.log(`Open http://127.0.0.1:${server.address().port}`);
}
