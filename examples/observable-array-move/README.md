# Move an observable array item

Move an item with Legend-State's observable array methods while preserving the array and item objects. Capture the plain item value before removing it, then batch the two splices so observers see only the completed order.

```js
import { observable } from '@legendapp/state';
import { moveItem } from './move-item.js';

const state$ = observable({ arr: [{ id: 0 }, { id: 1 }, { id: 2 }] });
const items$ = state$.arr;
moveItem(items$, 2, 1);
console.log(items$.peek()); // [{ id: 0 }, { id: 2 }, { id: 1 }]
```

`from` and `to` are zero-based indices; `to` is the item's position in the final array. Both must be valid integer indices. Invalid indices throw `RangeError` before mutation; moving to the same index does nothing. The sample uses an ordinary array of objects.

The helper uses the existing package directly:

```js
batch(() => {
  const item = items$[from].peek();
  items$.splice(from, 1);
  items$.splice(to, 0, item);
});
```

Reinserting `items$[from]` passes an observable proxy instead of the plain item. Calling `.peek()` before removal avoids that mistake. Mutate through the observable's `splice` methods: modifying the raw array returned by `.peek()` bypasses change notifications. Calling `.set()` afterward cannot recover changes already made to that same underlying data.

This avoids creating and setting a replacement array in the consumer. The library still creates internal snapshots; it is not a zero-allocation operation.

Use Node 24 and run:

```sh
npm ci --ignore-scripts
npm test
npm start
```

The demo prints:

```text
order: 0 1 2
order: 0 2 1
order: 0 1 2
order: 0 2 1
same array: true
```

The default dependency is pinned to stable 2.1.15. The same helper, tests and demo were also checked with preview 3.0.0-beta.48 in a separate installation. Tests check forward, reverse and repeated moves, original array/item identities, exactly one notification per completed move, invalid indices, no-op behavior and observer disposal. A control without batching records the intermediate state and two notifications.

These are Node core checks of the inline array workflow in [Legend-State #660](https://github.com/LegendApp/legend-state/issues/660). They do not establish React Compiler or application compatibility.

See the official [observable/value and array guidance](https://legendapp.com/open-source/state/v3/usage/observable/#arrays) and [batching guidance](https://legendapp.com/open-source/state/v3/usage/reactivity/#batching). Source is available under the [MIT license](./LICENSE).

## Optional coffee

This example is free to use. If it helped, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
