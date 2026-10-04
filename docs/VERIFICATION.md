# Verification — 2026-10-05

The detector release passed 33 Python tests and 13 frontend tests, JavaScript syntax checks, and Git whitespace checks. One upstream Starlette/AnyIO deprecation warning remains.

Actual model training used official Fakeddit splits, deterministic subsets and exact ID/normalized-text leakage exclusion. Selected C=1 on validation; evaluated independent 15,000 test headlines: 80.6467% accuracy, 0.8031223 macro-F1. A portable safe-JSON release passed probability parity checks against sklearn on 200 test headlines. See TEXT_MODEL_RELEASE.json for hashes and provenance. This is a text subset benchmark; no multimodal accuracy was reproduced.

Python checks cover real portable inference, abstention, request validation, separate classifier/source results, unavailable credentials, timeout isolation, retrieved-source-only citations, uncited-claim downgrades, partial-article evidence, mocked Groq search/structured requests and rate limits. Frontend checks reject invalid model scores, unsafe citation URLs and missing evidence IDs; optional source context is sent without local notes or credentials.

Chromium checks passed on the local server: default detector mode, actual trained classifier → API → rendered result, benchmark provenance, explicitly mocked claim verdict/citation rendering, provider text escaping, and no desktop/mobile overflow. Existing text analysis, media previews, mocked paired inference, imports, reports, cancellation, retry and themes also passed. Screenshots were inspected. No browser JavaScript errors were reported.

Live Groq verification has not yet been tested: GROQ_API_KEY must be configured in the server environment. Mocked provider tests verify integration/error handling, not live evidence quality. Docker and real CLIP inference were not run. Remote release checks must be reported separately after publication.

Run `bash scripts/verify.sh`. Browser scripts: tests/browser/detector-smoke.js and tests/browser/workspace-smoke.js. The deployment checker now covers the trained detector, favicon and every linked frontend module in addition to homepage/API health.
