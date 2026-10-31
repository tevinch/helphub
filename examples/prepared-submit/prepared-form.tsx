import { useMemo, useRef, useState } from 'react';
import { useForm } from '@tanstack/react-form';
import { prepareOnce } from './prepare-once';

export type TraceEvent = { step: 'prepare' | 'validate' | 'submit' | 'saved'; samePrepared?: boolean };

function validateDocument(value: unknown): string | undefined {
  if (typeof value !== 'object' || value === null || Array.isArray(value)
      || !('title' in value) || typeof value.title !== 'string' || !value.title.trim()) {
    return 'title must be a non-empty string';
  }
}

export function PreparedForm({ name, onTrace }: { name: string; onTrace: (event: TraceEvent) => void }) {
  const [, rerender] = useState(0);
  const [saved, setSaved] = useState('');
  const [saveError, setSaveError] = useState('');
  const lastValidated = useRef<unknown>(undefined);
  const prepare = useMemo(() => prepareOnce((raw: string): unknown => {
    onTrace({ step: 'prepare' });
    return JSON.parse(raw);
  }), [onTrace]);

  const form = useForm({
    defaultValues: { json: '{"title":"Draft"}' },
    validators: {
      onSubmit: ({ value }) => {
        try {
          const prepared = prepare(value.json);
          lastValidated.current = prepared;
          const error = validateDocument(prepared);
          onTrace({ step: 'validate' });
          return error;
        } catch {
          onTrace({ step: 'validate' });
          return 'Enter valid JSON';
        }
      },
    },
    onSubmit: async ({ value }) => {
      const prepared = prepare(value.json);
      onTrace({ step: 'submit', samePrepared: prepared === lastValidated.current });
      const response = await fetch('/api/documents', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: name, document: prepared }),
      });
      if (!response.ok) throw new Error('The example could not save the document');
      const receipt: { id: number } = await response.json();
      onTrace({ step: 'saved' });
      setSaved(`Saved document ${receipt.id}`);
    },
  });

  return <section data-form={name}>
    <h2>{name === 'first' ? 'First form' : 'Second form'}</h2>
    <form onSubmit={event => {
      event.preventDefault();
      event.stopPropagation();
      setSaveError('');
      void form.handleSubmit().catch(error => setSaveError(String(error)));
    }}>
      <form.Subscribe selector={state => state.isSubmitting}>
        {isSubmitting => <fieldset disabled={isSubmitting}>
          <form.Field name="json">{field => <label>
            JSON document
            <textarea value={field.state.value} onBlur={field.handleBlur}
              onChange={event => field.handleChange(event.target.value)} />
          </label>}</form.Field>
          <button type="submit">Save document</button>
        </fieldset>}
      </form.Subscribe>
      <form.Subscribe selector={state => state.errors}>
        {errors => errors.length > 0 && <p role="alert">{errors.join(', ')}</p>}
      </form.Subscribe>
      {saveError && <p role="alert">{saveError}</p>}
      <p role="status">{saved || 'No document saved yet'}</p>
    </form>
    <button type="button" onClick={() => rerender(value => value + 1)}>Rerender example</button>
  </section>;
}
