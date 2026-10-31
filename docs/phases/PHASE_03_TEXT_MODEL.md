# Phase 03: Text model

Status: Evaluated text-v1 deployed baseline. Updated 2026-10-31.

150,000 training headlines, 15,000 validation and 15,000 held-out test headlines. Test accuracy 80.65%, macro-F1 0.803. Portable export parity checked against sklearn. Calibration experiment and observational metadata audit recorded; external domain-shift evaluation remains pending.

See docs/MODEL.md, docs/TEXT_MODEL_RELEASE.json and docs/VERIFICATION_SETUP.md.

2026-10-31: Recorded sigmoid calibration experiment in TEXT_RELIABILITY_EVALUATION.json and overlap/source-shortcut audit in TEXT_GENERALIZATION_AUDIT.json. Test Brier 0.13851 → 0.13688; production unchanged. Source/author-disjoint and temporal performance remain pending. See EVALUATION.md.

2026-10-31: Recorded TEXT_SHIFT_EVALUATION.json: frozen unseen-author/domain subsets and independently fitted pre-2018 chronological baseline. Temporal accuracy 56.40% on 6,406 later test examples; production unchanged. External validation and dedicated calibration remain pending.
