import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import './style.css';
import { validateRange, localStamp } from './range.mjs';

function App() {
  const [[start, end], setRange] = useState([
    new Date(2026, 10, 3, 9), new Date(2026, 10, 3, 17),
  ]);
  const [result, setResult] = useState(null);
  const error = validateRange(start, end);
  function submit(event) {
    event.preventDefault();
    if (!error) setResult({ start: localStamp(start), end: localStamp(end) });
  }
  return <main>
    <h1>Independent date and time range</h1>
    <p>Choose the dates, then edit the start and end times separately.</p>
    <form onSubmit={submit}>
      <label htmlFor="range">Date and time range</label>
      <DatePicker id="range" selected={start} startDate={start} endDate={end}
        onChange={dates => { setRange(dates); setResult(null); }}
        selectsRange showTimeInput allowSameDay isClearable
        timeInputLabel="Time" dateFormat="yyyy-MM-dd HH:mm" strictParsing
        shouldCloseOnSelect={false} />
      <p id="validation" role="alert">{error}</p>
      <button type="submit" disabled={Boolean(error)}>Use range</button>
    </form>
    <pre id="result" aria-live="polite">{result ? JSON.stringify(result, null, 2) : 'No range submitted.'}</pre>
    <p>This example uses local dates and times. The output has no UTC offset or time zone.</p>
  </main>;
}
createRoot(document.getElementById('root')).render(<App />);
