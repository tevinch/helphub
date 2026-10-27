import { hasMeaningfulContent } from './content.mjs';

export const quill = new Quill('#editor', {
  theme: 'snow',
  modules: { toolbar: [['bold', 'italic', 'code-block']] },
  formats: ['bold', 'italic', 'code-block', 'image'],
});
quill.root.setAttribute('aria-labelledby', 'content-label');
quill.root.setAttribute('aria-describedby', 'content-error');
quill.root.setAttribute('aria-invalid', 'false');

const form = document.querySelector('#entry-form');
const error = document.querySelector('#content-error');
const status = document.querySelector('#status');
const receipt = document.querySelector('#receipt');
const button = form.querySelector('button[type=submit]');

form.addEventListener('submit', async event => {
  event.preventDefault();
  const delta = quill.getContents();
  if (!hasMeaningfulContent(delta)) {
    error.hidden = false;
    quill.root.setAttribute('aria-invalid', 'true');
    status.textContent = '';
    if (quill.isEnabled()) quill.focus();
    return;
  }
  error.hidden = true;
  quill.root.setAttribute('aria-invalid', 'false');
  status.textContent = 'Saving…';
  button.disabled = true;
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(delta),
    });
    if (!response.ok) throw new Error('Save failed');
    const saved = await response.json();
    status.textContent = `Saved entry ${saved.id}.`;
    receipt.textContent = JSON.stringify(saved.delta, null, 2);
  } catch {
    status.textContent = 'Save failed. Your content is still here; please try again.';
  } finally {
    button.disabled = false;
  }
});
