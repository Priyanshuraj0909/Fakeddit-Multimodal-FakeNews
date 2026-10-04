import { requestJSON, validateAnalysis } from './api.js';
import { prepareMedia, readTextFile, formatSize, MEDIA_EXTENSIONS } from './media.js';
import { createStore, buildReport } from './state.js';

const byId = id => document.getElementById(id);
const store = createStore();
const kinds = ['text', 'image', 'video'];
for (const kind of ['image', 'video']) {
  byId(`${kind}-file`).accept = [kind + '/*', ...MEDIA_EXTENSIONS[kind].map(extension => '.' + extension)].join(',');
}
const uploadControllers = new Map();
const uploads = new Set();
let textImportVersion = 0;
let analysisController = null;
let renderedReport = null;
const renderedMedia = { image: null, video: null };

function message(id, text) {
  const element = byId(id);
  element.textContent = text;
  element.hidden = !text;
}

function invalidateReport() {
  analysisController?.abort();
  analysisController = null;
  store.update({ report: null, status: 'idle', error: '' });
}

function setText(text) {
  invalidateReport();
  byId('headline').value = text;
  store.update({ text });
}

function renderReport(report) {
  byId('metrics').replaceChildren();
  if (!report) return;
  byId('verdict').textContent = report.mode === 'descriptive' ? 'Signals worth exploring.' : report.label;
  byId('result-note').textContent = report.note;
  const metrics = report.mode === 'descriptive'
    ? [['Words', report.word_count], ['Characters', report.character_count], ['Uppercase letters', `${Math.round(report.uppercase_ratio * 100)}%`], ['Exclamation marks', report.exclamation_count]]
    : Object.entries(report.probabilities).map(([label, value]) => [label, `${(value * 100).toFixed(1)}%`]);
  for (const [label, value] of metrics) {
    const metric = document.createElement('div'); metric.className = 'metric';
    const strong = document.createElement('strong'); strong.textContent = value;
    const span = document.createElement('span'); span.textContent = label;
    metric.append(strong, span); byId('metrics').append(metric);
  }
  byId('phrases').textContent = report.mode === 'descriptive'
    ? (report.phrases.length ? `Emphasis phrases: ${report.phrases.join(', ')}. These can appear in accurate and inaccurate reporting.` : 'No phrases from the small emphasis list were found. This does not establish credibility.')
    : 'Probabilities describe the fitted dataset classes; they are not calibrated truth probabilities.';
  const attachments = Object.entries(report.attachments);
  byId('report-media').hidden = !attachments.length;
  byId('report-media').textContent = attachments.map(([kind, media]) => `${kind === 'image' ? 'Image' : 'Video'} attached: ${media.name}. Preview only; not assessed.`).join(' ');
  byId('report-time').textContent = `Created ${new Date(report.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function renderMedia(kind, media) {
  const preview = byId(`${kind}-preview`);
  if (kind === 'video') preview.pause();
  preview.removeAttribute('src');
  if (kind === 'video') preview.load();
  byId(`${kind}-attachment`).hidden = !media;
  if (media) {
    preview.hidden = !media.url;
    byId(`${kind}-preview-note`).hidden = Boolean(media.url);
    if (media.url) preview.src = media.url;
    byId(`${kind}-name`).textContent = media.metadata.name;
    const duration = media.metadata.duration_seconds;
    byId(`${kind}-info`).textContent = !media.url ? `${formatSize(media.metadata.size)} · ${media.metadata.preview_note}` : `${media.metadata.width} × ${media.metadata.height} px · ${formatSize(media.metadata.size)}${kind === 'video' ? ` · ${duration === null ? 'duration unavailable' : `${duration}s`}` : ''}`;
  } else {
    byId(`${kind}-name`).textContent = '';
    byId(`${kind}-info`).textContent = '';
  }
}

store.subscribe(state => {
  const video = byId('video-preview');
  if (state.tab !== 'video' && !video.paused) video.pause();
  const hasText = Boolean(state.text.trim());
  const sourceCount = Number(hasText) + Number(Boolean(state.media.image)) + Number(Boolean(state.media.video));
  byId('count').textContent = `${state.text.length.toLocaleString()} / 10,000`;
  byId('text-indicator').hidden = !hasText;
  for (const kind of kinds) {
    const selected = kind === state.tab;
    byId(`tab-${kind}`).setAttribute('aria-selected', String(selected));
    byId(`tab-${kind}`).tabIndex = selected ? 0 : -1;
    byId(`panel-${kind}`).hidden = !selected;
  }
  for (const kind of ['image', 'video']) {
    byId(`${kind}-indicator`).hidden = !state.media[kind];
    if (renderedMedia[kind] !== state.media[kind]) {
      renderMedia(kind, state.media[kind]);
      renderedMedia[kind] = state.media[kind];
    }
  }
  byId('evidence-summary').textContent = sourceCount ? `${sourceCount} evidence ${sourceCount === 1 ? 'input' : 'inputs'} in this workspace` : 'Start with a headline';
  byId('evidence-detail').textContent = sourceCount ? (hasText ? 'Text analysis with media alongside for context.' : 'Add text to run language analysis.') : 'Add images or video for context.';
  byId('evidence-count').textContent = `${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'}`;
  const loading = state.status === 'loading';
  byId('submit').disabled = loading || uploads.size > 0;
  byId('submit-label').textContent = loading ? 'Analyzing…' : 'Analyze text';
  byId('report-card').setAttribute('aria-busy', String(loading));
  byId('empty').hidden = loading || Boolean(state.report);
  byId('loading').hidden = !loading;
  byId('result').hidden = loading || !state.report;
  byId('report-status').textContent = loading ? 'PROCESSING' : state.report ? 'REPORT READY' : state.error ? 'TRY AGAIN' : 'AWAITING INPUT';
  message('form-error', state.error);
  message('upload-error', state.uploadError);
  byId('upload-status').textContent = state.uploadStatus;
  if (renderedReport !== state.report) { renderReport(state.report); renderedReport = state.report; }
});

