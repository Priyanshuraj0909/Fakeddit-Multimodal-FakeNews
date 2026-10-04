import test from 'node:test';
import assert from 'node:assert/strict';
import { LIMITS, validateFile, readTextFile, formatSize } from '../../frontend/js/media.js';

const file = (name, type, content) => new File([content], name, { type });

test('upload validation rejects spoofed extensions, unsupported media, empty files, and limits', () => {
  assert.equal(validateFile(file('drawing.svg', 'image/svg+xml', '<svg/>'), 'image').name, 'drawing.svg');
  assert.throws(() => validateFile(file('payload.exe', 'image/png', 'x'), 'image'), /Choose/);
  assert.throws(() => validateFile(file('empty.mp4', 'video/mp4', ''), 'video'), /empty/);
  assert.throws(() => validateFile({ name: 'large.mp4', type: 'video/mp4', size: LIMITS.video + 1 }, 'video'), /too large/);
  assert.equal(validateFile(file('photo.PNG', 'image/png', 'x'), 'image').name, 'photo.PNG');
  assert.equal(validateFile(file('clip.webm', 'video/webm', 'x'), 'video').type, 'video/webm');
  for (const [name, type, kind] of [['photo.HEIC', 'image/heic', 'image'], ['scan.tiff', '', 'image'], ['raw.nef', 'application/octet-stream', 'image'], ['clip.MOV', 'video/quicktime', 'video'], ['clip.mkv', 'application/octet-stream', 'video'], ['clip.avi', 'video/x-msvideo', 'video']]) {
    assert.equal(validateFile(file(name, type, 'x'), kind).name, name);
  }
  assert.throws(() => validateFile(file('clip.mp4', 'image/png', 'x'), 'video'), /Choose/);
});

test('text import decodes UTF-8 and rejects invalid bytes and excessive characters', async () => {
  assert.equal(await readTextFile(file('headline.txt', 'text/plain', 'Evidence café')), 'Evidence café');
  await assert.rejects(readTextFile(file('bad.txt', 'text/plain', new Uint8Array([255, 254]))), /UTF-8/);
  await assert.rejects(readTextFile(file('long.txt', 'text/plain', 'x'.repeat(10001))), /10,000/);
  await assert.rejects(readTextFile(file('spaces.txt', 'text/plain', '   ')), /no readable text/);
});

test('media sizes are formatted with meaningful units', () => {
  assert.equal(formatSize(2048), '2 KB');
  assert.equal(formatSize(2 * 1024 * 1024), '2.0 MB');
});
