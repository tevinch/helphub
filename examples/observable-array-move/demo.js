import { observable, observe } from '@legendapp/state';
import { moveItem } from './move-item.js';

const state$ = observable({ arr: [{ id: 0 }, { id: 1 }, { id: 2 }] });
const items$ = state$.arr;
const originalArray = items$.peek();
const dispose = observe(() => {
  console.log('order:', items$.get().map((item) => item.id).join(' '));
});

try {
  moveItem(items$, 2, 1);
  moveItem(items$, 1, 2);
  moveItem(items$, 2, 1);
  console.log('same array:', items$.peek() === originalArray);
} finally {
  dispose();
}
