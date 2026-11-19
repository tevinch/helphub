import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

export async function assertMath(page, selector, expected) {
  const result = await page.evaluate(selector => {
    const el = document.querySelector(selector);
    const html = el.querySelector('.katex-html');
    const rect = html?.getBoundingClientRect();
    return {
      annotation: el.querySelector('annotation[encoding="application/x-tex"]')?.textContent,
      root: !!el.querySelector('math msqrt'),
      power: !!el.querySelector('math msup'),
      visible: !!rect && rect.width > 20 && rect.height > 10 && getComputedStyle(html).visibility !== 'hidden',
      width: rect?.width, height: rect?.height, connected: el.isConnected,
      error: !!el.querySelector('.katex-error'),
    };
  }, selector);
  assert.equal(result.annotation, expected, `${selector}: original TeX must reach MathML`);
  assert.ok(result.root && result.power && result.visible && !result.error, `${selector}: visible roots and exponents must render ${JSON.stringify(result)}`);
}

async function run() {
  const {startServer} = await import('./serve.mjs');
  const evidence = process.env.EVIDENCE_DIR;
  if (evidence) await fs.mkdir(evidence, {recursive: true});
  const server = await startServer(0);
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless: true, ...(process.env.CHROME_EXECUTABLE_PATH ? {executablePath: process.env.CHROME_EXECUTABLE_PATH} : {})});
  const page = await browser.newPage({viewport: {width: 1100, height: 850}, deviceScaleFactor: 1});
  const pageErrors = [], failed = [], fonts = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('requestfailed', r => failed.push(r.url()));
  page.on('response', r => { if (r.url().includes('/fonts/')) fonts.push({url: r.url(), status: r.status()}); });
  const original = String.raw`\sqrt{cos(x^2)} + se(x^2)`;
  const second = String.raw`\sqrt{x^{2}+1}`;
  const report = {mode: 'scripted assertions and software-operated Chromium; synthetic data', node:process.version, browser:await browser.version(), operations: [], negatives: []};
  const state = () => page.evaluate(async () => {
    const {chart} = await import('/main.js');
    return {visible: chart.data.datasets.map((_, i) => chart.isDatasetVisible(i)), points: chart.data.datasets.map((_, i) => chart.getDatasetMeta(i).data.map(p => ({x:p.x,y:p.y}))), labels: chart.data.datasets.map(d => d.label), values: chart.data.datasets.map(d => [...d.data]), area: {...chart.chartArea}, width:chart.width, height:chart.height, metas:chart.data.datasets.map((_,i)=>chart.getDatasetMeta(i).hidden)};
  });
  async function assertScene(formulas = [original, second], heading = original) {
    await page.evaluate(() => document.fonts.ready);
    await assertMath(page, '#math-heading', heading);
    const buttons = page.locator('#math-legend button');
    assert.equal(await buttons.count(), 2, 'registered legend plugin must render exactly two items');
    for (let i=0;i<2;i++) {
      await assertMath(page, `#math-legend button[data-dataset-index="${i}"] .formula`, formulas[i]);
      assert.equal(await buttons.nth(i).getAttribute('data-dataset-index'), String(i));
      const colors = await page.evaluate(i => {const el=document.querySelector(`#math-legend button[data-dataset-index="${i}"] .swatch`);return {fill:getComputedStyle(el).backgroundColor,stroke:getComputedStyle(el).borderColor};},i);
      const native = await page.evaluate(async i => { const {chart}=await import('/main.js'); const item=chart.options.plugins.legend.labels.generateLabels(chart).find(x=>x.datasetIndex===i); const canvas=document.createElement('canvas'); const c=canvas.getContext('2d'); c.fillStyle=item.fillStyle; const fill=c.fillStyle; c.fillStyle=item.strokeStyle; return {fill,stroke:c.fillStyle}; }, i);
      const normalized = await page.evaluate(c => {const el=document.createElement('span');document.body.append(el);el.style.backgroundColor=c.fill;el.style.borderColor=c.stroke;const out={fill:getComputedStyle(el).backgroundColor,stroke:getComputedStyle(el).borderColor};el.remove();return out;},native);
      assert.deepEqual(colors, normalized, 'generated native colors match the corresponding formula');
    }
    const s = await state();
    assert.ok(s.width > 250 && s.height > 200, 'actual chart must have visible dimensions');
    assert.equal(s.points[0].length, 5);
    assert.ok(s.points.flat().every(p => Number.isFinite(p.x) && Number.isFinite(p.y)), 'actual plotted points have finite geometry');
    const parent = await page.locator('canvas').evaluate(el => ({children:el.parentElement.children.length, position:getComputedStyle(el.parentElement).position}));
    assert.deepEqual(parent, {children:1,position:'relative'}, 'canvas keeps its documented dedicated responsive parent');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert.equal(overflow, false, 'heading and legend must fit the viewport');
    for (let i=0;i<2;i++) assert.equal(await buttons.nth(i).getAttribute('aria-pressed'), String(s.visible[i]));
    return s;
  }
  async function toggle(index, method='click') {
    const before=await state();
    const button=page.locator(`#math-legend button[data-dataset-index="${index}"]`);
    if(method==='click') await button.click(); else {await button.focus();await page.keyboard.press(method);}
    const after=await state();
    assert.equal(after.visible[index], !before.visible[index], 'clicked formula toggles its actual dataset index');
    assert.equal(after.visible[1-index], before.visible[1-index], 'other dataset visibility remains intact');
    assert.equal(after.metas[index], !after.visible[index], 'actual Chart.js hidden metadata changes');
    const painted = await page.locator('canvas').evaluate((el,index)=>{const d=el.getContext('2d').getImageData(0,0,el.width,el.height).data;let count=0;for(let i=0;i<d.length;i+=4){const matches=index===0?d[i]>130&&d[i+1]<120&&d[i+2]<150:d[i]<100&&d[i+1]>80&&d[i+1]<160&&d[i+2]>140;if(matches&&d[i+3]>100)count++;}return count;},index);
    assert.equal(painted>30,after.visible[index],'actual colored series drawing follows its visibility');
    if(method!=='click') assert.equal(await page.locator(':focus').getAttribute('data-dataset-index'),String(index),'keyboard focus survives native legend refresh');
    return after;
  }
  try {
    await page.goto(base);
    report.libraries=await page.evaluate(()=>({chart:Chart.version,katex:katex.version}));
    assert.deepEqual(report.libraries,{chart:'4.6.1',katex:'0.19.1'},'the pinned libraries actually run in the browser');
    const initial=await assertScene();
    assert.deepEqual(initial.visible,[true,false],'native initial hidden setting remains respected');
    assert.deepEqual(initial.labels,[original,second],'source strings remain unchanged');
    assert.deepEqual(initial.values,[[1.4,2,1.3,2.4,1.8],[.8,1.5,2.2,1.6,2.8]],'sample data is not evaluated or rewritten from math labels');
    const pixels=await page.locator('canvas').evaluate(el=>{const d=el.getContext('2d').getImageData(0,0,el.width,el.height).data;let colored=0;for(let i=0;i<d.length;i+=4)if(d[i]>130&&d[i+1]<120&&d[i+2]<150&&d[i+3]>100)colored++;return colored;});
    assert.ok(pixels>30,'real red series must be drawn on the canvas');
    report.operations.push('initial real chart, hidden series, exact source, math and native style mapping');
    for(const width of [390,1100]) {
      await page.setViewportSize({width,height:850});
      await page.waitForFunction(()=>{const c=document.querySelector('canvas'),chart=Chart.getChart(c);return Math.abs(chart.width-c.parentElement.clientWidth)<=1 && Math.abs(chart.height-c.parentElement.clientHeight)<=1;});
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      await assertScene();
      if(evidence) await page.screenshot({path:path.join(evidence,`original-${width}.png`),fullPage:true});
    }
    for(const i of [0,1]) {await toggle(i);await toggle(i);}
    await toggle(0,'Enter');await toggle(0,'Space');
    await toggle(1,'Space');await toggle(1,'Enter');
    report.operations.push('both series repeat mouse and keyboard toggles with retained focus');
    await toggle(0);await toggle(1);
    assert.deepEqual((await state()).visible,[false,true],'updates begin with user choices opposite to initial defaults');
    for(let n=0;n<3;n++) {
      const visibility=(await state()).visible;
      await page.locator('#update-example').click();
      const updated=await page.evaluate(async()=>{const m=await import('/main.js');return m.currentExample();});
      const s=await assertScene(updated.labels,updated.heading);
      assert.deepEqual(s.values,updated.values,'actual updated points use the new sample values');
      assert.deepEqual(s.visible,visibility,'label/data updates preserve chosen visibility');
      await toggle(1);await toggle(1);
    }
    report.operations.push('three complete title/formula/data updates, fresh legend and continued interaction');
    for(const width of [390,1100]) {
      await page.setViewportSize({width,height:850});
      await page.waitForFunction(w=>{const c=document.querySelector('canvas'),chart=Chart.getChart(c);return c.clientWidth < w && c.clientWidth > 250 && Math.abs(chart.width-c.parentElement.clientWidth)<=1 && Math.abs(chart.height-c.parentElement.clientHeight)<=1;},width);
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      const updated=await page.evaluate(async()=>{const m=await import('/main.js');return m.currentExample();});
      await assertScene(updated.labels,updated.heading);
      if(evidence) await page.screenshot({path:path.join(evidence,`chart-${width}.png`),fullPage:true});
    }
    assert.ok(fonts.length>0&&fonts.every(r=>r.status===200),'actual KaTeX fonts load successfully');
    assert.deepEqual(pageErrors,[]);assert.deepEqual(failed,[]);
    report.operations.push('390/1100 layout, actual fonts and screenshots without script errors');
    const variants=[
      ['math renderer','math-labels.js',s=>s.replace('katex.render(tex, target,','target.textContent = tex; return; katex.render(tex, target,'),'MathML'],
      ['heading renderer','math-labels.js',s=>s.replace('renderMath(options.heading, heading);','heading.textContent = options.heading;'),'MathML'],
      ['series renderer','math-labels.js',s=>s.replace('renderMath(item.text, formula);','formula.textContent = item.text;'),'MathML'],
      ['plugin registration','main.js',s=>s.replace('plugins: [mathLabels],','plugins: [],'),'MathML'],
      ['dataset mapping','math-labels.js',s=>s.replace('const index = item.datasetIndex;','const index = 1 - item.datasetIndex;'),'actual dataset index'],
    ];
    for(const [name,file,mutate,expected] of variants) {
      const source=await fs.readFile(new URL(file,import.meta.url),'utf8');const modified=mutate(source);assert.notEqual(modified,source);
      await page.route(`**/${file}`,route=>route.fulfill({contentType:'text/javascript',body:modified}));
      await page.goto(base);
      await assert.rejects(async()=>{if(name==='dataset mapping')await toggle(0);else await assertScene();},new RegExp(expected),`${name}: omitted essential behavior must fail`);
      await page.unroute(`**/${file}`);
      report.negatives.push({name,result:'failed the intended acceptance check'});
    }
    console.log(JSON.stringify({...report,fontsLoaded:fonts.length,result:'passed'},null,2));
  } finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
}
if(path.resolve(process.argv[1]||'')===fileURLToPath(import.meta.url)) await run();
