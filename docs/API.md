# API

Start `python -m uvicorn backend.app.main:app --reload` from the root. Interactive schemas are available at /docs.

| Method | Path | Contract |
| --- | --- | --- |
| GET/HEAD | /api/health | Service health and validated text-model readiness |
| GET | /api/capabilities | Available classifiers, upload limits and unsupported tasks |
| GET | /api/model-card | Recorded text-v1 metrics, artifact hash, dataset, runtime readiness, optional reliability experiment; 503 if release provenance is missing |
| POST | /api/detect | JSON text, optional source_url/publication_date; separate model assessment and Groq source verification |
| POST | /api/analyze | JSON text; descriptive language indicators |
| POST | /api/predict | JSON text; installed text classifier |
| POST | /api/predict/multimodal | Multipart text + image; installed paired classifier |

Text is required, trimmed and limited to 10,000 characters. Invalid JSON/schema input returns 422. Multipart images are decoded with byte/pixel limits; unsupported images return 415 and oversized requests return 413. Local paired uploads allow 10 MiB; the Vercel environment sets a lower 4 MiB file limit. Missing or incompatible model assets return 503.

Text predictions expose label, probabilities and uncalibrated_model_scores; multimodal predictions expose label, scores, task, label_source and image_assessed. These are dataset-class assessments, not verified truth. OpenAPI from the running application is authoritative for response details. No API authentication or server-side report persistence is implemented. The browser offers explicit local report saving. Responses include an x-request-id header.

/api/detect returns mode=news_detection, model_assessment and verification. Model status is ready, uncertain, abstained or unavailable. Verification status is completed or unavailable; verdicts are supported, contradicted, mixed, insufficient_evidence or not_checked. Retrieved sources have IDs, titles, URLs, publishers, a short excerpt and retrieval timestamp; excerpts are the beginning of retrieved content, not independently validated claim-specific quotations; claims reference evidence_ids. Groq failures preserve the classifier result. No combined truth probability is calculated.

Optional FAKEDDIT_REDIS_URL enables a shared fixed-window research quota. Without it, quotas use a per-process sliding window. Redis errors deny research while preserving model inference, with verification reason shared_quota_denied. No Redis dependency is imported unless configured.

/api/capabilities includes research_quota with configured backend, per-client/total windows and limits, and shared_across_instances. It does not assert Redis connection health. Research budgets are five/client/minute and 100 total/hour by default, overridable via FAKEDDIT_RESEARCH_TOTAL_MAX. Structured verification outcome logs carry the same request ID as the response header.

/api/model-card now includes shift_evaluation and an offline_multimodal_pilot summary with modality metrics, local resource measurements, paired uncertainty and limitations when their recorded reports exist. These research records never enable runtime image inference by themselves.
