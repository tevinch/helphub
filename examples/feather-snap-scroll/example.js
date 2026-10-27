import FeatherScroll from './node_modules/scrollfeather/dist/featherScroll.esm.js';
import Snap from './node_modules/lenis/dist/lenis-snap.mjs';

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const headerOffset = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-offset'));
const status = document.querySelector('#status');

// FeatherScroll already runs the animation loop for this Lenis instance.
export const scroll = new FeatherScroll({duration:1.2});
export const snap = new Snap(scroll.lenis, {
  type:'mandatory',
  duration:1.4,
  easing:t => 1 - Math.pow(1 - t, 3),
  debounce:200,
});
document.querySelectorAll('.snap-point').forEach(element => snap.addElement(element));

if (reducedMotion) {
  snap.stop();
  scroll.updateOptions({smoothWheel:false});
}

document.querySelectorAll('nav a').forEach(link => {
  link.addEventListener('click', event => {
    event.preventDefault();
    scroll.scrollTo(link.hash, {
      offset:-headerOffset,
      duration:1,
      immediate:reducedMotion,
      onComplete:() => { status.textContent = `Arrived at ${link.hash.slice(1)}.`; },
    });
  });
});
