const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { test } = require('node:test');
const { postmanToBruno } = require('@usebruno/converters');
const { parseRequest, parseFolder, parseCollection } = require('@usebruno/filestore');
const { bruToJsonV2 } = require('@usebruno/lang');

const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/local.postman_collection.json'), 'utf8'));
const writer = require('../convert.cjs');

function temporary(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'collection example '));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

async function runCli(cwd, report) {
  const cli = path.join(path.dirname(require.resolve('@usebruno/cli/package.json')), 'bin/bru.js');
  const args = [cli, 'run', '--reporter-json', report];
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, {
      cwd,
      env: { ...process.env, HTTP_PROXY: '', HTTPS_PROXY: '', ALL_PROXY: '', NO_PROXY: '127.0.0.1,localhost' },
      stdio: ['ignore', 'pipe', 'pipe']
    });
    let output = '';
    child.stdout.on('data', (s) => { output += s; });
    child.stderr.on('data', (s) => { output += s; });
    const timeout = setTimeout(() => { child.kill('SIGTERM'); reject(new Error('CLI timed out')); }, 30000);
    child.on('error', reject);
    child.on('exit', (code) => { clearTimeout(timeout); resolve({ code, output }); });
  });
}

async function assertNativeCollection(t, wrapped = false) {
  const dir = temporary(t);
  const seen = [];
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      seen.push({ method: req.method, url: req.url, headers: req.headers, body });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
    });
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const source = structuredClone(fixture);
  source.variable[0].value = `http://127.0.0.1:${server.address().port}`;
  const sourcePath = path.join(dir, 'source.json');
  const sourceBytes = JSON.stringify(wrapped ? { collection: source } : source);
  fs.writeFileSync(sourcePath, sourceBytes);
  const destination = path.join(dir, 'result');
  await writer.convertFile(sourcePath, destination);
  const report = path.join(dir, 'report.json');
  const run = await runCli(destination, report);
  if (process.env.TEST_EVIDENCE_DIR) {
    const evidence = wrapped ? path.join(process.env.TEST_EVIDENCE_DIR, 'wrapped-postman') : process.env.TEST_EVIDENCE_DIR;
    fs.mkdirSync(evidence, { recursive: true });
    fs.writeFileSync(path.join(evidence, 'cli-output.txt'), run.output);
    fs.writeFileSync(path.join(evidence, 'received.json'), JSON.stringify(seen, null, 2));
    if (fs.existsSync(report)) fs.copyFileSync(report, path.join(evidence, 'cli-report.json'));
  }
  assert.equal(run.code, 0, `Native CLI must execute the converted directory:\n${run.output}`);
  const results = JSON.parse(fs.readFileSync(report, 'utf8'));
  assert.equal(results[0].summary.totalRequests, 3);
  assert.equal(results[0].summary.passedRequests, 3);
  assert.equal(results[0].summary.totalPostResponseTests, 3);
  assert.equal(results[0].summary.passedPostResponseTests, 3);
  assert.deepEqual(seen.map(({ method, url }) => [method, url]), [
    ['POST', '/items'], ['GET', '/items?kind=sample&tag=a&tag=b'], ['GET', '/root']
  ]);
  assert.equal(seen[0].body, '{"message":"hello β"}');
  assert.ok(seen.every((request) => request.headers['x-collection'] === 'collection-ran'));
  assert.equal(seen[0].headers['x-folder'], 'folder-ran');
  assert.equal(seen[1].headers['x-folder'], 'folder-ran');
  assert.equal(seen[1].headers['x-request'], 'request-ran');
  for (const label of ['POST completed', 'GET completed', 'Root completed']) {
    assert.ok(run.output.includes(`✓ ${label}`), `Native post-response test did not pass: ${label}`);
  }
  assert.equal(fs.readFileSync(sourcePath, 'utf8'), sourceBytes);
  assert.ok(fs.existsSync(path.join(destination, 'bruno.json')));
  assert.equal(parseCollection(fs.readFileSync(path.join(destination, 'collection.bru'), 'utf8'), { format: 'bru' }).docs, source.info.description);
  const folder = path.join(destination, 'A folder β');
  assert.equal(parseFolder(fs.readFileSync(path.join(folder, 'folder.bru'), 'utf8'), { format: 'bru' }).meta.name, 'A folder β');
  const requestText = fs.readFileSync(path.join(folder, 'Read items.bru'), 'utf8');
  assert.equal(parseRequest(requestText, { format: 'bru' }).request.method, 'GET');
  assert.equal(bruToJsonV2(requestText).meta.name, 'Read items');
}

