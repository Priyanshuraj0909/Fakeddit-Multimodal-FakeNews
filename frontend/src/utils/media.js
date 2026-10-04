/** Validate files before allocating preview resources. */
export const LIMITS = Object.freeze({ image: 10 * 1024 * 1024, video: 50 * 1024 * 1024, text: 1024 * 1024 });
export const MEDIA_EXTENSIONS = Object.freeze({
  image: 'png jpg jpeg jpe jfif webp gif apng avif bmp dib svg ico cur tif tiff heic heif hif jxl jp2 j2k jpf jpx jpm mj2 psd psb raw arw cr2 cr3 nef nrw orf raf rw2 dng pef srw xcf tga pcx ppm pgm pbm pnm'.split(' '),
  video: 'mp4 webm mov qt m4v mkv avi wmv asf flv f4v mpg mpeg mpe m1v m2v mpv ogv ogg 3gp 3g2 ts mts m2ts vob divx rm rmvb mxf'.split(' '),
});

export function validateFile(file, kind) {
  if (!file || !LIMITS[kind]) throw new Error('Choose a supported file.');
  const extension = file.name.split('.').pop().toLowerCase();
  const type = (file.type || '').toLowerCase().split(';')[0].trim();
  const generic = !type || type === 'application/octet-stream';
  const allowed = kind === 'text'
    ? extension === 'txt' && (generic || type === 'text/plain')
    : MEDIA_EXTENSIONS[kind].includes(extension) && (generic || type.startsWith(kind + '/') ||
      (kind === 'video' && ['application/ogg', 'application/mxf', 'application/vnd.rn-realmedia', 'application/x-matroska'].includes(type)));
  if (!allowed) throw new Error(kind === 'text' ? 'Choose a UTF-8 .txt file.' : 'Choose an image or video file with a recognized media extension and matching file type.');
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

/** Keep accepted attachments even when their codec cannot be previewed; release all URLs. */
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
    const unavailable = reason => {
      if (finished) return;
      finished = true; clear(); release();
      resolve({ file, url: null, metadata: { name: file.name, type: file.type, size: file.size,
        width: null, height: null, preview_available: false, preview_note: reason,
        ...(kind === 'video' ? { duration_seconds: null } : {}) }, dispose: release });
    };
    const failure = () => unavailable('Attached without preview. This browser cannot decode the format or codec, or the file may be damaged.');
    const abort = () => fail(new DOMException('Cancelled', 'AbortError'));
    const success = () => {
      if (finished) return;
      const width = kind === 'image' ? element.naturalWidth : element.videoWidth;
      const height = kind === 'image' ? element.naturalHeight : element.videoHeight;
      const duration = kind === 'video' ? element.duration : null;
      if (!width || !height) { failure(); return; }
      finished = true;
      const metadata = { preview_available: true, name: file.name, type: file.type, size: file.size, width, height, ...(kind === 'video' ? { duration_seconds: Number.isFinite(duration) ? Math.round(duration * 10) / 10 : null } : {}) };
      clear(); resolve({ file, url, metadata, dispose: release });
    };
    const timer = setTimeout(() => unavailable('Attached without preview. Preview preparation timed out.'), 12000);
    element.addEventListener(event, success, { once: true });
    element.addEventListener('error', failure, { once: true });
    signal?.addEventListener('abort', abort, { once: true });
    if (kind === 'video') element.preload = 'metadata';
    element.src = url;
  });
}
