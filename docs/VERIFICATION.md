# Verification — 2026-10-05

The detector release passed 33 Python tests and 13 frontend tests, JavaScript syntax checks, and Git whitespace checks. One upstream Starlette/AnyIO deprecation warning remains.

Actual model training used official Fakeddit splits, deterministic subsets and exact ID/normalized-text leakage exclusion. Selected C=1 on validation; evaluated independent 15,000 test headlines: 80.6467% accuracy, 0.8031223 macro-F1. A portable safe-JSON release passed probability parity checks against sklearn on 200 test headlines. See TEXT_MODEL_RELEASE.json for hashes and provenance. This is a text subset benchmark; no multimodal accuracy was reproduced.

Python checks cover real portable inference, abstention, request validation, separate classifier/source results, unavailable credentials, timeout isolation, retrieved-source-only citations, uncited-claim downgrades, partial-article evidence, mocked Groq search/structured requests and rate limits. Frontend checks reject invalid model scores, unsafe citation URLs and missing evidence IDs; optional source context is sent without local notes or credentials.

Chromium checks passed on the local server: default detector mode, actual trained classifier → API → rendered result, benchmark provenance, explicitly mocked claim verdict/citation rendering, provider text escaping, and no desktop/mobile overflow. Existing text analysis, media previews, mocked paired inference, imports, reports, cancellation, retry and themes also passed. Screenshots were inspected. No browser JavaScript errors were reported.

Live Groq verification has not yet been tested: GROQ_API_KEY must be configured in the server environment. Mocked provider tests verify integration/error handling, not live evidence quality. Docker and real CLIP inference were not run. Remote release checks must be reported separately after publication.

Run `bash scripts/verify.sh`. Browser scripts: tests/browser/detector-smoke.js and tests/browser/workspace-smoke.js. The deployment checker now covers the trained detector, favicon and every linked frontend module in addition to homepage/API health.

## Resumed release checks — 2026-10-31

Ran `bash scripts/verify.sh`: **40 Python tests and 18 frontend tests passed**, plus JavaScript syntax and Git whitespace checks. The upstream Starlette/AnyIO deprecation warning remains.

Installed the locked Playwright dependency with npm ci. The cached test Chromium was incomplete (missing framework), so local browser checks used installed Google Chrome via FAKEDDIT_BROWSER_CHANNEL=chrome. Desktop 1440×1100 and mobile 390×844 checks passed: real local classifier/API rendering, explicitly mocked evidence and paired rendering, media/import/reset/cancellation/theme flows, and history save/reload/restore/review-update/delete/clear. No horizontal overflow or page JavaScript errors were reported. Inspected the mobile screenshot; mock evidence is labeled as a fixture and is not a live verification result.

The isolated real OCR browser check passed with FAKEDDIT_OCR_LIVE=1 and FAKEDDIT_OCR_ONLY=1: downloaded the actual CDN engine/language assets, recognized a generated English headline, edited it, and confirmed exported original text, TSV word locations and corrected submitted text. An earlier live attempt timed out; the retry succeeded. Browser OCR download availability remains dependent on the external CDNs.

Reliability and generalization JSON records were already produced by the preceding session; this continuation reviewed and documented them without rerunning the real-data evaluations or model training. Their hashes and protocols are preserved. Independent human-reviewed evidence evaluation, live Redis/MLflow services, real CLIP inference, and Docker execution remain unverified. See EVALUATION.md for pending assets and protocol limitations. GitHub CI and production deployment results will be recorded after publication.
