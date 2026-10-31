/** Packaged Pages files at their actual URL prefix; test transport forwards API calls to the real local classifier. */
import { spawn } from 'node:child_process';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
const { chromium } = await import(process.env.FAKEDDIT_PLAYWRIGHT_MODULE || 'playwright');
const python = process.env.FAKEDDIT_PYTHON || '.venv/bin/python';
const root = resolve(`artifacts/pages-smoke-${Date.now()}`);
const origin = 'https://priyanshuraj0909.github.io';
const prefix = '/Fakeddit-Multimodal-FakeNews/';
const local = 'http://127.0.0.1:8767';
let server, browser;
try {
  await mkdir('artifacts', { recursive: true });
  const builder = spawn(python, ['scripts/build_pages.py', '--output', root], { stdio: 'ignore' });
  await new Promise((done, reject) => { builder.on('error', reject); builder.on('exit', code => code === 0 ? done() : reject(new Error('Pages package failed'))); });
  server = spawn(python, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8767'], { stdio: 'ignore' });
  server.on('error', error => console.error(error.message));
  let ready = false;
  for (let i = 0; i < 100; i++) {
    try { ready = (await fetch(local + '/api/health', { signal: AbortSignal.timeout(1000) })).ok; } catch { /* Wait for startup. */ }
    if (ready) break;
    await new Promise(done => setTimeout(done, 100));
  }
  if (!ready) throw new Error('Pages test API did not start');
  browser = await chromium.launch({ headless: true, channel: process.env.FAKEDDIT_BROWSER_CHANNEL || 'chromium' });
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const errors = [], apiCalls = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route(origin + '/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (!pathname.startsWith(prefix)) return route.fulfill({ status: 404, body: 'Not found' });
      const target = resolve(root, pathname.slice(prefix.length) || 'index.html');
      if (!target.startsWith(root + sep)) return route.fulfill({ status: 404, body: 'Not found' });
      const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };
      try { await route.fulfill({ body: await readFile(target), contentType: types[extname(target)] || 'application/octet-stream' }); }
      catch { await route.fulfill({ status: 404, body: 'Missing packaged asset' }); }
    });
    await page.route('https://fakeddit-multimodal-fakenews.vercel.app/api/**', async route => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      apiCalls.push(pathname);
      const response = await route.fetch({ url: local + pathname, headers: { ...request.headers(), origin } });
      if (response.headers()['access-control-allow-origin'] !== origin) throw new Error('API did not authorize the Pages origin');
      await route.fulfill({ response });
    });
    await page.goto(origin + prefix);
    await page.waitForFunction(() => document.getElementById('connection').dataset.status === 'online');
    await page.locator('#headline').fill('Scientists discover a new species in the rainforest');
    await page.locator('#analysis-form').evaluate(form => form.requestSubmit());
    await page.waitForSelector('#result:not([hidden])');
    if (!(await page.locator('#detection-report').textContent()).includes('Trained model prediction')) throw new Error('Real classifier report missing from Pages package');
    await page.click('#save-report');
    await page.reload();
    await page.locator('.history-open').click();
    if (!(await page.locator('#headline').inputValue()).includes('rainforest')) throw new Error('Pages history restoration failed');
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Pages layout overflows');
    if (errors.length) throw new Error(errors.join('\n'));
    if (!apiCalls.includes('/api/detect')) throw new Error('Pages did not use the configured API');
    console.log(JSON.stringify({ pages: 'packaged prefix and modules, real local detector via explicit test transport, CORS, save/reload/restore', viewport: viewport.width, status: 'passed' }));
    await context.close();
  }
} finally {
  await browser?.close();
  server?.kill();
}
