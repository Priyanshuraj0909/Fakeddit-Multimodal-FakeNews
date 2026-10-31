import test from 'node:test';
import assert from 'node:assert/strict';
import { extractImageText } from '../../frontend/src/services/ocr.js';
import { readHistory, saveReport, deleteReport, clearHistory } from '../../frontend/src/services/history.js';

const report = () => ({ generated_at: '2026-10-31T00:00:00Z', context: {}, attachments: {}, mode: 'descriptive', note: 'Synthetic test fixture', word_count: 4, character_count: 20, exclamation_count: 0, uppercase_ratio: 0, phrases: [] });
function storage() { const map = new Map(); return { getItem: k => map.get(k) ?? null, setItem: (k,v) => map.set(k,v), removeItem: k => map.delete(k) }; }

test('history preserves explicit reviews, bounds entries and deletes without saving automatically', () => {
  const db = storage();
  assert.deepEqual(readHistory(db), []);
  for (let i = 0; i < 25; i++) saveReport(db, report(), 'needs_review', String(i));
  assert.equal(readHistory(db).length, 20);
  assert.equal(readHistory(db)[0].review, 'needs_review');
  deleteReport(db, '24');
  assert.equal(readHistory(db).length, 19);
  assert.throws(() => saveReport(db, { ...report(), mode: 'media_inspection' }, '', 'bad'));
  assert.throws(() => saveReport(db, report(), 'verified_true', 'bad'));
  clearHistory(db);
  assert.deepEqual(readHistory(db), []);
});

test('history reports corruption and full storage instead of silently losing saved reports', () => {
  assert.throws(() => readHistory({ getItem: () => '{broken' }));
  assert.throws(() => saveReport({ getItem: () => null, setItem: () => { throw new Error('quota'); } }, report(), '', 'id'), /quota/);
});

test('OCR returns recognition metadata and always terminates its worker', async () => {
  let terminated = 0;
  const engine = { createWorker: async () => ({ recognize: async () => ({ data: { text: ' A headline ', confidence: 95, tsv: 'word boxes' } }), terminate: async () => { terminated++; } }) };
  const result = await extractImageText(new File(['fixture'], 'image.png', { type: 'image/png' }), { engine });
  assert.equal(result.text, 'A headline');
  assert.equal(result.tsv, 'word boxes');
  assert.equal(terminated, 1);
});

test('cancelling an unresponsive OCR job ends the request and terminates its worker', async () => {
  let terminated = 0;
  const engine = { createWorker: async () => ({ recognize: () => new Promise(() => {}), terminate: async () => { terminated++; } }) };
  const controller = new AbortController();
  const pending = extractImageText(new File(['fixture'], 'image.png', { type: 'image/png' }), { engine, signal: controller.signal });
  await new Promise(resolve => setTimeout(resolve, 5));
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.ok(terminated >= 1);
});

test('OCR rejects empty results and unsupported formats', async () => {
  await assert.rejects(extractImageText(new File(['x'], 'x.svg', { type: 'image/svg+xml' })), /PNG/);
  const engine = { createWorker: async () => ({ recognize: async () => ({ data: { text: '' } }), terminate: async () => {} }) };
  await assert.rejects(extractImageText(new File(['x'], 'x.png', { type: 'image/png' }), { engine }), /No readable text/);
});
