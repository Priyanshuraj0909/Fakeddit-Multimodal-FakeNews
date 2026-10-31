# Phase 08: Explainability

Status: Text feature contributions implemented; image attribution pending. Updated 2026-10-05.

The portable linear model exposes weighted TF-IDF contributions. These explain dataset-class scores, not factual truth. Groq evidence citations explain factual assessments. Image explanations and stability studies remain pending.

See docs/MODEL.md, docs/TEXT_MODEL_RELEASE.json and docs/VERIFICATION_SETUP.md.

2026-10-31: Text-v2 adds signed character-within-word contributions labeled as character fragments. Contributions sum to the linear score with the intercept; they remain model-pattern explanations rather than evidence. Synthetic sklearn parity tests cover branch normalization, NB-weighted candidates, short words, whitespace and Unicode.
