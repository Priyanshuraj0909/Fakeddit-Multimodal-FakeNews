# Phase 10: Deployment

Status: Vercel deployment and GitHub CI verified; Docker remains unverified. Updated 2026-10-31.

Deliverable: Vercel entrypoint, Docker configuration, GitHub CI and ignored model/data assets.

The previous release passed remote CI and public behavior checks. Verify each subsequent release after publishing; Docker has not been run locally.

Acceptance: verify the documented behavior with representative inputs, record actual results, and keep phase status honest about missing assets. See PLAN.md and docs/VERIFICATION.md.

2026-10-31: Publish via the existing GitHub origin and connected Vercel integration; verify API, frontend assets, model card and detection with scripts/check_deployment.py. Optional Redis requires installing redis in the runtime before configuring its URL. MLflow remains offline-only. See VERIFICATION.md for actual deployment results.