for (const kind of kinds) {
  byId(`tab-${kind}`).addEventListener('click', () => store.update({ tab: kind }));
  byId(`tab-${kind}`).addEventListener('keydown', event => {
    const current = kinds.indexOf(kind);
    const next = { ArrowRight: (current + 1) % 3, ArrowLeft: (current + 2) % 3, Home: 0, End: 2 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    store.update({ tab: kinds[next] });
    byId(`tab-${kinds[next]}`).focus();
  });
}

byId('headline').addEventListener('input', () => {
  textImportVersion += 1;
  invalidateReport();
  store.update({ text: byId('headline').value });
});
byId('sample').addEventListener('click', () => {
  textImportVersion += 1;
  setText('BREAKING: You won\'t believe this shocking discovery! Read the original report before sharing.');
  byId('headline').focus();
});
byId('mode').addEventListener('change', () => {
  invalidateReport();
  store.update({ mode: byId('mode').value });
  byId('mode-help').textContent = byId('mode').value === 'predict' ? 'Text-only dataset classification. Media is not included in inference.' : 'Observable language patterns. No truth verdict.';
});

byId('text-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file) return;
  const version = ++textImportVersion;
  store.update({ uploadError: '' });
  try {
    const text = await readTextFile(file);
    if (version !== textImportVersion) return;
    setText(text);
    store.update({ tab: 'text', uploadStatus: `Imported ${file.name}` });
  } catch (error) { if (version === textImportVersion) store.update({ uploadError: error.message, uploadStatus: '' }); }
});

async function attachMedia(kind, files) {
  if (files.length !== 1) { store.update({ uploadError: 'Choose one file at a time for each media type.', uploadStatus: '' }); return; }
  uploadControllers.get(kind)?.abort();
  const controller = new AbortController();
  uploadControllers.set(kind, controller);
  uploads.add(kind);
  // Any evidence change cancels the in-flight report immediately.
  invalidateReport();
  store.update({ uploadError: '', uploadStatus: `Preparing ${kind} preview…` });
  try {
    const media = await prepareMedia(files[0], kind, controller.signal);
    if (controller.signal.aborted) { media.dispose(); return; }
    const previous = store.get().media[kind];
    store.update({ media: { [kind]: media }, uploadStatus: media.url ? `${kind === 'image' ? 'Image' : 'Video'} ready. Preview stays on your device.` : media.metadata.preview_note });
    previous?.dispose();
  } catch (error) {
    if (error.name !== 'AbortError') store.update({ uploadError: error.message, uploadStatus: '' });
  } finally {
    if (uploadControllers.get(kind) === controller) {
      uploads.delete(kind); uploadControllers.delete(kind);
      store.update({});
    }
  }
}

