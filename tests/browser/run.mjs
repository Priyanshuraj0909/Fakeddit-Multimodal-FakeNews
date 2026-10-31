/** Reproducible Chromium smoke checks. Optional live OCR downloads the actual engine. */
import { readFile, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
const { chromium } = await import(process.env.FAKEDDIT_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.FAKEDDIT_BASE_URL || 'http://127.0.0.1:8765';
let server;
let browser;
try {
  if (!process.env.FAKEDDIT_BASE_URL) {
    server = spawn(process.env.FAKEDDIT_PYTHON || '.venv/bin/python', ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8765'], { stdio: 'ignore' });
    server.on('error', error => { console.error(error.message); });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      try { ready = (await fetch(`${base}/api/health`)).ok; } catch { /* Await startup. */ }
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!ready) throw new Error('Local API did not start');
  }
  browser = await chromium.launch({ headless: true, channel: process.env.FAKEDDIT_BROWSER_CHANNEL || 'chromium' });
  await mkdir('artifacts/browser', { recursive: true });
  for (const viewport of (process.env.FAKEDDIT_OCR_ONLY === '1' ? [] : [{ width: 1440, height: 1100 }, { width: 390, height: 844 }])) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    for (const script of ['workspace-smoke.js', 'detector-smoke.js']) {
      const result = await page.evaluate(await readFile(new URL(script, import.meta.url), 'utf8'));
      if (result.overflow) throw new Error(`Horizontal overflow at ${viewport.width}`);
      console.log(JSON.stringify({ viewport: viewport.width, script, ...result }));
    }
    const submittedText = 'Scientists discover a new species in the rainforest\nA second paragraph retained for review.';
    await page.selectOption('#mode', 'analyze');
    await page.locator('#headline').fill(submittedText);
    await page.locator('.verification-fields').evaluate(details => { details.open = true; });
    await page.locator('#source-url').fill('https://example.com/original');
    await page.locator('#publication-date').fill('2026-10-31');
    await page.locator('#verification-notes').fill('Check the original event date.');
    await page.locator('#analysis-form').evaluate(form => form.requestSubmit());
    await page.waitForSelector('#result:not([hidden])');
    await page.selectOption('#review', 'needs_review');
    await page.click('#save-report');
    if (await page.locator('.history-entry').count() !== 1) throw new Error('Report was not saved');
    await page.reload();
    await page.locator('.history-open').click();
    if (await page.locator('#review').inputValue() !== 'needs_review') throw new Error('Review was not retained');
    if (await page.locator('#headline').inputValue() !== submittedText || await page.locator('#mode').inputValue() !== 'analyze'
        || await page.locator('#source-url').inputValue() !== 'https://example.com/original'
        || await page.locator('#publication-date').inputValue() !== '2026-10-31'
        || await page.locator('#verification-notes').inputValue() !== 'Check the original event date.') throw new Error('Original submission or context was not restored');
    await page.selectOption('#review', 'disagree');
    await page.click('#save-report');
    if (await page.locator('.history-entry').count() !== 1) throw new Error('Updating a review duplicated a saved report');
    await page.locator('.history-entry button').last().click();
    if (await page.locator('.history-entry').count() !== 0) throw new Error('Deletion failed');
    await page.click('#save-report');
    await page.click('#clear-history');
    if (await page.locator('.history-entry').count() !== 0) throw new Error('Clear history failed');
    console.log(JSON.stringify({ viewport: viewport.width, history: 'save/reload/restore/review/delete/clear passed' }));
    await page.screenshot({ path: `artifacts/browser/workspace-${viewport.width}.png`, fullPage: true });
    if (errors.length) throw new Error(errors.join('\n'));
    await context.close();
  }
  for (let attempt = 0; process.env.FAKEDDIT_OCR_LIVE === '1' && attempt < Number(process.env.FAKEDDIT_OCR_REPEATS || 1); attempt++) {
    const page = await browser.newPage();
    page.on('requestfailed', request => console.error(`OCR asset request failed: ${request.url()} ${request.failure()?.errorText}`));
    page.on('pageerror', error => console.error(`OCR browser error: ${error.message}`));
    await page.goto(base);
    const image = await page.evaluate(() => {
      const canvas = document.createElement('canvas'); canvas.width = 1400; canvas.height = 180;
      const ctx = canvas.getContext('2d'); ctx.fillStyle = 'white'; ctx.fillRect(0, 0, 1400, 180);
      ctx.font = '48px Arial'; ctx.fillStyle = 'black'; ctx.fillText('Scientists discover a new species in the rainforest', 30, 100);
      return canvas.toDataURL('image/png').split(',')[1];
    });
    await page.click('#tab-image');
    await page.locator('#image-file').setInputFiles({ name: 'ocr-smoke.png', mimeType: 'image/png', buffer: Buffer.from(image, 'base64') });
    await page.waitForFunction(() => !document.getElementById('extract-text').disabled);
    await page.click('#extract-text');
    await page.waitForFunction(() => /Scientists discover/.test(document.getElementById('headline').value) || document.getElementById('cancel-ocr').hidden, null, { timeout: 100000 });
    if (!/Scientists discover/.test(await page.locator('#headline').inputValue())) throw new Error(`Live OCR failed: ${await page.locator('#ocr-status').textContent()}`);
    console.log(JSON.stringify({ ocr: 'Real browser engine recognized generated English text', text: await page.locator('#headline').inputValue() }));
    await page.locator('#headline').fill('Scientists discover a new species in the rainforest today');
    await page.selectOption('#mode', 'analyze');
    await page.locator('#analysis-form').evaluate(form => form.requestSubmit());
    await page.waitForSelector('#result:not([hidden])');
    const downloadPromise = page.waitForEvent('download');
    await page.click('#download');
    const download = await downloadPromise;
    const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
    if (!exported.text_extraction?.edited || !exported.text_extraction.tsv || !exported.text_extraction.submitted_text.endsWith('today')) throw new Error('Corrected OCR text or word locations were not exported');
    console.log(JSON.stringify({ ocr: 'Corrected text, original extraction and word locations retained in exported report' }));
    await page.close();
  }
} finally {
  await browser?.close();
  server?.kill();
}
