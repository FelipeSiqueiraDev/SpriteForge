// Executado na nuvem; verifica a prévia com os PNGs locais, sem servidor.
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve('dist/training-dummy/index.html')).href);
    await page.waitForFunction(() => document.querySelectorAll('canvas').length === 8 &&
      Object.values(images).every(image => image.complete && image.naturalWidth > 0));
    assert.equal(await page.locator('canvas').count(), 8);
    assert.equal(await page.locator('#pause').textContent(), 'Reproduzir');
    await page.selectOption('#action', 'walk');
    await page.click('#step');
    await page.waitForFunction(() => document.querySelector('.caption').textContent.includes('Frame 2/6'));
    await page.locator('#guides').uncheck();
    await page.locator('#speed').fill('0.5');
    await page.locator('#speed').dispatchEvent('input');
    assert.equal(await page.locator('#rate').textContent(), '0.5×');
    // file:// permite desenhar os PNGs, mas bloqueia a leitura dos pixels de volta.
    // Os pixels são conferidos no roundtrip Python; aqui verificamos a renderização.
    for (const canvas of await page.locator('canvas').all()) {
      const screenshot = await canvas.screenshot({ omitBackground: true });
      assert.ok(screenshot.byteLength > 0);
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.click('#pause');
    await page.waitForFunction(() => document.querySelector('.caption').textContent.includes('Frame 3/6'));
    await page.click('#pause');
    await page.setViewportSize({ width: 1280, height: 900 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    await page.goto(pathToFileURL(path.resolve('dist/wardrobe.html')).href);
    await page.waitForFunction(() => Object.values(images).every(image => image.complete && image.naturalWidth > 0));
    assert.equal(await page.locator('#appearance option').count(), 2);
    await page.selectOption('#appearance', '1');
    await page.waitForFunction(() => atlas.id === 'humanoid-outfit-demo');
    assert.match(await page.locator('footer a').first().getAttribute('href'), /humanoid-outfit-demo\/atlas.json/);
    await page.selectOption('#action', 'walk');
    await page.click('#step');
    await page.waitForFunction(() => document.querySelector('.caption').textContent.includes('Frame 2/6'));
    await page.selectOption('#appearance', '0');
    await page.waitForFunction(() => atlas.id === 'humanoid-base' && frame === 0);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    console.log('Prévia OK: PNGs, 8 direções, ação, pausa, avanço, velocidade, guias, animação e larguras celular/desktop.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
