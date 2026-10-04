import test from 'node:test';
import assert from 'node:assert/strict';
import { requestJSON, validateAnalysis } from '../../frontend/src/services/api.js';

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

test('multimodal requests send a real image and text with multipart boundary managed by browser', async t => {
  let captured;
  t.mock.method(globalThis, 'fetch', async (_path, options) => {
    captured = options;
    return new Response(JSON.stringify({ mode: 'trained_multimodal', task: 'fakeddit_binary', image_assessed: true, label: 'Class 0',
      scores: { 'Class 0': .6, 'Class 1': .4 }, note: 'Mocked API schema' }));
  });
  const image = new File(['fixture'], 'image.png', { type: 'image/png' });
  const result = validateAnalysis(await requestJSON('/api/predict/multimodal', { text: 'headline', image }));
  assert.equal(result.mode, 'trained_multimodal');
  assert.equal(captured.body.get('text'), 'headline');
  assert.equal(captured.body.get('image').name, 'image.png');
  assert.equal(captured.headers, undefined);
  assert.throws(() => validateAnalysis({ ...result, scores: { 'Class 0': .6, 'Class 1': .6 } }), /incomplete/);
});
