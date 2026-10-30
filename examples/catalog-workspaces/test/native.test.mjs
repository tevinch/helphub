import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, cp, readdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const cli = resolve(here, '../node_modules/npm-check-updates/build/cli.js');
const bun = process.env.BUN_BIN || 'bun';
const workspaceFlags = process.env.CATALOG_TEST_OMIT_WORKSPACES === '1' ? [] : ['--workspaces'];
const observations = [];
const env = {
  ...process.env,
  NO_COLOR: '1',
  PATH: `${dirname(process.execPath)}:${bun.includes('/') ? dirname(bun) + ':' : ''}${process.env.PATH}`,
};

function run(executable, args, cwd, label) {
  const result = spawnSync(executable, args, { cwd, env, encoding: 'utf8', timeout: 180_000 });
  observations.push({ label, executable: executable === process.execPath ? 'node' : 'bun', args, status: result.status, stdout: result.stdout, stderr: result.stderr });
  assert.ifError(result.error);
  assert.equal(result.status, 0, `${label}: ${result.stdout}\n${result.stderr}`);
  return result.stdout;
}

async function snapshot(directory, prefix = '') {
  const entries = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === 'node_modules') continue;
    const name = prefix + entry.name;
    if (entry.isDirectory()) Object.assign(entries, await snapshot(join(directory, entry.name), name + '/'));
    else entries[name] = (await readFile(join(directory, entry.name))).toString('base64');
  }
  return entries;
}

function packageVersion(output, member) {
  const line = output.split('\n').find(line => line.includes(`"member":"${member}"`));
  assert.ok(line, `${member} check script actually ran`);
  const json = line.slice(line.indexOf('{'), line.lastIndexOf('}') + 1);
  return JSON.parse(json).version;
}

for (const form of ['top-level catalog', 'workspace-object and named catalog']) {
  test(form, { timeout: 600_000 }, async () => {
    const directory = await mkdtemp(join(tmpdir(), 'catalog-workspaces-'));
    try {
      await cp(resolve(here, '../workspace'), directory, { recursive: true, filter: path => !path.includes('node_modules') && !path.endsWith('bun.lock') });
      const rootFile = join(directory, 'package.json');
      if (form.startsWith('workspace-object')) {
        const root = JSON.parse(await readFile(rootFile, 'utf8'));
        root.workspaces = { packages: root.workspaces, catalog: root.catalog, catalogs: { build: { typescript: root.catalog.typescript } } };
        delete root.workspaces.catalog.typescript;
        delete root.catalog;
        await writeFile(rootFile, JSON.stringify(root, null, 2) + '\n');
        const webFile = join(directory, 'apps/web/package.json');
        const web = JSON.parse(await readFile(webFile, 'utf8'));
        web.dependencies.typescript = 'catalog:build';
        await writeFile(webFile, JSON.stringify(web, null, 2) + '\n');
      }

      run(bun, ['install', '--ignore-scripts'], directory, `${form}: initial Bun install`);
      const before = await snapshot(directory);
      const originalRoot = JSON.parse(await readFile(rootFile, 'utf8'));
      const originalCatalog = originalRoot.catalog || originalRoot.workspaces.catalog;
      const plain = run(process.execPath, [cli], directory, `${form}: missing-flag baseline`);
      assert.match(plain, /No dependencies/);
      assert.deepEqual(await snapshot(directory), before, 'plain ncu must not alter files');

      const preview = JSON.parse(run(process.execPath, [cli, '--jsonAll', ...workspaceFlags], directory, `${form}: native workspace preview`));
      const proposed = preview['package.json'];
      const proposedCatalog = proposed?.catalog || proposed?.workspaces?.catalog;
      assert.ok(proposedCatalog?.svelte, 'workspace preview must discover the root catalog');
      assert.notEqual(proposedCatalog.svelte, originalCatalog.svelte, 'preview must propose the intentionally old dependency');
      assert.deepEqual(await snapshot(directory), before, 'preview must leave every file byte unchanged');
      const withoutCatalogs = value => {
        const copy = structuredClone(value);
        delete copy.catalog;
        if (!Array.isArray(copy.workspaces)) {
          delete copy.workspaces.catalog;
          delete copy.workspaces.catalogs;
        }
        return copy;
      };
      assert.deepEqual(withoutCatalogs(proposed), withoutCatalogs(originalRoot), 'preview preserves all unrelated root settings');

      run(process.execPath, [cli, '-u', ...workspaceFlags], directory, `${form}: native workspace upgrade`);
      const upgraded = JSON.parse(await readFile(rootFile, 'utf8'));
      assert.deepEqual(upgraded, proposed, 'apply must produce the previewed root manifest');
      const after = await snapshot(directory);
      assert.deepEqual(Object.keys(after).sort(), Object.keys(before).sort(), 'upgrade creates no extra files');
      for (const [name, bytes] of Object.entries(before)) {
        if (name !== 'package.json') assert.equal(after[name], bytes, `upgrade preserves ${name}`);
      }

      run(bun, ['install', '--ignore-scripts'], directory, `${form}: consume updated catalogs`);
      const check = run(bun, ['run', 'check'], directory, `${form}: original root check script`);
      const catalog = upgraded.catalog || upgraded.workspaces.catalog;
      const typescript = upgraded.catalog?.typescript || upgraded.workspaces.catalogs.build.typescript;
      assert.equal(packageVersion(check, 'ui-shares'), catalog.svelte.replace(/^\^/, ''));
      assert.equal(packageVersion(check, 'web'), typescript.replace(/^\^/, ''));
      assert.match(check, /"member":"desktop","content":"unchanged"/);
      const installed = await snapshot(directory);
      for (const [name, bytes] of Object.entries(after)) {
        if (name !== 'bun.lock') assert.equal(installed[name], bytes, `Bun install and checks preserve ${name}`);
      }

      const repeatPreview = JSON.parse(run(process.execPath, [cli, '--jsonUpgraded', ...workspaceFlags], directory, `${form}: repeated preview`));
      assert.deepEqual(
        repeatPreview,
        Object.fromEntries(Object.keys(preview).map(name => [name, {}])),
        'the repeated preview must propose no upgrades in any workspace or catalog',
      );
      assert.deepEqual(await snapshot(directory), installed, 'repeated preview must leave every tracked byte unchanged');
      run(process.execPath, [cli, '-u', ...workspaceFlags], directory, `${form}: repeated apply`);
      assert.deepEqual(await snapshot(directory), installed, 'repeated apply must leave every tracked byte unchanged');
      const repeatedCheck = run(bun, ['run', 'check'], directory, `${form}: repeated member consumption`);
      assert.equal(packageVersion(repeatedCheck, 'ui-shares'), packageVersion(check, 'ui-shares'));
      assert.equal(packageVersion(repeatedCheck, 'web'), packageVersion(check, 'web'));
    } finally {
      if (process.env.RESULTS_FILE) await writeFile(process.env.RESULTS_FILE, JSON.stringify(observations, null, 2) + '\n');
      await rm(directory, { recursive: true, force: true });
    }
  });
}
