import {fileInfo,imageSourceInfo} from './image-policy.mjs';

// Call after Quill initializes so existing document HTML is never silently filtered.
export function installImageLimits(quill, {maxBytes,mimetypes,notify}) {
  const policy={maxBytes,mimetypes};
  const Delta=quill.constructor.import('delta');
  const uploader=quill.getModule('uploader');
  const nativeHandler=uploader.options.handler;
  uploader.options.handler=function(range,files) {
    if (!quill.isEnabled()) return;
    const accepted=[];
    for (const file of files) {
      const result=fileInfo(file,policy);
      if (result.ok) accepted.push(file);
      else notify(`Rejected ${file.name}: ${result.reason}`);
    }
    // An all-rejected batch must not delete the current selection.
    if (accepted.length) nativeHandler.call(this,range,accepted);
  };

  quill.clipboard.addMatcher('IMG',(node,delta)=>
    imageSourceInfo(node.getAttribute('src'),policy).ok ? delta : new Delta());

  quill.root.addEventListener('paste',event=>{
    if (event.defaultPrevented || !quill.isEnabled()) return;
    const html=event.clipboardData?.getData('text/html');
    if (!html) return;
    const doc=new DOMParser().parseFromString(html,'text/html');
    // Preserve the native single-IMG+Files route: the File, not its HTML URL, is validated.
    if (event.clipboardData.files.length && doc.body.childElementCount===1 && doc.body.firstElementChild.tagName==='IMG') return;
    const rejected=Array.from(doc.images, img=>quill.scroll.query('image')
      ? imageSourceInfo(img.getAttribute('src'),policy)
      : {ok:false,reason:'Image format is disabled in this editor.'}).filter(result=>!result.ok);
    if (!rejected.length) return;
    const range=quill.getSelection(true);
    if (!range) return;
    const formats=quill.getFormat(range.index);
    const converted=quill.clipboard.convert({html,text:event.clipboardData.getData('text/plain')},formats);
    const hasContent=converted.ops.some(op=>typeof op.insert==='string' ? /[^\n]/.test(op.insert) : Boolean(op.insert));
    // Native Clipboard deletes selected text even for an empty converted Delta.
    // Prevent its bubble handler only when nothing acceptable remains to paste.
    if (!hasContent) event.preventDefault();
    notify('Rejected image: '+rejected.map(result=>result.reason).join(' '));
  },true);
}
