/** One state store; file preview resources are owned by the UI controller. */
export function createStore() {
  let state = Object.freeze({ text: '', tab: 'text', mode: 'detect', context: Object.freeze({ source_url: '', publication_date: '', verification_notes: '' }), status: 'idle', report: null, error: '', uploadError: '', uploadStatus: '', media: Object.freeze({ image: null, video: null }) });
  const listeners = new Set();
  return {
    get: () => state,
    update(patch) {
      state = Object.freeze({ ...state, ...patch, ...(patch.context ? { context: Object.freeze({ ...state.context, ...patch.context }) } : {}), ...(patch.media ? { media: Object.freeze({ ...state.media, ...patch.media }) } : {}) });
      listeners.forEach(listener => listener(state));
    },
    subscribe(listener) { listeners.add(listener); listener(state); return () => listeners.delete(listener); },
  };
}

export function buildReport(data, state, now = new Date()) {
  return {
    generated_at: now.toISOString(),
    context: { ...state.context },
    ...data,
    attachments: Object.fromEntries(Object.entries(state.media).filter(([, media]) => media).map(([kind, media]) => [kind, { ...media.metadata, assessment: data.mode === 'trained_multimodal' && kind === 'image' ? 'Included in text-and-image model assessment' : 'Local preview only; no model inference' }])),
  };
}

/** A local inspection report never implies media classification. */
export function inspectMedia(state) {
  const media = Object.values(state.media).filter(Boolean);
  if (!media.length) throw new Error('Add text, an image, or a video to create a report.');
  return {
    mode: 'media_inspection',
    attachment_count: media.length,
    preview_count: media.filter(item => item.metadata.preview_available === true).length,
    total_bytes: media.reduce((total, item) => total + item.metadata.size, 0),
    note: 'Local media inspection only. File details and preview availability do not establish authenticity or factual truth.',
  };
}
