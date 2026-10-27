import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { createDemoServer } from './server.mjs';
import { hasMeaningfulContent } from './content.mjs';

// These assertions also document the content policy without needing a browser.
for (const ops of [[], [{insert:'\n'}], [{insert:' \t\u00a0\n'}],
  [{insert:'\n\n',attributes:{'code-block':'plain'}}], [{retain:2}],
  [{insert:{unrecognized:'value'}}, {insert:'\n'}]]) {
  assert.equal(hasMeaningfulContent({ops}), false);
}
assert.equal(hasMeaningfulContent({ops:[{insert:'code\n',attributes:{'code-block':'plain'}}]}), true);
assert.equal(hasMeaningfulContent({ops:[{insert:{image:'example.png'}},{insert:'\n'}]}), true);
assert.equal(hasMeaningfulContent({ops:[{insert:{image:'example.png'}}]},new Set()), false);
assert.equal(hasMeaningfulContent({ops:[{insert:{mention:'someone'}}]},new Set(['mention'])), true);

const server=createDemoServer();
const observed=[];
// This observer runs outside both the client submit handler and server save logic.
server.on('request',request=>{
  if(request.method==='POST' && request.url==='/submit') {
    const record={body:''}; observed.push(record);
    request.on('data',chunk=>{record.body+=chunk;});
  }
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try {
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  page.setDefaultTimeout(3000);
  await page.addInitScript(()=>{
    window.observedSubmitEvents=0;
    window.addEventListener('submit',()=>{window.observedSubmitEvents++;},true);
  });
  await page.goto('http://127.0.0.1:'+server.address().port);
  const editor=page.locator('.ql-editor');
  const submit=page.getByRole('button',{name:'Submit',exact:true});
  const read=()=>page.evaluate(async()=>{
    const {quill}=await import('/app.mjs');
    return {delta:JSON.parse(JSON.stringify(quill.getContents())),enabled:quill.isEnabled(),version:Quill.version,formats:quill.options.formats,html:quill.root.innerHTML};
  });
  const initial=await read();
  assert.equal(initial.version,'2.0.3');
  assert.deepEqual(initial.formats,['bold','italic','code-block','image']);
  assert.equal(await page.locator('.ql-toolbar .ql-code-block').count(),1);
  let rejected=0,accepted=0;
  async function reject(label) {
    const before=await read(); const posts=observed.length;
    await submit.click();
    await page.waitForFunction(()=>document.querySelector('#content-error')?.hidden===false || document.querySelector('#status')?.textContent.startsWith('Save failed.'));
    assert.equal(observed.length,posts,label+': blank content reached POST');
    await page.locator('#content-error:visible').waitFor();
    assert.equal(await editor.getAttribute('aria-invalid'),'true');
    assert.match(await page.locator('#content-error').textContent(),/Enter text or add an image/);
    assert.deepEqual((await read()).delta,before.delta,label+': validation changed content');
    rejected++; console.log('REJECT '+label+' posts='+posts);
  }
  async function accept(label) {
    const before=await read();const posts=observed.length;
    const resultPromise=page.waitForResponse(response=>response.url().endsWith('/submit') && response.request().method()==='POST');
    await submit.click();
    const response=await resultPromise;
    assert.equal(response.status(),200);
    const result=await response.json();
    await page.waitForFunction(id=>document.querySelector('#status').textContent==='Saved entry '+id+'.',result.id);
    assert.equal(observed.length,posts+1,label+': no actual POST');
    assert.deepEqual(JSON.parse(observed.at(-1).body),before.delta,label+': request Delta changed');
    assert.deepEqual(result.delta,before.delta,label+': acknowledged Delta changed');
    assert.deepEqual((await read()).delta,before.delta,label+': submission changed editor');
    assert.equal(await page.locator('#content-error').isHidden(),true);
    assert.equal(await editor.getAttribute('aria-invalid'),'false');
    accepted++; console.log('ACCEPT '+label+' id='+result.id+' exactDelta=true');
  }
  await reject('untouched document');
  await editor.click();await page.locator('.ql-code-block').click();
  const blankCode=await read();
  assert.equal(blankCode.delta.ops.at(-1).attributes['code-block'],'plain');
  assert.match(blankCode.html,/ql-code-block/);
  await reject('real empty code block');
  await editor.click();await page.keyboard.press('Enter');await page.keyboard.type('   ');
  await page.keyboard.press('Tab');
  const whitespaceCode=await read();
  const codeLines=whitespaceCode.delta.ops.filter(op=>op.attributes?.['code-block'])
    .reduce((count,op)=>count+(op.insert.match(/\n/g)?.length ?? 0),0);
  assert(codeLines>=2,'multiple actual code-block lines must exist');
  await reject('multiple blank code lines and spaces');
  await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.setText(' \t\u00a0\n\n');});
  await reject('spaces tabs NBSP and newlines');
  await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.setText('');quill.setSelection(0);});
  await page.locator('.ql-code-block').click();await editor.click();
  await page.keyboard.type('return 42;');
  const code=await read();assert.equal(code.delta.ops.at(-1).attributes['code-block'],'plain');
  await accept('typed code');
  await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.setText('');});
  await reject('cleared after success');
  await editor.click();await page.locator('.ql-bold').click();await page.keyboard.type('Again');
  await page.locator('.ql-italic').click();await page.keyboard.type('!');
  const marked=await read();assert.equal(marked.delta.ops[0].attributes.bold,true);
  assert.equal(marked.delta.ops[1].attributes.italic,true);
  await accept('filled again with marks');await accept('same content repeated');
  const image='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+cAxkAAAAASUVORK5CYII=';
  await page.evaluate(async image=>{const {quill}=await import('/app.mjs');quill.setText('');quill.insertEmbed(0,'image',image);},image);
  assert.equal((await read()).delta.ops[0].insert.image,image);
  await accept('registered image only');
  await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.disable();});
  await accept('existing content in disabled editor');assert.equal((await read()).enabled,false);
  await page.evaluate(async()=>{const {quill}=await import('/app.mjs');quill.setText('');});
  await reject('empty disabled editor');assert.equal((await read()).enabled,false);
  await page.evaluate(async image=>{const {quill}=await import('/app.mjs');quill.insertEmbed(0,'image',image);},image);
  // An actual failed request must preserve content and allow a successful retry.
  const port=server.address().port;
  server.closeAllConnections();
  await new Promise(resolve=>server.close(resolve));
  const failedDelta=(await read()).delta;
  await submit.click();await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Save failed.'));
  assert.deepEqual((await read()).delta,failedDelta);assert.equal((await read()).enabled,false);
  await new Promise(resolve=>server.listen(port,'127.0.0.1',resolve));
  await accept('retry after failed request');
  const events=await page.evaluate(()=>window.observedSubmitEvents);
  assert.equal(events,rejected+accepted+1,'independent submit-event observation');
  assert.equal(observed.length,accepted,'independent actual server POST count');
  console.log(JSON.stringify({result:'PASS',quill:initial.version,browser:browser.version(),rejected,accepted,actualServerPosts:observed.length,submitEvents:events,mode:'scripted native Chromium'}));
} finally {
  if(browser) await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
