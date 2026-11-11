# Keep an input draft when disabling it

In the [four-input example in Solid discussion #4496](https://github.com/solidjs/solid/discussions/4496), typing changes the input's DOM value, but the signal still contains `11`: nothing calls its setter. On the supplied Solid 2.0 release candidate, toggling `disabled()` can write that signal value back into the input.

Write edits into the signal with `onInput`:

```tsx
import { createSignal } from 'solid-js';

const [disabled, setDisabled] = createSignal(false);
const [value, setValue] = createSignal('11');

<input
  type="number"
  value={value()}
  disabled={disabled()}
  onInput={event => setValue(event.currentTarget.value)}
/>
```

The string stores the browser's current number-input value, including an empty draft. Convert it to a number when the application needs a validated number; converting every edit with `Number(...)` would turn an empty string into `0`. This does not preserve arbitrary invalid text that a native number input rejects.

Each independently editable field needs its own state. The original first and third inputs both read the same `value()` signal; adding writeback to both would make them share a value.

## Run the example

Use Node 22.18 or newer:

```sh
npm ci --ignore-scripts
npm run check
npm run build
npm start
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173). Edit the draft, toggle its disabled state, enable it again, and continue typing. Clear it and repeat. The state display shows the actual signal; **Read submitted value** reads the actual form data. **Set draft to 42** demonstrates updating it from application state while enabled or disabled.

The second section retains the original four comparisons, including their separate fragment roots. Change all four values and press **CLICK ME**. The original signal stays `11`. These inputs deliberately omit writeback to demonstrate the difference.

## Versions and the observed behavior

The supplied playground's import map pins `solid-js` 2.0.0-rc.19 and `@solidjs/web` 2.0.0-rc.19. This example pins those packages and the matching `@solidjs/babel-plugin` 2.0.0-rc.19. Its TypeScript `jsxImportSource` is `@solidjs/web`. These are prereleases.

In the matching compiler output, the first input's `disabled()` and `value()` reads share an effect. Toggling disabled reruns it, including an assignment of the unchanged signal value to the DOM input. The third comparison has its own reactive value effect; directly changing its disabled property does not rerun that effect. This explains the measured example; it is not a promise about compiler grouping in other JSX structures.

Current stable Solid 1.9.19 uses `solid-js/web` and `babel-preset-solid` 1.9.19. It did not reproduce the reset in the four-case comparison. Do not mix the 1.x renderer/setup with the 2.0 imports, or treat this as a stable 1.x defect. Event writeback remains necessary if the application should store the user's edit in a signal.

| Runtime and web renderer | Matching compiler | Four original cases | Draft with writeback |
| --- | --- | --- | --- |
| 2.0.0-rc.19 | `@solidjs/babel-plugin` 2.0.0-rc.19 | First input resets; other three retain edits | All four checks pass |
| 2.0.0-rc.21 | `@solidjs/babel-plugin` 2.0.0-rc.21 | First input resets; other three retain edits | All four checks pass |
| Stable 1.9.19 (`solid-js/web`) | `babel-preset-solid` 1.9.19 | All four retain DOM edits; signal remains `11` | All four checks pass |

## Verification and scope

Run the browser checks with a Playwright browser installed:

```sh
npx playwright install chromium
npm test
```

Alternatively, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an installed Chromium or Chrome executable before `npm test`.

The four checks use actual keyboard editing and clicks. They cover the original four cases, repeated disable/enable cycles, continued edits and final form submission, an empty number draft, and a programmatic signal update while disabled. An independent native-input observer plus the rendered signal state verifies that writeback actually occurred. Removing the handler makes the retention check fail at `21` being replaced by `11`.

This is a client-rendered number-input example. It has no persistence or network submission. Browser validation was software-operated in Chrome 157.0.8103.40 with Node 24.19.0; it was not human manual testing or a test of an unprovided application. SSR, hydration, other browsers, formatting/caret transformations and arbitrary invalid numeric text were not tested.

References: [Solid event handlers](https://docs.solidjs.com/concepts/components/event-handlers), [signal getter/setter contract](https://docs.solidjs.com/reference/basic-reactivity/create-signal), and the [first-party playground source/import map](https://api.solidjs.com/repl/6fabf761-9664-462b-a96e-2e5f82c3b3f3). The unversioned documentation is general guidance; the release-candidate behavior above comes from the pinned native checks.

## Optional coffee

If this helped, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
