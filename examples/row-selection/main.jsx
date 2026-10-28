import React from 'react';
import { createRoot } from 'react-dom/client';
import DataEditor, { GridCellKind } from '@glideapps/glide-data-grid';
import { useCellRowSelection } from './useCellRowSelection.js';
import '@glideapps/glide-data-grid/dist/index.css';
import './style.css';

const columns = [{ title: 'Name', width: 200 }, { title: 'Value', width: 200 }];
const rows = Array.from({ length: 8 }, (_, index) => [`Row ${index}`, `Keep ${index}`]);
function getCellContent([column, row]) {
  const value = rows[row][column];
  return { kind: GridCellKind.Text, data: value, displayData: value, allowOverlay: false, readonly: true };
}

function App() {
  const { onMouseDownCapture, onMouseUpCapture, ...selection } = useCellRowSelection();
  const { gridSelection } = selection;
  const visibleState = {
    rows: gridSelection.rows.toArray(),
    columns: gridSelection.columns.toArray(),
    current: gridSelection.current ?? null,
  };
  return <main>
    <h1>Select complete rows from data cells</h1>
    <p>Click a data cell to select its row. Ctrl-click or Command-click to toggle a row.
      Shift-click selects a range; add Ctrl or Command to keep the existing rows. Drag across cells as usual.</p>
    <div className="grid-shell" onMouseDownCapture={onMouseDownCapture} onMouseUpCapture={onMouseUpCapture}>
      <DataEditor {...selection} columns={columns} rows={rows.length} getCellContent={getCellContent}
        width={700} height={350} rowHeight={34} headerHeight={36}
        rowMarkers={{ kind: 'both', width: 44 }} rowSelect="multi" columnSelect="multi"
        rangeSelect="multi-rect" rangeSelectionBlending="exclusive"
        rowSelectionBlending="exclusive" columnSelectionBlending="exclusive" />
    </div>
    <h2>Current selection</h2>
    <pre id="selection-state" aria-live="polite">{JSON.stringify(visibleState, null, 2)}</pre>
    <details><summary>Original read-only values</summary><pre id="source-data">{JSON.stringify(rows, null, 2)}</pre></details>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
