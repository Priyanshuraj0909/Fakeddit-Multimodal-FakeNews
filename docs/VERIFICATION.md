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

### Publication of e22c951

Pushed feature release e22c951 to Priyanshuraj0909/Fakeddit-Multimodal-FakeNews on main. Vercel reported success in the king-09/fakeddit-multimodal-fakenews project: https://vercel.com/king-09/fakeddit-multimodal-fakenews/F8c1vxpSTC1FnRsuHEafzKcJwgi9 . GitHub's Verify public deployment workflow passed: https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41189128158 .

Ran the updated scripts/check_deployment.py against https://fakeddit-multimodal-fakenews.vercel.app : passed homepage, GET/HEAD, frontend assets including OCR/history modules, model-card contract, API health/capabilities, descriptive analysis and actual trained detection. Host Python lacked a complete trust store; the check used the installed certifi CA bundle via SSL_CERT_FILE, retaining certificate verification.

Verified the recorded reliability model hash and all prepared split hashes against current local artifacts; the generalization audit references those same splits. No training or real-data evaluation was rerun.

A final combined desktop/mobile + live OCR invocation again passed both viewport workflows but timed out at OCR. The isolated real OCR test passed including corrected export and word locations. Record this as intermittent initialization/download behavior under the current browser/network environment, not a consistently passing combined OCR run. Cancellation and timeout produce explicit UI errors; CDN availability is required. Live Redis/MLflow services and independently reviewed evidence support remain unverified.

The feature release's Verify project CI job completed successfully, including Python tests, JavaScript checks, frontend tests, locked dependency installation, and Chromium desktop/mobile browser checks: https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41189111349 . CI does not enable the optional live OCR download test.

## Reliability and research release 2.2.0 — 2026-10-31

Ran `bash scripts/verify.sh` after the reliability changes: 46 Python tests and 19 frontend tests passed, plus JavaScript syntax and whitespace checks. The upstream Starlette/AnyIO deprecation warning remains. New checks cover original-input restoration/legacy behavior, total quota expiry, platform-header trust, correlated telemetry without submitted content, unseen-group filters and constrained pilot download hosts/IDs, and unlabeled review worksheets.

Installed the lightweight Redis client and ran `scripts/check_shared_quota.py` against a real isolated Unix-socket Redis instance: two-instance per-client limits, concurrent total-budget enforcement, expiry and outage denial passed, with zero provider calls. Production Redis remains a separate configuration/integration requirement.

Ran desktop 1440×1100 and mobile 390×844 Chrome checks including full text/mode/source/date/notes restoration, report reviews and deletion, classifier/API rendering, explicit mocked evidence/paired rendering, import/media/cancellation/theme flows. Both passed with no horizontal overflow or page errors. Ran three consecutive real OCR browser flows with the maintained language asset; all passed extraction, correction and exported original text/TSV word locations. A later desktop/mobile regression pass also passed. Browser screenshots remain in ignored artifacts/browser.

Executed `scripts/evaluate_shift.py` on actual official local split data: hash-verified frozen release evaluated on unseen authors/domains; a fresh pre-2018 model fitted/selected on earlier train/validation only and scored on later test examples. Recorded 56.40% chronological test accuracy / 0.5535 macro F1 and detailed subgroup metrics in TEXT_SHIFT_EVALUATION.json. This exploratory result does not replace production or establish performance on new external data.

Executed bounded real image acquisition (600/200/200 balanced paired rows, exact content/ID checks), downloaded the pinned official CLIP snapshot with published LFS hash verification, converted tensor-only weights to safetensors, and ran real CPU extraction and all three modality training/evaluations. Recorded metrics, class recall, error IDs, artifact hashes, packages, 55.49 ms warmed median loaded-pipeline latency (five rows), and 958,988,288-byte process peak RSS in MULTIMODAL_PILOT_EVALUATION.json. Four-thread initialization initially faulted natively; the one-thread complete run passed, and local CLIP now defaults to one thread. No weight, raw image, embedding or dataset is committed.

Executed `scripts/compare_paired_predictions.py`: reproduced fixed text-only metrics and recorded paired uncertainty. Combined minus text macro-F1 +0.0251 has a 95% paired-bootstrap interval [-0.0300, 0.0801], McNemar p=0.4731. No reliable image benefit or production image readiness is asserted.

