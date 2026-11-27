const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson']);
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('8 points'));
  await page.check('#cell_size_auto');
  const first = Number(await page.inputValue('#cell_size'));
  if (!Number.isFinite(first) || first <= 0) throw new Error('auto cell not filled');
  await page.fill('#auto_cells', '100');
  const second = Number(await page.inputValue('#cell_size'));
  if (!(second > first * 1.5)) throw new Error(`auto cells not interactive: ${first} -> ${second}`);
  if (!(await page.isDisabled('#cell_size'))) throw new Error('cell size not locked');
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  const quality = await page.textContent('#metrics');
  if (!quality.includes('101 × 101')) throw new Error('auto cell goal not applied: ' + quality);

  await page.fill('#project_name', 'Auto cell');
  await page.click('#save-project');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Project saved'));
  await page.click('.projects summary');
  await page.waitForSelector('.project-open');
  await page.click('.project-open');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Loaded'));
  const loaded = await page.evaluate(() => ({
    auto: document.querySelector('#cell_size_auto').checked,
    cells: document.querySelector('#auto_cells').value,
  }));
  if (!loaded.auto || loaded.cells !== '100') throw new Error('auto cell did not survive reload');
  console.log(JSON.stringify({ first, second, loaded, errors }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
