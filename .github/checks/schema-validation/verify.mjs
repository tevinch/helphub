import assert from 'node:assert/strict';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { unit } from './dist/model.js';
import { compileUnit } from './dist/compile-unit.js';

// Literal expected decisions, independent of generator/converter output.
const valid = {
  id: '123e4567-e89b-42d3-a456-426614174000', age: 42,
  email: 'person@example.com', address: { city: 'London', postalCode: '12345' },
};
const before = JSON.stringify(unit);
console.log(JSON.stringify({ nativeSchemaUnit: unit }, null, 2));
assert.equal(unit.version, '3.1');
assert.equal(unit.schema.type, 'object', 'the native root is dereferenced to an object');
const addressReference = unit.schema.properties?.address?.$ref;
assert.equal(typeof addressReference, 'string', 'the nested Address must remain a generated reference');
const componentPrefix = '#/components/schemas/';
assert.ok(addressReference.startsWith(componentPrefix), 'the nested reference must name a local component');
assert.ok(unit.components.schemas?.[addressReference.slice(componentPrefix.length)],
  'the native component map must contain the actual referenced Address');
assert.ok(Object.keys(unit.components.schemas ?? {}).length >= 2,
  'the native transform must generate the User and Address definitions');

const { validate, schema, components } = compileUnit(unit);
assert.equal(typeof validate, 'function', 'Ajv must compile an actual validator');
assert.equal(JSON.stringify(unit), before, 'conversion must preserve the original generated unit');
const cases = [
  ['valid nested user', valid, true],
  ['optional email omitted', { id: valid.id, age: 42, address: valid.address }, true],
  ['minimum uint32 age', { ...valid, age: 0 }, true],
  ['maximum uint32 age', { ...valid, age: 4294967295 }, true],
  ['missing required id', { age: 42, address: valid.address }, false],
  ['malformed uuid', { ...valid, id: 'not-a-uuid' }, false],
  ['negative age', { ...valid, age: -1 }, false],
  ['fractional age', { ...valid, age: 1.5 }, false],
  ['age beyond uint32', { ...valid, age: 4294967296 }, false],
  ['string age is not coerced', { ...valid, age: '42' }, false],
  ['invalid email', { ...valid, email: 'not-an-email' }, false],
  ['invalid referenced city', { ...valid, address: { city: '', postalCode: '12345' } }, false],
  ['invalid referenced postal code', { ...valid, address: { city: 'London', postalCode: 'abc' } }, false],
  ['missing referenced field', { ...valid, address: { city: 'London' } }, false],
];
const decisions = [];
for (const [name, input, expected] of cases) {
  const snapshot = JSON.stringify(input);
  assert.equal(validate(input), expected, name);
  assert.equal(JSON.stringify(input), snapshot, `${name}: validation must not mutate input`);
  if (!expected) assert.ok(validate.errors?.length, `${name}: Ajv must report actual validation errors`);
  decisions.push({ name, valid: expected });
}

// Native refs are essential: omitting all referenced definitions must fail.
const missingDefinitions = addFormats(new Ajv2020({ strict: true }));
assert.throws(() => missingDefinitions.compile(schema), /resolve reference|can't resolve/i,
  'a skipped definition-registration step must not silently pass');

// The sample has named examples. Emended examples must be converted to arrays
// before a strict Ajv2020 instance can accept the schema metadata.
const raw = addFormats(new Ajv2020({ strict: true }));
assert.throws(() => {
  for (const [name, definition] of Object.entries(unit.components.schemas ?? {})) {
    raw.addSchema(definition, `#/components/schemas/${name}`);
  }
  raw.compile(unit.schema);
}, /examples|schema is invalid/i, 'omitting the published conversion must fail schema validation');

const noFormats = new Ajv2020({ strict: true });
assert.throws(() => {
  for (const [name, definition] of Object.entries(components.schemas ?? {})) {
    noFormats.addSchema(definition, `#/components/schemas/${name}`);
  }
  noFormats.compile(schema);
}, /unknown format/i, 'format registration must actually be required');

assert.equal(decisions.length, 14, 'all literal positive and negative cases must execute');
console.log(JSON.stringify({
  generatedDefinitions: Object.keys(unit.components.schemas),
  decisions,
  checks: ['native generated refs', 'original unit unchanged', 'strict Ajv compiled',
    '14 input decisions without mutation', 'missing definitions rejected',
    'missing conversion rejected', 'missing formats rejected'],
}, null, 2));
