import * as v from 'valibot';
import { OriginalSchema, ComplexSchema } from './dist/schema.js';

const schemas = new Map([
  ['original-form', OriginalSchema],
  ['complex-form', ComplexSchema],
]);

for (const form of document.querySelectorAll('form')) {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const fields = new FormData(form);
    const status = form.querySelector('[role="status"]');
    const errors = form.querySelector('[data-errors]');
    const output = form.querySelector('[data-output]');
    const issues = form.querySelector('[data-issues]');
    errors.replaceChildren();
    output.textContent = '';
    issues.textContent = '';

    let items;
    try {
      items = JSON.parse(fields.get('b'));
    } catch {
      status.dataset.state = 'invalid';
      status.textContent = 'Validation failed';
      const error = document.createElement('li');
      error.textContent = 'b: Enter a JSON array, for example [] or ["first"].';
      errors.append(error);
      return;
    }

    const input = { a: fields.get('a'), b: items };
    if (form.id === 'complex-form') input.notes = fields.get('notes');
    const result = v.safeParse(schemas.get(form.id), input);
    status.dataset.state = result.success ? 'valid' : 'invalid';
    status.textContent = result.success ? 'Valid output' : 'Validation failed';
    if (result.success) {
      output.textContent = JSON.stringify(result.output, null, 2);
    } else {
      for (const issue of result.issues) {
        const error = document.createElement('li');
        const path = issue.path?.map((part) => part.key).join('.') || '(root)';
        error.textContent = `${path}: ${issue.message}`;
        errors.append(error);
      }
      issues.textContent = JSON.stringify(result.issues, null, 2);
    }
  });
}
