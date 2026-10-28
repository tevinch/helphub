import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const escape = value => String(value).replace(/[&<>"']/g, char =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const csp = "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'self'; base-uri 'none'; form-action 'self'";

function policy(country, postal) {
  if (country === 'FR') return { hint: 'France: five digits, for example 75001.', valid: /^\d{5}$/.test(postal) };
  if (country === 'CA') return { hint: 'Canada: A1A 1A1, for example K1A 0B1.', valid: /^[A-Z]\d[A-Z] \d[A-Z]\d$/i.test(postal) };
  return { hint: 'Choose FR or CA for this example.', valid: false };
}

function postalRow(country, postal, reason = 'refresh', sequence = 0) {
  const { hint, valid } = policy(country, postal);
  const error = reason === 'refresh' ? '' : !postal ? 'Postal code is required.' : !valid ? 'Check the postal code format.' : '';
  return '<tr id="postal-row" data-sequence="' + sequence + '"><th><label for="postal_code">Postal code</label></th><td>' +
    '<input id="postal_code" name="postal_code" data-postal value="' + escape(postal) + '" ' +
    'hx-post="/postal" hx-trigger="focusout, input from:#country" hx-include="#country" hx-target="#postal-row" hx-swap="outerHTML" ' +
    'aria-describedby="hint error"><p id="hint">' + hint + '</p><p id="error" role="status">' + error + '</p></td></tr>';
}

function page(version) {
  return '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Postal request reasons</title>' +
    '<meta name="htmx-config" content=\'{"allowEval":false,"includeIndicatorStyles":false,"includeIndicatorCSS":false}\'>' +
    '<script defer src="/htmx-' + version + '.js"></script><script defer src="/reason.js"></script></head><body>' +
    '<h1>Refresh and validate a postal field</h1><p><a href="/?version=2.0.11">htmx 2.0.11</a> · <a href="/?version=4.0.0">htmx 4.0.0</a></p>' +
    '<form hx-post="/submit" hx-target="#submission"><table><tbody><tr><th><label for="country">Country</label></th>' +
    '<td><input id="country" name="country" value="FR" aria-label="Country: FR or CA"></td></tr>' +
    postalRow('FR', '') +
    '<tr><th><label for="notes">Notes</label></th><td><input id="notes" name="notes"></td></tr></tbody></table>' +
    '<button type="submit">Save address</button></form><p id="submission" role="status"></p></body></html>';
}

export function createDemoServer() {
  const requests = [];
  const server = http.createServer(async (request, response) => {
    response.setHeader('Content-Security-Policy', csp);
    response.setHeader('Cache-Control', 'no-store');
    const url = new URL(request.url, 'http://127.0.0.1');
    try {
      if (request.method === 'GET' && url.pathname === '/') {
        const version = url.searchParams.get('version') === '4.0.0' ? '4.0.0' : '2.0.11';
        response.setHeader('Content-Type', 'text/html; charset=utf-8');
        response.end(page(version)); return;
      }
      const assets = {
        '/htmx-2.0.11.js': './node_modules/htmx-two/dist/htmx.js',
        '/htmx-4.0.0.js': './node_modules/htmx-four/dist/htmx.js',
        '/reason.js': './reason.js'
      };
      if (request.method === 'GET' && assets[url.pathname]) {
        response.setHeader('Content-Type', 'text/javascript; charset=utf-8');
        response.end(await readFile(new URL(assets[url.pathname], import.meta.url))); return;
      }
      if (request.method === 'POST' && ['/postal', '/submit'].includes(url.pathname)) {
        let body = '';
        for await (const chunk of request) {
          body += chunk;
          if (body.length > 8192) { response.writeHead(413).end(); return; }
        }
        const values = new URLSearchParams(body);
        const country = (values.get('country') ?? '').trim().toUpperCase();
        const postal = values.get('postal_code') ?? '';
        const notes = values.get('notes') ?? '';
        response.setHeader('Content-Type', 'text/html; charset=utf-8');
        if (url.pathname === '/postal') {
          const reason = request.headers['x-postal-reason'];
          requests.push({ route: '/postal', reason: reason ?? 'missing', country, postal });
          response.end(postalRow(country, postal, reason === 'refresh' ? 'refresh' : 'validate', requests.length));
        } else {
          const valid = policy(country, postal).valid;
          requests.push({ route: '/submit', country, postal, notes, valid });
          response.end(valid ? 'Saved: ' + escape(country + ' / ' + postal + ' / ' + notes) : 'Address not saved: check country and postal code.');
        }
        return;
      }
      response.writeHead(404).end('Not found');
    } catch {
      response.writeHead(500).end('Example request failed');
    }
  });
  return { server, requests };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { server } = createDemoServer();
  server.listen(3000, '127.0.0.1', () => console.log('Open http://127.0.0.1:3000/'));
}
