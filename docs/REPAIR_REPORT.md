# Engineering repair report — 2026-10-04

## Findings and root causes

1. The core text + image workflow was absent: no multipart API, no encoder-backed runtime, and no mode that sent image bytes.
2. Multimodal artifacts saved only a model and a feature count. Encoder identity, preprocessing, label provenance, modality widths, and reproducibility metadata were missing.
3. A total feature-width check accepted image/text widths that changed individually while keeping the same sum.
4. Post-ID checks did not detect repeated text or identical image bytes across train/validation/test splits.
5. Image previews were conflated with future image inference in some documentation; legacy scores could be mistaken for confidence.
6. Per-request text predictions were not validated even though the readiness probe was.
7. The text-model dropdown had a malformed closing tag, so the browser never created its option; capability initialization then incorrectly reported the API offline.
8. No actual data, production checkpoints, database models, history, or feedback implementation was found. Missing model assets are an explicit prerequisite, not an installation error to conceal.

## Implemented repairs

- Added shared image decoding with byte/pixel limits and EXIF/RGB/first-frame preprocessing.
- Added bounded multipart API with proper input/error statuses, thread-pooled CPU work, and explicit missing-model behavior.
- Added local-only CLIP encoding shared by extraction and inference; checkpoint checksum, snapshot fingerprint, package version and dimension checks.
- Added pairing/extraction CLIs with retained IDs, image hashes, missing/corrupt/ambiguous sample records, and output preservation.
- Added strict split manifests, content leakage checks, individual modality checks, L2 checks, macro-F1/per-class metrics, confusion matrices, error records, and optional ablations.
- Added frontend model mode, multipart requests, score-schema validation, host upload limits, cancellation, accurate privacy statements, and explicit image assessment in exports.
- Added focused tests; preserved the existing FastAPI/native JS stack, UI, media-only reports, and video playback scope.

## Changed files by responsibility

- API/runtime: `backend/app/main.py`, `backend/app/api/uploads.py`, `ml/preprocessing/image_input.py`, `ml/inference/multimodal.py`.
- ML: `ml/contracts.py`, `clip_encoder.py`, `prepare_pairs.py`, `extract_embeddings.py`, `train_multimodal.py`, `train_text.py`.
- UI: `frontend/index.html`, `frontend/src/services/api.js`, `app.js`, `media.js`, `state.js`.
- Dependencies: `requirements-app.txt`, `requirements-multimodal.txt`, `pyproject.toml`.
- Tests: `tests/test_project.py`, `tests/test_multimodal.py`, `tests/frontend/api.test.js`, `tests/browser/workspace-smoke.js`.
- Guides: README, architecture, audit, backend guide, verification, this report, and TRAINING.md.

## Verification

Executed application/test dependency installation and pip check; Python module compilation; Python regressions; JavaScript syntax checks and Node tests; local Uvicorn startup; deployment-check script against local server; and Chromium browser smoke flow.

- Python: 23 tests passed. One upstream Starlette/AnyIO deprecation warning remains.
- Frontend: 10 tests passed; syntax checks passed.
- Small synthetic XGBoost training and image-only/text-only comparisons passed.
- Browser: text API/report, missing-checkpoint error, mocked text + image multipart/report flow, media previews/fallback, media-only reports, notes, cancellation, reset, themes.
- No production frontend build exists: the browser serves native ES modules.

Browser checks caught a missing new mode option and a pre-existing malformed text-model option tag that made capability status falsely offline. Both were fixed; the smoke script now waits for online capability status and asserts all three modes before testing inference. Full checkpoint inference was not run: no real encoder/model is supplied and heavyweight dependencies/downloads were deliberately not launched.

## Run locally

From repository root, Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-app.txt
python -m uvicorn backend.app.main:app --reload --port 8005
```

Open http://127.0.0.1:8005 and /docs. To check software:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
npm run check
npm test
python scripts/check_deployment.py http://127.0.0.1:8005
```

Node 20+ is required. On macOS, install libomp for XGBoost. Follow [TRAINING.md](TRAINING.md) for exact real-data preparation, extraction, evaluation, label provenance, and inference steps.

## Remaining prerequisites and limitations

Real production inference remains unavailable until legitimate data, verified class mappings, a matching local CLIP snapshot, and evaluated checkpoints are provided. Existing Colab results/notebooks were preserved; their leakage and environment issues remain documented. Near-duplicate detection, calibrated uncertainty/abstention, domain-shift evaluation, video AI, OCR and source retrieval are not implemented. Database history/feedback were absent and were not introduced as unrelated features.


Structure updated 2026-10-05: see README.md and PLAN.md for current module locations and phase status. Dated historical findings above describe their original review context.
