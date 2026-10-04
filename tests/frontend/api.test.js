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

const detection = () => ({
  mode: 'news_detection', note: 'Separate assessments',
  model_assessment: { status: 'ready', label: 'Likely real', probabilities: { 'Likely real': 0.8, 'Likely fake': 0.2 }, note: 'Dataset prediction' },
  verification: { status: 'completed', verdict: 'supported', summary: 'Documented',
    claims: [{ statement: 'A specific claim', verdict: 'supported', explanation: 'Direct evidence', evidence_ids: [1] }],
    sources: [{ id: 1, title: 'Evidence', publisher: 'example.com', url: 'https://example.com/evidence' }] }
});

test('detector validates model scores and source provenance independently', () => {
  assert.equal(validateAnalysis(detection()).mode, 'news_detection');
  const invalidScore = detection(); invalidScore.model_assessment.probabilities['Likely real'] = NaN;
  assert.throws(() => validateAnalysis(invalidScore));
  const missingSource = detection(); missingSource.verification.claims[0].evidence_ids = [2];
  assert.throws(() => validateAnalysis(missingSource));
  const unsafeURL = detection(); unsafeURL.verification.sources[0].url = 'javascript:alert(1)';
  assert.throws(() => validateAnalysis(unsafeURL));
  const unsupported = detection(); unsupported.verification.claims[0].evidence_ids = [];
  assert.throws(() => validateAnalysis(unsupported));
});

test('unavailable verification and model abstention are explicit valid reports', () => {
  const report = detection();
  report.verification = { status: 'unavailable', verdict: 'not_checked', summary: 'Setup required', claims: [], sources: [] };
  report.model_assessment = { status: 'abstained', label: 'Insufficient text', probabilities: {}, note: 'No prediction' };
  assert.equal(validateAnalysis(report), report);
});

test('news request sends source context without local notes or credentials', async () => {
  const oldFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (_path, options) => {
      assert.deepEqual(JSON.parse(options.body), { text: 'Claim', source_url: 'https://example.com/source', publication_date: '2026-10-05' });
      assert.equal(options.headers.Authorization, undefined);
      return new Response('{}');
    };
    await requestJSON('/api/detect', { text: 'Claim', source_url: 'https://example.com/source', publication_date: '2026-10-05' });
  } finally { globalThis.fetch = oldFetch; }
});
