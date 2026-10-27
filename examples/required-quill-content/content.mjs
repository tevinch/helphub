// Read a full document Delta from quill.getContents(), not a change Delta.
const defaultEmbeds = new Set(['image']);

export function hasMeaningfulContent(delta, acceptedEmbeds = defaultEmbeds) {
  return Array.isArray(delta?.ops) && delta.ops.some(op => {
    const insert = op?.insert;
    if (typeof insert === 'string') return insert.trim().length > 0;
    return insert !== null && typeof insert === 'object' &&
      Object.keys(insert).some(type => acceptedEmbeds.has(type));
  });
}
