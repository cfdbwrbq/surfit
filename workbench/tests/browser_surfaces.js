const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.setInputFiles('#files', ['examples/points.geojson', 'examples/func.func']);
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('1 surfaces'));
  const roles = await page.$$eval('.file-role', (nodes) => nodes.map((node) => node.value));
  if (roles.join(',') !== 'points,surfaces') throw new Error('wrong roles: ' + roles.join(','));
  await page.click('.surface-rules summary');
  await page.check('#mean-enabled');
  await page.fill('#mean-value', '10');
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  const quality = await page.textContent('#quality');
  if (!quality.includes('f_mean')) throw new Error('mean rule missing');
  await page.screenshot({ path: 'tests/screenshots/surfaces.png', fullPage: true });

  await page.fill('#project_name', 'Surface rules');
  await page.click('#save-project');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Project saved'));
  await page.click('.projects summary');
  await page.waitForSelector('.project-open');
  await page.click('.project-open');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Loaded'));
  const loaded = await page.evaluate(() => ({
    count: document.querySelector('#surface-count').textContent,
    mean: document.querySelector('#mean-enabled').checked,
    value: document.querySelector('#mean-value').value,
  }));
  if (loaded.count !== '1' || !loaded.mean || loaded.value !== '10') {
    throw new Error('surface rule did not survive reload: ' + JSON.stringify(loaded));
  }
  console.log(JSON.stringify({ status: await page.textContent('#status'), roles, loaded, errors }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
