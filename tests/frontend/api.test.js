import test from 'node:test';
import assert from 'node:assert/strict';
import { requestJSON, validateAnalysis } from '../../frontend/js/api.js';

test('valid JSON with an invalid report schema is rejected before rendering', () => {
  assert.throws(() => validateAnalysis({ mode: 'descriptive', note: 'Missing metrics' }), /incomplete analysis/);
  assert.throws(() => validateAnalysis({ mode: 'trained_text_baseline', note: 'Bad model', label: 'Class 0', probabilities: { 'Class 0': 4 } }), /incomplete analysis/);
});

test('API reports service errors and malformed responses without leaking internals', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: 'Model unavailable' }), { status: 503 }));
  await assert.rejects(requestJSON('/api/predict', { text: 'headline' }), /Model unavailable/);
  globalThis.fetch = async () => new Response('<html>gateway error</html>');
  await assert.rejects(requestJSON('/api/analyze'), /unreadable response/);
});

test('API timeouts terminate an unresponsive request', async t => {
  t.mock.method(globalThis, 'fetch', (_path, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  }));
  await assert.rejects(requestJSON('/api/analyze', { text: 'headline', timeout: 5 }), /timed out/);
});

test('API forwards user cancellation separately from a network error', async t => {
  t.mock.method(globalThis, 'fetch', (_path, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  }));
  const controller = new AbortController();
  const request = requestJSON('/api/analyze', { signal: controller.signal });
  controller.abort();
  await assert.rejects(request, { name: 'AbortError' });
});
