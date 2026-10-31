# Typia schema validation with Ajv

Generate and convert schemas from TypeScript types for strict Ajv2020. `typia.json.schema<User>()` returns a unit containing `version`, `schema` and `components`; pass the converted root to Ajv rather than the whole unit.

## Run

Use Node.js 24 and npm. Pinned: typia/@typia/utils 15.2.2, Ajv 8.20.0, ajv-formats 3.0.1, ttsc 0.34.3, TypeScript 7.0.2.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm start
```

`npm test` uses `ttsc`'s native typia transform, then runs checks. Initial plugin compilation may take minutes. Stock `tsc` does not apply the transform.

Verified on Ubuntu 24.04.5 x64 with Node.js 24.21.0 and npm 11.19.0 in [this CI run](https://github.com/tevinch/helphub/actions/runs/41183648550). The fresh consumer's actual `npm start` output was:

```json
{"valid":true,"errors":null}
```

That consumer copied only the eight source files, installed dependencies with a separate empty npm cache, and rebuilt. It reused the fixture's compiler cache; this was not a cold compiler-cache check.

## Model and conversion

[model.ts](./model.ts) supplies sample `User` and `Address` types; the question supplies no application model. Native output has an object root, retained `User` and `Address` definitions and a nested `#/components/schemas/Address` reference.

```ts
age: number & tags.Type<'uint32'> & tags.Maximum<4294967295>;
```

In 15.2.2, `Type<'uint32'>` alone emits an integer with minimum 0. `Maximum` explicitly supplies the inclusive upper bound. This schema representation is coarser than the Type tag's runtime numeric-width check.

[compile-unit.ts](./compile-unit.ts) converts both parts:

```ts
const components = OpenApiConverter.downgradeComponents(unit.components, '3.1');
const schema = OpenApiConverter.downgradeSchema({
  components: unit.components,
  schema: unit.schema,
  version: '3.1',
  downgraded: components,
});
```

Register each converted definition with `ajv.addSchema(definition, '#/components/schemas/' + name)` before compiling the root. The 3.1 root converter preserves references without collecting missing definitions into an empty component map. Named `examples` become arrays. Raw native output failed Ajv schema checking: `data/properties/email/examples must be array`.

The helper explicitly registers [OpenAPI's singular `example` annotation](https://spec.openapis.org/oas/v3.1.1.html#schema-object):

```ts
ajv.addKeyword({ keyword: 'example' });
```

The 15.2.2 converter includes this property even when undefined; Ajv checks keyword names independently of values. [Annotation registration](https://ajv.js.org/strict-mode.html#unknown-keywords) adds no data-validation rule. Strict mode and schema validation stay enabled; other unknown keywords still fail. Named `examples` conversion is a separate step.

The helper adds `ajv-formats` and disables coercion, default insertion and property removal. No schema is handwritten or fetched from a reference URL.

## Checks and scope

The fixture and fresh consumer each passed the same 14 literal cases: four valid and ten invalid inputs covering UUID/email formats, required fields, numeric boundaries and referenced Address constraints. Invalid inputs produced validation errors; input and source-unit snapshots stayed unchanged.

Both runs also rejected missing definitions, unconverted metadata, missing formats and omitted `example` registration. A separate stock-compiler control reached typia's specific missing-transform error.

Scope is one sample graph on pinned versions. Recursive/multiple-root models, arbitrary emended output, complete OpenAPI documents and the requester's application remain unverified. Naming and dialect terminology concerns are unchanged.

## References and license

- [Typia setup](https://typia.io/docs/setup/) and [schema guide](https://typia.io/docs/json/schema/)
- [15.2.2 converter source](https://raw.githubusercontent.com/samchon/typia/v15.2.2/packages/utils/src/converters/OpenApiConverter.ts)
- [15.2.2 Type tag](https://raw.githubusercontent.com/samchon/typia/v15.2.2/packages/interface/src/tags/Type.ts) and [Maximum tag](https://raw.githubusercontent.com/samchon/typia/v15.2.2/packages/interface/src/tags/Maximum.ts)
- [Ajv schema registration](https://ajv.js.org/api.html#ajv-addschema-schema-object-object-key-string-ajv), [addKeyword API](https://ajv.js.org/api.html#ajv-addkeyword-definition-string-object-ajv) and [formats](https://ajv.js.org/packages/ajv-formats.html)

Free to use under the MIT license. See [LICENSE](./LICENSE).

## Optional coffee

This example is free to use. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
