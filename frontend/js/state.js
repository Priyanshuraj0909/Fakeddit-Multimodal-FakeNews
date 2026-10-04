/** One state store; file preview resources are owned by the UI controller. */
export function createStore() {
  let state = Object.freeze({ text: '', tab: 'text', mode: 'analyze', status: 'idle', report: null, error: '', uploadError: '', uploadStatus: '', media: Object.freeze({ image: null, video: null }) });
  const listeners = new Set();
  return {
    get: () => state,
    update(patch) {
      state = Object.freeze({ ...state, ...patch, ...(patch.media ? { media: Object.freeze({ ...state.media, ...patch.media }) } : {}) });
      listeners.forEach(listener => listener(state));
    },
    subscribe(listener) { listeners.add(listener); listener(state); return () => listeners.delete(listener); },
  };
}

export function buildReport(data, state, now = new Date()) {
  return {
    generated_at: now.toISOString(),
    ...data,
    attachments: Object.fromEntries(Object.entries(state.media).filter(([, media]) => media).map(([kind, media]) => [kind, { ...media.metadata, assessment: 'Local preview only; no model inference' }])),
  };
}
