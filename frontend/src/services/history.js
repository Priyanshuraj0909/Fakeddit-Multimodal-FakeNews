/** Explicitly saved, bounded browser history. No automatic saving or training labels. */
import { validateAnalysis } from './api.js';
const KEY = 'fakeddit-reports-v1';
const MAX_BYTES = 500000;

function valid(entry) {
  if (!entry || typeof entry.id !== 'string' || !entry.id || entry.id.length > 100 || !entry.report
      || typeof entry.report.generated_at !== 'string' || !Number.isFinite(Date.parse(entry.report.generated_at))
      || !['', 'agree', 'disagree', 'needs_review'].includes(entry.review)) return false;
  try {
    const report = entry.report;
    if (!report.context || typeof report.context !== 'object' || !report.attachments || typeof report.attachments !== 'object') return false;
    if (report.mode === 'media_inspection') return false;
    validateAnalysis(report);
    return true;
  } catch { return false; }
}

export function readHistory(storage) {
  const raw = storage.getItem(KEY);
  if (!raw) return [];
  if (raw.length > MAX_BYTES) throw new Error('Saved history is too large. Clear it to start again.');
  const items = JSON.parse(raw);
  if (!Array.isArray(items) || items.length > 20 || !items.every(valid)) throw new Error('Saved history is unreadable. Clear it to start again.');
  return items;
}

export function saveReport(storage, report, review = '', id = crypto.randomUUID()) {
  const entry = { id, report, review };
  if (!valid(entry)) throw new Error('Only a completed text assessment can be saved.');
  const entries = [entry, ...readHistory(storage).filter(item => item.id !== id)].slice(0, 20);
  const raw = JSON.stringify(entries);
  if (raw.length > MAX_BYTES) throw new Error('History is full. Delete older reports or export JSON.');
  storage.setItem(KEY, raw);
  return entries;
}

export function deleteReport(storage, id) { storage.setItem(KEY, JSON.stringify(readHistory(storage).filter(item => item.id !== id))); }
export function clearHistory(storage) { storage.removeItem(KEY); }
