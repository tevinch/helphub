import React, { StrictMode, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ClientSideRowModelModule, DateFilterModule } from 'ag-grid-community';
import { AgGridProvider, AgGridReact } from 'ag-grid-react';
import 'flatpickr/dist/flatpickr.css';
import { DatePicker } from './date-picker.jsx';
import './styles.css';

const rows = [
  { name: 'Early', date: new Date(2026, 10, 8) },
  { name: 'Middle', date: new Date(2026, 10, 14) },
  { name: 'Late', date: new Date(2026, 10, 21) },
  { name: 'Last', date: new Date(2026, 10, 27) },
];
const columns = [
  { field: 'name', flex: 1 },
  {
    field: 'date',
    flex: 1,
    cellDataType: 'date',
    filter: 'agDateColumnFilter',
    dateComponent: DatePicker,
    valueFormatter: ({ value }) => value?.toLocaleDateString('en-GB') ?? '',
    filterParams: {
      filterOptions: ['inRange'],
      filterPlaceholder: 'dd/mm/yyyy',
      maxNumConditions: 1,
      inRangeInclusive: true,
    },
  },
];
const modules = [ClientSideRowModelModule, DateFilterModule];

function Example() {
  const grid = useRef(null);
  const [model, setModel] = useState(null);
  return (
    <main>
      <h1>Validate a custom date range</h1>
      <button type="button" onClick={() => grid.current.api.showColumnFilter('date')}>
        Open date filter
      </button>
      <div className="grid">
        <AgGridProvider modules={modules}>
          <AgGridReact
            ref={grid}
            columnDefs={columns}
            rowData={rows}
            onFilterChanged={({ api }) => setModel(api.getColumnFilterModel('date'))}
          />
        </AgGridProvider>
      </div>
      <output aria-label="Applied date filter">{model ? JSON.stringify(model) : 'No date filter'}</output>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<StrictMode><Example /></StrictMode>);
