# Active text-v2 release

The active safe-JSON model combines independently L2-normalized word (1,2) and char_wb (3,5) TF-IDF branches, with 100,000 features each, sublinear TF and balanced Logistic Regression C=1.0. Word minimum document frequency is two, character minimum frequency three. Selection used validation macro F1 among fixed word-only, word/character, NB-weighted and class-weighted candidates; the selected architecture was refitted on all 502,605 eligible official training rows. The original 15,000 validation and 15,000 test files are unchanged, and ID/normalized-text disjointness is checked. No author/domain/subreddit metadata is a model feature.

Recorded validation accuracy/macro F1: 83.05%/0.8292. Historical test: 83.35%/0.8323, versus text-v1 80.65%/0.8031. The +2.71-point accuracy difference has paired-bootstrap 95% interval [+2.23,+3.20] points. Real recall improves 8.07 points; fake/misleading recall declines 1.63 points. See TEXT_MODEL_V2_RELEASE.json and TEXT_MODEL_V2_EVALUATION.json for selection, class metrics, hashes, promotion gates, uncertainty and exploratory chronological checks. This is not a new external factual benchmark.

The versioned text-v2.json.gz is 3,310,051 bytes. Dependency-free inference reproduces sklearn branch normalization and character padding, including short words and Unicode. NB ratios can be absorbed into portable coefficients for supported experimental candidates; the selected release uses ordinary balanced logistic coefficients. Export parity compared 456 usable validation/whitespace inputs, maximum probability error about 1e-15. Usability/0.65 thresholds remain fixed. Character fragments are explicitly labeled in signed contribution reports; they explain the model score, not factual support.

Text-v1 artifacts and documentation below are preserved. Existing calibration/original shift reports concern text-v1; /api/model-card identifies their historical release association and exposes a separate accuracy_improvement record for text-v2. Scores are still uncalibrated. No fresh independently labeled news corpus or transformer fine-tuning is claimed; this CPU experiment selected a measured lightweight improvement.

## Historical text-v1

The preserved historical text-v1 baseline is trained from the publisher's Fakeddit v2 multimodal-only TSVs, using only clean_title. Fixed-seed subsets contain 150,000 train, 15,000 validation and 15,000 test samples after ID and normalized exact-text exclusions. Binary 1 matches six-way label 0 (true); binary 0 covers the other categories. Verified against the publisher's mapping and every downloaded row.

TF-IDF uses unigrams/bigrams, sublinear TF, L2 normalization and 40,000 features. Logistic regression regularization was selected on validation macro-F1 from C=0.1,1,10; C=1 won. Independent test accuracy: 0.8064667, macro-F1: 0.8031223. Full class metrics, hashes, rows and configuration: TEXT_MODEL_RELEASE.json. This is a subset text baseline, not the historical multimodal 93.9% result.

The portable release under backend/app/models/releases stores safe gzip JSON vocabulary, IDF and coefficients. scripts/export_text_release.py checks parity against sklearn on 200 evaluation headlines with a 1e-10 tolerance. Normal Python math/regex implements inference. Original joblib training outputs and heavy weights remain ignored. Invalid explicit model overrides produce unavailable status.

The combined detector scores the first nonempty headline line, up to 400 characters. Fewer than three tokens or less than 20% vocabulary coverage triggers abstention; maximum model score below 0.65 is marked uncertain. These are conservative product heuristics, not calibrated uncertainty. Feature contributions describe dataset patterns rather than factual evidence. Long articles, languages other than English and domain shift can reduce reliability.

Groq verification is separate from this classifier and does not receive the model score. It researches up to five central claims using browser_search, then assesses retrieved excerpts with strict JSON output. Supported, contradicted, mixed and insufficient_evidence outcomes retain per-claim source links. No usable sources → insufficient evidence. Missing key/provider failure → not checked.

Image/text CLIP adapters, image-first fusion and CPU XGBoost have an evaluated small offline pilot; no production paired checkpoint is bundled. Standalone image training, image explanations, calibration and video inference remain pending.
