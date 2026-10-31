# Implementation plan

Updated 2026-10-31. Engineering availability is separate from real-model readiness.

| Phase | Status | Guide |
| --- | --- | --- |
| 00 Audit | Engineering complete | [Details](docs/phases/PHASE_00_AUDIT.md) |
| 01 Foundation | Engineering complete | [Details](docs/phases/PHASE_01_FOUNDATION.md) |
| 02 Data | Official text splits downloaded and prepared | [Details](docs/phases/PHASE_02_DATA.md) |
| 03 Text model | Evaluated text-v1 release implemented | [Details](docs/phases/PHASE_03_TEXT_MODEL.md) |
| 04 Image model | CLIP image-only pilot evaluated; full release pending | [Details](docs/phases/PHASE_04_IMAGE_MODEL.md) |
| 05 Multimodal | Small paired pilot evaluated; deployment/external validation pending | [Details](docs/phases/PHASE_05_MULTIMODAL.md) |
| 06 Backend | Detector, verification and operational tracing implemented | [Details](docs/phases/PHASE_06_BACKEND.md) |
| 07 Frontend | Detector, editable OCR and optional local history implemented | [Details](docs/phases/PHASE_07_FRONTEND.md) |
| 08 Explainability | Text contributions implemented; image attribution pending | [Details](docs/phases/PHASE_08_EXPLAINABILITY.md) |
| 09 Testing | Automated suites implemented | [Details](docs/phases/PHASE_09_TESTING.md) |
| 10 Deployment | Vercel verified; GitHub Pages workflow prepared; Docker pending | [Details](docs/phases/PHASE_10_DEPLOYMENT.md) |

Next: scale and externally validate the real paired pilot; obtain consistency-specific benchmark labels; collect independent human-reviewed evidence assessments; validate on fresh external data; exploratory unseen-group and chronological results are recorded. Calibration and observational generalization audits are recorded, while production uses the original scores. Text-v1 has real subset evaluation recorded in docs/TEXT_MODEL_RELEASE.json.
