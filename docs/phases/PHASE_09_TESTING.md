# Phase 09: Testing

Status: Automated suites implemented. Updated 2026-10-31.

Deliverable: Python API/ML regression tests, Node frontend tests and browser smoke script.

Real text and small paired checkpoints have been exercised locally. Larger external evaluation, image–headline consistency and independent evidence quality remain pending.

Acceptance: verify the documented behavior with representative inputs, record actual results, and keep phase status honest about missing assets. See PLAN.md and docs/VERIFICATION.md.

2026-10-31: Added reliability, citation-review, lexical audit, OCR lifecycle and history tests. Browser runner covers desktop/mobile and optional real CDN-backed OCR (FAKEDDIT_OCR_LIVE=1). See VERIFICATION.md for checks actually run.

2026-10-31: Added original-input restoration, total-budget expiry, trusted-header, telemetry privacy, unseen-group and download-host tests. Three repeated real OCR runs and desktop/mobile restoration checks passed.
