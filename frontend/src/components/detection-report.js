/** Render model assessment and retrieved evidence without injecting provider HTML. */
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

const labels = { supported: 'Supported by retrieved evidence', contradicted: 'Contradicted by retrieved evidence', mixed: 'Mixed evidence', insufficient_evidence: 'Insufficient evidence', not_checked: 'Verification not completed' };

export function renderDetection(report, container) {
  container.replaceChildren();
  const model = report.model_assessment;
  const modelCard = element('section', undefined, 'assessment-section');
  modelCard.append(element('h4', '1. Trained model prediction'), element('p', model.label, `assessment-verdict ${model.status}`));
  for (const [label, score] of Object.entries(model.probabilities || {})) {
    const row = element('div', undefined, 'score-row');
    row.append(element('span', label), element('strong', `${(score*100).toFixed(1)}%`));
    modelCard.append(row);
  }
  modelCard.append(element('p', model.reason || model.note, 'result-note'));
  if (model.assessed_text) modelCard.append(element('p', `Headline assessed: ${model.assessed_text}`, 'benchmark-note'));
  if (model.metrics?.test_accuracy !== undefined) {
    modelCard.append(element('p', `Held-out Fakeddit subset: ${(model.metrics.test_accuracy*100).toFixed(2)}% accuracy · ${model.metrics.rows.test.toLocaleString()} headlines. These are benchmark results, not certainty about this news.`, 'benchmark-note'));
  }
  if (model.signals?.length) {
    const detail = element('details');
    detail.append(element('summary', 'Which text features influenced the model?'));
    for (const signal of model.signals) detail.append(element('p', `${signal.term} → ${signal.direction === 'real' ? 'real-class' : 'fake-class'} pattern`, 'feature-signal'));
    detail.append(element('p', 'Feature contributions explain the classifier score; they are not evidence of factual truth.', 'benchmark-note'));
    modelCard.append(detail);
  }
  const evidence = report.verification;
  const evidenceCard = element('section', undefined, 'assessment-section');
  evidenceCard.append(element('h4', '2. News claims and source verification'), element('p', labels[evidence.verdict], `assessment-verdict ${evidence.verdict}`), element('p', evidence.summary, 'result-note'));
  for (const claim of evidence.claims) {
    const card = element('article', undefined, 'claim-card');
    card.append(element('h5', claim.statement), element('span', labels[claim.verdict], `claim-status ${claim.verdict}`), element('p', claim.explanation));
    const links = element('div', undefined, 'evidence-links');
    for (const id of claim.evidence_ids) {
      const source = evidence.sources.find(item => item.id === id);
      if (!source) continue;
      const link = element('a', `[${id}] ${source.title}`);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
      links.append(link);
    }
    card.append(links); evidenceCard.append(card);
  }
  if (evidence.sources.length) {
    const list = element('div', undefined, 'source-list');
    list.append(element('h5', 'Sources used in this assessment'));
    for (const source of evidence.sources) {
      const link = element('a', `[${source.id}] ${source.publisher}: ${source.title}`);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
      list.append(link);
    }
    evidenceCard.append(list);
  }
  if (evidence.checked_at) evidenceCard.append(element('p', `Sources checked ${new Date(evidence.checked_at).toLocaleString()}`, 'benchmark-note'));
  evidenceCard.append(element('p', evidence.note || 'No source-based factual verdict was issued.', 'benchmark-note'));
  container.append(modelCard, evidenceCard);
}
