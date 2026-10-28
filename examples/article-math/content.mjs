const TYPES = new Set(['text', 'link', 'pull_quote', 'image', 'formula']);
export function validateContent(content) {
  if (!Array.isArray(content)) throw new Error('Article content must be an array of paragraphs.');
  for (const paragraph of content) {
    if (!Array.isArray(paragraph)) throw new Error('Each paragraph must be an array.');
    for (const segment of paragraph) {
      if (!segment || !TYPES.has(segment.contentType)) throw new Error('Unsupported content type.');
      if (typeof segment.content !== 'string') throw new Error('Content must be text.');
      if (segment.contentType === 'formula' && !segment.content.trim()) throw new Error('Formula cannot be empty.');
      if (segment.contentType === 'link' && typeof segment.href !== 'string') throw new Error('Link requires href.');
      if (segment.contentType === 'link') checkUrl(segment.href, true);
      if (segment.contentType === 'image') checkUrl(segment.content, false);
      if (segment.contentType !== 'formula' && segment.content.includes('\n')) throw new Error('Text segments cannot contain paragraph breaks.');
    }
    if (paragraph.some(s => s.contentType === 'pull_quote') && !(paragraph.length === 1 && paragraph[0].contentType === 'pull_quote'))
      throw new Error('A pull quote occupies its own paragraph.');
  }
  return content;
}
function checkUrl(value, mail) {
  const url = new URL(value, 'https://example.org/');
  if (!['http:', 'https:', ...(mail ? ['mailto:'] : [])].includes(url.protocol)) throw new Error('Unsupported URL protocol.');
}
export function toDelta(content) {
  validateContent(content);
  const ops = [];
  for (const paragraph of content) {
    for (const segment of paragraph) {
      switch (segment.contentType) {
        case 'formula': ops.push({ insert: { formula: segment.content } }); break;
        case 'image': ops.push({ insert: { image: segment.content } }); break;
        case 'link': ops.push({ insert: segment.content, attributes: { link: segment.href } }); break;
        default: if (segment.content) ops.push({ insert: segment.content });
      }
    }
    ops.push({ insert: '\n', ...(paragraph[0]?.contentType === 'pull_quote' ? { attributes: { blockquote: true } } : {}) });
  }
  return { ops: ops.length ? ops : [{ insert: '\n' }] };
}
export function toArticleContent(delta) {
  if (!Array.isArray(delta?.ops)) throw new Error('Expected the complete editor Delta.');
  const paragraphs = [];
  let line = [];
  function append(segment) {
    const previous = line.at(-1);
    if (previous && ['text','link'].includes(segment.contentType) &&
        previous.contentType === segment.contentType && previous.href === segment.href) previous.content += segment.content;
    else line.push(segment);
  }
  function finish(quote) {
    if (quote) {
      if (line.some(s => s.contentType !== 'text')) throw new Error('A pull quote can only contain plain text in this storage model.');
      line = [{ contentType: 'pull_quote', content: line.map(s => s.content).join('') }];
    }
    paragraphs.push(line);
    line = [];
  }
  for (const op of delta.ops) {
    for (const key of Object.keys(op.attributes || {})) if (!['link','blockquote'].includes(key)) throw new Error('Unsupported formatting: ' + key);
    if (typeof op.insert === 'object' && Object.keys(op.attributes || {}).length) throw new Error('Unsupported formatting on an embed.');
    if (typeof op.insert === 'string') {
      const pieces = op.insert.split('\n');
      pieces.forEach((text,index) => {
        if (text) append(op.attributes?.link ? {contentType:'link',content:text,href:op.attributes.link} : {contentType:'text',content:text});
        if (index < pieces.length - 1) finish(op.attributes?.blockquote);
      });
    } else if (op.insert && Object.keys(op.insert).length === 1 && typeof op.insert.formula === 'string') {
      append({ contentType:'formula', content:op.insert.formula });
    } else if (op.insert && Object.keys(op.insert).length === 1 && typeof op.insert.image === 'string') {
      append({ contentType:'image', content:op.insert.image });
    } else throw new Error('Unsupported editor content.');
  }
  if (line.length) throw new Error('Expected a full document ending in a newline.');
  return validateContent(paragraphs);
}

