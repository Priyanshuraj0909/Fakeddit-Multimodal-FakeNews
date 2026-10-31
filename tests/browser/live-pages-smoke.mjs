/** Real public Pages → Vercel browser regression; no requests or predictions are mocked. */
import { readFile, mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
const manifest = JSON.parse(await readFile(new URL('../../docs/TEXT_MODEL_V2_RELEASE.json', import.meta.url), 'utf8'));
const browser = await chromium.launch({ headless: true, channel: process.env.FAKEDDIT_BROWSER_CHANNEL || 'chromium' });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto('https://priyanshuraj0909.github.io/Fakeddit-Multimodal-FakeNews/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (response.status() !== 200) throw new Error('Pages did not return HTTP 200');
  await page.waitForFunction(() => document.getElementById('connection').dataset.status === 'online', null, { timeout: 30000 });
  await page.locator('#headline').fill('Scientists discover a new species in the rainforest');
  await page.locator('#analysis-form').evaluate(form => form.requestSubmit());
  await page.waitForSelector('#result:not([hidden])', { timeout: 70000 });
  const report = await page.locator('#detection-report').textContent();
  if (!report.includes('Trained model prediction') || !report.includes(`${(manifest.metrics.test_accuracy * 100).toFixed(2)}% accuracy`)) throw new Error('Current trained classifier benchmark is missing');
  const evidence = await page.evaluate(async () => {
    const response = await fetch('https://fakeddit-multimodal-fakenews.vercel.app/api/model-card', { cache: 'no-store' });
    return response.json();
  });
  if (evidence.release !== manifest.release || evidence.artifact_sha256 !== manifest.artifact.sha256) throw new Error('Live release/artifact differs from the evaluated manifest');
  await page.click('#save-report');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.history-open').click();
  if (!(await page.locator('#headline').inputValue()).includes('rainforest')) throw new Error('Saved original input was not restored');
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Mobile layout overflows');
  if (errors.length) throw new Error(errors.join('\n'));
  await mkdir('artifacts/browser', { recursive: true });
  await page.screenshot({ path: 'artifacts/browser/live-pages.png', fullPage: true });
  console.log(JSON.stringify({ url: page.url(), status: 'passed', release: evidence.release, application_version: evidence.runtime.version, recorded_test_accuracy: manifest.metrics.test_accuracy,
    checks: ['public HTML/assets', 'real cross-origin capabilities and classifier', 'current benchmark rendered', 'release and artifact match', 'save/reload/restore', 'mobile overflow', 'no page errors'], mocked_requests: false }));
} finally {
  await browser.close();
}
