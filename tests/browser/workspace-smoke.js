// Run with: agent-browser eval --stdin < tests/browser/workspace-smoke.js
(async () => {
  const get = id => document.getElementById(id);
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const waitFor = async (predicate, message) => {
    const end = Date.now() + 15000;
    while (!predicate()) {
      if (Date.now() > end) throw new Error(message);
      await new Promise(resolve => setTimeout(resolve, 30));
    }
  };
  const upload = (kind, file) => {
    const transfer = new DataTransfer(); transfer.items.add(file);
    get(`${kind}-file`).files = transfer.files;
    get(`${kind}-file`).dispatchEvent(new Event('change', { bubbles: true }));
  };
  const results = [];
  get('reset').click();
  get('analysis-form').requestSubmit();
  assert(get('form-error').textContent.includes('Add a headline'), 'Missing-text error not shown');
  get('sample').click(); get('analysis-form').requestSubmit();
  await waitFor(() => !get('result').hidden, 'Text report did not render');
  assert(get('metrics').children.length === 4, 'Text metrics missing');
  results.push('Text input → API → report');
  get('tab-text').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
  assert(get('tab-image').getAttribute('aria-selected') === 'true', 'Keyboard tabs failed');

  get('tab-image').click();
  upload('image', new File(['not a photo'], 'broken.png', { type: 'image/png' }));
  await waitFor(() => get('upload-error').textContent.includes('decoded'), 'Corrupt-image error missing');
  assert(get('image-attachment').hidden, 'Corrupt image shown as valid');
  const canvas = document.createElement('canvas'); canvas.width = 160; canvas.height = 90;
  const context = canvas.getContext('2d'); context.fillStyle = '#b5a0ff'; context.fillRect(0, 0, 160, 90);
  const image = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  const imageTransfer = new DataTransfer();
  imageTransfer.items.add(new File([image], 'evidence.png', { type: 'image/png' }));
  get('image-dropzone').dispatchEvent(new DragEvent('drop', { dataTransfer: imageTransfer, bubbles: true, cancelable: true }));
  await waitFor(() => !get('image-attachment').hidden, 'Valid image not previewed');
  assert(get('image-info').textContent.includes('160 × 90'), 'Image dimensions incorrect');
  assert(get('result').hidden, 'Old report survived an evidence change');
  results.push('Corrupt image rejected; valid image decoded');

  get('tab-video').click();
  upload('video', new File([new Uint8Array(50 * 1024 * 1024 + 1)], 'large.mp4', { type: 'video/mp4' }));
  await waitFor(() => get('upload-error').textContent.includes('too large'), 'Oversized-video error missing');
  upload('video', new File(['unsupported'], 'clip.mov', { type: 'video/quicktime' }));
  await waitFor(() => get('upload-error').textContent.includes('MP4 or WebM'), 'Unsupported-video error missing');
  const stream = canvas.captureStream(10);
  const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
  const chunks = [];
  recorder.ondataavailable = event => chunks.push(event.data);
  const recording = new Promise(resolve => { recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' })); });
  recorder.start();
  for (let i = 0; i < 4; i++) {
    context.fillStyle = i % 2 ? '#101218' : '#b5a0ff'; context.fillRect(0, 0, 160, 90);
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  recorder.stop();
  const video = await recording;
  stream.getTracks().forEach(track => track.stop());
  upload('video', new File([video], 'evidence.webm', { type: 'video/webm' }));
  await waitFor(() => !get('video-attachment').hidden, 'Valid video not previewed');
  assert(get('video-preview').controls, 'Video controls missing');
  assert(get('video-info').textContent.includes('160 × 90'), 'Video dimensions incorrect');
  get('analysis-form').requestSubmit();
  await waitFor(() => !get('result').hidden, 'Report with media did not render');
  assert(get('report-media').textContent.includes('Image attached') && get('report-media').textContent.includes('Video attached'), 'Report metadata missing');
  assert(get('evidence-count').textContent === '3 sources', 'Evidence count incorrect');
  results.push('WebM preview and combined report metadata');

  get('remove-video').click();
  assert(get('video-attachment').hidden && !get('video-preview').hasAttribute('src'), 'Video resource not cleared');
  get('reset').click();
  upload('text', new File(['Imported UTF-8 claim café'], 'claim.txt', { type: 'text/plain' }));
  await waitFor(() => get('headline').value.includes('café'), 'Text file import failed');
  results.push('Removal/reset and UTF-8 import');

  const originalFetch = window.fetch;
  try {
    window.fetch = async () => new Response(JSON.stringify({ mode: 'descriptive', note: 'Missing metrics' }));
    get('analysis-form').requestSubmit();
    await waitFor(() => get('form-error').textContent.includes('incomplete analysis'), 'Incomplete-response error missing');
    window.fetch = async (path, options) => path === '/api/analyze' ? new Response(JSON.stringify({ detail: 'Test service unavailable' }), { status: 503, headers: { 'Content-Type': 'application/json' } }) : originalFetch(path, options);
    get('analysis-form').requestSubmit();
    await waitFor(() => get('form-error').textContent.includes('Test service unavailable'), 'API error not rendered');
    assert(!get('submit').disabled, 'Retry button stayed disabled');
    window.fetch = (path, options) => path === '/api/analyze' ? new Promise(resolve => setTimeout(() => resolve(new Response(JSON.stringify({ mode: 'descriptive', phrases: [], note: 'Stale response' }))), 150)) : originalFetch(path, options);
    get('analysis-form').requestSubmit();
    get('headline').value = 'A newer headline'; get('headline').dispatchEvent(new Event('input'));
    await new Promise(resolve => setTimeout(resolve, 250));
    assert(get('result').hidden && !get('submit').disabled, 'Cancelled request rendered stale output');
    results.push('API failure/retry and stale-response cancellation');
  } finally { window.fetch = originalFetch; }
  const originalTheme = document.documentElement.dataset.theme;
  get('theme-toggle').click();
  assert(document.documentElement.dataset.theme !== originalTheme, 'Theme did not change');
  get('theme-toggle').click();
  get('reset').click();
  get('sample').click(); get('analysis-form').requestSubmit();
  await waitFor(() => !get('result').hidden, 'Final report did not render');
  results.push('Theme toggle');
  return { passed: results, overflow: document.documentElement.scrollWidth > innerWidth };
})()
