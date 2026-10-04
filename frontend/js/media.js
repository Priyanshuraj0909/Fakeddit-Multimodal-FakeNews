/** Validate files before allocating preview resources. */
export const LIMITS = Object.freeze({ image: 10 * 1024 * 1024, video: 50 * 1024 * 1024, text: 1024 * 1024 });
const TYPES = {
  image: { 'image/png': ['png'], 'image/jpeg': ['jpg', 'jpeg'], 'image/webp': ['webp'] },
  video: { 'video/mp4': ['mp4'], 'video/webm': ['webm'] },
  text: { 'text/plain': ['txt'], '': ['txt'] },
};

export function validateFile(file, kind) {
  if (!file || !TYPES[kind]) throw new Error('Choose a supported file.');
  const extensions = TYPES[kind][file.type];
  const extension = file.name.split('.').pop().toLowerCase();
  if (!extensions?.includes(extension)) {
    const formats = { image: 'PNG, JPEG, or WebP', video: 'MP4 or WebM', text: 'a UTF-8 .txt' };
    throw new Error(`Choose ${formats[kind]} file.`);
  }
  if (file.size === 0) throw new Error('This file is empty. Choose another file.');
  if (file.size > LIMITS[kind]) throw new Error(`File is too large. The ${kind} limit is ${LIMITS[kind] / 1024 / 1024} MB.`);
  return file;
}

export async function readTextFile(file) {
  validateFile(file, 'text');
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()); }
  catch { throw new Error('This text file cannot be read. Save it as UTF-8 and try again.'); }
  if (!text.trim()) throw new Error('The text file contains no readable text.');
  if (text.length > 10000) throw new Error('The text file exceeds 10,000 characters. Import a shorter excerpt.');
  return text;
}

export function formatSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** Resolve only decoded media; release URLs on failures, replacement, and cancellation. */
export function prepareMedia(file, kind, signal) {
  validateFile(file, kind);
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Cancelled', 'AbortError')); return; }
    const url = URL.createObjectURL(file);
    const element = kind === 'image' ? new Image() : document.createElement('video');
    const event = kind === 'image' ? 'load' : 'loadedmetadata';
    let finished = false;
    let released = false;
    const release = () => { if (!released) { URL.revokeObjectURL(url); released = true; } };
    const clear = () => {
      clearTimeout(timer);
      element.removeEventListener(event, success);
      element.removeEventListener('error', failure);
      signal?.removeEventListener('abort', abort);
      element.removeAttribute('src');
      if (kind === 'video') element.load();
    };
    const fail = error => {
      if (finished) return;
      finished = true; clear(); release(); reject(error);
    };
    const failure = () => fail(new Error(kind === 'image' ? 'This file could not be decoded as an image.' : 'This video cannot be played in your browser. Try an H.264 MP4 or a WebM file.'));
    const abort = () => fail(new DOMException('Cancelled', 'AbortError'));
    const success = () => {
      if (finished) return;
      const width = kind === 'image' ? element.naturalWidth : element.videoWidth;
      const height = kind === 'image' ? element.naturalHeight : element.videoHeight;
      const duration = kind === 'video' ? element.duration : null;
      if (!width || !height) { failure(); return; }
      finished = true;
      const metadata = { name: file.name, type: file.type, size: file.size, width, height, ...(kind === 'video' ? { duration_seconds: Number.isFinite(duration) ? Math.round(duration * 10) / 10 : null } : {}) };
      clear(); resolve({ url, metadata, dispose: release });
    };
    const timer = setTimeout(() => fail(new Error('Preview timed out. Try a smaller file or a different format.')), 12000);
    element.addEventListener(event, success, { once: true });
    element.addEventListener('error', failure, { once: true });
    signal?.addEventListener('abort', abort, { once: true });
    if (kind === 'video') element.preload = 'metadata';
    element.src = url;
  });
}
