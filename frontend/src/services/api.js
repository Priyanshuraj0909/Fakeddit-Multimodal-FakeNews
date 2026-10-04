/** Same-origin requests with bounded waits and user-readable failures. */
export function validateAnalysis(data) {
  const invalid = () => { throw new Error('The server returned an incomplete analysis. Please try again.'); };
  if (!data || typeof data.note !== 'string') invalid();
  if (data.mode === 'descriptive') {
    const counts = ['word_count', 'character_count', 'exclamation_count'];
    if (counts.some(key => !Number.isInteger(data[key]) || data[key] < 0)
      || !Number.isFinite(data.uppercase_ratio) || data.uppercase_ratio < 0 || data.uppercase_ratio > 1
      || !Array.isArray(data.phrases) || data.phrases.some(phrase => typeof phrase !== 'string')) invalid();
  } else if (data.mode === 'trained_text_baseline' || data.mode === 'trained_multimodal') {
    const scores = data.mode === 'trained_multimodal' ? data.scores : data.probabilities;
    if (data.mode === 'trained_multimodal' && (data.task !== 'fakeddit_binary' || data.image_assessed !== true || Object.keys(scores || {}).length !== 2)) invalid();
    if (typeof data.label !== 'string' || !scores || typeof scores !== 'object'
      || Array.isArray(scores) || !Object.keys(scores).length
      || Object.values(scores).some(value => !Number.isFinite(value) || value < 0 || value > 1)
      || Math.abs(Object.values(scores).reduce((sum, value) => sum + value, 0) - 1) > 0.001
      || !Object.hasOwn(scores, data.label)) invalid();
  } else invalid();
  return data;
}

export async function requestJSON(path, { text, image, signal, timeout = 20000 } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    let body;
    if (image) {
      body = new FormData();
      body.append('text', text); body.append('image', image, image.name);
    } else if (text !== undefined) body = JSON.stringify({ text });
    const response = await fetch(path, {
      method: text === undefined ? 'GET' : 'POST',
      ...(body === undefined ? {} : { body }),
      ...(body !== undefined && !image ? { headers: { 'Content-Type': 'application/json' } } : {}),
      signal: controller.signal,
      cache: 'no-store',
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The server returned an unreadable response. Please try again.'); }
    if (!response.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be processed. Check your input and try again.');
    }
    return data;
  } catch (error) {
    if (timedOut) throw new Error('The request timed out. Please try again.');
    if (error.name === 'AbortError') throw error;
    if (error instanceof TypeError) throw new Error('Cannot reach the API. Check your connection and try again.');
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}
