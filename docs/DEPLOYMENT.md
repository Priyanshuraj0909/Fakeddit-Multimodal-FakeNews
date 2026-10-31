# Deployment

Local: `python -m uvicorn backend.app.main:app --reload`. Container: `docker compose up --build`; serves port 8000 and mounts models read-only. The container installs lightweight app dependencies, so trained inference requires an image extended with the matching training/multimodal dependency group. Docker execution has not been verified locally.

Vercel: pyproject.toml declares backend.app.main:app and vercel.json targets backend/app/main.py. Static frontend files are served by FastAPI. Datasets, notebooks, results and tests are excluded from the function bundle. Large CLIP inference should use appropriately provisioned compute; the web deployment bundles the evaluated portable text baseline.

GitHub Actions runs Python and native frontend checks. Existing hosting documentation recorded https://fakeddit-multimodal-fakenews.vercel.app as the connected domain; verify its current release after publication using scripts/check_deployment.py. A Git push is not proof of a successful deployment. No deployment settings or access policies are changed by the restructure.

Never commit .env, model weights or datasets. .env.example documents optional paths. Public health means the server is available; inspect /api/capabilities for actual classifier readiness.

## Frontend packaging repair — 2026-10-05

The production restructure exposed FileNotFoundError for frontend/public/index.html and favicon.svg, despite healthy API responses. These files now live directly under frontend, alongside the src directory. The application serves frontend/index.html and /static/favicon.svg. This avoids the deployment's special handling of public directories. Production validation must check homepage, favicon and module assets as well as API health.

Text-v1 is bundled under backend/app/models/releases; heavy dependencies are unnecessary for that classifier. Configure GROQ_API_KEY in Production and redeploy to enable browser-based source research. Do not expose it in frontend code. The combined route allows 60 seconds of Vercel runtime and a 50-second verification deadline. See VERIFICATION_SETUP.md.

## Review tools and monitoring — 2026-10-31

Screenshot OCR downloads pinned Tesseract.js 6.0.1/core assets and English language data on demand. Images are processed in the browser; the CDN receives asset requests. Users can edit extracted text before submitting it to the API. JSON exports retain original text and TSV word locations, plus submitted corrections. History saves reports, source details, notes and reviews in localStorage only on request (20 reports, bounded serialized size). It does not provide shared accounts, PostgreSQL storage, or reviewed training labels.

Every API response includes x-request-id. The fakeddit.requests Python logger emits request IDs, route templates, method, status and duration at INFO level; configure server log collection to retain these events. Submitted content, query strings, IPs and credentials are excluded. This is structured logging, not an OpenTelemetry rollout or a hosted monitoring dashboard.

Research defaults to per-process limits. For a multi-instance deployment, configure FAKEDDIT_REDIS_URL with a private Redis URL. The lightweight Redis client is included in requirements-app.txt; MLflow belongs in the offline environment. Redis uses atomic increment/expiry fixed windows; outages or a missing client deny research while preserving model results. The isolated real Redis integration check validates two-instance limits, concurrent atomic totals, expiry and outage behavior. Production Redis connectivity and a deployed load test remain unverified. Production Redis was not configured by this change.

## Reliability hardening — 2026-10-31

OCR language data now uses the pinned maintained @tesseract.js-data/eng@1.0.0/4.0.0_best_int asset on jsDelivr, replacing the deprecated projectnaptha endpoint. Three consecutive real-browser OCR runs passed, including corrected exports and word locations. History stores original submitted text and mode in explicitly saved/exported reports. Reopening restores text, mode, source URL, date and notes; media files must be reattached. Older reports disclose incomplete original input instead of reconstructing an article from a headline.

Research limits now enforce both five requests per client per minute and a total of 100 requests per hour by default. Override the total with FAKEDDIT_RESEARCH_TOTAL_MAX. With Redis both limits are checked and incremented atomically, using fixed windows. Without Redis both are process-local sliding windows; this is not a deployment-wide spend cap. On Vercel, client identity uses only the platform-overwritten x-vercel-forwarded-for header; other hosts use the direct ASGI client identity and ignore forwarded headers. Production quotas should also be bounded at the provider/account level.

The dedicated fakeddit.requests logger now installs an INFO stream handler, emitting correlated request and verification outcome records with status/reason and elapsed time. Submitted text, credentials, IPs and source URLs stay out of these records. Configure your hosting log retention/alerts separately; no hosted monitoring service is claimed.

Run `.venv/bin/python scripts/check_shared_quota.py` with local redis-server and the Redis client installed for the isolated optional integration check. It creates a temporary Unix-socket Redis process, makes no provider calls, and shuts it down after testing. Run `scripts/check_deployment.py --require-verification` after setting GROQ_API_KEY to require an actual live research response; this measures connectivity, not evidence correctness.

The 2.2.0 deployment includes Redis in both lightweight dependency manifests. Vercel excludes root models/** as well as data/** and local environments, preserving the intentionally versioned backend/app/models/releases text artifact. The 605 MB offline CLIP snapshot and research classifiers are not deployed.

## Release 2.3: GitHub Pages and OpenTelemetry

`python scripts/build_pages.py --output artifacts/github-pages` packages the existing frontend under a repository-prefix-safe URL, with a public HTTPS API origin in HTML metadata. The default backend is https://fakeddit-multimodal-fakenews.vercel.app . GitHub Pages serves the browser workspace; FastAPI, Groq credentials and model inference remain on Vercel. No separate simulated backend is introduced.

The Publish GitHub Pages workflow runs after successful Verify project CI on a push to main in this repository, or on explicit workflow dispatch. It checks out the verified SHA, uploads only packaged browser files, and deploys through actions/deploy-pages. Pull-request/fork workflow results cannot trigger publication. GitHub Pages must be enabled with build_type=workflow in the repository settings. The intended public URL is https://priyanshuraj0909.github.io/Fakeddit-Multimodal-FakeNews/ . Actual publication is recorded in VERIFICATION.md after deployment.

FastAPI allows the exact origin https://priyanshuraj0909.github.io for GET/HEAD/POST with Content-Type, without cookies/credentials or wildcard origins. FAKEDDIT_CORS_ORIGINS can override this comma-separated allowlist. CORS is a browser access policy, not API authentication. x-request-id and x-trace-id are exposed to the browser.

Manual OpenTelemetry SDK tracing is included in the lightweight runtime. FAKEDDIT_TRACE_EXPORTER defaults to console, FAKEDDIT_TRACE_SAMPLE_RATIO to 0.1. Set exporter=none to disable. Console spans are emitted synchronously for sampled traces so the serverless response does not depend on a background export flush. Child spans cover model.classify, research.quota, verification, provider.search and provider.assess. Correlated metadata logs cover every request. No submitted text, URL or exception message is added to spans; only allowlisted operational attributes are recorded.

For remote OTLP/HTTP export, install requirements-telemetry.txt and set exporter=otlp, OTEL_EXPORTER_OTLP_ENDPOINT and optional OTEL_EXPORTER_OTLP_HEADERS in the server environment. Keep collector credentials out of Git/browser files. The collector is not automatically provisioned or claimed operational. Batched remote export may need lifecycle/flush tuning for a serverless host. Missing exporter dependencies or endpoint produce explicit disabled configuration status in /api/capabilities instead of a false readiness claim.