Independent human-reviewed evidence quality, labeled NewsCLIPpings/VisualNews consistency evaluation, production Redis/MLflow services and Docker remain pending. The live production API still reported missing_api_key during this work; credentials must be configured and a live research check must complete before claiming source verification works. Publication checks for this release follow separately below.

A real local API integration check also passed with the offline pilot and encoder paths explicitly supplied only to that test process: /api/capabilities reported the paired model ready, and an actual multipart /api/predict/multimodal request returned HTTP 200, trained_multimodal and image_assessed=true with an x-request-id. Production settings were not changed by this local check. Verified the paired comparison's source-report hash, all extracted split hashes and the combined classifier hash against recorded artifacts before publication.

### Published 2.2.0 release

Feature commit 30cccde4616921101ed7498f56acf90b16f75a26 was pushed to main. Vercel reported successful deployment in king-09/fakeddit-multimodal-fakenews: https://vercel.com/king-09/fakeddit-multimodal-fakenews/EbDbSB5jNSNVRN4mrQ3xTQFU82Ar . Both GitHub workflows passed: Verify project https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41190904412 and Verify public deployment https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41190939273 .

Ran the updated public deployment checker successfully against https://fakeddit-multimodal-fakenews.vercel.app : application version 2.2.0, public homepage/HEAD, frontend assets, model card, health, capabilities, descriptive analysis and actual trained detection all passed. Separately confirmed that the live model card contains the 6,406-row chronological evaluation and 600/200/200 offline pilot with the 2,000-resample comparison; the deployed OCR module uses the maintained pinned language path. The text-v1 runtime remained ready.

Production still reported verification unavailable/missing_api_key and process_local quotas (five/client/minute, 100 total/hour). Source verification and deployment-wide Redis quotas are not claimed enabled. The user indicated they would configure the key/connect Vercel; no secret was available to this session. GitHub's unauthenticated API reached its rate limit during checks, so final CI status was verified using the repository's existing GitHub authentication in process memory, without printing or saving credentials.

## Tracing and GitHub Pages release 2.3.0 — 2026-10-31

Ran bash scripts/verify.sh: 56 Python tests and 20 frontend tests passed, together with JavaScript syntax and Git whitespace checks. The upstream Starlette/AnyIO deprecation warning remains. Real OpenTelemetry SDK tests use an in-memory exporter to verify request/child span parentage, threadpool context, trace headers and exclusion of submitted news, source URLs, query strings and exception messages. Additional checks cover approved-origin CORS, Pages packaging/API routing, verification preflight/transport failures, null correctness metrics without reviewed claims, and independent-review provenance.

Ran FAKEDDIT_BROWSER_CHANNEL=chrome npm run test:browser. The normal workspace and packaged Pages interface passed desktop/mobile checks. Pages checks serve the package at its intended repository URL prefix and explicitly forward API requests through a test transport to the actual local classifier, asserting the backend's approved-origin CORS response. Actual source-provider/paired render fixtures remain explicitly mocked; no live evidence-quality result is inferred. Saved input/context restoration, media/import/cancellation/theme flows and no-overflow checks passed.

Enabled Actions-based GitHub Pages for the existing public repository using its existing authenticated GitHub access. GitHub returned the intended URL https://priyanshuraj0909.github.io/Fakeddit-Multimodal-FakeNews/ with build_type=workflow. This configuration alone does not prove publication; actual deployment results will be recorded below. The package contains browser assets only and calls the Vercel FastAPI service. No credentials, datasets or model weights are packaged.

The runtime includes sampled manual console tracing; remote OTLP export is optional and no remote collector is claimed configured. The verification batch/review workflow captures actual service outcomes and requires supplied independent judgments; no reviewed 100-claim corpus, re-ranking model, quantized model or C2PA feature is claimed completed by this release. An initial read-only production readiness request timed out; the post-publication check will report actual service configuration.

### Published 2.3.0 release

Feature commit d9fd009a28c00958d752eb569a891cf5f41d8cab was pushed to main. Verify project passed: https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41218547150 . The CI-gated Publish GitHub Pages workflow passed: https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41218658330 . Vercel reported successful deployment: https://vercel.com/king-09/fakeddit-multimodal-fakenews/8YdcUmzHPnsbQTZH8nAAfaFcLNgo ; its public deployment workflow passed: https://github.com/Priyanshuraj0909/Fakeddit-Multimodal-FakeNews/actions/runs/41218572226 . Skipped public-check workflows for non-production deployment events are not failures.

