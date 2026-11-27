const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()); });
  page.on('pageerror', (err) => errors.push('page: ' + err.message));
  await page.goto('http://127.0.0.1:8010/', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/studio-initial.png', fullPage: true });
  await page.setInputFiles('#files', [
    'examples/points.geojson',
    'examples/faults.geojson',
    'examples/contours.geojson',
  ]);
  const roles = await page.$$eval('.file-role', (nodes) => nodes.map((node) => node.value));
  if (roles.join(',') !== 'points,faults,contours') throw new Error('wrong roles: ' + roles.join(','));
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('8 points'));
  const preview = await page.textContent('#map-stats');
  if (!preview.includes('2 contours') || !preview.includes('1 faults')) throw new Error('preview missing: ' + preview);
  await page.screenshot({ path: '/tmp/studio-preview.png', fullPage: true });
  await page.check('#cell_size_auto');
  if (!(await page.$eval('#cell_size', (input) => input.disabled))) {
    throw new Error('auto cell size did not disable the manual input');
  }
  await page.uncheck('#cell_size_auto');
  await page.fill('#min_value', '11');
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('4 points'));
  await page.fill('#min_value', '');
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('8 points'));
  await page.locator('.file-enabled').nth(2).uncheck();
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('0 contours'));
  await page.locator('.file-enabled').nth(2).check();
  await page.waitForFunction(() => document.querySelector('#map-stats').textContent.includes('2 contours'));
  await page.fill('#cell_size', '1');
  await page.fill('#tol', '0.000001');
  await page.click('#solve');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Done'), null, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector('#quality').textContent.includes('f_points'), null, { timeout: 5000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: '/tmp/studio-result.png', fullPage: true });
  await page.click('.section-panel summary');
  await page.click('#draw-section');
  await page.waitForFunction(() => document.querySelector('#section-note').textContent.includes('samples'));
  await page.screenshot({ path: '/tmp/studio-section.png', fullPage: true });
  const reportPromise = page.waitForEvent('download');
  await page.click('#download-report');
  const report = await reportPromise;
  if (report.suggestedFilename() !== 'surfit-report.json') {
    throw new Error('wrong report filename: ' + report.suggestedFilename());
  }

  await page.fill('#project_name', 'Browser project');
  await page.click('#save-project');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Project saved'));
  await page.click('.projects summary');
  await page.waitForSelector('.project-open');
  await page.click('.project-open');
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Loaded'));
  const loaded = await page.evaluate(() => ({
    status: document.querySelector('#status').textContent,
    tab: document.querySelector('.tab.is-active')?.dataset.tab,
    title: document.querySelector('#hud-title')?.textContent,
  }));
  if (loaded.tab !== 'result' || loaded.title !== '13 × 13 grid') {
    throw new Error('project did not restore result: ' + JSON.stringify(loaded));
  }
  await page.screenshot({ path: '/tmp/studio-loaded.png', fullPage: true });

  await page.waitForSelector('.project-export');
  const archivePromise = page.waitForEvent('download');
  await page.click('.project-export');
  const archive = await archivePromise;
  const archivePath = await archive.path();
  await page.setInputFiles('#project-archive', archivePath);
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Loaded'));
  const imported = await page.evaluate(() => ({
    status: document.querySelector('#status').textContent,
    tab: document.querySelector('.tab.is-active')?.dataset.tab,
  }));
  if (imported.tab !== 'result') throw new Error('import did not restore result: ' + JSON.stringify(imported));

  await page.click('[data-tab="map"]');
  await page.waitForTimeout(300);
  await page.click('#map-zoom-in');
  const zoom = await page.$eval('#map', (canvas) => canvas.dataset.zoom);
  if (!(Number(zoom) > 1)) throw new Error('map zoom did not change: ' + zoom);
  await page.click('#map-reset');
  await page.screenshot({ path: '/tmp/studio-map.png', fullPage: true });
  const canvas = await page.evaluate(() => {
    const c = document.querySelector('#scene canvas');
    return { width: c?.width, height: c?.height, title: document.querySelector('#hud-title')?.textContent,
             tab: document.querySelector('.tab.is-active')?.dataset.tab };
  });
  console.log(JSON.stringify({ canvas, errors, status: await page.textContent('#status') }));
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