function removeMedia(kind) {
  uploadControllers.get(kind)?.abort();
  uploadControllers.delete(kind); uploads.delete(kind);
  const previous = store.get().media[kind];
  invalidateReport();
  store.update({ media: { [kind]: null }, uploadStatus: '', uploadError: '' });
  previous?.dispose();
  byId(`${kind}-file`).value = '';
}

for (const kind of ['image', 'video']) {
  byId(`${kind}-file`).addEventListener('change', event => {
    const files = Array.from(event.target.files); event.target.value = '';
    if (files.length) attachMedia(kind, files);
  });
  byId(`remove-${kind}`).addEventListener('click', () => removeMedia(kind));
  const zone = byId(`${kind}-dropzone`);
  let depth = 0;
  zone.addEventListener('dragenter', event => { event.preventDefault(); depth += 1; zone.classList.add('dragging'); });
  zone.addEventListener('dragover', event => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; });
  zone.addEventListener('dragleave', () => { depth = Math.max(0, depth - 1); if (!depth) zone.classList.remove('dragging'); });
  zone.addEventListener('drop', event => {
    event.preventDefault(); depth = 0; zone.classList.remove('dragging');
    attachMedia(kind, Array.from(event.dataTransfer.files));
  });
}
// Prevent a file dropped outside the upload targets from navigating away.
window.addEventListener('dragover', event => { if (Array.from(event.dataTransfer.types).includes('Files')) event.preventDefault(); });
window.addEventListener('drop', event => { if (Array.from(event.dataTransfer.types).includes('Files')) event.preventDefault(); });

byId('reset').addEventListener('click', () => {
  textImportVersion += 1;
  removeMedia('image'); removeMedia('video');
  setText('');
  byId('mode').value = 'analyze';
  byId('mode-help').textContent = 'Observable language patterns. No truth verdict.';
  store.update({ tab: 'text', mode: 'analyze', uploadError: '', uploadStatus: '' });
  byId('headline').focus();
});

byId('analysis-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (store.get().status === 'loading' || uploads.size) return;
  const state = store.get();
  if (!state.text.trim()) {
    store.update({ error: 'Add a headline or article to analyze. Image and video previews do not run classification.', tab: 'text' });
    byId('headline').focus(); return;
  }
  analysisController?.abort();
  const controller = new AbortController(); analysisController = controller;
  store.update({ status: 'loading', report: null, error: '' });
  try {
    const data = await requestJSON(`/api/${state.mode}`, { text: state.text, signal: controller.signal });
    if (!controller.signal.aborted) store.update({ status: 'ready', report: buildReport(validateAnalysis(data), state) });
  } catch (error) {
    if (!controller.signal.aborted && error.name !== 'AbortError') store.update({ status: 'error', error: error.message });
  } finally { if (analysisController === controller) analysisController = null; }
});

byId('download').addEventListener('click', () => {
  const report = store.get().report;
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'fakeedit-evidence-report.json';
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === 'dark';
  byId('theme-icon').textContent = dark ? '☀' : '☾';
  byId('theme-toggle').setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
  document.querySelector('meta[name="theme-color"]').content = dark ? '#101218' : '#f5f5fa';
}
try { applyTheme(localStorage.getItem('fakeedit-theme') === 'light' ? 'light' : 'dark'); }
catch { applyTheme('dark'); }
byId('theme-toggle').addEventListener('click', () => {
  const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(theme);
  try { localStorage.setItem('fakeedit-theme', theme); } catch { /* Theme still works with storage blocked. */ }
});

requestJSON('/api/health', { timeout: 10000 }).then(health => {
  if (health.status !== 'ok' || typeof health.model_available !== 'boolean') throw new Error('Invalid health response');
  byId('connection').dataset.status = 'online';
  byId('connection-text').textContent = health.model_available ? 'Text model connected' : 'Text explorer online';
  if (health.model_available) {
    const option = byId('mode').options[1]; option.disabled = false; option.textContent = 'Trained text classifier';
  }
}).catch(() => {
  byId('connection').dataset.status = 'offline';
  byId('connection-text').textContent = 'API unavailable · retry analysis';
});

window.addEventListener('pagehide', () => {
  textImportVersion += 1;
  analysisController?.abort();
  uploadControllers.forEach(controller => controller.abort());
  Object.values(store.get().media).forEach(media => media?.dispose());
  // Reset attachment state so a back-forward cache restore has no revoked previews.
  uploads.clear(); uploadControllers.clear();
  store.update({ media: { image: null, video: null }, status: 'idle', report: null, uploadStatus: '' });
});
