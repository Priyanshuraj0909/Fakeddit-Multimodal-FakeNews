/** Same-origin requests with bounded waits and user-readable failures. */
export function validateAnalysis(data) {
  const invalid = () => { throw new Error('The server returned an incomplete analysis. Please try again.'); };
  if (!data || typeof data.note !== 'string') invalid();
  if (data.mode === 'news_detection') {
    const model = data.model_assessment, evidence = data.verification;
    if (!model || !['ready', 'uncertain', 'abstained', 'unavailable'].includes(model.status)
      || typeof model.label !== 'string' || typeof model.note !== 'string') invalid();
    const scores = model.probabilities;
    if (!scores || typeof scores !== 'object' || Array.isArray(scores)) invalid();
    if (['ready', 'uncertain'].includes(model.status) && (Object.keys(scores).length !== 2
      || Object.values(scores).some(x => !Number.isFinite(x) || x < 0 || x > 1)
      || Math.abs(Object.values(scores).reduce((a,b) => a+b, 0)-1) > 0.001)) invalid();
    if (['abstained', 'unavailable'].includes(model.status) && Object.keys(scores).length) invalid();
    const verdicts = ['supported', 'contradicted', 'mixed', 'insufficient_evidence'];
    if (!evidence || !['completed', 'unavailable'].includes(evidence.status) || typeof evidence.summary !== 'string'
      || !Array.isArray(evidence.claims) || !Array.isArray(evidence.sources)
      || (evidence.status === 'unavailable' ? evidence.verdict !== 'not_checked' : !verdicts.includes(evidence.verdict))) invalid();
    const ids = new Set();
    for (const source of evidence.sources) {
      if (!Number.isInteger(source.id) || source.id < 1 || ids.has(source.id)
        || typeof source.title !== 'string' || typeof source.publisher !== 'string') invalid();
      ids.add(source.id);
      try { if (!['http:', 'https:'].includes(new URL(source.url).protocol)) invalid(); } catch { invalid(); }
    }
    for (const claim of evidence.claims) {
      if (typeof claim.statement !== 'string' || typeof claim.explanation !== 'string' || !verdicts.includes(claim.verdict)
        || !Array.isArray(claim.evidence_ids) || claim.evidence_ids.some(id => !ids.has(id))
        || (claim.verdict !== 'insufficient_evidence' && !claim.evidence_ids.length)) invalid();
    }
  } else if (data.mode === 'portable_text') {
    validateAnalysis({ mode: 'news_detection', note: data.note, model_assessment: data,
      verification: { status: 'unavailable', verdict: 'not_checked', summary: '', claims: [], sources: [] } });
  } else if (data.mode === 'descriptive') {
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

export async function requestJSON(path, { text, image, source_url, publication_date, signal, timeout = 20000 } = {}) {
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
    } else if (text !== undefined) body = JSON.stringify({ text, ...(source_url !== undefined ? { source_url } : {}), ...(publication_date !== undefined ? { publication_date } : {}) });
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
