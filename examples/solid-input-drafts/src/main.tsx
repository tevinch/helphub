import { createSignal } from 'solid-js';
import { render } from '@solidjs/web';

function OriginalComparison() {
  let directSignal!: HTMLInputElement;
  let directLiteral!: HTMLInputElement;
  const [disabled, setDisabled] = createSignal(false);
  const [value] = createSignal(11);
  return <>
    <h2>The four original cases</h2>
    <p>Edit each input, then toggle. The shared signal remains <output id="original-state">{value()}</output>.</p>
    <button type="button" onClick={() => {
      setDisabled(previous => !previous);
      directSignal.disabled = !directSignal.disabled;
      directLiteral.disabled = !directLiteral.disabled;
    }}>CLICK ME</button>
    <label for="one">1. Reactive disabled and reactive value</label>
    <input id="one" disabled={disabled()} type="number" value={value()} />
    <label for="two">2. Reactive disabled and literal value</label>
    <input id="two" disabled={disabled()} type="number" value={11} />
    <label for="three">3. Direct disabled and reactive value</label>
    <input id="three" ref={directSignal} type="number" value={value()} />
    <label for="four">4. Direct disabled and literal value</label>
    <input id="four" ref={directLiteral} type="number" value={11} />
  </>;
}

function EditableDraft() {
  const [disabled, setDisabled] = createSignal(false);
  const [value, setValue] = createSignal('11');
  const [submitted, setSubmitted] = createSignal<string | null>(null);
  return <section>
    <h2>Keep the draft in a signal</h2>
    <form onSubmit={event => {
      event.preventDefault();
      const entry = new FormData(event.currentTarget).get('quantity');
      setSubmitted(typeof entry === 'string' ? entry : null);
    }}>
      <label>Editable number draft
        <input id="draft" name="quantity" type="number" step="any"
          value={value()} disabled={disabled()}
          onInput={event => setValue(event.currentTarget.value)} />
      </label>
      <p>Current signal: <output id="draft-state">{JSON.stringify(value())}</output></p>
      <button type="button" onClick={() => setDisabled(previous => !previous)}>Toggle draft disabled</button>
      <button type="button" onClick={() => setValue('42')}>Set draft to 42</button>
      <button type="submit" disabled={disabled()}>Read submitted value</button>
      <p>Submitted value: <output id="submitted">{JSON.stringify(submitted())}</output></p>
    </form>
  </section>;
}

function App() {
  return <>
    <h1>Keep an input draft when disabling it</h1>
    <p>Try editing the number, disabling it, and enabling it again. A string draft also keeps an empty number input empty.</p>
    <EditableDraft />
    <section id="original"><OriginalComparison /></section>
  </>;
}
render(App, document.getElementById('app')!);
