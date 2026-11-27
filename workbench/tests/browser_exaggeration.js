const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  const points = [
    '0 0 50', '1000000 0 120', '0 1000000 180', '1000000 1000000 60',
    '250000 250000 90', '750000 750000 200',
  ].join('\n');
  await page.setInputFiles('#files', {
    name: 'carbon_like.csv', mimeType: 'text/plain', buffer: Buffer.from(points),
  });
  await page.check('#cell_size_auto');
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 60000 });
  const value = await page.textContent('#exaggeration-value');
  const slider = await page.$eval('#exaggeration', (node) => Number(node.value));
  if (value === '×1' || !/×\d/.test(value)) throw new Error('auto exaggeration not applied: ' + value);
  if (Math.abs(slider - Math.log10(Number(value.slice(1)))) > 0.06) throw new Error('slider not synchronized');
  await page.screenshot({ path: 'tests/screenshots/exaggeration.png', fullPage: true });
  console.log(JSON.stringify({ value, slider, errors, status: await page.textContent('#status') }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
