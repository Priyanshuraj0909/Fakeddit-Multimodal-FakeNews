# Models

The deployed text-v1 baseline is trained from the publisher's Fakeddit v2 multimodal-only TSVs, using only clean_title. Fixed-seed subsets contain 150,000 train, 15,000 validation and 15,000 test samples after ID and normalized exact-text exclusions. Binary 1 matches six-way label 0 (true); binary 0 covers the other categories. Verified against the publisher's mapping and every downloaded row.

TF-IDF uses unigrams/bigrams, sublinear TF, L2 normalization and 40,000 features. Logistic regression regularization was selected on validation macro-F1 from C=0.1,1,10; C=1 won. Independent test accuracy: 0.8064667, macro-F1: 0.8031223. Full class metrics, hashes, rows and configuration: TEXT_MODEL_RELEASE.json. This is a subset text baseline, not the historical multimodal 93.9% result.

The portable release under backend/app/models/releases stores safe gzip JSON vocabulary, IDF and coefficients. scripts/export_text_release.py checks parity against sklearn on 200 evaluation headlines with a 1e-10 tolerance. Normal Python math/regex implements inference. Original joblib training outputs and heavy weights remain ignored. Invalid explicit model overrides produce unavailable status.

The combined detector scores the first nonempty headline line, up to 400 characters. Fewer than three tokens or less than 20% vocabulary coverage triggers abstention; maximum model score below 0.65 is marked uncertain. These are conservative product heuristics, not calibrated uncertainty. Feature contributions describe dataset patterns rather than factual evidence. Long articles, languages other than English and domain shift can reduce reliability.

Groq verification is separate from this classifier and does not receive the model score. It researches up to five central claims using browser_search, then assesses retrieved excerpts with strict JSON output. Supported, contradicted, mixed and insufficient_evidence outcomes retain per-claim source links. No usable sources → insufficient evidence. Missing key/provider failure → not checked.

Image/text CLIP adapters, image-first fusion and CPU XGBoost remain available for offline training but lack real paired checkpoints. Standalone image training, image explanations, calibration and video inference remain pending.
