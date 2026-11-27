const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()); });
  page.on('pageerror', (err) => errors.push('page: ' + err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', 'examples/contours.geojson');
  await page.fill('#cell_size', '1');
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: '/tmp/studio-contours-only.png', fullPage: true });
  console.log(JSON.stringify({ status: await page.textContent('#status'), errors, title: await page.textContent('#hud-title') }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
