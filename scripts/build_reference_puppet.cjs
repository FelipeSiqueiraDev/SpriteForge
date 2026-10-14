const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');

(async()=>{
  const [source,output]=process.argv.slice(2);
  if(!source||!output)throw new Error('Usage: node scripts/build_reference_puppet.cjs parts.png output-directory');
  fs.mkdirSync(path.join(output,'frames'),{recursive:true});
  fs.mkdirSync(path.join(output,'preview-frames'),{recursive:true});
  const data='data:image/png;base64,'+fs.readFileSync(source).toString('base64');
  const script=fs.readFileSync(path.join(__dirname,'reference_puppet.js'),'utf8');
  const html=`<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Carequinha — caminhada</title><style>*{box-sizing:border-box}body{margin:0;background:#16212d;color:#f6ecdf;font:16px system-ui;text-align:center}main{max-width:720px;margin:auto;padding:24px}h1{font-size:23px;margin:0 0 6px}p{color:#b8c8d8}canvas{display:block;width:min(100%,512px);height:auto;margin:18px auto;background:#283340;border-radius:18px;image-rendering:pixelated}nav{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;align-items:center}button,select{font:inherit;padding:9px 14px;border:1px solid #64778b;border-radius:9px;color:#f6ecdf;background:#28394a}label{display:inline-flex;gap:9px;align-items:center;margin:16px}small{display:block;color:#aabccb}</style><main><h1>Carequinha caminhando</h1><p>Teste de movimento em uma direção</p><canvas width="512" height="512" aria-label="Personagem animado"></canvas><nav><select id="action" aria-label="Ação"><option value="walk">Caminhar</option><option value="idle">Parado</option></select><button id="pause">Pausar</button><button id="step">Avançar quadro</button><span id="frame"></span></nav><label>Velocidade <input id="speed" type="range" min="0.25" max="1.5" step="0.05" value="1"><span id="rate">1.00×</span></label><small>Estudo para revisão visual.</small></main><script>window.ATLAS_DATA=${JSON.stringify(data)};<\/script><script>${script}<\/script></html>`;
  fs.writeFileSync(path.join(output,'preview.html'),html);
  const executablePath=process.env.SPRITEFORGE_CHROMIUM;
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
  try{
    const page=await browser.newPage({viewport:{width:720,height:850}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.setContent(html);await page.waitForFunction(()=>window.puppet?.ready);
    await page.click('#pause');
    const records=[];
    for(let index=0;index<32;index++){
      const result=await page.evaluate(index=>{
        const p=window.puppet.render(index/32),c=document.querySelector('canvas');
        const rgba=c.toDataURL('image/png');
        const head=c.getContext('2d').getImageData(180,18+Math.round(p.bob),153,140).data;
        let fingerprint=2166136261;for(const value of head)fingerprint=Math.imul(fingerprint^value,16777619)>>>0;
        window.puppet.render(index/32,true);
        return {rgba,preview:c.toDataURL('image/png'),pose:p,head_fingerprint:fingerprint};
      },index);
      const name=String(index).padStart(2,'0')+'.png';
      fs.writeFileSync(path.join(output,'frames',name),Buffer.from(result.rgba.split(',')[1],'base64'));
      fs.writeFileSync(path.join(output,'preview-frames',name),Buffer.from(result.preview.split(',')[1],'base64'));
      records.push({...result.pose,head_fingerprint:result.head_fingerprint});
    }
    await page.evaluate(()=>window.puppet.seek(0));
    await page.screenshot({path:path.join(output,'preview.png')});
    const montage=await page.evaluate(()=>{
      const sheet=document.createElement('canvas');sheet.width=1024;sheet.height=512;
      const target=sheet.getContext('2d');target.imageSmoothingEnabled=false;
      for(let i=0;i<8;i++){window.puppet.render(i/8,true);target.drawImage(document.querySelector('canvas'),i%4*256,Math.floor(i/4)*256,256,256);}
      return sheet.toDataURL('image/png');
    });
    fs.writeFileSync(path.join(output,'poses.png'),Buffer.from(montage.split(',')[1],'base64'));
    const metadata=await page.evaluate(()=>({parts:window.puppet.parts,first:window.puppet.pose(0),last:window.puppet.pose(1)}));
    const assert=require('node:assert/strict');
    assert.equal(new Set(records.map(p=>p.head_fingerprint)).size,1,'Head pixels must stay identical after registration');
    assert.deepEqual(metadata.first,metadata.last,'The loop must close without a pose jump');
    for(const pose of records)for(const limb of Object.values(pose.limbs)){
      for(const [a,b,l] of [['hip','knee',77],['knee','ankle',77],['shoulder','elbow',55],['elbow','wrist',55]]){
        assert.ok(Math.abs(Math.hypot(limb[a][0]-limb[b][0],limb[a][1]-limb[b][1])-l)<1e-8);
      }
    }
    await page.selectOption('#action','idle');await page.click('#step');
    await page.locator('#speed').fill('0.5');await page.locator('#speed').dispatchEvent('input');
    assert.equal(await page.locator('#rate').textContent(),'0.50×');
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    fs.writeFileSync(path.join(output,'rig.json'),JSON.stringify({version:1,frame_count:32,duration_ms:30,head:'single-shared-bitmap',...metadata,poses:records},null,2));
    fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({
      frame_count:32,cell:[512,512],duration_ms:30,loop_ms:960,
      head_pixel_hashes:[...new Set(records.map(p=>p.head_fingerprint))],
      identical_registered_head_pixels:'passed',fixed_limb_lengths:'passed',
      loop_closure:'passed',preview_controls:'passed',mobile_width:'passed',
      source_sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(source)).digest('hex'),
      status:'visual-study-one-direction-not-crona-calibrated'
    },null,2));
    if(errors.length)throw new Error(errors.join('\n'));
    console.log('32 frames: identical registered head pixels, fixed limb lengths, closed loop and preview controls passed.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
