# Conditional schema validation

Reuse a Valibot schema when another field controls whether its rules apply. The selected schema supplies its own messages, issue types, nested paths and validated output. `check` continues to expect a boolean requirement.

This example uses **Valibot 1.5.0** and Node.js **18.20 or later**. It includes the original `{ a: string; b: string[] }` case, a separate nested example, tests and a local form.

## Run

From this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run check
npm start
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173). The form runs locally and sends no form data to a server. Stop the local server with Ctrl+C. Set `PORT` to use another local port.

## Keep the reusable schema in the selected branch

```ts
import * as v from 'valibot';

const StringArray = v.array(v.string());
const Base = v.object({ a: v.string(), b: StringArray });
const RequiredItems = v.pipe(StringArray, v.minLength(1));
const Active = v.object({ ...Base.entries, b: RequiredItems });

const Schema = v.lazy((input) => {
  const active =
    input !== null &&
    typeof input === 'object' &&
    'a' in input &&
    (input.a === 'foo' || input.a === 'bar');
  return active ? Active : Base;
});

v.safeParse(Schema, { a: 'foo', b: [] });  // min_length issue at b
v.safeParse(Schema, { a: 'other', b: [] }); // success
v.parse(Schema, { a: 'bar', b: ['first'] }); // complete validated object
```

`lazy` receives the current input on every parse. Build the branches once, then select between them each time. Calling `safeParse` inside a boolean `check` and returning only `.success` discards the nested schema's issues; placing that schema in the selected object lets Valibot retain them directly.

Put a custom message on `minLength`, or on the reusable schema's other actions, once. [schema.ts](./schema.ts) includes both a default-message version and `OriginalCustomSchema`. The input and output types remain structurally `{ a: string; b: string[] }`.

The selector examines the raw `a` value. This is a synchronous example. A condition based on transformed values, an async schema or a particular form framework needs its own integration and lifecycle checks. For a finite set of discriminators, consider Valibot's documented `variant` schema.

## Preserve the rest of the form

`ComplexSchema` illustrates a reusable array-of-objects schema. For `foo` or `bar`, entries require nonempty names and positive integer quantities. Failures retain paths such as `b.0.name` and `b.1.quantity`. Other values of `a` keep the base name/string and quantity/number constraints.

Both branches spread the common entries, including an existing required `notes` field. Start from your complete existing entries so that other fields and constraints remain present. The example uses `object` in both branches: undeclared keys are stripped under its native policy. If your existing schema uses `looseObject`, `strictObject` or `objectWithRest`, retain that constructor and verify its policy when adapting the pattern.

Try this complete sequence in the local form:

1. Submit `a: foo` and `b: []`; the original schema's length error appears at `b` and the entered values remain.
2. Change `a` to `other` and submit; the empty array succeeds. Change it to `bar` and submit; the requirement returns. Enter `["first"]` and submit successfully.
3. In the nested example, submit `a: foo` with `b: [{"name":"","quantity":0},{"name":"","quantity":0}]`. All four nested errors appear with their individual paths.
4. Change `a` to `other` and submit, then back to `bar` and submit. The conditional errors disappear and return, while `notes` stays intact.
5. Correct `b` to `[{"name":"Apple","quantity":2}]`. Empty `notes` still fails its existing constraint; restoring it returns the complete validated object.

These forms submit through standard `safeParse`; they display its output only after success. `novalidate` lets this demonstration show the schema's messages instead of browser-native field validation. Validation does not persist a record.

## Verification and references

`npm test` builds and runs eight Node.js tests. They cover repeated branch switching, full native issues, multiple nested failures, base types, schema-owned messages, standard `parse` errors/success, unrelated fields, unknown-key stripping and native abort configuration. The build also checks the inferred input/output shapes.

The local form's repeated edit/submit/correct sequence was additionally verified with software-operated Chromium 156, including preserved input, all four nested paths and the final complete output. This does not establish integration with an unprovided application or adoption by another user.

- [Valibot lazy](https://valibot.dev/api/lazy/)
- [Objects and their key policies](https://valibot.dev/guides/objects/)
- [Parsing data](https://valibot.dev/guides/parse-data/)
- [Variant schemas](https://valibot.dev/api/variant/)
- [Conditional schema use case](https://github.com/open-circle/valibot/issues/1605)

## Optional coffee

This example is free. If it saves you time and you would like to buy me a coffee, a small contribution is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
