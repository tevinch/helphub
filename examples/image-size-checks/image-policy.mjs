export function fileInfo(file, {maxBytes, mimetypes}) {
  if (!mimetypes.includes(file.type)) return {ok:false, bytes:file.size, reason:'Unsupported image type.'};
  if (file.size > maxBytes) return {ok:false, bytes:file.size, reason:`${file.size} bytes exceeds the ${maxBytes} byte limit.`};
  return {ok:true, bytes:file.size};
}

export function imageSourceInfo(source, {maxBytes, mimetypes}) {
  if (typeof source !== 'string' || !source.startsWith('data:')) {
    return {ok:false, bytes:null, reason:'Image size is unknown locally. Choose an image file instead of a URL.'};
  }
  const match = /^data:([^;,]+);base64,([A-Za-z0-9+/]*={0,2})$/.exec(source);
  if (!match || match[2].length % 4 !== 0) return {ok:false, bytes:null, reason:'Image must use a valid base64 data URL.'};
  const [,mime,base64] = match;
  const bytes = base64.length / 4 * 3 - (base64.endsWith('==') ? 2 : base64.endsWith('=') ? 1 : 0);
  if (!mimetypes.includes(mime)) return {ok:false, bytes, reason:'Unsupported image type.'};
  if (bytes > maxBytes) return {ok:false, bytes, reason:`${bytes} bytes exceeds the ${maxBytes} byte limit.`};
  return {ok:true, bytes};
}

export function auditDelta(delta, policy) {
  if (!Array.isArray(delta?.ops)) return [{index:0,reason:'Expected a Delta ops array.'}];
  let index=0; const issues=[];
  for (const op of delta.ops) {
    if (op.insert && typeof op.insert === 'object' && 'image' in op.insert) {
      const result=imageSourceInfo(op.insert.image,policy);
      if (!result.ok) issues.push({index,reason:result.reason});
    }
    index += typeof op.insert === 'string' ? op.insert.length : op.insert ? 1 : 0;
  }
  return issues;
}
