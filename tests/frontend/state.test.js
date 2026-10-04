import test from 'node:test';
import assert from 'node:assert/strict';
import { createStore, buildReport, inspectMedia } from '../../frontend/src/hooks/state.js';

test('updating one attachment preserves the other and exported reports exclude blob URLs', () => {
  const store = createStore();
  store.update({ media: { image: { url: 'blob:private', metadata: { name: 'image.png', width: 10 } } } });
  store.update({ media: { video: { url: 'blob:video', metadata: { name: 'video.mp4', duration_seconds: 2 } } } });
  const report = buildReport({ mode: 'descriptive' }, store.get(), new Date('2026-10-04T00:00:00Z'));
  assert.equal(report.attachments.image.name, 'image.png');
  assert.equal(report.attachments.video.duration_seconds, 2);
  assert.ok(!JSON.stringify(report).includes('blob:'));
  store.update({ media: { image: null } });
  assert.ok(store.get().media.video);
});

test('media-only reports preserve verification context without making classification claims', () => {
  const store = createStore();
  assert.throws(() => inspectMedia(store.get()), /Add text/);
  store.update({ context: { source_url: 'https://example.com/report', verification_notes: 'Caption requires checking' },
    media: { image: { url: null, metadata: { name: 'photo.heic', size: 100, preview_available: false } } } });
  const report = buildReport(inspectMedia(store.get()), store.get());
  assert.equal(report.mode, 'media_inspection');
  assert.equal(report.attachment_count, 1);
  assert.equal(report.preview_count, 0);
  assert.equal(report.total_bytes, 100);
  assert.equal(report.context.source_url, 'https://example.com/report');
  assert.match(report.note, /do not establish authenticity/);
  assert.equal(report.label, undefined);
});
