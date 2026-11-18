import { useEffect, useRef } from 'react';

export function useParentReveal(panelRef) {
  const frame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  return event => {
    // React clears currentTarget after the handler returns.
    const tree = event.currentTarget;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      const panel = panelRef.current;
      if (!panel?.isConnected || !tree.isConnected || !panel.contains(tree)) return;
      const document = tree.ownerDocument;
      if (!tree.contains(document.activeElement)) return;
      const active = document.getElementById(tree.getAttribute('aria-activedescendant'));
      if (!active || !tree.contains(active) || active.getAttribute('role') !== 'treeitem') return;

      const item = active.getBoundingClientRect();
      const top = panel.getBoundingClientRect().top + panel.clientTop;
      const bottom = top + panel.clientHeight;
      if (item.top < top) panel.scrollTop += item.top - top;
      else if (item.bottom > bottom) panel.scrollTop += item.bottom - bottom;
    });
  };
}
