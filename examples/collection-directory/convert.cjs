#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const { postmanToBruno } = require('@usebruno/converters');
const {
  stringifyRequest, stringifyFolder, stringifyCollection, stringifyEnvironment,
  parseRequest, parseFolder, parseCollection, parseEnvironment
} = require('@usebruno/filestore');

function nameForDisk(name) {
  if (typeof name !== 'string' || !name || name !== name.trim()
      || /[<>:"/\\|?*\x00-\x1f\x7f]/u.test(name) || /[. ]$/u.test(name)
      || name === '.' || name === '..' || name.toLowerCase().includes('node_modules')
      || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/iu.test(name)
      || name === '.git') {
    throw new Error(`Unsupported filesystem name: ${JSON.stringify(name)}`);
  }
  return name;
}

function canonical(value) {
  if (value === null || value === undefined || value === '') return undefined;
  if (Array.isArray(value)) return value.length ? value.map(canonical) : undefined;
  if (typeof value === 'object') {
    const entries = Object.entries(value)
      .filter(([key, child]) => key !== 'uid' && key !== 'itemUid' && key !== 'filename'
        && !(key === 'enabled' && child === true && 'name' in value && 'value' in value))
      .map(([key, child]) => [key, canonical(child)])
      .filter(([, child]) => child !== undefined);
    return entries.length ? Object.fromEntries(entries) : undefined;
  }
  return value;
}

function assertPreserved(expected, actual, location) {
  const wanted = canonical(expected);
  const found = canonical(actual);
  function check(a, b, at) {
    if (a === undefined) return;
    if (Array.isArray(a)) {
      if (!Array.isArray(b) || a.length !== b.length) throw new Error(`Cannot preserve ${at}`);
      a.forEach((child, index) => check(child, b[index], `${at}[${index}]`));
    } else if (typeof a === 'object' && a !== null) {
      for (const [key, child] of Object.entries(a)) check(child, b?.[key], `${at}.${key}`);
    } else if (!isDeepStrictEqual(a, b)) {
      throw new Error(`Cannot preserve ${at} with the pinned .bru serializer`);
    }
  }
  check(wanted, found, location);
}

function knownKeys(object, allowed, location) {
  if (!object || typeof object !== 'object' || Array.isArray(object)) {
    throw new Error(`Unsupported ${location}: expected an object`);
  }
  for (const key of Object.keys(object)) {
    if (!allowed.includes(key) && canonical(object[key]) !== undefined) {
      throw new Error(`Unsupported ${location}.${key}`);
    }
  }
}

function planCollection(collection) {
  knownKeys(collection, ['name', 'uid', 'version', 'root', 'items', 'environments', 'packageReport'], 'collection');
  if (!collection.name || !Array.isArray(collection.items) || collection.version !== '1') {
    throw new Error('Unsupported converted collection: expected name, version "1" and items');
  }
  const report = collection.packageReport || {};
  if (report.unsupported?.length || report.needsInstall?.length || report.devMode?.length) {
    throw new Error('Unsupported script dependencies: review the converter package report first');
  }
  const files = new Map();
  const add = (relative, content) => { files.set(relative, content); };
  const config = { version: '1', name: collection.name, type: 'collection', ignore: ['node_modules', '.git'] };
  add('bruno.json', `${JSON.stringify(config, null, 2)}\n`);
  const root = collection.root || {};
  const rootText = stringifyCollection(root, config, { format: 'bru' });
  assertPreserved(root, parseCollection(rootText, { format: 'bru' }), 'collection.root');
  add('collection.bru', rootText);

  function itemsAt(items, directory) {
    if (!Array.isArray(items)) throw new Error(`Unsupported items at ${directory || 'collection'}`);
    const used = new Set(['folder.bru', 'collection.bru', 'bruno.json', 'environments', '.git', 'node_modules']);
    const displayNames = new Set();
    for (const item of items) {
      const name = nameForDisk(item.name);
      const displayKey = name.normalize('NFC').toLowerCase();
      if (displayNames.has(displayKey)) throw new Error(`Duplicate or colliding name: ${name}`);
      displayNames.add(displayKey);
      if (!['folder', 'http-request', 'graphql-request'].includes(item.type)) {
        throw new Error(`Unsupported item type: ${item.type}`);
      }
      const component = nameForDisk(item.filename || name);
      const filename = item.type === 'folder' || component.endsWith('.bru') ? component : `${component}.bru`;
      const key = filename.normalize('NFC').toLowerCase();
      if (used.has(key)) throw new Error(`Reserved or colliding name: ${filename}`);
      used.add(key);
      const relative = path.join(directory, filename);
      if (item.type === 'folder') {
        knownKeys(item, ['uid', 'name', 'type', 'seq', 'items', 'root', 'filename'], relative);
        const folderRoot = {
          ...(item.root || {}),
          meta: { ...(item.root?.meta || {}), name, ...(item.seq === undefined ? {} : { seq: item.seq }) }
        };
        const text = stringifyFolder(folderRoot, { format: 'bru' });
        assertPreserved(folderRoot, parseFolder(text, { format: 'bru' }), relative);
        add(path.join(relative, 'folder.bru'), text);
        itemsAt(item.items || [], relative);
      } else {
        knownKeys(item, ['uid', 'name', 'type', 'seq', 'request', 'settings', 'tags', 'examples', 'app', 'filename'], relative);
        const text = stringifyRequest(item, { format: 'bru' });
        assertPreserved(item, parseRequest(text, { format: 'bru' }), relative);
        add(relative, text);
      }
    }
  }
  itemsAt(collection.items, '');
  if (collection.environments !== undefined && !Array.isArray(collection.environments)) {
    throw new Error('Unsupported environments: expected an array');
  }
  const environmentNames = new Set();
  for (const environment of collection.environments || []) {
    knownKeys(environment, ['uid', 'name', 'variables'], 'environment');
    const name = nameForDisk(environment.name);
    const key = name.normalize('NFC').toLowerCase();
    if (environmentNames.has(key)) throw new Error(`Duplicate environment name: ${name}`);
    environmentNames.add(key);
    const text = stringifyEnvironment(environment, { format: 'bru' });
    assertPreserved({ variables: environment.variables }, parseEnvironment(text, { format: 'bru' }), `environment ${name}`);
    add(path.join('environments', `${name}.bru`), text);
  }
  return files;
}

async function writeCollection(collection, destination) {
  const output = path.resolve(destination);
  if (fs.existsSync(output)) throw new Error(`Output already exists: ${output}`);
  const files = planCollection(collection);
  fs.mkdirSync(output);
  try {
    for (const [relative, content] of files) {
      const filename = path.join(output, relative);
      fs.mkdirSync(path.dirname(filename), { recursive: true });
      fs.writeFileSync(filename, content, { encoding: 'utf8', flag: 'wx' });
    }
  } catch (error) {
    fs.rmSync(output, { recursive: true, force: true });
    throw error;
  }
  return { directory: output, files: files.size };
}

async function convertFile(source, destination) {
  const input = JSON.parse(fs.readFileSync(source, 'utf8'));
  let converted;
  if (input.info?.schema || input.collection?.info?.schema) {
    converted = await postmanToBruno(input);
  } else {
    converted = input.collection ? input : { collection: input, issues: [] };
  }
  knownKeys(converted, ['collection', 'issues'], 'converter result');
  if (converted.issues !== undefined && !Array.isArray(converted.issues)) {
    throw new Error('Unsupported conversion issues: expected an array');
  }
  if (converted.issues?.length) {
    throw new Error(`Unsupported conversion issues: ${JSON.stringify(converted.issues)}`);
  }
  return writeCollection(converted.collection, destination);
}

if (require.main === module) {
  const [source, destination, ...extra] = process.argv.slice(2);
  if (!source || !destination || extra.length) {
    console.error('Usage: node convert.cjs source.json new-output-directory');
    process.exitCode = 1;
  } else {
    convertFile(source, destination)
      .then(({ directory, files }) => console.log(`Wrote ${files} files to ${directory}`))
      .catch((error) => { console.error(error.message); process.exitCode = 1; });
  }
}

module.exports = { convertFile, writeCollection };
