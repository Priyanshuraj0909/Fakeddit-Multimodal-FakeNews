# Phase 06: Backend

Status: Combined detector implemented. Updated 2026-10-31.

/api/detect returns model assessment and separate Groq source verification. Missing credentials/provider errors preserve the model result. Activate GROQ_API_KEY and run live checks.

See docs/MODEL.md, docs/TEXT_MODEL_RELEASE.json and docs/VERIFICATION_SETUP.md.

2026-10-31: Added source excerpts/retrieval timestamps, /api/model-card, request IDs/timing logs, and optional Redis shared research quotas that deny research on dependency/service failure. Live Redis and provider evidence quality are not established by mocked checks.

2026-10-31: Added atomic client/total research budgets, Vercel-specific trusted client header, explicit quota configuration in capabilities, active INFO telemetry and correlated verification outcomes. Real local Redis checks passed; production services still require configuration.
