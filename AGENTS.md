# Project contribution instructions

Work from the repository root. Keep the original notebooks and result files as research provenance. Use `backend/app` for API code, `frontend/src` for browser code, and `ml` for offline/model code. Heavy ML dependencies must remain optional for the API.

Read PLAN.md and the affected phase document before changing scope. Update documentation alongside path/API changes. Do not fabricate predictions, benchmark metrics, datasets, explainability, or completed phases. Missing artifacts must produce explicit unavailable status.

Keep train/validation/test independent; fit preprocessing on training only and select models using validation. Preserve post IDs and check feature alignment and content leakage. Do not commit datasets, weights, secrets, or local environments.

Run `bash scripts/verify.sh` after code changes. Browser verification is needed for UI behavior changes. Record checks actually run and limitations. GitHub publication follows the user's authorized task scope.
