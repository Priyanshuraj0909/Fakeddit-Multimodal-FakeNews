# Implementation plan

Updated 2026-10-05. Engineering availability is separate from real-model readiness.

| Phase | Status | Guide |
| --- | --- | --- |
| 00 Audit | Engineering complete | [Details](docs/phases/PHASE_00_AUDIT.md) |
| 01 Foundation | Engineering complete | [Details](docs/phases/PHASE_01_FOUNDATION.md) |
| 02 Data | Tools implemented; real-data pending | [Details](docs/phases/PHASE_02_DATA.md) |
| 03 Text model | Pipeline implemented; real training pending | [Details](docs/phases/PHASE_03_TEXT_MODEL.md) |
| 04 Image model | Encoder adapter implemented; standalone evaluation pending | [Details](docs/phases/PHASE_04_IMAGE_MODEL.md) |
| 05 Multimodal | Pipeline implemented; real training pending | [Details](docs/phases/PHASE_05_MULTIMODAL.md) |
| 06 Backend | Engineering complete; classifier assets pending | [Details](docs/phases/PHASE_06_BACKEND.md) |
| 07 Frontend | Engineering complete | [Details](docs/phases/PHASE_07_FRONTEND.md) |
| 08 Explainability | Planned | [Details](docs/phases/PHASE_08_EXPLAINABILITY.md) |
| 09 Testing | Automated suites implemented | [Details](docs/phases/PHASE_09_TESTING.md) |
| 10 Deployment | Configuration implemented; release verification pending | [Details](docs/phases/PHASE_10_DEPLOYMENT.md) |

Next: obtain and validate Fakeddit splits and image assets, install a matching local CLIP snapshot, train/evaluate, then implement explanation methods and verify a model-backed release.
