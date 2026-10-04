# Architecture

`backend/app/main.py` is the FastAPI entrypoint. It serves frontend/public/index.html and mounts frontend under /static. Request schemas live in schemas; text analysis lives in services; bounded multipart upload handling lives in api. Reserved core/models/utils directories allow future backend additions without mixing them with ML training.

`frontend/src/pages/workspace.js` controls the browser interface, importing request logic from services, state/report logic from hooks, and file processing from utils. CSS lives in components; public assets live in frontend/public. The application intentionally retains native ES modules rather than introducing a build framework solely for the directory change.

`ml/datasets` pairs local files; preprocessing decodes and extracts local CLIP features; models contains encoder adapters, validated fusion and classifier configuration; training performs independent split evaluation; evaluation computes metrics; inference loads verified artifacts. utils defines label, preprocessing, fingerprint and leakage contracts.

Text/image request → upload validation → decoded RGB image → local CLIP features → image-first concatenation → XGBoost scores → validated browser report. Missing artifacts return 503, never substitute predictions. Offline extraction and training run separately from the API.

Data and models are ignored except directory placeholders. Original notebooks/results are retained. No database, persistent upload history, OCR, video classifier or explanation engine exists.
