import { useRef, useState, type ComponentProps } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceArea, Tooltip, XAxis, YAxis } from 'recharts';

const data = [
  { name: 'a', value: 100 },
  { name: 'b', value: 200 },
  { name: 'c', value: 300 },
  { name: 'd', value: 150 },
  { name: 'e', value: 385 },
  { name: 'f', value: 300 },
  { name: 'g', value: 50 },
];

export type ChartObservation = {
  phase: 'down' | 'move' | 'up';
  label: string | null;
  index: number | null;
  buttons: number;
};

type Handler = NonNullable<ComponentProps<typeof LineChart>['onMouseDown']>;
type Point = { label: string; index: number };
type Selection = { start: Point; end: Point };

function pointFrom(state: Parameters<Handler>[0]): Point | null {
  if (state.activeIndex == null || state.activeLabel == null) return null;
  const index = Number(state.activeIndex);
  const label = String(state.activeLabel);
  if (!Number.isInteger(index) || data[index]?.name !== label) return null;
  return { label, index };
}

export function ChartRange({ onEvent }: { onEvent?: (event: ChartObservation) => void }) {
  const draft = useRef<Selection | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);

  const observe = (phase: ChartObservation['phase'], state: Parameters<Handler>[0], event: Parameters<Handler>[1]) => {
    onEvent?.({
      phase,
      label: state.activeLabel == null ? null : String(state.activeLabel),
      index: state.activeIndex == null ? null : Number(state.activeIndex),
      buttons: event.buttons,
    });
  };

  const onMouseDown: Handler = (state, event) => {
    observe('down', state, event);
    const start = pointFrom(state);
    draft.current = event.button === 0 && start ? { start, end: start } : null;
    setSelection(null);
  };

  const onMouseMove: Handler = (state, event) => {
    observe('move', state, event);
    const end = pointFrom(state);
    if (draft.current && event.buttons === 1 && end) draft.current.end = end;
  };

  const onMouseUp: Handler = (state, event) => {
    observe('up', state, event);
    const current = draft.current;
    draft.current = null;
    const end = pointFrom(state);
    if (event.button === 0 && current && end && current.end.index === end.index) {
      setSelection(current);
    }
  };

  const lower = selection && (selection.start.index <= selection.end.index ? selection.start : selection.end);
  const upper = selection && (selection.start.index <= selection.end.index ? selection.end : selection.start);

  return (
    <main>
      <h1>Chart range selection</h1>
      <p>Drag across the chart to select a category range.</p>
      <LineChart width={800} height={400} data={data}
        onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp}>
        <XAxis dataKey="name" />
        <YAxis dataKey="value" />
        <Tooltip />
        <CartesianGrid strokeOpacity={0.1} />
        <Line dataKey="value" />
        {lower && upper && (
          <ReferenceArea x1={lower.label} x2={upper.label} fill="#3182bd" fillOpacity={0.15} pointerEvents="none" />
        )}
      </LineChart>
      <p role="status" aria-label="Selection">
        {selection && lower && upper
          ? `Selected ${selection.start.label} (${selection.start.index}) → ${selection.end.label} (${selection.end.index}). Range: ${lower.label}–${upper.label}.`
          : 'No completed selection.'}
      </p>
    </main>
  );
}
