// Real classifier + explicit mocked evidence rendering; live Groq calls require a server key.
(async () => {
  const get = id => document.getElementById(id);
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const waitFor = async predicate => {
    const end = Date.now()+15000;
    while (!predicate()) {
      if (Date.now() > end) throw new Error('Detector browser flow timed out');
      await new Promise(resolve => setTimeout(resolve, 30));
    }
  };
  await waitFor(() => get('connection').dataset.status === 'online');
  get('reset').click();
  assert(get('mode').value === 'detect', 'Detection is not the default mode');
  get('headline').value = 'Scientists discover a new species in the rainforest';
  get('headline').dispatchEvent(new Event('input'));
  get('analysis-form').requestSubmit();
  await waitFor(() => !get('result').hidden);
  assert(get('detection-report').textContent.includes('Trained model prediction'), 'Actual classifier report missing');
  assert(get('detection-report').textContent.includes('Held-out Fakeddit subset'), 'Model evaluation provenance missing');
  const realFetch = window.fetch;
  const baseline = await (await realFetch('/api/detect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: 'Scientists discover a new species in the rainforest' }) })).json();
  try {
    window.fetch = async (path, options) => {
      if (path !== '/api/detect') return realFetch(path, options);
      return new Response(JSON.stringify({ ...baseline, verification: {
        status: 'completed', verdict: 'contradicted', summary: 'MOCK evidence for browser rendering only', provider: 'Groq',
        claims: [{ statement: '<img src=x onerror="window.injected=true">The Moon is made of cheese', verdict: 'contradicted', explanation: 'MOCK rocky-Moon evidence', evidence_ids: [1] }],
        sources: [{ id: 1, url: 'https://science.nasa.gov/moon/', title: 'MOCK NASA source', publisher: 'science.nasa.gov' }]
      } }), { headers: { 'Content-Type': 'application/json' } });
    };
    get('headline').value = 'NASA confirms the Moon is made of cheese.';
    get('headline').dispatchEvent(new Event('input'));
    get('analysis-form').requestSubmit();
    await waitFor(() => !get('result').hidden);
    assert(get('detection-report').textContent.includes('Contradicted by retrieved evidence'), 'Claim verdict missing');
    assert(get('detection-report').querySelector('a').href === 'https://science.nasa.gov/moon/', 'Source link missing');
    assert(!get('detection-report').querySelector('img') && !window.injected, 'Provider text injected HTML');
    assert(get('metrics').hidden && get('observations').hidden, 'Language stats mixed into news verdict');
  } finally { window.fetch = realFetch; }
  return { passed: ['Default news detection mode', 'Real trained classifier → API → report', 'Benchmark provenance', 'MOCKED claim verdict and citation rendering', 'Provider text cannot inject HTML'], overflow: document.documentElement.scrollWidth > window.innerWidth };
})()
