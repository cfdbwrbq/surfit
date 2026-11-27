const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson']);
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  const note = await page.textContent('#section-note');
  if (!note.includes('samples')) throw new Error('default section not computed: ' + note);
  const before = Number(await page.inputValue('#sec-y0'));
  await page.click('[data-tab="map"]');
  await page.waitForTimeout(150);
  const box = await page.locator('#map').boundingBox();
  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + 20, startY + 35, { steps: 5 });
  await page.mouse.up();
  const after = Number(await page.inputValue('#sec-y0'));
  if (!Number.isFinite(after) || Math.abs(after - before) < 1e-6) {
    throw new Error(`section did not move: ${before} -> ${after}`);
  }
  await page.screenshot({ path: 'tests/screenshots/section-drag.png', fullPage: true });
  console.log(JSON.stringify({ note, before, after, errors }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
