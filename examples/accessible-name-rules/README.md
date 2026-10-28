# Why unnamed menu items appear under different axe rules

`role="menuitem"` does not make axe use the same naming rule for every underlying HTML element. Rule selection also uses the element's native naming methods.

For the reduced example in [axe-core #5501](https://github.com/dequelabs/axe-core/issues/5501), both axe-core 4.13.0 and 4.14.0 produce this grouping:

| Element | Naming rule | Reason |
| --- | --- | --- |
| `<div role="menuitem">` | `aria-command-name` | The role matches, and a `div` has no native naming method. |
| `<button role="menuitem">` | `button-name` | The button rule selects `button`; `menuitem` still requires a name. |
| `<a href="#" role="menuitem">` | `link-name` | The link rule selects `a[href]`, including this element with its explicit role. |

The [`aria-command-name` rule](https://github.com/dequelabs/axe-core/blob/v4.13.0/lib/rules/aria-command-name.json) uses [`no-naming-method-matches`](https://github.com/dequelabs/axe-core/blob/v4.13.0/lib/rules/no-naming-method-matches.js). That matcher excludes elements for which axe already defines a native naming method, so it does not duplicate the button and link findings. The [`button-name` matcher](https://github.com/dequelabs/axe-core/blob/v4.13.0/lib/rules/no-explicit-name-required-matches.js) still includes a button whose explicit role requires a name. The [`link-name` selector](https://github.com/dequelabs/axe-core/blob/v4.13.0/lib/rules/link-name.json) is `a[href]`.

These three findings share the missing accessible-name problem. For triage, group the affected nodes by that problem while retaining each original rule ID, target and impact. Do not suppress `button-name` or `link-name` in order to count only `aria-command-name`, or change the elements just to obtain a different report label.

Give each control a meaningful name. Visible text or `aria-labelledby` are also options; for an icon-only control, for example:

```html
<button role="menuitem" aria-label="Save">
  <i class="icon-save" aria-hidden="true"></i>
</button>
```

Choose names that describe the actual actions. The named fixture in [index.html](./index.html) preserves the original `div`, `button`, link and roles, then supplies names. Its icons are decorative once the controls have names.

## Run the comparison

Use Node.js 22 or later. From this directory:

```sh
npm ci --ignore-scripts
npx playwright install chromium
npm test
```

[verify.mjs](./verify.mjs) loads the real published axe bundles into headless Chromium. For each version it checks that:

- The original fixture produces exactly one finding under each rule, targeting the expected element.
- The named fixture has no violations or incomplete results for those three rules, and all three individual nodes appear in the corresponding passes.
- A second scan preserves the same result and leaves the fixture unchanged.

The output includes the actual axe versions and node targets. This example was checked on macOS Arm64 with Node.js 24.22.1 and Playwright 1.64.1. It uses axe-core directly; the browser extension UI and the original application were not tested.

This is a reduced naming diagnostic. It runs only these three rules and does not implement menu actions or keyboard navigation. A complete menubar also needs the interaction described in the [WAI-ARIA menubar pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menubar/). Passing these naming checks alone does not establish that the menu is accessible.

## Optional coffee

This example is free to use. If it saves you some time, a small coffee contribution is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
