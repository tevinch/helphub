import { useEffect, useRef, useState, type RefObject } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as RadioGroup from '@radix-ui/react-radio-group';
import { useControl, useForm } from '@conform-to/react/future';
import { coerceFormValue, getConstraints } from '@conform-to/zod/v4/future';
import { itemSchema } from '../schema.mjs';
import type { z } from 'zod';

type Item = z.infer<typeof itemSchema>;
type SavedDocument = { item: Item & { id: string }; settings: Record<string, unknown>; revision: number };
const formSchema = coerceFormValue(itemSchema);
const constraints = getConstraints(itemSchema);

function ColorControl({ name, id, defaultValue, invalid, skipBlur, baseRef }: {
  name: string; id: string; defaultValue: string; invalid: boolean | undefined;
  skipBlur: (next: EventTarget | null) => boolean;
  baseRef: RefObject<HTMLInputElement | null>;
}) {
  const groupRef = useRef<HTMLDivElement>(null);
  const control = useControl({
    defaultValue,
    onFocus() {
      const group = groupRef.current;
      const selected = group?.querySelector<HTMLElement>('[role="radio"][data-state="checked"]');
      (selected ?? group?.querySelector<HTMLElement>('[role="radio"]'))?.focus();
    },
  });
  return <>
    <input hidden name={name} ref={element => { baseRef.current = element; control.register(element); }} />
    <RadioGroup.Root id={id} ref={groupRef} value={control.value ?? ''}
      aria-labelledby="color-label" aria-describedby="color-error" aria-invalid={invalid}
      className="color-options" onValueChange={value => control.change(value)}
      onBlur={event => {
        // The real destination is available here; control.blur() emits a proxy
        // event with no relatedTarget. Keep ordinary group departure validated.
        if (!event.currentTarget.contains(event.relatedTarget) && !skipBlur(event.relatedTarget)) control.blur();
      }}>
      {(['red', 'blue'] as const).map(color => <div className="color-choice" key={color}>
        <RadioGroup.Item id={`${id}-${color}`} value={color} className="radio" aria-label={color === 'red' ? 'Red' : 'Blue'}>
          <RadioGroup.Indicator className="radio-dot" />
        </RadioGroup.Item>
        <label htmlFor={`${id}-${color}`}>{color === 'red' ? 'Red' : 'Blue'}</label>
      </div>)}
    </RadioGroup.Root>
  </>;
}

function Editor({ initial, contentRef, closing, onSaved }: {
  initial: Item; contentRef: RefObject<HTMLDivElement | null>;
  closing: RefObject<boolean>; onSaved: (saved: SavedDocument) => void;
}) {
  const colorBaseRef = useRef<HTMLInputElement>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  function skipExitBlur(next: EventTarget | null) {
    return closing.current || !(next instanceof Node) || !contentRef.current?.contains(next)
      || (next instanceof Element && next.closest('[data-dismiss]') !== null);
  }
  const { form, fields } = useForm(formSchema, {
    constraint: constraints,
    defaultValue: initial,
    shouldValidate: 'onBlur',
    shouldRevalidate: 'onInput',
    onBlur(event) {
      // Do not mistake the color adapter's synthetic null destination for a
      // native focus departure. That adapter already checked its real event.
      if (closing.current || (event.target !== colorBaseRef.current && skipExitBlur(event.relatedTarget))) {
        event.preventDefault();
      }
    },
    async onSubmit(event, { value }) {
      event.preventDefault();
      if (saving) return;
      setSaving(true);
      setSaveError('');
      try {
        const response = await fetch('/api/item', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value),
        });
        if (!response.ok) throw Error('Save failed');
        onSaved(await response.json());
        // Leave the mounted form exactly as-is through Radix's exit animation.
        // The next opening gets a new session and the acknowledged defaults.
      } catch {
        setSaveError('Could not save. Your changes are still here. Please try again.');
      } finally {
        setSaving(false);
      }
    },
  });
  return <form {...form.props} aria-busy={saving}>
    <div data-layout>
      <label htmlFor={fields.title.id}>Title</label>
      <input id={fields.title.id} name={fields.title.name} defaultValue={fields.title.defaultValue}
        {...constraints?.title} aria-invalid={fields.title.ariaInvalid} aria-describedby="title-error" />
      <div id="title-error" className="field-error" data-field-error aria-live="polite">{fields.title.errors}</div>
    </div>
    <div data-layout>
      <span id="color-label">Color</span>
      <ColorControl name={fields.color.name} id={fields.color.id} defaultValue={fields.color.defaultValue}
        invalid={fields.color.ariaInvalid} skipBlur={skipExitBlur} baseRef={colorBaseRef} />
      <div id="color-error" className="field-error" data-field-error aria-live="polite">{fields.color.errors}</div>
    </div>
    <div data-layout>
      <span id="notes-label">Notes</span>
      <p className="retained-note" data-retained-note aria-labelledby="notes-label">{initial.notes}</p>
      <input type="hidden" name={fields.notes.name} value={initial.notes} />
      <small id="notes-description">This existing note is retained when saving.</small>
    </div>
    <p className="save-message" role={saveError ? 'alert' : 'status'}>{saveError}</p>
    <div className="actions" data-layout>
      <Dialog.Close asChild><button type="button" data-dismiss>Cancel</button></Dialog.Close>
      <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
    </div>
  </form>;
}

export default function App() {
  const [record, setRecord] = useState<SavedDocument | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [open, setOpen] = useState(false);
  const [snapshot, setSnapshot] = useState<Item | null>(null);
  const [session, setSession] = useState(0);
  const currentSession = useRef(0);
  const contentRef = useRef<HTMLDivElement>(null);
  const closing = useRef(false);
  useEffect(() => {
    fetch('/api/item').then(response => {
      if (!response.ok) throw Error('Could not load');
      return response.json();
    }).then(setRecord).catch(() => setLoadError(true));
  }, []);
  function changeOpen(next: boolean) {
    closing.current = !next;
    if (next && record) {
      setSnapshot({ title: record.item.title, color: record.item.color, notes: record.item.notes });
      currentSession.current += 1;
      setSession(currentSession.current);
    }
    setOpen(next);
  }
  return <main>
    <h1>Edit an item in a dialog</h1>
    <p>Validation starts when a field loses focus and updates as you correct it.</p>
    {loadError && <p role="alert">Could not load the item. Please reload.</p>}
    {record && <section className="summary" data-summary aria-live="polite">
      <h2>{record.item.title}</h2><p>Color: {record.item.color}</p><p className="retained-note">{record.item.notes}</p>
      <small>Saved revision: {record.revision}</small>
    </section>}
    <Dialog.Root open={open} onOpenChange={changeOpen}>
      <Dialog.Trigger asChild><button disabled={!record}>Edit item</button></Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="dialog" ref={contentRef}>
          <Dialog.Title>Edit item</Dialog.Title>
          <Dialog.Description>Change the title and color, then save your changes.</Dialog.Description>
          {snapshot && <Editor key={session} initial={snapshot} closing={closing} contentRef={contentRef}
            onSaved={saved => {
              setRecord(saved);
              // An earlier pending save may finish after the user reopens.
              // Keep the newer session and its draft open in that case.
              if (currentSession.current === session) changeOpen(false);
            }} />}
          <Dialog.Close asChild><button type="button" className="close" data-dismiss aria-label="Close editor">×</button></Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  </main>;
}
