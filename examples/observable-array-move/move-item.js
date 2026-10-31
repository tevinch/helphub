import { batch } from '@legendapp/state';

// `to` is the desired index in the final array.
export function moveItem(items$, from, to) {
  const length = items$.peek().length;
  if (!Number.isInteger(from) || !Number.isInteger(to) ||
      from < 0 || to < 0 || from >= length || to >= length) {
    throw new RangeError('from and to must be valid array indices');
  }
  if (from === to) return;

  batch(() => {
    const item = items$[from].peek();
    items$.splice(from, 1);
    items$.splice(to, 0, item);
  });
}
