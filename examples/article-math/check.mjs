import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright';
import {buildExample} from './build.mjs';
import {startServer,seedArticle} from './server.mjs';

await buildExample();
const temporary=await mkdtemp(path.join(tmpdir(),'article-math-'));
const storePath=path.join(temporary,'article.json');
const server=await startServer({storePath,port:0});
const url='http://127.0.0.1:'+server.address().port;
let browser;
const evidence={mode:'Software-operated Chromium with real ReactQuill, native keyboard and HTTP JSON file storage',writes:[],checks:[]};
try{
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1100,height:1000}});
  page.setDefaultTimeout(10000);
  const failures=[];
  page.on('pageerror',error=>failures.push(error.message));
  page.on('requestfinished',request=>{
    if(request.method()==='PUT'&&request.url()===url+'/article')evidence.writes.push(JSON.parse(request.postData()));
  });
  await page.goto(url);await page.getByRole('status').filter({hasText:'Article loaded.'}).waitFor();
  assert.deepEqual(JSON.parse(await readFile(storePath,'utf8')),seedArticle);
  assert.equal(await page.locator('.ql-toolbar').count(),0);
  await page.getByRole('article',{name:'Saved article'}).getByRole('link',{name:'the reference'}).waitFor();
  assert.equal(await page.locator('article blockquote').innerText(),'Keep this existing pull quote.');
  evidence.checks.push('Existing text, link, pull quote, empty paragraph and sources loaded.');

  const edit=page.locator('.ql-editor');
  await edit.locator('p').last().click();await page.keyboard.press('End');await page.keyboard.press('Enter');
  const initial=String.raw`f(v)=\frac{m}{k_B T}v e^{-\frac{mv^2}{2k_B T}}`;
  const revised=String.raw`P(v)=\frac{m v}{k_B T}\exp\left(-\frac{m v^2}{2k_B T}\right)`;
  await page.getByLabel('TeX source').fill(initial);await page.getByRole('button',{name:'Insert equation',exact:true}).click();
  await page.locator('.ql-editor .ql-formula').waitFor();
  assert.equal(await page.locator('.ql-formula').getAttribute('data-value'),initial);
  await page.locator('.ql-formula').click();await page.getByLabel('TeX source').fill(revised);
  await page.getByRole('button',{name:'Replace selected equation'}).click();
  assert.equal(await page.locator('.ql-formula').getAttribute('data-value'),revised);
  await page.getByRole('button',{name:'Save article',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Article saved.'}).waitFor();
  const first=JSON.parse(await readFile(storePath,'utf8'));
  assert.equal(first.articleContent.flat().filter(x=>x.contentType==='formula').length,1);
  assert.equal(first.articleContent.flat().find(x=>x.contentType==='formula').content,revised);
  assert.deepEqual(first.articleContent.slice(0,4),seedArticle.articleContent.slice(0,4));
  assert.deepEqual(first.sources,seedArticle.sources);
  assert(!JSON.stringify(first).includes('katex-html'));
  assert(await page.locator('article .equation .katex-html').innerText());
  assert(await page.locator('article .equation math').getAttribute('xmlns'));
  evidence.checks.push('Typed a complex formula, edited native embed, saved through PUT, and saw nonempty KaTeX HTML and MathML from on-disk TeX.');

  // A new document and editor must reconstruct the persisted formula.
  await page.reload();await page.getByRole('status').filter({hasText:'Article loaded.'}).waitFor();
  assert.equal(await page.locator('.ql-formula').getAttribute('data-value'),revised);
  await page.locator('.ql-formula').click();await page.getByLabel('TeX source').fill(String.raw`\int_0^1 x^2\,dx=\frac{1}{3}`);
  await page.getByRole('button',{name:'Replace selected equation'}).click();
  await page.getByRole('button',{name:'Save article',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Article saved.'}).waitFor();
  const second=JSON.parse(await readFile(storePath,'utf8'));
  assert.equal(second.articleContent.flat().find(x=>x.contentType==='formula').content,String.raw`\int_0^1 x^2\,dx=\frac{1}{3}`);
  assert.deepEqual(second.articleContent.slice(0,4),seedArticle.articleContent.slice(0,4));
  await page.reload();await page.getByRole('status').filter({hasText:'Article loaded.'}).waitFor();
  assert.equal(await page.locator('article .equation').getAttribute('data-source'),String.raw`\int_0^1 x^2\,dx=\frac{1}{3}`);
  evidence.checks.push('Reopened in a new editor, edited again, saved again and reopened typeset updated math with old content intact.');

  await page.getByLabel('Read-only editor').check();
  assert(await page.getByRole('button',{name:'Insert equation',exact:true}).isDisabled());
  assert(await page.getByRole('button',{name:'Save article',exact:true}).isDisabled());
  assert.equal(await edit.getAttribute('contenteditable'),'false');
  await page.getByLabel('Read-only editor').uncheck();
  await page.getByLabel('TeX source').fill(String.raw`\notARealCommand{`);
  await page.getByRole('button',{name:'Insert equation',exact:true}).click();
  assert.equal(await page.locator('.ql-formula').count(),1);
  assert.deepEqual(JSON.parse(await readFile(storePath,'utf8')),second);
  evidence.checks.push('Read-only setting disables mutation; invalid entered TeX neither inserts nor overwrites saved article.');

  const invalid=await fetch(url+'/article',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...second,articleContent:[[{contentType:'future',content:'keep me'}]]})});
  assert.equal(invalid.status,422);assert.deepEqual(JSON.parse(await readFile(storePath,'utf8')),second);
  const broken={...second,articleContent:[[{contentType:'formula',content:String.raw`\notARealCommand{`}],...seedArticle.articleContent]};
  assert.equal((await fetch(url+'/article',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(broken)})).status,200);
  await page.reload();await page.getByRole('status').filter({hasText:'Article loaded.'}).waitFor();
  await page.locator('article .math-error').waitFor();assert((await page.locator('article').innerText()).includes(String.raw`\notARealCommand{`));
  assert.deepEqual(failures,[]);
  assert.equal(evidence.writes.length,2);
  evidence.checks.push('Unsupported storage rejected with HTTP422 and no overwrite; invalid preexisting TeX stays visible and editable.');
  console.log(JSON.stringify(evidence,null,2));
}finally{
  await browser?.close();await new Promise(resolve=>server.close(resolve));await rm(temporary,{recursive:true,force:true});
}

