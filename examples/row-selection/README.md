# Toggle complete rows by clicking data cells

A controlled Glide Data Grid can select whole rows from cell ranges, but rebuilding `rows` from `current` alone cannot toggle a selected row off. The old cell rectangle can also keep a removed row highlighted.

This example keeps ordinary data-cell clicks and dragging, then handles Ctrl-click and Command-click through the public `onCellClicked` callback. It uses the published `@glideapps/glide-data-grid` 6.0.3 package and React 18.3.1. The [original question](https://github.com/glideapps/glide-data-grid/issues/1191) was opened June 18, 2026 and followed up July 16, 2026.

## Run

Use Node.js 22.12 or later:

```sh
npm ci
npm run dev
```

Open the local address Vite prints. Click an ordinary cell, then Ctrl-click the same cell: its entire row is deselected and `current` becomes `null` in the displayed selection state.

- A plain cell click selects that row.
- Ctrl-click or Command-click adds or removes just that row.
- Shift-click selects the range from the previous anchor to the clicked cell. After a toggle, the last clicked cell is the new anchor.
- Ctrl+Shift-click or Command+Shift-click adds the range to the existing rows.
- Dragging across cells keeps Glide's native rectangle and selects the rows it covers.
- Row markers, column headers and Escape keep their native behavior. Use the platform's usual modifier for multiple markers or headers.

The demo's eight rows are read-only so you can inspect selection without changing their values. Expand “Original read-only values” to compare them.

## Use the hook in your grid

Copy [useCellRowSelection.js](./useCellRowSelection.js) into your application:

```jsx
const { onMouseDownCapture, onMouseUpCapture, ...selection } = useCellRowSelection();

return (
  <div onMouseDownCapture={onMouseDownCapture} onMouseUpCapture={onMouseUpCapture}>
    <DataEditor
      {...selection}
      columns={columns}
      rows={data.length}
      getCellContent={getCellContent}
      rangeSelect="multi-rect"
      rowSelect="multi"
      columnSelect="multi"
      rangeSelectionBlending="exclusive"
      rowSelectionBlending="exclusive"
      columnSelectionBlending="exclusive"
    />
  </div>
);
```

The wrapper mouse-down capture handler is necessary: Glide updates the current cell on mouse-down, before `onCellClicked` runs on mouse-up. Saving the selection before that update lets the later click toggle the row against its previous state. The mouse-up capture discards any unused pending rows; the hook also clears them before native keyboard handling.

The hook maps native cell rectangles and `rangeStack` entries to full rows. On a modified cell click it changes the row selection and removes `current` and its range stack, so a stale rectangle cannot repaint a row you just deselected. Before the next native additive drag, retained rows without a rectangle are represented as contiguous runs in `rangeStack`. Additive Shift-click does the same for disjoint rows. Later native drag updates and Alt+Arrow navigation can therefore keep them. Notifications without a current cell retain the rows or columns supplied by Glide; they include marker and header selections.

Keep your data-loading, editing and cell-permission callbacks. The hook changes selection only; the demo's `readonly` setting is not part of the hook. If your grid already uses these selection/click/header/keyboard handlers, compose them deliberately rather than overwriting one with a later prop spread. The wrapper must receive the real mouse-down event before the grid does.

This recipe assumes every displayed row is selectable. Applications with disabled-row policies must enforce those policies as well. Selection uses displayed row indexes; sorting, filtering or replacing the data needs the application's usual selection reset or ID-to-index mapping. Touch, pen, editing behavior and host-specific restrictions were not validated here.

See Glide's [selection documentation](https://docs.grid.glideapps.com/api/dataeditor/selection-handling) and the [6.0.3 public event types](https://unpkg.com/@glideapps/glide-data-grid@6.0.3/dist/dts/data-editor/data-editor.d.ts).

## Check

```sh
npm test
npm run build
```

The browser check requires Playwright's Chromium to be installed. If you already have a compatible Chromium executable, set `CHROMIUM_EXECUTABLE` to its absolute path. The check does not download a browser.

One scripted Chromium flow performs 47 physical mouse/keyboard operations, checking Ctrl/Command toggles, removed-row rectangle cleanup, Shift and additive ranges, two-column dragging and disjoint range stacks, additive dragging after toggles and Shift-click, Alt+Arrow selection retention, ordinary keyboard arrows, subsequent interaction, native headers and markers, Escape and unchanged source values. These are software-operated browser checks; the original application's behavior and the requester's adoption are unverified.

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It's entirely optional; the example remains free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
