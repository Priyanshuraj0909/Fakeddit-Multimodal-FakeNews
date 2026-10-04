# Verification — 2026-10-05

The restructured project passed 23 Python regressions and 10 frontend tests, JavaScript syntax checks, and Git whitespace checks. One upstream Starlette/AnyIO deprecation warning remains.

A local Uvicorn server using backend.app.main:app loaded the Fakeddit UI in Chromium with the new static paths. Browser checks passed: real text input/API/report, missing-checkpoint errors, explicitly mocked paired inference, image fallback/decoding, WebM previews, report metadata, media-only reports, notes, UTF-8 imports, reset, cancellation, errors/retry and themes. No browser errors or horizontal overflow were reported. A desktop screenshot was inspected.

Real-model inference and benchmark accuracy were not verified: datasets, encoder weights and trained checkpoints are absent. Docker was not run. Remote publication and deployment status should be checked separately from local tests. The historical 93.9% figure is not a reproduced result of this application.

Run `bash scripts/verify.sh`; start the server and run `npx --yes agent-browser --session fakeddit open http://127.0.0.1:8000`, then `npx --yes agent-browser --session fakeddit eval --stdin < tests/browser/workspace-smoke.js`. Deployment checks use `python scripts/check_deployment.py URL`.
