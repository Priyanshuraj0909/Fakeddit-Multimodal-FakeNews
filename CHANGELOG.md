# Change log

## 2026-10-05 — Trained news detector and Groq evidence verification

- Downloaded official Fakeddit splits, removed exact ID/text leakage, sampled reproducible subsets, trained and independently evaluated the text baseline.
- Added a compact portable inference release with sklearn parity verification and honest abstention/uncertainty behavior.
- Added combined /api/detect with independent classifier and Groq browser-research results, retrieved-source validation, failure isolation and bounded requests.
- Made detection the main UI mode; added per-claim verdicts, citations, feature contributions and benchmark provenance.
- Live Groq verification requires GROQ_API_KEY in Production; model predictions work independently.

## 2026-10-05 — Fix deployed homepage failure

- Moved HTML and favicon out of frontend/public after deployment logs showed those files missing from the Python runtime.
- Preserved frontend/src module structure and updated serving paths and documentation.
- Expanded deployment checks to cover the favicon and linked assets.

## 2026-10-05 — Fakeddit modular project restructure

- Restored Fakeddit branding and reorganized API under backend/app, browser modules under frontend/src, and model tooling under ml.
- Updated imports, static URLs, tests, training output paths, CI checks and Vercel entrypoint.
- Added image/text encoder adapters, shared fusion validation, classifier configuration, and evaluation module.
- Added master workflow, phase plan, contribution guidance, environment template, container configuration, and setup/download/preprocessing/training/verification scripts.
- Preserved original notebooks and historical results. Real-data model training and explainability remain pending.

## 2026-10-04 — Existing engineering work

Optional paired inference, local encoder extraction, model contracts, upload validation and regression tests were present in the working tree before restructuring. See docs/REPAIR_REPORT.md for that implementation record.
