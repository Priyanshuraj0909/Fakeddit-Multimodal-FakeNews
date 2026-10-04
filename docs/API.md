# API

Start `python -m uvicorn backend.app.main:app --reload` from the root. Interactive schemas are available at /docs.

| Method | Path | Contract |
| --- | --- | --- |
| GET/HEAD | /api/health | Service health and validated text-model readiness |
| GET | /api/capabilities | Available classifiers, upload limits and unsupported tasks |
| POST | /api/analyze | JSON text; descriptive language indicators |
| POST | /api/predict | JSON text; installed text classifier |
| POST | /api/predict/multimodal | Multipart text + image; installed paired classifier |

Text is required, trimmed and limited to 10,000 characters. Invalid JSON/schema input returns 422. Multipart images are decoded with byte/pixel limits; unsupported images return 415 and oversized requests return 413. Local paired uploads allow 10 MiB; the Vercel environment sets a lower 4 MiB file limit. Missing or incompatible model assets return 503.

Text predictions expose label, probabilities and uncalibrated_model_scores; multimodal predictions expose label, scores, task, label_source and image_assessed. These are dataset-class assessments, not verified truth. OpenAPI from the running application is authoritative for response details. No authentication or persistence is implemented.
