import { cleanup, fireEvent, render } from '@testing-library/react';
import { commands } from '@vitest/browser/context';
import { afterEach, beforeEach, expect, test } from 'vitest';
import { ChartRange, type ChartObservation } from '../src/ChartRange';

beforeEach(async () => {
  await commands.moveOutside();
});

afterEach(async () => {
  // Release even when a deliberately incomplete gesture leaves the button down.
  await commands.release();
  cleanup();
});

function mount() {
  const events: ChartObservation[] = [];
  const view = render(<ChartRange onEvent={(event) => events.push(event)} />);
  const chart = () => view.container.querySelector<SVGSVGElement>('.recharts-surface')!;
  const status = () => view.getByRole('status', { name: 'Selection' }).textContent;
  return { ...view, events, chart, status };
}

async function hover(label: string, events: ChartObservation[]) {
  const previous = events.length;
  await commands.moveToLabel(label);
  // The callback runs after Recharts' real hover update, without fake timers.
  await expect.poll(() => events.slice(previous).findLast((event) => event.phase === 'move')?.label)
    .toBe(label);
  await expect.poll(() => {
    const tooltip = document.querySelector<HTMLElement>('.recharts-tooltip-wrapper');
    if (!tooltip || getComputedStyle(tooltip).visibility !== 'visible') return null;
    return tooltip.querySelector('.recharts-tooltip-label')?.textContent;
  }).toBe(label);
}

async function drag(labels: string[], events: ChartObservation[], release = true) {
  await hover(labels[0], events);
  const previous = events.length;
  await commands.press();
  await expect.poll(() => events.slice(previous).some((event) => event.phase === 'down')).toBe(true);
  for (const label of labels.slice(1)) await hover(label, events);
  if (release) await commands.release();
  return events.slice(previous);
}

test('press-only reproduces an unavailable active label', async () => {
  const { chart, events } = mount();
  await expect.poll(() => chart().querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value').length).toBe(7);
  const box = chart().getBoundingClientRect();
  // Match a press-only DOM test: no mouseenter/mousemove has populated hover state.
  fireEvent.mouseDown(chart(), { clientX: box.left + 200, clientY: box.top + 200, button: 0 });
  await expect.poll(() => events.find((event) => event.phase === 'down')).toBeDefined();
  expect(events.find((event) => event.phase === 'down')).toEqual({ phase: 'down', label: null, index: null, buttons: 0 });
});

test('synchronous DOM hover and press omit the hover update wait', async () => {
  const { chart, container, events } = mount();
  await expect.poll(() => chart().querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value').length).toBe(7);
  const tick = Array.from(container.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value'))
    .find((element) => element.textContent === 'b')!.getBoundingClientRect();
  const box = chart().getBoundingClientRect();
  const position = { clientX: tick.left + tick.width / 2, clientY: box.top + box.height / 2 };
  // Both DOM events run in one task, so the intervening animation frame cannot run.
  fireEvent.mouseMove(chart(), position);
  fireEvent.mouseDown(chart(), { ...position, button: 0, buttons: 1 });
  await expect.poll(() => events.find((event) => event.phase === 'down')).toBeDefined();
  expect(events.find((event) => event.phase === 'down')).toEqual({ phase: 'down', label: null, index: null, buttons: 1 });
});

test('a drag without release cannot complete a selected range', async () => {
  const { events, status } = mount();
  const observed = await drag(['b', 'c', 'd', 'e'], events, false);
  expect(observed.filter((event) => event.phase === 'move' && event.buttons === 1).map(({ label }) => label))
    .toEqual(['c', 'd', 'e']);
  expect(observed.some((event) => event.phase === 'up')).toBe(false);
  expect(status()).toBe('No completed selection.');
});

test('completes exact ranges, then a different range and a reverse range', async () => {
  const { chart, container, events, status } = mount();
  await expect.poll(() => container.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value').length)
    .toBe(7);
  await expect.poll(() => container.querySelectorAll('.recharts-line-dot').length).toBe(7);
  const lineBefore = container.querySelector('.recharts-line-curve')?.getAttribute('d');
  const xBefore = container.querySelector('.recharts-xAxis-tick-labels')?.textContent;
  const yBefore = container.querySelector('.recharts-yAxis-tick-labels')?.textContent;
  expect(lineBefore).toBeTruthy();
  expect(xBefore).toBe('abcdefg');
  expect(yBefore).toBeTruthy();

  const first = await drag(['b', 'c', 'd', 'e'], events);
  await expect.poll(status).toBe('Selected b (1) → e (4). Range: b–e.');
  expect(first.filter((event) => event.phase === 'down')).toEqual([
    { phase: 'down', label: 'b', index: 1, buttons: 1 },
  ]);
  expect(first.filter((event) => event.phase === 'move' && event.buttons === 1).map(({ label, index }) => [label, index]))
    .toEqual([['c', 2], ['d', 3], ['e', 4]]);
  expect(first.filter((event) => event.phase === 'up')).toEqual([
    { phase: 'up', label: 'e', index: 4, buttons: 0 },
  ]);

  const second = await drag(['a', 'b', 'c'], events);
  await expect.poll(status).toBe('Selected a (0) → c (2). Range: a–c.');
  expect(second.find((event) => event.phase === 'down')).toEqual({ phase: 'down', label: 'a', index: 0, buttons: 1 });
  expect(second.find((event) => event.phase === 'up')).toEqual({ phase: 'up', label: 'c', index: 2, buttons: 0 });

  const reverse = await drag(['f', 'e', 'd'], events);
  await expect.poll(status).toBe('Selected f (5) → d (3). Range: d–f.');
  expect(reverse.find((event) => event.phase === 'down')).toEqual({ phase: 'down', label: 'f', index: 5, buttons: 1 });
  expect(reverse.filter((event) => event.phase === 'move' && event.buttons === 1).map(({ label, index }) => [label, index]))
    .toEqual([['e', 4], ['d', 3]]);
  expect(reverse.find((event) => event.phase === 'up')).toEqual({ phase: 'up', label: 'd', index: 3, buttons: 0 });

  expect(chart().getBoundingClientRect().width).toBe(800);
  expect(chart().getBoundingClientRect().height).toBe(400);
  expect(container.querySelectorAll('.recharts-line-dot')).toHaveLength(7);
  expect(container.querySelector('.recharts-line-curve')?.getAttribute('d')).toBe(lineBefore);
  expect(container.querySelector('.recharts-xAxis-tick-labels')?.textContent).toBe(xBefore);
  expect(container.querySelector('.recharts-yAxis-tick-labels')?.textContent).toBe(yBefore);
  expect(container.querySelector('.recharts-cartesian-grid')).not.toBeNull();
  const highlight = container.querySelector('.recharts-reference-area-rect')!.getBoundingClientRect();
  const ticks = Array.from(container.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value'));
  const center = (label: string) => {
    const box = ticks.find((tick) => tick.textContent === label)!.getBoundingClientRect();
    return box.left + box.width / 2;
  };
  expect(highlight.left).toBeCloseTo(center('d'), 0);
  expect(highlight.right).toBeCloseTo(center('f'), 0);
});
