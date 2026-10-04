const byId = id => document.getElementById(id);
const headline = byId('headline');
let report = null;
headline.addEventListener('input', () => { byId('count').textContent = `${headline.value.length.toLocaleString()} / 10,000`; });
byId('sample').addEventListener('click', () => {
  headline.value = 'BREAKING: You won\'t believe this shocking discovery! Read the original report before sharing.';
  headline.dispatchEvent(new Event('input'));
  headline.focus();
});
fetch('/api/health').then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(status => {
  byId('connection').textContent = status.model_available ? 'Trained text model available' : 'Text explorer online';
  if (status.model_available) {
    const option = byId('mode').options[1]; option.disabled = false; option.textContent = 'Trained text classifier';
  }
}).catch(() => { byId('connection').textContent = 'API unavailable'; });
byId('analysis-form').addEventListener('submit', async event => {
  event.preventDefault();
  byId('form-error').textContent = '';
  if (!headline.value.trim()) { byId('form-error').textContent = 'Enter a headline or article.'; return; }
  byId('submit').disabled = true;
  try {
    const response = await fetch(`/api/${byId('mode').value}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:headline.value})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please enter between 1 and 10,000 characters.');
    report = {generated_at:new Date().toISOString(), ...data};
    byId('verdict').textContent = data.mode === 'descriptive' ? 'Signals, not a truth verdict.' : data.label;
    byId('result-note').textContent = data.note;
    byId('metrics').replaceChildren();
    const metrics = data.mode === 'descriptive' ? [['Words',data.word_count],['Characters',data.character_count],['Uppercase letters',`${Math.round(data.uppercase_ratio*100)}%`],['Exclamation marks',data.exclamation_count]] : Object.entries(data.probabilities).map(([label,p]) => [label,`${(p*100).toFixed(1)}%`]);
    for (const [label,value] of metrics) {
      const metric = document.createElement('div'); metric.className = 'metric';
      const strong = document.createElement('strong'); strong.textContent = value;
      const span = document.createElement('span'); span.textContent = label;
      metric.append(strong,span); byId('metrics').append(metric);
    }
    byId('phrases').textContent = data.mode === 'descriptive' ? (data.phrases.length ? `Emphasis phrases: ${data.phrases.join(', ')}. These can appear in both accurate and inaccurate reporting.` : 'No phrases from the explorer’s small emphasis list were found. This does not establish credibility.') : 'Model probabilities describe the fitted dataset classes; they are not calibrated truth probabilities.';
    byId('empty').hidden = true; byId('result').hidden = false;
  } catch (error) { byId('form-error').textContent = error.message || 'Analysis failed. Please try again.'; }
  finally { byId('submit').disabled = false; }
});
byId('download').addEventListener('click', () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'fakeddit-analysis.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
let imageUrl = null;
byId('image-file').addEventListener('change', () => {
  const file = byId('image-file').files[0];
  const preview = byId('image-preview');
  preview.hidden = true;
  if (imageUrl) { URL.revokeObjectURL(imageUrl); imageUrl = null; }
  preview.removeAttribute('src');
  if (!file) { byId('image-info').textContent = 'PNG, JPEG, or WebP · up to 10 MB'; return; }
  if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    byId('image-info').textContent = 'Choose a PNG, JPEG, or WebP image under 10 MB.'; return;
  }
  imageUrl = URL.createObjectURL(file);
  preview.onload = () => { preview.hidden = false; byId('image-info').textContent = `${file.name} · ${preview.naturalWidth} × ${preview.naturalHeight} pixels · ${(file.size/1024).toFixed(0)} KB`; };
  preview.onerror = () => { byId('image-info').textContent = 'This file could not be decoded as an image.'; };
  preview.src = imageUrl;
});
