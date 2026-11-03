# Postman collection to a Bruno directory

Convert a local Postman collection into a folder Bruno can open and its CLI can run, without a UI import. You can also write the JSON returned by `postmanToBruno()`.

This example uses the published Bruno converter and file serializers. It writes `bruno.json`, collection and folder metadata, request `.bru` files, and any converted environments.

## Run

Use Node.js 22 or newer:

```sh
npm ci --ignore-scripts
node convert.cjs source.postman_collection.json ./api-collection
```

The output directory must not exist; its parent directory must already exist. Existing destinations, including empty directories, are refused. The source file is left unchanged.

For an existing converter result saved as JSON:

```sh
node convert.cjs converted.json ./api-collection
```

Both the `{ collection, issues }` result and its `collection` property are accepted. Nonempty conversion issues stop the operation.

In JavaScript, you can pass the converter result directly:

```js
const { postmanToBruno } = require('@usebruno/converters');
const { writeCollection } = require('./convert.cjs');

async function convert(postmanCollection) {
  const { collection, issues } = await postmanToBruno(postmanCollection);
  if (issues.length) throw new Error(JSON.stringify(issues));
  await writeCollection(collection, './api-collection');
}
```

Open the resulting folder in Bruno, or run it from that directory:

```sh
cd api-collection
../node_modules/.bin/bru run
```

Running a collection sends its requests and executes its scripts. Conversion itself only reads and writes local files.

## Supported scope

The exact pins are `@usebruno/converters` 0.25.0, `@usebruno/filestore` 0.14.0, `@usebruno/lang` 0.41.0 and, for verification, `@usebruno/cli` 4.3.0. The lockfile fixes their dependency versions.

HTTP and GraphQL requests, nested folders, variables, scripts, documentation, saved responses and representable request settings pass through Bruno's own serializers. The example checks that nonempty converted data survives parsing before it creates the output directory. Regenerated internal IDs and default enabled flags are normalized for that check. Unsupported item types, fields the pinned `.bru` format cannot retain, and script dependencies needing extra setup are rejected with a location to inspect. In particular, nonempty collection or folder settings that these serializers omit are rejected.

Names are kept as supplied. Invalid portable filenames, path separators, reserved filenames, duplicate names and case or Unicode-normalization collisions are refused instead of renamed.

Sequence metadata is retained. Bruno CLI 4.3.0 visits folders before sibling standalone requests, so collections mixing those types may run in a different order from Postman.

As of November 3, 2026, published CLI 4.3.0 has no `import postman` command. Native Postman CLI import has [merged upstream](https://github.com/usebruno/bruno/pull/9643), and may replace this small disk-writing example in a later release.

## Verify

```sh
npm test
```

The tests convert the included fixture, start a loopback HTTP server, and run the actual Bruno CLI against the generated directory. They check three requests, their query and JSON body, execution order, collection/folder/request hooks, and three passing post-response tests. Additional checks cover converted JSON input, GraphQL, saved responses, environments, settings, unchanged inputs and existing destinations, rejected names, and unsupported content. These are scripted checks using controlled fixtures; the original questioner's collection has not been validated.

Verified with Node.js 24.22.1 and Bruno CLI 4.3.0 on macOS. No API account is required for the test suite.

References: [original question](https://github.com/usebruno/bruno/discussions/9224), [converter usage](https://docs.usebruno.com/converters/postman-to-bruno), [published serializer interface](https://github.com/usebruno/bruno/blob/v4.3.0/packages/bruno-filestore/src/index.ts).

## Optional coffee

If this saved you some time, a coffee is entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
