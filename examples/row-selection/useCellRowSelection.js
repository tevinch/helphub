import { useRef, useState } from 'react';
import { CompactSelection } from '@glideapps/glide-data-grid';

const emptySelection = () => ({
  columns: CompactSelection.empty(),
  rows: CompactSelection.empty(),
});

// Keep row-only selections in native range geometry before an additive operation.
function retainRows(current, retained) {
  if (retained === undefined) return current;
  let missing = retained;
  for (const range of [current.range, ...current.rangeStack]) {
    missing = missing.remove([range.y, range.y + range.height]);
  }
  const extra = [];
  let first;
  let end;
  function appendRun() {
    if (first !== undefined) {
      extra.push({ x: current.range.x, y: first, width: current.range.width, height: end - first });
    }
  }
  for (const row of missing) {
    if (first === undefined) {
      first = row; end = row + 1;
    } else if (row === end) {
      end++;
    } else {
      appendRun(); first = row; end = row + 1;
    }
  }
  appendRun();
  return extra.length === 0 ? current : { ...current, rangeStack: [...current.rangeStack, ...extra] };
}

export function useCellRowSelection() {
  const [gridSelection, setGridSelection] = useState(emptySelection);
  const beforePress = useRef(gridSelection);
  const lastClickedCell = useRef();
  const additiveRows = useRef();

  function onMouseDownCapture(event) {
    additiveRows.current = undefined;
    if (event.button === 0) {
      beforePress.current = gridSelection;
      if (event.ctrlKey || event.metaKey) additiveRows.current = gridSelection.rows;
    }
  }

  function clearPendingRows() {
    additiveRows.current = undefined;
  }

  function onGridSelectionChange(next) {
    const retained = additiveRows.current;
    additiveRows.current = undefined;
    // Marker/header selections already contain the rows/columns Glide chose.
    if (next.current === undefined) {
      setGridSelection(next);
      if (next.rows.length === 0 && next.columns.length === 0) {
        lastClickedCell.current = undefined;
      }
      return;
    }
    const current = retainRows(next.current, retained);
    let rows = CompactSelection.empty();
    const ranges = [current.range, ...current.rangeStack];
    for (const range of ranges) {
      rows = rows.add([range.y, range.y + range.height]);
    }
    setGridSelection({ ...next, current, rows });
  }

  function onCellClicked(cell, event) {
    clearPendingRows();
    if (event.button !== 0) return;
    if (cell[0] < 0) {
      // Row markers use a negative public column index.
      lastClickedCell.current = undefined;
      return;
    }
    const previous = beforePress.current;
    const multi = event.ctrlKey || event.metaKey;

    if (event.shiftKey) {
      const from = previous.current?.cell ?? lastClickedCell.current ?? cell;
      const top = Math.min(from[1], cell[1]);
      const bottom = Math.max(from[1], cell[1]) + 1;
      const rows = multi
        ? previous.rows.add([top, bottom])
        : CompactSelection.fromSingleSelection([top, bottom]);
      setGridSelection({
        columns: CompactSelection.empty(),
        rows,
        current: retainRows({
          cell: from,
          range: {
            x: Math.min(from[0], cell[0]),
            y: top,
            width: Math.abs(from[0] - cell[0]) + 1,
            height: bottom - top,
          },
          rangeStack: [],
        }, multi ? previous.rows : undefined),
      });
      event.preventDefault();
    } else if (multi) {
      const rows = previous.rows.hasIndex(cell[1])
        ? previous.rows.remove(cell[1])
        : previous.rows.add(cell[1]);
      // Clear the cell rectangle too; otherwise it still highlights a removed row.
      setGridSelection({ columns: CompactSelection.empty(), rows });
      lastClickedCell.current = cell;
      event.preventDefault();
    } else {
      lastClickedCell.current = cell;
    }
  }

  function onHeaderClicked() {
    clearPendingRows();
    lastClickedCell.current = undefined;
  }

  return {
    gridSelection,
    onMouseDownCapture,
    onMouseUpCapture: clearPendingRows,
    onKeyDown: clearPendingRows,
    onGridSelectionChange,
    onCellClicked,
    onHeaderClicked,
  };
}
