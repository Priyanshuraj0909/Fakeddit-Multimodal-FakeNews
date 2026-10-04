# Change log

## 2026-10-05 — Fakeddit modular project restructure

- Restored Fakeddit branding and reorganized API under backend/app, browser modules under frontend/src, and model tooling under ml.
- Updated imports, static URLs, tests, training output paths, CI checks and Vercel entrypoint.
- Added image/text encoder adapters, shared fusion validation, classifier configuration, and evaluation module.
- Added master workflow, phase plan, contribution guidance, environment template, container configuration, and setup/download/preprocessing/training/verification scripts.
- Preserved original notebooks and historical results. Real-data model training and explainability remain pending.

## 2026-10-04 — Existing engineering work

Optional paired inference, local encoder extraction, model contracts, upload validation and regression tests were present in the working tree before restructuring. See docs/REPAIR_REPORT.md for that implementation record.
