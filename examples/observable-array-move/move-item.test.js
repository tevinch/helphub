import assert from 'node:assert/strict';
import test from 'node:test';
import { observable, observe } from '@legendapp/state';
import { moveItem } from './move-item.js';

function track() {
  const state$ = observable({ arr: [{ id: 0 }, { id: 1 }, { id: 2 }] });
  const items$ = state$.arr;
  const array = items$.peek();
  const objects = [array[0], array[1], array[2]];
  const observations = [];
  const dispose = observe(() => {
    // Same dependency as the original: get the array, then read raw item ids.
    observations.push(items$.get().map((item) => item.id));
  });
  return { items$, array, objects, observations, dispose };
}

test('forward, reverse and repeated moves retain identities with one final-only observation each', () => {
  const h = track();
  try {
    assert.deepEqual(h.observations, [[0, 1, 2]]);
    const steps = [[2, 1, [0, 2, 1]], [1, 2, [0, 1, 2]], [2, 1, [0, 2, 1]]];
    for (const [from, to, expected] of steps) {
      const before = h.observations.length;
      moveItem(h.items$, from, to);
      const actual = h.items$.peek();
      assert.deepEqual(actual.map((item) => item.id), expected);
      assert.equal(h.observations.length - before, 1);
      assert.deepEqual(h.observations.slice(before), [expected]);
      assert.equal(actual, h.array);
      for (let i = 0; i < expected.length; i += 1) {
        assert.equal(actual[i], h.objects[expected[i]]);
      }
    }
  } finally {
    h.dispose();
  }
  const calls = h.observations.length;
  h.items$[0].id.set(100);
  assert.equal(h.observations.length, calls, 'disposed observer receives no later mutation');
});

test('omitting batch exposes an intermediate state and violates the single-notification requirement', () => {
  const h = track();
  try {
    const item = h.items$[2].peek();
    h.items$.splice(2, 1);
    h.items$.splice(1, 0, item);
    assert.deepEqual(h.items$.peek().map((entry) => entry.id), [0, 2, 1]);
    assert.deepEqual(h.observations, [[0, 1, 2], [0, 1], [0, 2, 1]]);
    assert.equal(h.observations.length - 1, 2);
  } finally {
    h.dispose();
  }
});

test('invalid indices reject before any mutation or notification', () => {
  const h = track();
  try {
    for (const [from, to] of [[-1, 1], [3, 1], [1, -1], [1, 3], [0.5, 1], [1, NaN]]) {
      assert.throws(() => moveItem(h.items$, from, to), RangeError);
      assert.deepEqual(h.items$.peek().map((item) => item.id), [0, 1, 2]);
      assert.equal(h.items$.peek(), h.array);
      assert.deepEqual(h.observations, [[0, 1, 2]]);
    }
    const empty$ = observable([]);
    assert.throws(() => moveItem(empty$, 0, 0), RangeError);
    assert.deepEqual(empty$.peek(), []);
  } finally {
    h.dispose();
  }
});

test('moving to the same index leaves values and observations unchanged', () => {
  const h = track();
  try {
    moveItem(h.items$, 1, 1);
    assert.equal(h.items$.peek(), h.array);
    assert.deepEqual(h.items$.peek().map((item) => item.id), [0, 1, 2]);
    assert.deepEqual(h.observations, [[0, 1, 2]]);
  } finally {
    h.dispose();
  }
});
