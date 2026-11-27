const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()); });
  page.on('pageerror', (err) => errors.push('page: ' + err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson', 'examples/contours.geojson']);
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('2 contours'));
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('8 points'));
  await page.click('.line-editor summary');
  const before = await page.locator('.line-row').count();
  if (before !== 2) throw new Error('expected 2 line rows, got ' + before);
  await page.locator('.line-row button').first().click();
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('1 contours'));
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector('#quality').textContent.includes('f_cntr'));
  await page.screenshot({ path: '/tmp/studio-edited-lines.png', fullPage: true });
  console.log(JSON.stringify({ status: await page.textContent('#status'), errors,
                               rowsAfter: await page.locator('.line-row').count() }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
