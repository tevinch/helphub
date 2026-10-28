import {installImageLimits} from './image-limits.mjs';
import {auditDelta} from './image-policy.mjs';
export const policy={maxBytes:102400,mimetypes:['image/png','image/jpeg']};
const status=document.querySelector('#status');
const notify=message=>{status.textContent=message;};
const options={theme:'snow',formats:['bold','italic','image'],modules:{toolbar:[['bold','italic','image']],uploader:{mimetypes:policy.mimetypes}}};
export const quill=new Quill('#editor',options);
export const restored=new Quill('#restored',options);
installImageLimits(quill,{...policy,notify});installImageLimits(restored,{...policy,notify});
document.querySelector('#export').addEventListener('click',()=>{
 const delta=quill.getContents();const issues=auditDelta(delta,policy);
 if(issues.length){notify('Export blocked: '+issues.map(issue=>issue.reason).join('; '));return;}
 document.querySelector('#delta').value=JSON.stringify(delta,null,2);notify('Delta exported. The editor is unchanged.');
});
document.querySelector('#restore').addEventListener('click',()=>{
 try{const delta=JSON.parse(document.querySelector('#delta').value);const issues=auditDelta(delta,policy);
  if(issues.length)throw new Error(issues.map(issue=>issue.reason).join('; '));
  if(!restored.isEnabled())throw new Error('The second editor is read-only.');
  restored.setContents(delta);notify('Delta restored. Continue editing below.');
 }catch(error){notify('Restore blocked: '+error.message);}
});
