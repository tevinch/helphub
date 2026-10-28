import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const versions = { '2.0.11': 'htmx-two', '4.0.0': 'htmx-four' };
const cities = {
  fr: [['paris', 'Paris'], ['lyon', 'Lyon']],
  de: [['berlin', 'Berlin'], ['hamburg', 'Hamburg']],
  be: [['brussels', 'Brussels'], ['antwerp', 'Antwerp']],
};
const escape = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]));

function citySelect(group, country = '') {
  return `<select id="${group}" name="${group}" data-country="${escape(country)}"
    hx-post="/cities/${group}" hx-trigger="input from:[data-source~=${group}]"
    hx-swap="outerHTML">
    <option value="">Choose a city</option>
    ${(cities[country] || []).map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}
  </select>`;
}

export function createExampleServer() {
  const requests = [];
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, 'http://localhost');
    response.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; object-src 'none'");
    response.setHeader('Cache-Control', 'no-store');
    try {
      if (request.method === 'GET' && url.pathname === '/') {
        const version = url.searchParams.get('version') || '2.0.11';
        if (!Object.hasOwn(versions, version)) {
          response.writeHead(400).end('Unknown example version');
          return;
        }
        const template = await readFile(new URL('./index.html', import.meta.url), 'utf8');
        response.setHeader('Content-Type', 'text/html; charset=utf-8');
        response.end(template.replaceAll('__VERSION__', version)
          .replace('__CITY__', citySelect('city'))
          .replace('__SHIPPING_CITY__', citySelect('shipping_city')));
        return;
      }
      const libraryVersion = /^\/htmx\/(2\.0\.11|4\.0\.0)\.js$/.exec(url.pathname)?.[1];
      if (request.method === 'GET' && libraryVersion) {
        response.setHeader('Content-Type', 'text/javascript; charset=utf-8');
        response.end(await readFile(new URL(`./node_modules/${versions[libraryVersion]}/dist/htmx.min.js`, import.meta.url)));
        return;
      }
      if (request.method === 'GET' && url.pathname === '/style.css') {
        response.setHeader('Content-Type', 'text/css; charset=utf-8');
        response.end(await readFile(new URL('./style.css', import.meta.url)));
        return;
      }
      if (request.method === 'POST' && ['/cities/city', '/cities/shipping_city', '/submit'].includes(url.pathname)) {
        let body = '';
        for await (const chunk of request) {
          body += chunk;
          if (Buffer.byteLength(body) > 16_384) {
            response.writeHead(413).end('Form is too large');
            return;
          }
        }
        const fields = Object.fromEntries(new URLSearchParams(body));
        requests.push({ path: url.pathname, fields });
        response.setHeader('Content-Type', 'text/html; charset=utf-8');
        if (url.pathname === '/submit') {
          response.end(`<!doctype html><html lang="en"><meta charset="utf-8"><title>Submitted form</title><h1>Submitted form</h1><pre id="result">${escape(JSON.stringify(fields, null, 2))}</pre><p><a href="/">Start again</a></p></html>`);
        } else {
          const group = url.pathname.endsWith('/shipping_city') ? 'shipping_city' : 'city';
          const country = fields[group === 'city' ? 'country' : 'shipping_country'] || '';
          response.end(citySelect(group, Object.hasOwn(cities, country) ? country : ''));
        }
        return;
      }
      response.writeHead(404).end('Not found');
    } catch {
      response.writeHead(500).end('The example could not complete this request');
    }
  });
  return { server, requests };
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const { server } = createExampleServer();
  const port = Number(process.env.PORT || 3000);
  server.listen(port, '127.0.0.1', () => console.log(`Open http://127.0.0.1:${port}/`));
}
