import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {createDemoServer} from './server.mjs';

const MAX=102400;
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+cAxkAAAAASUVORK5CYII=','base64');
const file=(size,name='picture.png',mimeType='image/png')=>({name,mimeType,buffer:Buffer.concat([png,Buffer.alloc(size-png.length)])});
const dataURL=size=>'data:image/png;base64,'+file(size).buffer.toString('base64');
const server=createDemoServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const records=[];let browser;
try {
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage();page.setDefaultTimeout(5000);
 const externalRequests=[];
 await page.route('**/*',route=>{
  if(new URL(route.request().url()).hostname==='127.0.0.1')return route.continue();
  externalRequests.push(route.request().url());return route.abort();
 });
 await page.addInitScript(()=>{
  window.fileReads=[];window.nativeEvents={paste:0,drop:0,change:0};
  const read=FileReader.prototype.readAsDataURL;
  FileReader.prototype.readAsDataURL=function(blob){const entry={size:blob.size,done:false};window.fileReads.push(entry);this.addEventListener('loadend',()=>entry.done=true,{once:true});return read.call(this,blob);};
  for(const kind of ['paste','drop','change'])document.addEventListener(kind,()=>window.nativeEvents[kind]++,true);
 });
 const url='http://127.0.0.1:'+server.address().port;
 async function fresh(){await page.goto(url);await page.evaluate(async()=>{
  const {quill}=await import('/app.mjs');window.handlerCalls=0;const uploader=quill.getModule('uploader');const handler=uploader.options.handler;
  uploader.options.handler=function(...args){window.handlerCalls++;return handler.apply(this,args);};quill.setSelection(0,8);
 });}
 const read=()=>page.evaluate(async()=>{const {quill}=await import('/app.mjs');return {version:Quill.version,text:quill.getText(),delta:quill.getContents(),selection:quill.getSelection(),images:Array.from(quill.root.querySelectorAll('img'),img=>img.getAttribute('src')),html:quill.root.innerHTML,enabled:quill.isEnabled(),reads:window.fileReads.length,handlerCalls:window.handlerCalls,events:window.nativeEvents,status:document.querySelector('#status').textContent};});
 async function settle(){await page.waitForFunction(()=>window.fileReads.every(entry=>entry.done));await page.evaluate(()=>new Promise(requestAnimationFrame));}
 async function deliver(route,payload,{html='',target='quill'}={}){
  if(route==='toolbar'){
   const toolbar=target==='quill'?page.locator('.ql-toolbar').nth(0):page.locator('.ql-toolbar').nth(1);
   const chooser=page.waitForEvent('filechooser');await toolbar.locator('button.ql-image').click();await (await chooser).setFiles(payload);
  }else{
   await page.evaluate(async({route,payload,html,target})=>{
    const app=await import('/app.mjs');const quill=app[target];const bytes=Uint8Array.from(atob(payload.base64),c=>c.charCodeAt(0));const transfer=new DataTransfer();transfer.items.add(new File([bytes],payload.name,{type:payload.mimeType}));
    if(html)transfer.setData('text/html',html);
    if(route==='paste')quill.root.dispatchEvent(new ClipboardEvent('paste',{clipboardData:transfer,bubbles:true,cancelable:true}));
    else{
     const text=quill.root.querySelector('p')?.firstChild;const range=document.createRange();range.setStart(text,0);range.setEnd(text,0);const rect=range.getBoundingClientRect();
     quill.root.dispatchEvent(new DragEvent('drop',{dataTransfer:transfer,bubbles:true,cancelable:true,clientX:rect.x+0.1,clientY:rect.y+rect.height/2}));
    }
   },{route,payload:{name:payload.name,mimeType:payload.mimeType,base64:payload.buffer.toString('base64')},html,target});
  }
  await settle();
 }
 async function pasteHTML(html){await page.evaluate(async html=>{const {quill}=await import('/app.mjs');const transfer=new DataTransfer();transfer.setData('text/html',html);quill.root.dispatchEvent(new ClipboardEvent('paste',{clipboardData:transfer,bubbles:true,cancelable:true}));},html);await settle();}
 const failures=[];
 // Run all three original routes even when a baseline lacks the guard.
 for(const route of ['toolbar','paste','drop']){
  await fresh();const before=await read();assert.equal(before.version,'2.0.3');await deliver(route,file(MAX+1,'large.png'));const after=await read();
  records.push({case:'oversized-'+route,beforeImages:before.images.length,afterImages:after.images.length,handlerCalls:after.handlerCalls,reads:after.reads,events:after.events});
  try{
   assert.equal(after.handlerCalls,1,route+' must reach native uploader');
   assert.equal(JSON.stringify(after.delta),JSON.stringify(before.delta),route+' rejected file changed the document');
   assert.deepEqual(after.selection,before.selection,route+' rejected file changed selection');
   assert.equal(after.reads,0,route+' rejected file was read');assert.match(after.status,/limit|exceeds|Rejected/);
  }catch(error){failures.push(route+': '+error.message.split('\n')[0]);}
 }
 console.log(JSON.stringify({originalRoutes:records}));
 assert.deepEqual(failures,[],'all original native routes must reject oversize images');
 // Match native Clipboard's text/plain behavior inside the host's current code block.
 const codeBlockPaste=await page.evaluate(async()=>{
  const {installImageLimits}=await import('/image-limits.mjs');
  const results=[];
  for(const installed of [false,true]){
   const host=document.createElement('div');document.body.append(host);
   const q=new Quill(host,{formats:['code-block','image'],modules:{toolbar:false}});
   q.setContents({ops:[{insert:'Keep me'},{insert:'\n',attributes:{'code-block':'plain'}}]});
   if(installed)installImageLimits(q,{maxBytes:102400,mimetypes:['image/png','image/jpeg'],notify:()=>{}});
   q.setSelection(0,4);
   const data=new DataTransfer();data.setData('text/html','<img src="https://example.invalid/code-block.png">');data.setData('text/plain','plain alternative');
   const events=window.nativeEvents.paste;
   q.root.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));
   results.push({installed,text:q.getText(),images:q.root.querySelectorAll('img').length,format:q.getFormat(0)['code-block'],pasteEvents:window.nativeEvents.paste-events});
  }
  return results;
 });
 console.log(JSON.stringify({codeBlockPaste}));
 for(const result of codeBlockPaste){
  assert.equal(result.text,'plain alternative me\n',`${result.installed?'installed':'native control'} code-block paste must insert the plain-text alternative`);
  assert.equal(result.images,0);assert.equal(result.format,'plain');assert.equal(result.pasteEvents,1);
 }
 records.push({case:'code-block-plaintext-alternative',results:codeBlockPaste});

 for(const route of ['toolbar','paste','drop'])for(const size of [png.length,MAX]){
  await fresh();const before=await read();await deliver(route,file(size));const after=await read();
  assert.equal(after.images.length,before.images.length+1,route+' accepted image missing');assert.equal(after.handlerCalls,1);assert.equal(after.reads,1);
  const inserted=after.images.find(src=>!before.images.includes(src));assert.equal(Buffer.from(inserted.split(',')[1],'base64').length,size);
  if(route==='drop')assert.equal(typeof after.delta.ops[0].insert,'object','drop must insert at the hit-tested start');
  assert.equal(await page.locator('#editor img').last().evaluate(img=>img.complete&&img.naturalWidth===1),true);
  records.push({case:'accepted-'+route,size,reads:after.reads,images:after.images.length});
 }
 await fresh();await deliver('paste',file(png.length),{html:'<img src="https://example.invalid/from-clipboard.png">'});
 assert.equal((await read()).handlerCalls,1,'singleIMG+Files must use native uploader');assert.equal((await read()).reads,1);
 for(const html of [
  '<img src="'+dataURL(MAX+1)+'">',
  '<p><img src="'+dataURL(MAX+1)+'"></p>',
  '<img src="https://example.invalid/unknown.png">',
  '<img src="data:image/png;base64,!bad">',
 ]){
  await fresh();const before=await read();const externalBefore=externalRequests.length;await pasteHTML(html);const after=await read();
  assert.equal(externalRequests.length,externalBefore,'rejected pasted IMG must not request an external URL');
  assert.equal(JSON.stringify(after.delta),JSON.stringify(before.delta),'all-rejected HTML deleted selected content');assert.deepEqual(after.selection,before.selection);
  assert.equal(after.reads,0);assert.equal(after.handlerCalls,0);assert.match(after.status,/Rejected|limit|unknown|base64/);
 }
 for(const size of [png.length,MAX]){
  await fresh();const before=await read();await pasteHTML('<img src="'+dataURL(size)+'">');const after=await read();assert.equal(after.images.length,before.images.length+1);assert.equal(after.handlerCalls,0);
 }
 await fresh();await pasteHTML('<p><strong>Allowed</strong><img src="'+dataURL(MAX+1)+'"><em> text</em><img src="'+dataURL(png.length)+'"></p>');
 let state=await read();assert.equal(state.images.length,1);assert(state.delta.ops.some(op=>op.insert==='Allowed'&&op.attributes?.bold));assert(state.delta.ops.some(op=>op.insert===' text'&&op.attributes?.italic));assert.match(state.status,/Rejected/);
 await fresh();await deliver('paste',file(MAX+1),{html:'<p><strong>Mixed</strong><img src="'+dataURL(MAX+1)+'"></p>'});
 state=await read();assert.equal(state.handlerCalls,0,'mixedHTML+Files must exercise clipboard bypass');assert(state.delta.ops.some(op=>op.insert==='Mixed'&&op.attributes?.bold));assert.equal(state.images.length,0);
 await fresh();const initial=await read();assert(initial.html.includes('<strong>bold</strong>'));await page.locator('#export').click();assert.equal(JSON.stringify((await read()).delta),JSON.stringify(initial.delta));
 // Native entry, continued editing, actual export, second editor restore, editing and a second native entry.
 await deliver('toolbar',file(png.length));await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.setSelection(quill.getLength()-1);});await page.locator('#editor .ql-editor').press('End');await page.keyboard.type(' continued');
 const firstEdit=await read();
 assert.match(firstEdit.text,/ continued/,'first editor must contain the continued keyboard edit before export');
 const exported=firstEdit.delta;
 assert.match(exported.ops.filter(op=>typeof op.insert==='string').map(op=>op.insert).join(''),/ continued/,'first Delta must contain the continued keyboard edit');
 await page.locator('#export').click();assert.deepEqual(JSON.parse(await page.locator('#delta').inputValue()),exported);
 await page.locator('#restore').click();
 const restoredSnapshot=await page.evaluate(async()=>{const {restored}=await import('/app.mjs');return {delta:restored.getContents(),text:restored.getText()};});
 assert.deepEqual(restoredSnapshot.delta,exported);
 assert.match(restoredSnapshot.text,/ continued/,'restored editor must contain the first continued edit');
 await page.evaluate(async()=>{const {restored}=await import('/app.mjs');restored.setSelection(restored.getLength()-1);});await page.locator('#restored .ql-editor').press('End');await page.keyboard.type(' again');
 await deliver('toolbar',file(MAX),{target:'restored'});const restored=await page.evaluate(async()=>{const {restored}=await import('/app.mjs');return {delta:restored.getContents(),text:restored.getText(),images:restored.root.querySelectorAll('img').length};});assert.match(restored.text,/again/);assert.equal(restored.images,2);
 // A final audit must catch programmatic/old-document paths without deleting them or the previous export.
 const lastExport=await page.locator('#delta').inputValue();
 for(const source of [dataURL(MAX+1),'https://example.invalid/existing.png']){
  await page.evaluate(async source=>{const {quill}=await import('/app.mjs');quill.insertEmbed(0,'image',source);},source);const before=await read();await page.locator('#export').click();const after=await read();
  assert.match(after.status,/Export blocked/);assert.equal(JSON.stringify(after.delta),JSON.stringify(before.delta));assert.equal(await page.locator('#delta').inputValue(),lastExport);
 }
 // Existing images survive attaching the policy after initialization, including an older oversized one.
 const existingPreserved=await page.evaluate(async source=>{
  const {installImageLimits}=await import('/image-limits.mjs');const host=document.createElement('div');host.innerHTML='<p>Original <strong>text</strong><img src="'+source+'"></p>';document.body.append(host);const q=new Quill(host,{formats:['bold','image']});const before=JSON.stringify(q.getContents());installImageLimits(q,{maxBytes:102400,mimetypes:['image/png','image/jpeg'],notify:()=>{}});return before===JSON.stringify(q.getContents());
 },dataURL(MAX+1));assert.equal(existingPreserved,true);
 for(const route of ['toolbar','paste','drop']){
  await fresh();await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.disable();});const before=await read();await deliver(route,file(png.length));const after=await read();assert.equal(JSON.stringify(after.delta),JSON.stringify(before.delta));assert.equal(after.enabled,false);assert.equal(after.reads,0);
 }
 await fresh();await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.disable();});const disabled=await read();await pasteHTML('<p><strong>ignored</strong><img src="'+dataURL(png.length)+'"></p>');assert.equal(JSON.stringify((await read()).delta),JSON.stringify(disabled.delta));
 const excluded=await page.evaluate(async source=>{
  const {installImageLimits}=await import('/image-limits.mjs');const host=document.createElement('div');host.textContent='Keep';document.body.append(host);const q=new Quill(host,{formats:['bold'],modules:{toolbar:false}});installImageLimits(q,{maxBytes:102400,mimetypes:['image/png','image/jpeg'],notify:()=>{}});const before=JSON.stringify(q.getContents());const reads=window.fileReads.length;q.setSelection(0);const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob(source.split(',')[1]),c=>c.charCodeAt(0))],'small.png',{type:'image/png'}));host.querySelector('.ql-editor').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));const fileSame=before===JSON.stringify(q.getContents());q.setSelection(0,4);const htmlTransfer=new DataTransfer();htmlTransfer.setData('text/html','<img src="'+source+'">');host.querySelector('.ql-editor').dispatchEvent(new ClipboardEvent('paste',{clipboardData:htmlTransfer,bubbles:true,cancelable:true}));return {same:fileSame,htmlSame:before===JSON.stringify(q.getContents()),reads:window.fileReads.length-reads,formats:q.options.formats};
 },dataURL(png.length));assert.deepEqual(excluded,{same:true,htmlSame:true,reads:0,formats:['bold']});
 await fresh();await deliver('paste',{...file(png.length),mimeType:'image/gif'});state=await read();assert.equal(state.reads,0);assert.equal(state.handlerCalls,0);assert.equal(state.images.length,0);
 console.log(JSON.stringify({result:'PASS',quill:await page.evaluate(()=>Quill.version),browser:browser.version(),maxBytes:MAX,originalRoutes:3,acceptedFileCases:6,policyCases:'pure/mixedHTML,selectionNOOP,MIME,formats,readOnly,initialContent,export,restore,continuedEdit',mode:'scripted Chromium; native file chooser selection and synthetic ClipboardEvent/DragEvent',records}));
} finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
