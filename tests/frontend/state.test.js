import test from 'node:test';
import assert from 'node:assert/strict';
import { createStore, buildReport } from '../../frontend/js/state.js';

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
