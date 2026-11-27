const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson', 'examples/contours.geojson']);
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('8 points'));
  const pane = await page.locator('#map-pane').boundingBox();
  const box = await page.locator('#map').boundingBox();
  await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.4);
  const transforms = [];
  for (let i = 0; i < 4; i += 1) {
    await page.mouse.wheel(0, -120);
    await page.waitForTimeout(80);
    transforms.push(await page.$eval('#map', c => [c.dataset.zoom, c.dataset.pan]));
  }
  const overflow = await page.$eval('#map-pane', p => getComputedStyle(p).overflow);
  if (overflow !== 'hidden') throw new Error('map pane does not clip: ' + overflow);
  await page.click('#map-reset');
  await page.mouse.move(pane.x + pane.width / 2, pane.y + pane.height / 2);
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(80);
  const out = await page.$eval('#map', c => [c.dataset.zoom, c.dataset.pan]);
  await page.click('#map-reset');
  const reset = await page.$eval('#map', c => [c.dataset.zoom, c.dataset.pan]);
  console.log(JSON.stringify({ transforms, out, reset, errors }));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