test('the generated directory executes nested GET and POST requests with the native CLI', async (t) => {
  await assertNativeCollection(t);
});

test('a wrapped Postman export executes the same nested requests with the native CLI', async (t) => {
  await assertNativeCollection(t, true);
});

test('already-converted JSON can be written without converting it a second time', async (t) => {
  const dir = temporary(t);
  const converted = await postmanToBruno(structuredClone(fixture));
  const input = path.join(dir, 'converted.json');
  fs.writeFileSync(input, JSON.stringify(converted));
  await writer.convertFile(input, path.join(dir, 'out'));
  assert.ok(fs.existsSync(path.join(dir, 'out', 'A folder β', 'A nested', 'Send JSON.bru')));
});

test('occupied output directories and the input file remain unchanged', async (t) => {
  const dir = temporary(t);
  const input = path.join(dir, 'source.json');
  fs.writeFileSync(input, JSON.stringify(fixture));
  const out = path.join(dir, 'out');
  fs.mkdirSync(out);
  fs.writeFileSync(path.join(out, 'keep.txt'), 'existing content');
  await assert.rejects(writer.convertFile(input, out), /exist/i);
  assert.deepEqual(fs.readdirSync(out), ['keep.txt']);
  assert.equal(fs.readFileSync(path.join(out, 'keep.txt'), 'utf8'), 'existing content');
  assert.equal(fs.readFileSync(input, 'utf8'), JSON.stringify(fixture));
  const empty = path.join(dir, 'empty');
  fs.mkdirSync(empty);
  await assert.rejects(writer.convertFile(input, empty), /exist/i);
  assert.deepEqual(fs.readdirSync(empty), []);
});

test('invalid and colliding names fail before creating the destination', async (t) => {
  const dir = temporary(t);
  for (const name of ['../outside', '..', 'trailing.', 'a/b', 'a\\b', 'NUL', 'bad\nname', 'collection']) {
    const source = structuredClone(fixture);
    source.item[1].name = name;
    const out = path.join(dir, `out-${Buffer.from(name).toString('hex')}`);
    await assert.rejects(writer.writeCollection((await postmanToBruno(source)).collection, out), /name|collis|reserved/i, name);
    assert.equal(fs.existsSync(out), false);
  }
  for (const names of [['Same', 'same'], ['é', 'e\u0301']]) {
    const source = structuredClone(fixture);
    source.item = names.map((name) => ({ name, request: { method: 'GET', url: 'http://127.0.0.1/' } }));
    const out = path.join(dir, `duplicate-${names[0]}`);
    await assert.rejects(writer.writeCollection((await postmanToBruno(source)).collection, out), /collis|duplic/i);
    assert.equal(fs.existsSync(out), false);
  }
});

test('unsupported converted content is rejected before any output is written', async (t) => {
  const dir = temporary(t);
  const converted = (await postmanToBruno(structuredClone(fixture))).collection;
  for (const change of [
    (c) => { c.items[1].type = 'script'; },
    (c) => { c.items[1].request.futureOption = 'must not disappear'; },
    (c) => { c.root.settings = { futureOption: true }; }
  ]) {
    const collection = structuredClone(converted);
    change(collection);
    const out = path.join(dir, `unsupported-${fs.readdirSync(dir).length}`);
    await assert.rejects(writer.writeCollection(collection, out), /unsupported|preserv|round.trip/i);
    assert.equal(fs.existsSync(out), false);
  }
});

