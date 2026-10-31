# Phase 02: Data

Status: Official text data prepared. Updated 2026-10-05.

Official Fakeddit v2 multimodal-only text splits downloaded locally, labels cross-checked, exact duplicates excluded and fixed-seed subsets prepared. Raw files remain ignored; a later 600/200/200 balanced image pilot is now acquired locally; full image acquisition remains pending.

See docs/MODEL.md, docs/TEXT_MODEL_RELEASE.json and docs/VERIFICATION_SETUP.md.

2026-10-31: Text-v2 uses all 502,605 eligible official training rows under ignored data/processed/text-accuracy-v2. Validation/test CSV hashes are identical to the historical release. Label mapping, IDs and normalized exact-text disjointness are checked; source/author metadata is reserved for audits, not features.
