# Phase 05: Multimodal

Status: Real small paired pilot evaluated; deployment and external validation pending. Updated 2026-10-31.

Deliverable: Image-first fusion, CPU XGBoost, manifest/checksum contracts and leakage checks.

Completed: Real CLIP extraction and aligned text/image/combined pilot evaluation on 600/200/200 samples. Remaining: larger external validation, independent image–headline consistency labels, and suitably provisioned deployment.

Acceptance: verify the documented behavior with representative inputs, record actual results, and keep phase status honest about missing assets. See PLAN.md and docs/VERIFICATION.md.

2026-10-31: No paired images or local CLIP snapshot are present, so multimodal release and learned image–headline consistency remain unavailable. Existing --compare supports aligned modality ablations. Optional MLflow hooks record nested metrics, encoder and split fingerprints, manifests and error IDs when configured; no real paired run is claimed.

Later 2026-10-31: Acquired a balanced 1,000-example paired pilot and a hash-verified official CLIP snapshot. Combined/text/image macro F1 0.7247/0.6995/0.6248 on identical 200 test IDs. Paired interval includes zero; no reliable image benefit established. See MULTIMODAL_PILOT_EVALUATION.json, MULTIMODAL_PILOT_COMPARISON.json and EVALUATION.md. Artifacts remain offline and ignored.
