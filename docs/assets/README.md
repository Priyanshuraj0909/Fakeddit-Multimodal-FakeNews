# README screenshot provenance

Captured on 2026-10-21 from the actual local FastAPI application at
http://127.0.0.1:8010 using headless Google Chrome, with a 4-second virtual-time
budget to allow native frontend modules and capability requests to finish.

- `workspace-desktop.png`: 1440 × 1200 browser viewport.
- `workspace-mobile.png`: 430 × 1100 browser viewport.

The bundled text release was available. Groq credentials were not configured for
these captures. Screenshots show the initial workspace; no predictions, evidence,
or claim reports were fabricated or injected. Capture involved no application
logic changes. These are local captures, not proof of public deployment readiness.

README verification: `bash scripts/verify.sh` passed (33 Python tests, 13 frontend
tests, JavaScript syntax checks, and diff whitespace check). Relative documentation
links and screenshot paths were checked, and the bundled release SHA-256 matched
`docs/TEXT_MODEL_RELEASE.json`. Benchmark training, Docker execution, live Groq
verification, and full GitHub Mermaid rendering were not reproduced in this update.

The public deployment check also passed on 2026-10-21 using
`SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python scripts/check_deployment.py`.
The initial attempt used a Python trust store without the needed issuer and failed
certificate validation; the successful retry used the system CA store without
disabling TLS verification. This checks public assets/API/detection, not live Groq.
