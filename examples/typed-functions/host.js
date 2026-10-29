'use strict';

(() => {
  const report = { rounds: [] };
  const hostCalls = { primitive: 0, person: 0, formatter: 0 };
  let current;
  const status = document.querySelector('#status');
  const output = document.querySelector('#result');
  const button = document.querySelector('button');

  const fixture = {
    primitive: null,
    person: null,
    repeat: null,
    report,

    format(value) {
      hostCalls.formatter++;
      return `JS:${value.toUpperCase()}`;
    },

    runRound(round) {
      if (typeof fixture.primitive !== 'function' ||
          typeof fixture.person !== 'function') {
        throw new Error('Both Dart callbacks must be bound before running.');
      }
      const label = `batch${round}`;
      const amount = round + 2;
      hostCalls.primitive++;
      const primitiveResult = fixture.primitive(label, amount);
      hostCalls.person++;
      const personResult = fixture.person({ name: `person${round}`, age: 30 + round });
      current = {
        round,
        primitive: primitiveResult,
        person: { name: personResult.name, age: personResult.age },
      };
    },

    recordRound(round, primitiveCalls, personCalls, formatted) {
      const row = {
        ...current,
        formatted,
        hostCalls: { ...hostCalls },
        dartCalls: { primitive: primitiveCalls, person: personCalls },
      };
      report.rounds.push(row);
      const passed = row.round === round &&
        row.primitive === `batch${round}:${(round + 2) * 2}` &&
        row.person.name === `PERSON${round}` && row.person.age === 31 + round &&
        row.formatted === `JS:ROUND${round}` &&
        Object.values(row.hostCalls).every(value => value === round) &&
        Object.values(row.dartCalls).every(value => value === round);
      status.textContent = passed ? `PASS — ${round} ${round === 1 ? 'round' : 'rounds'}` : 'FAIL — inspect results';
      output.textContent = JSON.stringify(report, null, 2);
    },

    ready() {
      button.disabled = false;
      button.addEventListener('click', () => fixture.repeat());
    },
  };
  window.typedFunctions = fixture;
  window.addEventListener('error', event => {
    report.error = event.message;
    status.textContent = 'FAIL — inspect results';
    output.textContent = JSON.stringify(report, null, 2);
  });
})();
