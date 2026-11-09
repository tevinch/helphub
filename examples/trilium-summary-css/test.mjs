import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const css = await readFile(new URL('./summary.css', import.meta.url), 'utf8');
const wrongCss = '.note-book-card .note-book-card-content { background-color: #fff3a6; }';
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const blockedNetworkWrites = [];
const remoteApiRequests = [];
try {
  // Standalone Trilium requires its service worker, which bridges to the local database.
  const context = await browser.newContext({colorScheme:'light'});
  // Fixture mutations use localFetch below. Audit and block routed network writes.
  await context.route('**/*', async route => {
    if(new URL(route.request().url()).pathname.startsWith('/api/')) remoteApiRequests.push(route.request().url());
    if (!['GET', 'HEAD'].includes(route.request().method())) {
      blockedNetworkWrites.push({method:route.request().method(),url:route.request().url()});
      await route.abort();
    } else await route.continue();
  });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto('https://app.triliumnotes.org');
  await page.getByRole('button', {name:'Continue', exact:true}).click();
  await page.getByText('New knowledge base', {exact:true}).click();
  await page.getByText('Empty', {exact:true}).click();
  await page.waitForFunction(() => window.glob?.dbInitialized && window.glob?.appContext?.tabManager?.getActiveContext() && window.glob?.froca && window.standaloneApi?.localFetch, null, {timeout:60000});
  await page.locator('.note-title-widget input.note-title:visible').first().waitFor();
  const runtime = await page.evaluate(() => ({version:glob.triliumVersion,standalone:glob.isStandalone,isDev:glob.isDev}));
  assert.deepEqual(runtime,{version:'0.107.0',standalone:true,isDev:false},'verify the actual stable app and local mode');

  async function local(path, method='GET', data) {
    return await page.evaluate(async ({path, method, data}) => {
      if (!glob.isStandalone || !window.standaloneApi?.localFetch) throw new Error('local standalone transport required');
      const headers = Object.fromEntries(Object.entries(await glob.getHeaders()).filter(([,v]) => v != null));
      if(data !== undefined) headers['content-type']='application/json';
      const response = await window.standaloneApi.localFetch(new Request(new URL(path,location.href), {method,headers,body:data===undefined?undefined:JSON.stringify(data)}));
      const text = await response.text();
      if(!response.ok) throw new Error(`${response.status} ${path}: ${text}`);
      try { return JSON.parse(text); } catch { return text; }
    }, {path,method,data});
  }
  const parent = await local('/api/notes/root/children?target=into','POST',{title:'Summary examples',type:'book',mime:'',content:''});
  const parentId=parent.note.noteId;
  const content = ['<p>First summary with <strong>existing emphasis</strong>.</p>','<p>Second summary with existing text.</p>'];
  const children=[];
  for(let index=0;index<2;index++){const result=await local(`/api/notes/${parentId}/children?target=into`,'POST',{title:`Note ${index+1}`,type:'text',mime:'text/html',content:content[index]});children.push(result.note.noteId);}
  await local(`/api/notes/${parentId}/set-attribute`,'PUT',{type:'label',name:'viewType',value:'grid'});
  await page.evaluate(id => glob.appContext.tabManager.getActiveContext().setNote(id),parentId);
  await page.reload();
  await page.waitForFunction(() => window.glob?.appContext?.tabManager && window.glob?.getActiveContextNote);
  await page.waitForFunction(id=>window.glob?.getActiveContextNote?.()?.noteId===id,parentId);
  await page.locator('.note-list.grid-view .note-book-card:visible .note-book-content-ready').first().waitFor({timeout:15000});
  const selector='.note-list.grid-view .note-book-card:visible > .note-book-content';
  const styleSnapshot = () => page.locator('.note-list.grid-view .note-book-card:visible').evaluateAll(cards => cards.map(card => {
    function sample(el){const s=getComputedStyle(el);return {background:s.backgroundColor,color:s.color,border:s.border,font:s.font,padding:s.padding};}
    return {card:sample(card),header:sample(card.querySelector('.note-book-header')),title:sample(card.querySelector('.note-book-title')),content:card.querySelector('.note-book-content').textContent};
  }));
  await page.mouse.move(0,0);
  const baseline=await styleSnapshot();
  const summaryBackgrounds=()=>page.locator(selector).evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).backgroundColor));
  const baselineBackgrounds=await summaryBackgrounds();
  assert.equal(baseline.length,2,'both actual summaries must exist');
  assert.equal(await page.locator('.note-book-card-content').count(),0,'the original selector matches no summary');
  const storedBefore=await Promise.all(children.map(id=>local(`/api/notes/${id}/blob`)));

  const cssNote=await local('/api/notes/root/children?target=into','POST',{title:'Summary background',type:'code',mime:'text/css',content:wrongCss});
  await local(`/api/notes/${cssNote.note.noteId}/set-attribute`,'PUT',{type:'label',name:'appCss',value:''});
  await page.reload();
  await page.locator(selector+'.note-book-content-ready').first().waitFor({timeout:45000});
  assert.ok((await page.evaluate(()=>glob.appCssNoteIds)).includes(cssNote.note.noteId),'the actual app CSS label must be loaded');
  assert.deepEqual(await summaryBackgrounds(),baselineBackgrounds,'original selector must leave the real summary backgrounds unchanged');
  await local(`/api/notes/${cssNote.note.noteId}/data`,'PUT',{content:css});
  await page.reload();
  await page.locator(selector+'.note-book-content-ready').first().waitFor({timeout:45000});
  const backgrounds=await summaryBackgrounds();
  console.log('CSS',JSON.stringify({appCssLoaded:(await page.evaluate(()=>glob.appCssNoteIds)).includes(cssNote.note.noteId),backgrounds}));
  assert.deepEqual(backgrounds,['rgb(255, 243, 166)','rgb(255, 243, 166)'],'both summaries must have the requested background');
  assert.deepEqual(await styleSnapshot(),baseline,'header/title/outer card styling and existing text must remain unchanged');

  for(const id of children){
    await page.locator(`.note-book-card[data-note-id="${id}"]:visible > .note-book-content`).click();
    await page.waitForFunction(noteId=>glob.getActiveContextNote()?.noteId===noteId,id);
    // The note context changes before the lazy-loaded editor has mounted.
    const editor=page.locator('.ck-editor__editable.ck-content:visible').filter({hasText:id===children[0]?'First summary':'Second summary'});
    await editor.waitFor({state:'visible',timeout:30000});
    assert.equal((await editor.innerText()).trim(),id===children[0]?'First summary with existing emphasis.':'Second summary with existing text.','summary click must show the full note in the editor');
    await page.evaluate(id => glob.appContext.tabManager.getActiveContext().setNote(id),parentId);
    await page.locator(selector+'.note-book-content-ready').first().waitFor();
  }
  assert.deepEqual(await Promise.all(children.map(id=>local(`/api/notes/${id}/blob`))),storedBefore,'stored note HTML must remain exactly unchanged');
  await page.mouse.move(0,0);
  const artifacts=new URL('./artifacts/',import.meta.url);
  await mkdir(artifacts,{recursive:true});
  await page.screenshot({path:new URL('summary.png',artifacts).pathname,fullPage:true});
  await local(`/api/notes/${cssNote.note.noteId}/data`,'PUT',{content:''});
  await page.reload();
  await page.locator(selector+'.note-book-content-ready').first().waitFor();
  await page.mouse.move(0,0);
  assert.deepEqual(await styleSnapshot(),baseline,'removing CSS must restore original card styles');
  const restoredBackgrounds=await summaryBackgrounds();
  assert.deepEqual(restoredBackgrounds,baselineBackgrounds,'removing CSS must restore the actual summary backgrounds');
  assert.deepEqual(remoteApiRequests,[],'no API requests should reach the browser network route');
  assert.ok(blockedNetworkWrites.every(request=>request.method==='POST' && new URL(request.url).origin==='https://app.triliumnotes.org' && new URL(request.url).pathname==='/cdn-cgi/rum'),'only known host telemetry may attempt a blocked network write');
  assert.deepEqual(pageErrors,[],'no page errors');
  console.log(JSON.stringify({runtime,summaries:2,summaryClicks:2,storedContentUnchanged:true,baselineBackgrounds,restoredBackgrounds,remoteApiRequests,blockedTelemetryRequests:blockedNetworkWrites.length,pageErrors}));
  console.log('PASS: real app CSS note, summary-only backgrounds, preserved card styles/content, repeated navigation, removal');
} finally { await browser.close(); }
