/** Same-origin requests with bounded waits and user-readable failures. */
export function validateAnalysis(data) {
  const invalid = () => { throw new Error('The server returned an incomplete analysis. Please try again.'); };
  if (!data || typeof data.note !== 'string') invalid();
  if (data.mode === 'descriptive') {
    const counts = ['word_count', 'character_count', 'exclamation_count'];
    if (counts.some(key => !Number.isInteger(data[key]) || data[key] < 0)
      || !Number.isFinite(data.uppercase_ratio) || data.uppercase_ratio < 0 || data.uppercase_ratio > 1
      || !Array.isArray(data.phrases) || data.phrases.some(phrase => typeof phrase !== 'string')) invalid();
  } else if (data.mode === 'trained_text_baseline') {
    if (typeof data.label !== 'string' || !data.probabilities || typeof data.probabilities !== 'object'
      || Array.isArray(data.probabilities) || !Object.keys(data.probabilities).length
      || Object.values(data.probabilities).some(value => !Number.isFinite(value) || value < 0 || value > 1)) invalid();
  } else invalid();
  return data;
}

export async function requestJSON(path, { text, signal, timeout = 20000 } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    const response = await fetch(path, {
      method: text === undefined ? 'GET' : 'POST',
      ...(text === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) }),
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
