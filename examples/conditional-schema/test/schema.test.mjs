import assert from 'node:assert/strict';
import test from 'node:test';
import * as v from 'valibot';
import { OriginalSchema, OriginalCustomSchema, ComplexSchema } from '../dist/schema.js';

const paths = (result) => result.issues?.map((issue) => issue.path?.map((part) => part.key).join('.') ?? '') ?? [];

// Independent native schemas provide the expected full issue/output contract.
const nativeOriginalActive = v.object({
  a: v.string(),
  b: v.pipe(v.array(v.string()), v.minLength(1)),
});
const nativeComplexActive = v.object({
  a: v.string(),
  b: v.pipe(v.array(v.object({
    name: v.pipe(v.string(), v.nonEmpty('Name is required.')),
    quantity: v.pipe(v.number(), v.integer('Quantity must be an integer.'), v.minValue(1, 'Quantity must be at least 1.')),
  })), v.minLength(1, 'Add at least one entry for foo or bar.')),
  notes: v.pipe(v.string(), v.nonEmpty('Notes are required.')),
});

// Removing or freezing the condition would incorrectly accept active empty lists.
test('the original condition retains default native min-length issues', () => {
  for (const a of ['foo', 'bar']) {
    const input = { a, b: [] };
    const result = v.safeParse(OriginalSchema, input);
    assert.equal(result.success, false);
    assert.deepEqual(paths(result), ['b']);
    assert.equal(result.issues[0].type, 'min_length');
    assert.equal(result.issues[0].requirement, 1);
    assert.deepEqual(result, v.safeParse(nativeOriginalActive, input));
  }
});

test('each submission uses its current condition and finishes with valid output', () => {
  const inputs = [
    { a: 'foo', b: [] },
    { a: 'other', b: [] },
    { a: 'bar', b: [] },
    { a: 'bar', b: ['kept'] },
  ];
  const results = inputs.map((input) => v.safeParse(OriginalSchema, input));
  assert.deepEqual(results.map((result) => result.success), [false, true, false, true]);
  assert.deepEqual(results[1].output, { a: 'other', b: [] });
  assert.deepEqual(results[3].output, { a: 'bar', b: ['kept'] });
});

test('a schema-owned custom message needs no duplicated check message', () => {
  const result = v.safeParse(OriginalCustomSchema, { a: 'foo', b: [] });
  assert.equal(result.success, false);
  assert.equal(result.issues[0].message, 'Add at least one item for foo or bar.');
  assert.equal(result.issues[0].type, 'min_length');
  assert.deepEqual(paths(result), ['b']);
});

test('inactive inputs still obey all original base types', () => {
  for (const [input, expected] of [
    [{ a: 42, b: [] }, ['a']],
    [{ a: 'other', b: 'wrong' }, ['b']],
    [{ a: 'other', b: [42] }, ['b.0']],
    [{ a: 'foo', b: [42] }, ['b.0']],
  ]) {
    const result = v.safeParse(OriginalSchema, input);
    assert.equal(result.success, false);
    assert.deepEqual(paths(result), expected);
  }
  for (const input of [null, undefined, 42, 'foo', false]) {
    assert.equal(v.safeParse(OriginalSchema, input).success, false);
  }
});

// A boolean-only check, copying one error, or losing item paths fails here.
test('a reusable complex schema retains every nested native issue', () => {
  const input = {
    a: 'foo',
    b: [{ name: '', quantity: 0 }, { name: '', quantity: 0 }],
    notes: 'Keep this existing value.',
  };
  const result = v.safeParse(ComplexSchema, input);
  assert.equal(result.success, false);
  assert.deepEqual(paths(result), ['b.0.name', 'b.0.quantity', 'b.1.name', 'b.1.quantity']);
  assert.deepEqual(result.issues.map((issue) => issue.message), [
    'Name is required.', 'Quantity must be at least 1.',
    'Name is required.', 'Quantity must be at least 1.',
  ]);
  assert.deepEqual(result, v.safeParse(nativeComplexActive, input));
  assert.equal(input.notes, 'Keep this existing value.');
});

test('the complex branch is conditional while declared unrelated fields remain required', () => {
  const input = { a: 'other', b: [{ name: '', quantity: 0 }], notes: 'Preserved.' };
  assert.deepEqual(v.parse(ComplexSchema, input), input);
  const active = v.safeParse(ComplexSchema, { ...input, a: 'bar' });
  assert.equal(active.success, false);
  assert.deepEqual(paths(active), ['b.0.name', 'b.0.quantity']);
  for (const a of ['foo', 'other']) {
    const invalidNotes = v.safeParse(ComplexSchema, { a, b: [{ name: 'Apple', quantity: 2 }], notes: '' });
    assert.equal(invalidNotes.success, false);
    assert.deepEqual(paths(invalidNotes), ['notes']);
    assert.deepEqual(v.parse(ComplexSchema, { a, b: [{ name: 'Apple', quantity: 2 }], notes: 'Preserved.' }), {
      a, b: [{ name: 'Apple', quantity: 2 }], notes: 'Preserved.',
    });
  }
});

test('standard parse throws then returns the complete corrected object', () => {
  const bad = { a: 'foo', b: [{ name: '', quantity: 0 }], notes: 'Still here.' };
  assert.throws(() => v.parse(ComplexSchema, bad), (error) => {
    assert.ok(error instanceof v.ValiError);
    assert.deepEqual(error.issues, v.safeParse(ComplexSchema, bad).issues);
    return true;
  });
  const good = { a: 'foo', b: [{ name: 'Apple', quantity: 2 }], notes: 'Still here.' };
  const result = v.safeParse(ComplexSchema, good);
  assert.equal(result.success, true);
  assert.deepEqual(result.output, good);
  assert.deepEqual(v.parse(ComplexSchema, good), good);
});

test('native object stripping and parse configuration pass through unchanged', () => {
  for (const a of ['foo', 'other']) {
    assert.deepEqual(v.parse(OriginalSchema, { a, b: ['one'], unknownKey: 'not declared' }), { a, b: ['one'] });
  }
  const bad = { a: 'bar', b: [{ name: '', quantity: -0.5 }], notes: '' };
  for (const config of [{}, { abortEarly: true }, { abortPipeEarly: true }, { lang: 'en', abortEarly: false }]) {
    assert.deepEqual(v.safeParse(ComplexSchema, bad, config), v.safeParse(nativeComplexActive, bad, config));
  }
});
