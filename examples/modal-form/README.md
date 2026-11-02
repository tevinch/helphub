# Conform forms inside a Radix dialog

Keep normal blur validation while closing a modal without adding errors during its exit. This complete example also keeps radio buttons in place when a preceding field becomes invalid, saves through a local HTTP endpoint, and opens again with the saved values.

It addresses the Radix portion of [Conform discussion #1344](https://github.com/edmundhung/conform/discussions/1344). It uses Conform's existing APIs; it does not patch Conform or Radix.

## Run

Use Node 22 or newer:

```sh
npm ci --ignore-scripts
npm run check
npm run build
npm start
```

Open `http://127.0.0.1:4173`. The server binds only to loopback and stores this example's ordinary item in `.data/item.json`. Stop with Ctrl+C. To use a separate example data file, set `MODAL_FORM_DATA_FILE` before starting. Existing item properties and unrelated settings are retained when title/color/notes are saved. This is a single-user local demonstration, not a production storage or concurrency design.

For browser checks, install Playwright's Chromium if you do not already have its matching browser:

```sh
npx playwright install chromium
npm test
```

Alternatively, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an existing compatible Chromium executable. Tests use temporary data files and disposable browser contexts, then remove them. They do not use your normal browser profile.

## Try the complete interaction

1. Choose **Edit item**, replace the title with `x`, then Tab to another control. An error appears. Correct the title while still typing; the error clears without another blur.
2. Close and reopen, enter `x`, then click **Red** once. The title error appears and that first radio click still selects Red. Space is reserved for these short errors, so the radio stays under the pointer.
3. Close and reopen, then enter `x`, then close using **×**, **Cancel**, Escape or the backdrop. The current form fades out without newly validating or resetting. Radix returns focus to **Edit item**. Unsaved changes do not replace the saved item.
4. Reopen, enter a valid title and choose a color, then **Save changes**. The form closes after the HTTP save succeeds. The summary shows the acknowledged result.
5. Open it again, edit and save a second time. Reload and reopen: the saved title/color and the existing note remain.

## The integration points

[`src/App.tsx`](src/App.tsx) contains the complete dialog and form. [`schema.mjs`](schema.mjs) defines the shared Zod schema; [`server.mjs`](server.mjs) validates and persists the local save.

- Keep `shouldValidate: 'onBlur'` and `shouldRevalidate: 'onInput'`. Use Conform's documented `onBlur` callback and `event.preventDefault()` only for a native blur toward an explicit dismiss button or outside this modal, or after closing has begun. Field-to-field focus changes still validate. A null destination on a real native blur is treated as leaving this modal's focusable content; adapt this policy if your own focus model differs.
- Closing on `onOpenChange(false)` alone is too late for some pointer interactions: a close button and current Radix backdrop dismissal complete on click, after pointerdown may already blur the field. The real `relatedTarget` handles that earlier blur; a per-dialog ref handles Escape, successful save and teardown.
- The radio adapter follows [Conform's UI-library pattern](https://github.com/edmundhung/conform/blob/v1.21.3/docs/integration/ui-libraries.md): one named hidden control registered with `useControl`, with Radix's internal inputs unnamed. It forwards changes and visible focus. It examines the real group blur destination before `control.blur()` emits its synthetic event, whose `relatedTarget` is null. Internal movement between radio options is ignored; ordinary departure still validates.
- Keep the form mounted throughout Radix's CSS exit animation. Do not reset it during close or prevent Radix's default `onCloseAutoFocus`. A new editing session receives a new key and the acknowledged saved defaults on the next open.
- Keep unrelated retained text as text: the note uses `white-space: pre-wrap` and a named hidden input, preserving its newlines and Unicode exactly. It is not an editable textarea integration.
- Reserve error space sized for the actual messages and supported widths. The fixed space here covers this fixture's short messages. Longer/localized error lists need their own layout design.
- Await the save before updating the canonical record and closing. Capture the editing session: if the user dismissed a pending save and opened a new draft, the earlier acknowledgement updates the canonical record but does not close that newer draft. An HTTP failure leaves the draft available for retry. The server preserves unrelated item properties/settings; the form retains its note.

Conform 1.21.3 already includes the [event opt-out repair](https://github.com/edmundhung/conform/pull/1349). A repair wrapper or source build is unnecessary. The exact versions are pinned in `package-lock.json`: Conform 1.21.3, Zod 4.6.7, React 19.3.1, Radix Dialog 1.3.1 and RadioGroup 1.5.1. Conform's `/future` exports are experimental and can change in minor versions.

## Checks and scope

[`tests/browser.test.mjs`](tests/browser.test.mjs) exercises normal blur/input validation (including the radio proxy), a real pointerdown/up radio click and keyboard navigation, X/Cancel/Escape/backdrop exits, native focus return, invalid submit/correction, two actual persisted saves with reopen/reload, and a failed HTTP response followed by a real retry. It compares draft/errors/geometry on each observed animation frame, checks the data file outside the submission callback, includes reduced-motion behavior, and holds an earlier HTTP request while a new editing session is opened. The failure check injects a 503 response; the retry and successful saves use the actual local endpoint. A separate real HTTP check splits UTF-8 characters across chunks, verifies exact title/note persistence, and checks the 16 KiB raw-byte request limit.

The nine browser checks passed in Chromium 156.0.8078.4 with Node 24.21.0.

This is one client-rendered **Radix Dialog + RadioGroup** integration. It does not establish behavior for editable textareas, Base UI, sheets, nested dialogs, React Router revalidation, SSR, View Transitions, concurrent editing, or an unprovided application. A user may dismiss a pending request; the session check protects a reopened draft, but the example does not cancel server work or implement conflict resolution.

References: [Conform future useForm](https://conform.guide/api/react/future/useForm), [useControl](https://conform.guide/api/react/future/useControl), [Radix Dialog](https://www.radix-ui.com/primitives/docs/components/dialog), [Radix RadioGroup](https://www.radix-ui.com/primitives/docs/components/radio-group). The radio adapter follows the upstream MIT-licensed [Radix adapter example](https://github.com/edmundhung/conform/blob/v1.21.3/examples/radix-ui/src/form.tsx); its copyright/license notice is retained in [LICENSE.conform](LICENSE.conform). Other files in this example use the repository's MIT license.

## Optional coffee

If this helped, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
