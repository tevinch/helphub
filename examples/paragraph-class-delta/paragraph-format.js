const Quill = window.Quill;
const { ClassAttributor, Scope } = Quill.import('parchment');

export const FORMAT_NAME = 'customKey';
export const ParagraphClass = new ClassAttributor(FORMAT_NAME, 'class', {
  scope: Scope.BLOCK,
  whitelist: ['a', 'b'],
});

// Register before constructing an editor with a formats allowlist.
Quill.register(ParagraphClass);