Ran scripts/check_deployment.py against the public Vercel app: version 2.3.0, homepage/HEAD, frontend assets, model card, API health/capabilities, descriptive analysis and actual trained detection passed. Production capabilities reported manual console tracing enabled with sample ratio 0.1. Separately checked a valid x-trace-id response header and the exact GitHub Pages Access-Control-Allow-Origin value. This verifies runtime trace configuration/context, not a separately hosted collector or dashboard.

Ran a real Chrome mobile check at https://priyanshuraj0909.github.io/Fakeddit-Multimodal-FakeNews/ with no mocked requests. Public Pages HTML/assets loaded; the browser connected cross-origin to the real Vercel API, rendered the actual classifier result, saved/reloaded/restored the original report input, and showed no horizontal overflow or page JavaScript errors. The screenshot is in ignored artifacts/browser/github-pages-live.png.

Production still reported verification unavailable/missing_api_key and process_local quotas. Groq credentials, production Redis, a remote OTLP collector and independent reviewer judgments were not provisioned or fabricated. The verification capture/evaluation tooling is implemented; independently reviewed evidence correctness remains unmeasured. The deployed classifier remains text-v1, and the prior offline research results are unchanged.

## Accuracy release text-v2 / application 2.4.0 — 2026-10-31

Executed the fixed candidate search in scripts/improve_text_accuracy.py on real local official data. Compared word-only, word/character, NB-weighted and class-weighted Logistic Regression, with C=0.3,1,3, using validation macro F1 only. Expanded the winning architecture's training to all 502,605 eligible official rows. Validation and test CSV hashes remain byte-identical to text-v1. The selected balanced word/character model (C=1, 100,000 word and 100,000 character features) and its hash were frozen before final test scoring. Training/vectorizer/NB-ratio fitting used training only; source/author metadata was used only for audits/split masks.

Actual historical test results: accuracy 80.6467% → 83.3533%, macro F1 0.8031223 → 0.8323142. Net +406 correct among the same 15,000 rows. Paired-bootstrap 95% accuracy-difference interval [+2.2265,+3.20] points; exact McNemar p=5.79e-27. Real-class recall improved 8.07 points; fake/misleading recall declined 1.63 points. Prespecified promotion gates, including a maximum two-point class-recall decline and temporal noninferiority, all passed. Equal-data chronological refits scored 56.87%/0.5559 for the word baseline and 58.98%/0.5871 for the new architecture, still a substantial weakness. These are exploratory existing-data measurements, not new external factual accuracy.

Exported backend/app/models/releases/text-v2.json.gz (3,310,051 bytes), SHA256 d7c70eb25c2b59dadc2786f1f96abc6b9eaf46f7e168a31e0feb3065e15f91f6. On 502 validation/whitespace inputs, 456 usable outputs matched sklearn with maximum probability difference 9.99e-16; 46 policy abstentions were explicitly excluded from score parity. Full checkpoints/datasets remain ignored. Text-v1 artifact/results are preserved. The active model card identifies old calibration/shift reports as text-v1 and exposes the separate text-v2 comparison.

Ran bash scripts/verify.sh after implementation: 65 Python tests and 20 frontend tests passed, with syntax/whitespace checks and the existing Starlette/AnyIO deprecation warning. Synthetic parity checks cover character padding, short words, Unicode, whitespace, branch normalization, NB-weighted candidates and historical v1 loading. These fixtures are not research benchmarks. A subsequent active-manifest consistency regression check was added and its final count is recorded below.

Ran FAKEDDIT_BROWSER_CHANNEL=chrome npm run test:browser: normal workspace and packaged Pages interface passed desktop/mobile classifier rendering, benchmark provenance, explicit mocked evidence/paired rendering, media/import/cancellation/theme flows and saved-input restoration, with no overflow or page errors. Pages package calls the real local text-v2 classifier through an explicit test transport proxy; actual live hosting checks follow publication separately. No transformer fine-tuning, independent human-reviewed corpus, live Groq quality evaluation or Docker validation is claimed.

Final local verification: 66 Python tests and 20 frontend tests passed, including the active manifest/artifact/hash/history consistency check. The versioned compact artifact and its public manifest agree on text-v2, training rows and benchmark metrics. Deployment checks are recorded after publication below.