test('GraphQL, saved examples, request settings and environment variables remain usable data', async (t) => {
  const dir = temporary(t);
  const source = {
    info: { name: 'Rich data', schema: fixture.info.schema },
    item: [{
      name: 'GraphQL query',
      request: {
        method: 'POST', url: 'http://127.0.0.1/graphql',
        body: { mode: 'graphql', graphql: { query: 'query Example { id }', variables: '{"id": 1}' } }
      },
      response: [{
        name: 'Saved response', status: 'OK', code: 200, header: [{ key: 'Content-Type', value: 'application/json' }],
        body: '{"data":{"id":1}}',
        originalRequest: { method: 'POST', url: 'http://127.0.0.1/graphql', body: { mode: 'graphql', graphql: { query: 'query Example { id }', variables: '{"id": 1}' } } }
      }]
    }]
  };
  const converted = (await postmanToBruno(source)).collection;
  converted.items[0].settings.timeout = 3000;
  converted.environments = [{ name: 'Local β', variables: [
    { name: 'base', value: 'http://127.0.0.1', enabled: true, type: 'text' },
    { name: 'unused', value: 'kept', enabled: false, type: 'text' }
  ] }];
  const out = path.join(dir, 'rich');
  await writer.writeCollection(converted, out);
  const request = parseRequest(fs.readFileSync(path.join(out, 'GraphQL query.bru'), 'utf8'), { format: 'bru' });
  assert.equal(request.type, 'graphql-request');
  assert.equal(request.request.body.graphql.query, 'query Example { id }');
  assert.equal(request.request.body.graphql.variables, '{"id": 1}');
  assert.equal(request.settings.timeout, 3000);
  assert.equal(request.examples[0].name, 'Saved response');
  assert.equal(request.examples[0].response.status, 200);
  assert.equal(request.examples[0].response.body.content, '{"data":{"id":1}}');
  const { bruToEnvJsonV2 } = require('@usebruno/lang');
  const environment = bruToEnvJsonV2(fs.readFileSync(path.join(out, 'environments', 'Local β.bru'), 'utf8'));
  assert.deepEqual(environment.variables.map(({ name, value, enabled }) => ({ name, value, enabled })), [
    { name: 'base', value: 'http://127.0.0.1', enabled: true },
    { name: 'unused', value: 'kept', enabled: false }
  ]);
});

test('conversion preserves scripts as data without executing them', async (t) => {
  const dir = temporary(t);
  const source = structuredClone(fixture);
  source.item[1].event = [{ listen: 'prerequest', script: { exec: ['throw new Error("conversion-must-not-execute-scripts");'] } }];
  const input = path.join(dir, 'source.json');
  fs.writeFileSync(input, JSON.stringify(source));
  const out = path.join(dir, 'out');
  await writer.convertFile(input, out);
  const request = parseRequest(fs.readFileSync(path.join(out, 'Read root.bru'), 'utf8'), { format: 'bru' });
  assert.match(request.request.script.req, /conversion-must-not-execute-scripts/);
});

test('converter-reported skipped content and malformed JSON leave no destination', async (t) => {
  const dir = temporary(t);
  for (const [name, text] of [
    ['issues', JSON.stringify({ collection: (await postmanToBruno(structuredClone(fixture))).collection, issues: [{ message: 'request skipped' }] })],
    ['invalid', '{ invalid JSON']
  ]) {
    const input = path.join(dir, `${name}.json`);
    fs.writeFileSync(input, text);
    const out = path.join(dir, name);
    await assert.rejects(writer.convertFile(input, out));
    assert.equal(fs.existsSync(out), false);
    assert.equal(fs.readFileSync(input, 'utf8'), text);
  }
});

test('unsupported wrapper data is rejected instead of being silently ignored', async (t) => {
  const dir = temporary(t);
  const converted = await postmanToBruno(structuredClone(fixture));
  converted.futureConversionSetting = 'must not disappear';
  const input = path.join(dir, 'converted.json');
  fs.writeFileSync(input, JSON.stringify(converted));
  const out = path.join(dir, 'out');
  await assert.rejects(writer.convertFile(input, out), /unsupported/i);
  assert.equal(fs.existsSync(out), false);
});
