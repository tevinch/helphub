# Prepare once for validation and submission

When validation needs prepared data, share a small preparation cache between TanStack Form's native validator and submit callback. Both receive the raw form value; both can call the same accessor to get the same prepared object.

This example answers [the prepare → validate → submit question](https://github.com/TanStack/form/discussions/2353). It uses `@tanstack/react-form` **1.33.5** and a JSON text field: parsing produces the object that is validated and then saved through a local HTTP endpoint.

## The pattern

[prepare-once.ts](./prepare-once.ts) keeps only the last successful result:

```ts
export function prepareOnce<Input, Output>(prepare: (input: Input) => Output) {
  let entry: { input: Input; output: Output } | undefined;
  return (input: Input): Output => {
    if (!entry || !Object.is(entry.input, input)) entry = { input, output: prepare(input) };
    return entry.output;
  };
}
```

Create this accessor once per mounted form, then use it in both native callbacks. In your component, the essential wiring is:

```tsx
const preparedFor = useMemo(
  () => prepareOnce((raw: string): unknown => JSON.parse(raw)),
  [],
);

const form = useForm({
  defaultValues: { json: '{"title":"Draft"}' },
  validators: {
    onSubmit: ({ value }) => {
      try {
        return validateDocument(preparedFor(value.json));
      } catch {
        return 'Enter valid JSON';
      }
    },
  },
  onSubmit: ({ value }) => saveDocument(preparedFor(value.json)),
});
```

`validateDocument` and `saveDocument` are your application's validation and saving operations. The complete [React consumer](./prepared-form.tsx) supplies validation, error rendering, the real `fetch`, and the native form submit event. The example's lifecycle trace also checks that validation and submission use the same object identity.

Preparation must be **pure and synchronous**. The key must include every input or dependency that changes its result. Here the complete input is a string, so equality is sufficient. For an object key, update it immutably; changing it in place would reuse stale data. Keep the prepared result read-only too. If your preparation depends on other settings, include those in the key or recreate the accessor when those settings change. Each form must own its cache.

Changed input prepares again. An unchanged successful input reuses its result, including after an ordinary rerender. A thrown preparation is not cached; the validator reports it and a later attempt can retry. This example does not provide an asynchronous preparation pipeline.

TanStack Form's [submission guide](https://tanstack.com/form/latest/docs/framework/react/guides/submission-handling) explains that Standard Schema output is not preserved for `onSubmit`; its simple example parses again there. The shared accessor avoids that second preparation. Use the ordinary [function-validator API](https://tanstack.com/form/latest/docs/framework/react/guides/validation), rather than treating submission metadata or state transforms as a preparation hook.

## Run it

Use Node.js 22.12 or newer. Node.js **24.21.0** was used for verification.

```sh
npm ci --ignore-scripts
npx playwright install chromium
npm test
npm start
```

Open [the local example](http://127.0.0.1:4173). Give the JSON document a non-empty `title`, save it, try an invalid title or JSON, then correct it and save again. The second form demonstrates a separate cache. [Saved receipts](http://127.0.0.1:4173/api/documents) remain in the demonstration server's memory until it stops.

`npm test` checks types, builds, and runs six scripted browser sequences. They cover shared preparation and object identity, native validation blocking invalid saves, syntax-error recovery, changed-input retry, unchanged-input reuse across rerenders, and separate mounted forms. The first save also checks native `isSubmitting` while a real HTTP request is paused and continued. Each successful path checks the actual saved HTTP payload. The local server is a demonstration, not a production storage service.

Verified with React **19.3.1** and Playwright Chromium **156.0.8078.4**. Vite emits warnings about upstream `use client` directives in this client-rendered example. These checks use sample JSON inputs; the questioner's application, workload performance and adoption have not been verified.

## Optional coffee

If this example saved you some time, buying me a coffee is entirely optional. It remains free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
