import test from 'node:test';
import assert from 'node:assert/strict';
import { toArticleContent, toDelta, validateContent } from './content.mjs';

// Removing formula mapping, quote handling or link attributes must lose data here.
test('stored text, link, equation, quote and empty paragraph survive a complete edit round trip', () => {
  const saved = [
    [{ contentType: 'text', content: 'A Unicode α and literal <b> label ' },
     { contentType: 'link', content: 'source', href: 'https://example.org/source' },
     { contentType: 'text', content: ' ends here.' }],
    [{ contentType: 'formula', content: String.raw`f(v)=\frac{m}{k_B T}v e^{-\frac{mv^2}{2k_B T}}` }],
    [{ contentType: 'pull_quote', content: 'Keep this quotation.' }],
    [],
    [{ contentType: 'text', content: 'Inline ' }, { contentType: 'formula', content: 'x^2' }, { contentType: 'text', content: ' remains.' }]
  ];
  assert.deepEqual(toArticleContent(toDelta(saved)), saved);
});
test('full native editor Delta becomes ordered paragraphs without copying rendered formula markup', () => {
  const delta = { ops: [
    { insert: 'Before ' }, { insert: { formula: String.raw`\sqrt{x^2+y^2}` } },
    { insert: ' after\n' }, { insert: 'Reference', attributes: { link: 'https://example.org' } },
    { insert: '\n' }, { insert: 'Quoted' }, { insert: '\n', attributes: { blockquote: true } }
  ] };
  assert.deepEqual(toArticleContent(delta), [
    [{ contentType: 'text', content: 'Before ' }, { contentType: 'formula', content: String.raw`\sqrt{x^2+y^2}` }, { contentType: 'text', content: ' after' }],
    [{ contentType: 'link', content: 'Reference', href: 'https://example.org' }],
    [{ contentType: 'pull_quote', content: 'Quoted' }]
  ]);
});
test('unsupported formatting or embeds stop the save instead of silently losing them', () => {
  assert.throws(() => toArticleContent({ops:[{insert:'important',attributes:{bold:true}},{insert:'\n'}]}), /unsupported/i);
  assert.throws(() => toArticleContent({ops:[{insert:{video:'https://example.org'}},{insert:'\n'}]}), /unsupported/i);
});
test('unknown stored content and empty formulas fail validation before persistence', () => {
  assert.throws(() => validateContent([[{ contentType:'formula', content:'' }]]), /formula/i);
  assert.throws(() => validateContent([[{ contentType:'future', content:'do not discard' }]]), /unsupported/i);
});


test('image source survives while unsupported linked formulas cannot silently lose their link', () => {
  const stored=[[{contentType:'image',content:'https://example.org/figure.png'}]];
  assert.deepEqual(toArticleContent(toDelta(stored)),stored);
  assert.throws(() => toArticleContent({ops:[{insert:{formula:'x^2'},attributes:{link:'https://example.org'}},{insert:'\n'}]}),/unsupported/i);
});
