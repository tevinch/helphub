import React, { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RoughSVG } from 'react-rough-fiber';
import './style.css';

function Example({ onUnmount }) {
  const [large, setLarge] = useState(false);
  const [rectangle, setRectangle] = useState(false);
  const [visible, setVisible] = useState(true);

  return (
    <article>
      <h1>Rough SVG with React 19</h1>
      <p>Change the drawing, add a shape, or remove and restore the drawing.</p>
      <div className="controls">
        <button onClick={() => setLarge((value) => !value)}>Change circle</button>
        <button onClick={() => setRectangle((value) => !value)}>
          {rectangle ? 'Remove rectangle' : 'Add rectangle'}
        </button>
        <button onClick={() => setVisible((value) => !value)}>
          {visible ? 'Hide drawing' : 'Show drawing'}
        </button>
        <button onClick={onUnmount}>Unmount example</button>
      </div>
      <div className="drawing">
        {visible && (
          <RoughSVG options={{ seed: 1, roughness: 1.2 }}>
            <svg role="img" aria-label="Editable rough shapes" viewBox="0 0 400 240" width="400" height="240">
              <circle cx="110" cy="105" r={large ? 70 : 40} fill="none" stroke={large ? '#c2410c' : '#2563eb'} strokeWidth="3" />
              {rectangle && <rect x="220" y="50" width="120" height="100" fill="none" stroke="#15803d" strokeWidth="3" />}
              <text x="200" y="215" textAnchor="middle" fill="#1f2937">
                {large ? 'Large orange circle' : 'Small blue circle'}
              </text>
            </svg>
          </RoughSVG>
        )}
      </div>
      <p>React 19.0.9 · React DOM 19.0.9 · react-reconciler 0.31.0 · react-rough-fiber 0.0.8</p>
    </article>
  );
}

const root = createRoot(document.getElementById('root'));
root.render(<StrictMode><Example onUnmount={() => root.unmount()} /></StrictMode>);
