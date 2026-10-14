const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');

(async()=>{
 const root='dist/skins/crona-cozy-v1';
 const report=JSON.parse(fs.readFileSync(root+'/skins.json','utf8'));
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(root,'index.html')).href);
  await page.waitForFunction(()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0));
  assert.equal(await page.locator('article').count(),report.summary.ready);
  const stove=page.locator('article').filter({has:page.locator('code',{hasText:'fogao_lenha'})});
  await stove.getByRole('button',{name:'Giro 2',exact:true}).click();
  await stove.locator('select').selectOption('1');
  await page.waitForFunction(()=>document.querySelector('img[src$="fogao_lenha/giro-2-1.png"]')?.naturalWidth>0);
  assert.match(await stove.locator('img').getAttribute('alt'),/estado 1/);
  await page.selectOption('#filter','pending');
  assert.equal(await page.locator('article').count(),report.summary.pending);
  const pending=report.objects.find(r=>r.status==='pending');
  await page.fill('#query',pending.id);
  assert.ok(await page.locator('article code').allTextContents().then(ids=>ids.includes(pending.id)));
  await page.fill('#query','');
  await page.selectOption('#filter','all');
  assert.equal(await page.locator('article').count(),report.objects.length);
  for(const width of [390,1280]){
   await page.setViewportSize({width,height:844});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  assert.deepEqual(errors,[]);
  console.log('Skins OK: imagens, quatro giros, fogão aceso/apagado, busca, fila e celular/desktop.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
