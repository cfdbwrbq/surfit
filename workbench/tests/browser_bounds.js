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

  await page.check('#auto_bounds');
  const autoLower = Number(await page.inputValue('#lower'));
  const autoUpper = Number(await page.inputValue('#upper'));
  if (autoLower !== lower || autoUpper !== upper) {
    throw new Error(`auto bounds mismatch: ${autoLower}..${autoUpper}`);
  }
  if (!(await page.isDisabled('#lower'))) throw new Error('auto bounds inputs not locked');

  await page.fill('#project_name', 'Auto bounds');
  await page.click('#save-project');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Project saved'));
  await page.click('.projects summary');
  await page.waitForSelector('.project-open');
  await page.click('.project-open');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Loaded'));
  if (!(await page.isChecked('#auto_bounds'))) throw new Error('auto bounds did not survive reload');
  console.log(JSON.stringify({ range, lower, upper, autoLower, autoUpper, errors }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
