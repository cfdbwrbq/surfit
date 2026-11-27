const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson']);
  await page.waitForFunction(() => !document.querySelector('#bounds-from-data').disabled);
  const range = await page.textContent('#data-z-range');
  await page.click('#bounds-from-data');
  const lower = Number(await page.inputValue('#lower'));
  const upper = Number(await page.inputValue('#upper'));
  if (!Number.isFinite(lower) || !Number.isFinite(upper) || lower > upper) {
    throw new Error(`bad data bounds: ${lower}..${upper}`);
  }
  console.log(JSON.stringify({ range, lower, upper, errors }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
