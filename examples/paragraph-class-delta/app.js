import { FORMAT_NAME } from './paragraph-format.js';

const Quill = window.Quill;
const host = document.querySelector('#editor-host');
const saved = document.querySelector('#saved-json');
const status = document.querySelector('#status');
const formats = [FORMAT_NAME, 'bold', 'align', 'header', 'list'];
const toolbar = [['bold'], [{ align: [] }], [{ header: [1, 2, false] }], [{ list: 'bullet' }]];

function sampleContents() {
  return {
    ops: [
      { insert: 'Alpha', attributes: { bold: true } },
      { insert: '\n', attributes: { [FORMAT_NAME]: 'a' } },
      { insert: 'Beta' },
      { insert: '\n', attributes: { [FORMAT_NAME]: 'b', align: 'center' } },
      { insert: 'Ordinary\nHeading' },
      { insert: '\n', attributes: { header: 2 } },
      { insert: 'List item' },
      { insert: '\n', attributes: { list: 'bullet' } },
    ],
  };
}

function createEditor(contents) {
  if (window.quill) window.quill.disable();
  const container = document.createElement('div');
  host.replaceChildren(container);
  window.quill = new Quill(container, { theme: 'snow', formats, modules: { toolbar } });
  window.quill.setContents(contents);
}

document.querySelector('#reset').addEventListener('click', () => {
  window.quill.setContents(sampleContents());
  status.textContent = 'Sample loaded. This replaces the editor contents.';
});

document.querySelector('#toggle').addEventListener('click', () => {
  const current = window.quill.getFormat(0, 1)[FORMAT_NAME];
  const next = current === 'a' ? 'b' : 'a';
  window.quill.formatLine(0, 1, FORMAT_NAME, next, 'user');
  status.textContent = `First paragraph now uses class-${next}. Export again to save this change.`;
});

document.querySelector('#export').addEventListener('click', () => {
  saved.value = JSON.stringify(window.quill.getContents(), null, 2);
  document.querySelector('#restore').disabled = false;
  status.textContent = 'Current Delta exported below.';
});

document.querySelector('#clear').addEventListener('click', () => {
  window.quill.setText('');
  status.textContent = 'Editor cleared. Exported JSON is kept for restoration.';
});

document.querySelector('#restore').addEventListener('click', () => {
  createEditor(JSON.parse(saved.value));
  status.textContent = 'Exported Delta restored in a new editor. You can continue editing.';
});

createEditor(sampleContents());
