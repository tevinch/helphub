import * as v from 'valibot';

const needsItems = (input: unknown) =>
  input !== null &&
  typeof input === 'object' &&
  'a' in input &&
  (input.a === 'foo' || input.a === 'bar');

// The original { a: string; b: string[] } example.
const StringArray = v.array(v.string());
const OriginalBase = v.object({ a: v.string(), b: StringArray });
const OriginalActive = v.object({
  ...OriginalBase.entries,
  b: v.pipe(StringArray, v.minLength(1)),
});

export const OriginalSchema = v.lazy((input) =>
  needsItems(input) ? OriginalActive : OriginalBase
);

// A message belongs to the reused schema, rather than a second check.
const OriginalCustomActive = v.object({
  ...OriginalBase.entries,
  b: v.pipe(StringArray, v.minLength(1, 'Add at least one item for foo or bar.')),
});
export const OriginalCustomSchema = v.lazy((input) =>
  needsItems(input) ? OriginalCustomActive : OriginalBase
);

// A separate illustration with nested constraints and an existing notes field.
const Entry = v.object({ name: v.string(), quantity: v.number() });
const CheckedEntry = v.object({
  ...Entry.entries,
  name: v.pipe(Entry.entries.name, v.nonEmpty('Name is required.')),
  quantity: v.pipe(
    Entry.entries.quantity,
    v.integer('Quantity must be an integer.'),
    v.minValue(1, 'Quantity must be at least 1.')
  ),
});
const RequiredEntries = v.pipe(
  v.array(CheckedEntry),
  v.minLength(1, 'Add at least one entry for foo or bar.')
);
const ComplexBase = v.object({
  a: v.string(),
  b: v.array(Entry),
  notes: v.pipe(v.string(), v.nonEmpty('Notes are required.')),
});
const ComplexActive = v.object({ ...ComplexBase.entries, b: RequiredEntries });

export const ComplexSchema = v.lazy((input) =>
  needsItems(input) ? ComplexActive : ComplexBase
);

export type OriginalInput = v.InferInput<typeof OriginalSchema>;
export type OriginalOutput = v.InferOutput<typeof OriginalSchema>;
export type ComplexOutput = v.InferOutput<typeof ComplexSchema>;
