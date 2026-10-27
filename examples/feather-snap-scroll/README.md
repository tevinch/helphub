# FeatherScroll: slower snapping and section links

This example answers the [FeatherScroll usage question](https://github.com/ranvijay-raj/Feather-scroll-js/issues/2) with one scrolling instance, section links and a timed snap after wheel scrolling. It uses unmodified `scrollfeather` **1.2.9**, whose distribution bundles Lenis **1.3.1**, and the matching `lenis/snap` extension from **1.3.1**.

## Browser support

FeatherScroll does not publish a browser/version support matrix or minimum versions. This example was checked with **Chromium 156.0.8078.4** on macOS using scripted browser operations. Firefox, Safari, touch input and older browser versions were not verified.

The shipped JavaScript requires modern JavaScript syntax and browser APIs, including `requestAnimationFrame`, `ResizeObserver` and `MutationObserver`; the 1.3.1 snap extension also calls `Array.prototype.findLast` without providing a polyfill. Check those capabilities and run the example on your target browsers. A browser table for an optional feature in a newer Lenis release is not a support guarantee for FeatherScroll's bundled version.

## CSS smooth scrolling

Let the scrolling library control animation on its scrolling root:

```css
html {
  scroll-behavior: auto;
  scroll-snap-type: none;
}
```

Remove competing `scroll-behavior: smooth` and native CSS scroll snapping from that same root. Lenis documents that native CSS scroll snap is not supported and points to its snap extension instead. Keep unrelated layout and content styles. If your application uses a custom scrolling container, these settings belong on that container; this example verifies full-page vertical scrolling.

## Scroll to a section

The existing FeatherScroll instance forwards the target and options to Lenis:

```js
scroll.scrollTo('#middle', {
  offset: -72,
  duration: 1, // seconds
  onComplete: () => {
    // The requested navigation has finished.
  },
});
```

The target can also be an existing element or a numeric scroll position. The method uses a completion callback; it does not return a completion promise. For a navigation link, prevent the browser's default anchor jump before calling it. See the complete handler in [example.js](example.js).

The negative offset leaves room for the fixed header. Each section has a small `.snap-point` marker positioned the same 72 pixels above it, so later automatic snapping preserves that clearance. The shared distance is declared as `--header-offset` in the example's CSS and read by JavaScript. Changing the offset without moving the snap points would let snapping undo the intended alignment.

## Make snapping take longer

FeatherScroll 1.2.9 has no built-in snap option. This integration uses the existing underlying instance with the official extension:

```js
// For a bundler; the runnable page uses the equivalent local distribution files.
import FeatherScroll from 'scrollfeather';
import Snap from 'lenis/snap';

const scroll = new FeatherScroll({ duration: 1.2 });
const snap = new Snap(scroll.lenis, {
  type: 'mandatory',
  duration: 1.4, // seconds for the snap animation
  easing: t => 1 - Math.pow(1 - t, 3),
  debounce: 200, // milliseconds before the pending snap check
});

document.querySelectorAll('.snap-point').forEach(element => {
  snap.addElement(element);
});
```

Increase the snap `duration` for a slower settling animation. The wheel animation and snap animation have separate settings. `debounce` delays the pending snap check after the plugin observes slowing movement; it is not an animation duration or an exact delay after the last wheel event.

Do not create a second Lenis instance or add another animation loop: FeatherScroll already runs one. `.lenis` is a field exposed by the 1.2.9 implementation, rather than an integration API promised by its README, so this recipe pins that version. Version 1.3.1 of the extension has `addElement`; examples for newer versions may use methods that do not exist here.

The original question does not include its snapping code, so this does not diagnose its exact cause. It provides a complete alternative using the existing timing controls, without native CSS snap competing for the same scroll position.

## Run

With Node.js 20 or newer and Python 3:

```sh
npm ci --ignore-scripts
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000`. Click **Middle**, scroll forward until it settles at **End**, then scroll back. The links and later wheel interactions remain usable, and the note field keeps its contents.

The example reads the reduced-motion preference at page load. When enabled, links move immediately, automatic snapping stops and wheel input stays native. Reload after changing the system preference.

## Verify

```sh
npx playwright install chromium
npm test
```

The verifier serves the example on a local ephemeral port and runs real Chromium interactions. It checks six completed anchor/wheel operations, intermediate native scroll positions, final section alignment, gradual snap timing, repeated reverse scrolling, the shared underlying instance and preserved content. A separate reduced-motion page checks immediate navigation and native wheel settings.

The check was run with Node.js 24.22.1, Playwright 1.64.1 and Chromium 156.0.8078.4. These are scripted checks of this example, not human manual testing or validation of the requester's application.

References: [FeatherScroll source](https://github.com/ranvijay-raj/Feather-scroll-js/blob/main/src/featherScroll.js), [Lenis guidance](https://github.com/darkroomengineering/lenis#limitations), [snap extension](https://github.com/darkroomengineering/lenis/tree/main/packages/snap). The example uses the pinned 1.3.1 extension; its installed source/types are the reference for the available methods.

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
