import { useCallback, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PreparedForm, type TraceEvent } from './prepared-form';

function Example({ name }: { name: string }) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const record = useCallback((event: TraceEvent) => setEvents(previous => [...previous, event]), []);
  return <>
    <PreparedForm name={name} onTrace={record} />
    <details open><summary>{name}: lifecycle trace</summary>
      <pre data-events={name}>{JSON.stringify(events, null, 2)}</pre>
    </details>
  </>;
}

createRoot(document.getElementById('root')!).render(<main>
  <h1>Prepare once before validation and submission</h1>
  <p>Edit a JSON document with a non-empty title. Each form has its own preparation cache.</p>
  <Example name="first" />
  <Example name="second" />
</main>);
