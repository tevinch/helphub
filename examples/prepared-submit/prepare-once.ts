/** The key must contain every input to a pure, synchronous preparation. */
export function prepareOnce<Input, Output>(prepare: (input: Input) => Output) {
  let entry: { input: Input; output: Output } | undefined;
  return (input: Input): Output => {
    if (!entry || !Object.is(entry.input, input)) entry = { input, output: prepare(input) };
    return entry.output;
  };
}
