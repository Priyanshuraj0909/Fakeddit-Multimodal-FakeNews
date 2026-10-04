# Fakeddit project audit

Reviewed 2026-10-04 against the current repository. This is a code and application audit, not an independent reproduction of model accuracy.

## Real-world problem and intended purpose

Misleading posts can combine a persuasive headline with a real image used out of context. Looking only at words can miss that relationship. The research portion of this project explores text and image representations and fusion classifiers using the Fakeddit benchmark.

Fakeddit is a research dataset, rather than a live fact-checking service. Its authors provide text, metadata, and images; their benchmark comparisons use samples containing both text and images. Video is an extension of this application's interface, not an implemented Fakeddit video classifier. Dataset documentation: https://github.com/entitize/Fakeddit

The deployed Fakeddit app currently helps a user collect evidence, inspect descriptive writing signals and media metadata, and record what they checked before sharing a claim. A strong real-world workflow is: find the original source, verify dates and locations, compare independent evidence, and review any model suggestion alongside that evidence.

Example: a flood photograph paired with today's headline might depict a different year. The workspace can display the photo and let the user record the original publication. It does not automatically discover the photograph's origin or determine whether the caption is true.

## What actually works

| Capability | Current implementation | Limits |
| --- | --- | --- |
| Text input and UTF-8 import | Native frontend, FastAPI validation | 10,000 characters |
| Descriptive text analysis | Counts, capitalization, emphasis phrases | Style is not a truth verdict |
| Image/video attachment | Browser-local preview or metadata fallback | 10 MB image; 50 MB video; no server upload |
| Media-only reports | Local attachment count, size, preview status | No AI authenticity assessment |
| Verification context | User-supplied source URL, date, notes in report/export | No automated verification or persistence |
| JSON export | Analysis, attachment metadata, verification context | No raw media bytes |
| Optional text classifier | TF-IDF/logistic-regression training and inference | Requires trusted trained artifacts and dependencies |
| Multimodal research | Historical notebooks and aligned-embedding XGBoost training | Offline; not connected to the UI |
| Operational checks | Health, capabilities, unit tests, browser flow, GitHub CI | No model accuracy claim |

## Gaps fixed in this update

1. **Media-only inputs previously could not produce reports.** They now create a local inspection report without requiring dummy text or contacting the text API.
2. **Health could advertise corrupt model files as ready.** Readiness now loads trusted artifacts, checks classes/label mapping, and probes probability output before enabling the classifier. Status distinguishes missing artifacts, missing dependencies, and invalid artifacts.
3. **Evidence context was absent from exports.** Optional source URL, publication date, and verification notes now appear in reports and JSON. They remain user supplied and local.
4. **Available features were hard to distinguish from research plans.** The interface shows classifier availability, and GET /api/capabilities explicitly states which inference features exist.
5. **Documentation described old structure/format restrictions.** Architecture, verification, review, and setup records now reflect backend/ and expanded format fallback.

## Original missing parts and their prerequisites

| Missing part | Why it matters | What is required |
| --- | --- | --- |
| Original Fakeddit datasets and exact experiment inputs | Cannot reproduce results from notebooks alone | Download dataset splits from the official source; recover original preprocessing and embeddings |
| Trained production text model | Live classifier currently unavailable | Train on legitimate train/validation splits; evaluate once on independent test data; deploy trusted model and inference dependencies |
| Online image + text classification | Current uploaded images never enter an AI model | Consistent encoder/preprocessing, trained fusion model, inference service, media validation, and UI/API integration |
| Reproducible embedding extraction | New XGBoost tool starts from precomputed NPZ files | Extract configurable encoder pipeline from notebook experiments; persist post IDs, encoder version, dimensions, and failure records |
| Video intelligence | Playback does not inspect a video's content | Frame sampling, timestamps, transcription/OCR if required, aggregation model, labeled video evaluation |
| OCR and image-text relationship checking | Captions and image text may disagree | OCR/embedding models, comparison logic, and evaluated failure handling |
| Source verification and reverse-image lookup | A classifier alone cannot establish factual truth | Evidence retrieval providers, provenance/citations, verified source policies, and appropriate credentials |
| Universal format conversion | Browsers cannot decode every codec/container | A conversion service or bundled decoders with measured memory/time limits; current fallback retains metadata only |
| Image/video editing | Upload and playback are not crop, trim, or timeline editing | Dedicated editing controls and export/encoding pipeline |
| Saved history and shared reports | Current reports disappear on reload unless exported | Explicit persistence workflow; storage; authentication if private multi-user history is needed |
| Production ML evaluation | Historical 93.9% cannot be treated as current reliability | Independent held-out results, precision/recall/F1, per-class errors, leakage checks, domain-shift tests, calibration |

No synthetic model, guessed dataset, or invented accuracy was added to fill these gaps.

## Research issues still visible in historical notebooks

- Notebook 07 uses test data in early stopping and reports metrics on that same test set. Historical scores need fresh evaluation.
- Subreddit/author metadata may create source shortcuts. Evaluate author/source-disjoint splits.
- Google Drive paths, GPU assumptions, repeated definitions, and notebook state remain in the preserved experiments.
- Separate stored text/image arrays need post-ID alignment and identical encoders across splits.
- The modern training scripts improve split separation and alignment, but do not reproduce every notebook model.

## Completion order for a genuine classifier

1. Obtain official datasets and record data/label provenance; choose the task and supported languages.
2. Train and evaluate a text baseline; save model, label mapping, metrics, dependency versions, and split records.
3. Build reproducible image/text embedding extraction; record encoder and preprocessing configuration.
4. Train fusion models with validation-only selection; evaluate held-out and source-disjoint data.
5. Deploy an inference service suited to model memory and latency, then connect validated media requests.
6. Add evidence retrieval and citations; present model suggestions separately from verified evidence.
7. Extend to video only after defining a video dataset, evaluation task, and compute budget.

## Verify the current application

Run from repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q
npm run check
npm test
python -m uvicorn backend.app.main:app --reload --port 8004
```

Visit http://127.0.0.1:8004 and /docs. Test text analysis, a media-only report, an unpreviewable attachment, context fields, JSON export, reset, and theme switching.

```bash
python scripts/check_deployment.py
```

Software tests verify behavior. They do not measure real-world fake-news detection accuracy.

## Subsequent engineering repairs

The text + image API, local CLIP embedding extraction, dataset pairing, checkpoint contracts, content leakage checks, and modality dimension checks are now implemented. They still require genuine compatible artifacts before production inference is available. Read [REPAIR_REPORT.md](REPAIR_REPORT.md) and [TRAINING.md](TRAINING.md) for current behavior and exact setup. The original missing-parts table above records the audit before these repairs.


Structure updated 2026-10-05: see README.md and PLAN.md for current module locations and phase status. Dated historical findings above describe their original review context.
