import React, { useRef, useState } from 'react';
import { Tree } from 'antd';
import { useParentReveal } from './useParentReveal.js';

const groups = Array.from({ length: 11 }, (_, group) => ({
  key: `group-${group + 1}`,
  title: `Group ${String(group + 1).padStart(2, '0')}`,
  children: Array.from({ length: 8 }, (_, leaf) => {
    const number = String(12 + group * 8 + leaf).padStart(3, '0');
    return {
      key: `file-${number}`,
      title: `File ${number}${number === '050' ? ' — configuration for the shared internationalization resources and development documentation' : number === '098' ? ' (disabled)' : ''}`,
      disabled: number === '098',
    };
  }),
}));
const treeData = [{ key: 'project', title: 'Project', children: groups }];
const expandedKeys = ['project', ...groups.map(group => group.key)];
const params = new URLSearchParams(window.location.search);

export default function App() {
  const panelRef = useRef(null);
  const revealActive = useParentReveal(panelRef);
  const [maximum, setMaximum] = useState(400);
  const [expanded, setExpanded] = useState(params.get('expanded') === 'all' ? expandedKeys : []);
  const [selected, setSelected] = useState(params.get('selected') === 'file-099' ? ['file-099'] : []);

  return <main>
    <h1>Tree with a parent maximum</h1>
    <p>The parent owns the maximum height and scrolling. Short content uses only the space it needs.</p>
    <div className="controls" aria-label="Panel controls">
      <button onClick={() => setExpanded(expandedKeys)}>Expand all</button>
      <button onClick={() => setExpanded([])}>Collapse all</button>
      <button onClick={() => setMaximum(180)}>Maximum 180px</button>
      <button onClick={() => setMaximum(400)}>Maximum 400px</button>
      <button id="focus-away">Outside focus</button>
    </div>
    <div className="demo-slot"><section className="files-panel" role="region" aria-label="Bounded files panel" ref={panelRef} style={{ maxHeight: maximum }}>
      <Tree
        aria-label="Project files"
        virtual={false}
        onFocus={revealActive}
        onKeyDown={revealActive}
        treeData={treeData}
        expandedKeys={expanded}
        autoExpandParent={false}
        onExpand={setExpanded}
        selectedKeys={selected}
        onSelect={setSelected}
        styles={{ itemTitle: { whiteSpace: 'normal', overflowWrap: 'anywhere' } }}
      />
    </section></div>
    <p role="status">Selected key: {selected[0] || 'none'}</p>
    <section id="other-panel" aria-label="Reference panel">
      <h2>Separate tree</h2>
      <Tree aria-label="Reference files" virtual={false} defaultExpandAll treeData={[{ key: 'reference', title: 'Reference', children: [{ key: 'reference-leaf', title: 'Reference leaf' }] }]} />
    </section>
    <p id="sentinel">The rest of the page keeps its position.</p>
  </main>;
}
