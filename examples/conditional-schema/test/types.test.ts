import type * as v from 'valibot';
import { OriginalSchema, OriginalCustomSchema, ComplexSchema } from '../schema.js';

// Native lazy infers a union of equivalent branch shapes. Require both
// assignment directions, the same keys, and a concrete non-any type.
type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
type SameShape<A, B> = 0 extends (1 & A) ? false
  : Equal<keyof A, keyof B> extends true
    ? [A] extends [B] ? [B] extends [A] ? true : false : false
    : false;
type Assert<T extends true> = T;
type Original = { a: string; b: string[] };
type Complex = { a: string; b: { name: string; quantity: number }[]; notes: string };

type OriginalInputIsPreserved = Assert<SameShape<v.InferInput<typeof OriginalSchema>, Original>>;
type OriginalOutputIsPreserved = Assert<SameShape<v.InferOutput<typeof OriginalSchema>, Original>>;
type CustomOutputIsPreserved = Assert<SameShape<v.InferOutput<typeof OriginalCustomSchema>, Original>>;
type ComplexInputIsPreserved = Assert<SameShape<v.InferInput<typeof ComplexSchema>, Complex>>;
type ComplexOutputIsPreserved = Assert<SameShape<v.InferOutput<typeof ComplexSchema>, Complex>>;
