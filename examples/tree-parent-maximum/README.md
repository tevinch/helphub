# Tree with a parent maximum

Let the parent own `max-height` and `overflow: auto`. Set Ant Design Tree's `virtual={false}` and omit its `height` prop, so a short tree stays short and expanded content scrolls inside the parent.

```css
.files-panel {
  max-height: 400px;
  overflow: auto;
}
```

The example uses Ant Design **6.7.1** and React **19.3.1**. It contains exactly 100 nodes, nested branches, a long title and a disabled leaf. The controls change only the parent's maximum, between 400px and 180px; they preserve the same data and selection.

## Run

Use Node 20.19+ or 22.12+ (Node 24 also works).

```sh
npm ci --ignore-scripts
npm run dev
```

Open the local URL printed by Vite. To run the browser checks and production build:

```sh
npx playwright install --no-shell chromium firefox
npm test
npm run build
```

Vite and Playwright are pinned at 8.3.8 and 1.65.1. The lockfile pins the dependency graph. The install command skips package lifecycle scripts; browser downloads are an explicit separate step.

The Chromium test project uses the full browser through `channel: 'chromium'`, matching Playwright's documented [new headless mode](https://playwright.dev/docs/browsers#chromium-new-headless-mode). The install command skips the separate headless shell.

## Keyboard scrolling

An outer scroller also needs to keep the Tree's active item visible during keyboard interaction. The Tree exposes that item through the standard `aria-activedescendant` attribute. The small event composition in this example waits until native focus/key handling has updated the attribute, then moves only the owned panel enough to reveal that element. It leaves native navigation, selection and expansion in charge.

```jsx
const panelRef = useRef(null);
const revealActive = useParentReveal(panelRef);

<section ref={panelRef} className="files-panel">
  <Tree
    virtual={false}
    onFocus={revealActive}
    onKeyDown={revealActive}
    treeData={treeData}
  />
</section>
```

Copy the small [`useParentReveal`](src/useParentReveal.js) helper with the panel recipe. If you already handle these events, call your existing handlers too. The helper does not call `preventDefault`, replace native keys or use private Tree selectors.

Pending work is replaced on a new event and cancelled on unmount. Before scrolling, the callback checks that the panel and Tree still exist, the Tree still has focus, and the active treeitem belongs to it. Moving focus away cannot cause a later panel scroll. Avoid `scrollIntoView()` here: it may also move outer ancestors or the page.

The demo reserves a 400px presentation area to keep the separate Tree and page text stationary while the panel grows or shrinks. That reserved area is optional; the panel itself has no fixed height. Titles wrap through the public `styles.itemTitle` setting. No global Tree CSS override or dependency patch is used.

## Scope

Scripted acceptance passed in Firefox 159.0 and Chrome for Testing 159.0.8154.6 on macOS with Playwright 1.65.1. Checks cover pointer selection, collapse/re-expand, 400→180→400 parent resizing, native keyboard traversal and selection, offscreen initial focus, disabled content, long titles, and focus-away without later scrolling. A CSS-only baseline failed active-item visibility in Firefox; the event helper addresses that gap.

This is an independent consumer example for a parent-controlled maximum, rather than a reproduction of the original linked CodeSandbox, which was unavailable for inspection. It does not establish the original layout, operating-system behavior, screen-reader behavior or adoption by the requester.

A numeric Tree `height` is already a shrinking maximum when virtualization is disabled. If that value fits your layout, use the built-in option. This example is for a maximum owned by parent CSS. A percentage maximum needs a containing block with a definite height; `max-height: 100%` alone does not supply one. Avoid measuring an auto-sized panel and feeding its collapsed height back into Tree.

See the official [Tree API](https://ant.design/components/tree/), [ARIA active descendant reference](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-activedescendant), and [`scrollIntoView` ancestor behavior](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
