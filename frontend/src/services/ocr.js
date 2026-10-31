/** English OCR in a browser worker. Image bytes are never uploaded. */
const VERSION = '6.0.1';
let loading;

function loadEngine() {
  if (globalThis.Tesseract?.createWorker) return Promise.resolve(globalThis.Tesseract);
  if (!loading) loading = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    const failed = () => { clearTimeout(timer); script.remove(); loading = null; reject(new Error('OCR download failed. Check your connection and retry.')); };
    const timer = setTimeout(failed, 30000);
    script.src = `https://cdn.jsdelivr.net/npm/tesseract.js@${VERSION}/dist/tesseract.min.js`;
    script.crossOrigin = 'anonymous';
    script.onload = () => { clearTimeout(timer); globalThis.Tesseract?.createWorker ? resolve(globalThis.Tesseract) : failed(); };
    script.onerror = failed;
    document.head.append(script);
  });
  return loading;
}

export async function extractImageText(file, { signal, onProgress = () => {}, engine } = {}) {
  if (!file || !['image/png', 'image/jpeg', 'image/webp', 'image/bmp'].includes(file.type)) throw new Error('For text extraction, choose a PNG, JPEG, WebP or BMP image.');
  if (file.size > 10 * 1024 * 1024) throw new Error('OCR images must be 10 MB or smaller.');
  let worker;
  let stopped = false;
  let rejectCancelled;
  const cancelled = new Promise((_, reject) => { rejectCancelled = reject; });
  const abort = () => { stopped = true; rejectCancelled(new DOMException('Cancelled', 'AbortError')); worker?.terminate().catch(() => {}); };
  const check = () => { if (stopped || signal?.aborted) throw new DOMException('Cancelled', 'AbortError'); };
  check();
  signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(abort, 90000);
  try {
    const library = engine || await Promise.race([loadEngine(), cancelled]);
    check();
    await Promise.race([library.createWorker('eng', 1, {
      workerPath: `https://cdn.jsdelivr.net/npm/tesseract.js@${VERSION}/dist/worker.min.js`,
      corePath: 'https://cdn.jsdelivr.net/npm/tesseract.js-core@6.0.0',
      langPath: 'https://cdn.jsdelivr.net/npm/@tesseract.js-data/eng@1.0.0/4.0.0_best_int',
      logger: message => { if (!stopped) onProgress(message.status, message.progress); },
    }).then(instance => { worker = instance; if (stopped) instance.terminate().catch(() => {}); }), cancelled]);
    check();
    const { data } = await Promise.race([worker.recognize(file, {}, { text: true, tsv: true }), cancelled]);
    check();
    const text = (data.text || '').trim();
    if (!text) throw new Error('No readable text was found. Try a clearer screenshot.');
    if (text.length > 10000) throw new Error('Extracted text exceeds 10,000 characters. Crop the image and retry.');
    return { text, confidence: data.confidence, tsv: data.tsv || '', engine: `Tesseract.js ${VERSION}`, language: 'eng' };
  } catch (error) {
    if (stopped && !signal?.aborted) throw new Error('OCR download or recognition timed out. Check your connection, then retry with a smaller image.');
    check();
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
    if (worker) await worker.terminate().catch(() => {});
  }
}
