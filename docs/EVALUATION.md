# Evaluation and remaining evidence

Recorded 2026-10-31. These are research measurements, separate from factual truth and production readiness.

## Text reliability

[TEXT_RELIABILITY_EVALUATION.json](TEXT_RELIABILITY_EVALUATION.json) preserves split hashes, model hash, reliability bins, Brier score, log loss, and accuracy versus coverage. The frozen text-v1 baseline was already selected using the full validation split. Sigmoid calibration was fitted on 7,500 stratified validation rows and selected against raw scores using Brier score on the other 7,500, with seed 42. Test was used only for evaluation. Validation reuse after base-model selection limits independence; a new calibration corpus and external test set would strengthen this result.

Test Brier score: raw **0.13851**, sigmoid **0.13688**. The experiment selected sigmoid; the deployed model still uses raw scores and the heuristic 0.65 threshold. Reliability concerns Reddit dataset labels, never the probability that a claim is factually true. No new model training is implied by publishing this record.

Reproduce from trusted locally trained checkpoints (joblib is unsafe for untrusted files):

```bash
.venv/bin/python scripts/evaluate_reliability.py \
  --directory models/exported/text-release-v1 \
  --train data/processed/text-release-v1/train.csv \
  --validation data/processed/text-release-v1/validation.csv \
  --test data/processed/text-release-v1/test.csv \
  --output artifacts/reliability-reproduction.json
```

The evaluator checks exact ID/content disjointness and split counts; users must supply the actual fitted model's splits. Compare their hashes to the recorded evaluation before comparing results. Outputs refuse to overwrite existing records.

## Generalization audit

[TEXT_GENERALIZATION_AUDIT.json](TEXT_GENERALIZATION_AUDIT.json) records an observational audit against official raw metadata. About **48.18%** of known test authors and **96.89%** of known test domains also appear in training. All test subreddits appear in training. Train-only majority baselines score **72.60%** test accuracy using domain and **100%** using subreddit. The deployed text model does not use these metadata features. This exposes dataset construction shortcuts and does not establish real-world fact-checking accuracy.

A 64-bit lexical SimHash audit found **3 candidate test overlaps** among 10,969 eligible test headlines (minimum five tokens, word/unigram-bigram sets, Hamming distance ≤3). These are candidates requiring review, not proven duplicates or evidence that all other examples are independent. Existing official splits are preserved. No source/author-disjoint, semantic-duplicate or temporal benchmark has been completed.

```bash
.venv/bin/python scripts/audit_generalization.py \
  --raw data/raw --prepared data/processed/text-release-v1 \
  --output artifacts/generalization-reproduction.json
```

## Evidence support evaluation

`scripts/evaluate_verification.py` scores report exports against independently human-reviewed reference assessments. No reviewed corpus is available here, so **evidence correctness and citation-support metrics remain unavailable**. Synthetic unit tests only check evaluator behavior.

Supply JSONL with one object per report; `claim_index` is zero-based. The following is a schema example, not an evaluated case:

```json
{"id":"review-001","report":{"verification":{"claims":[{"verdict":"supported","evidence_ids":[1]}],"sources":[{"id":1}]}},"reviews":[{"claim_index":0,"expected_verdict":"insufficient_evidence","citations":[{"source_id":1,"supports_assessment":false}]}]}
```

Reviewers must inspect the original claim and sources rather than derive reference labels from model output. Valid reference verdicts: supported, contradicted, mixed, insufficient_evidence. Only explicitly reviewed claims/citations enter denominators. The current evaluator measures claim-verdict agreement and citation support; retrieval recall, missing-evidence coverage, provider-failure rates and end-to-end latency require a separately curated run log and protocol.

```bash
.venv/bin/python scripts/evaluate_verification.py \
  --reviews artifacts/human-reviews.jsonl --output artifacts/evidence-evaluation.json
```

The UI exposes retrieval timestamps and a short initial excerpt for context. Citation-ID validation and excerpts do not prove that a source supports a claim.

## Paired release and consistency

A real multimodal evaluation remains blocked by missing paired image files and a compatible local CLIP snapshot. Text-only, image-only and combined benchmarks must use exactly the same paired IDs. Use the existing multimodal training `--compare` option; record class recall, macro F1, latency, memory and reviewed errors before releasing. No such release metrics are claimed here.

A learned image–headline consistency classifier and NewsCLIPpings evaluation remain pending. Low CLIP similarity alone must not create a fake verdict. OCR extracts text for subsequent review; it does not assess image authenticity or consistency.

## Optional experiment tracking

Install `mlflow-skinny` from requirements-observability.txt in the offline training environment, then set `FAKEDDIT_MLFLOW_URI` to your tracking service. Text and paired training hooks record nested metrics, split fingerprints, parameters, and evaluation reports; paired runs include the encoder fingerprint and manifest. Error reports contain IDs and expected/predicted dataset labels. Raw datasets, full weights and submitted news are not automatically uploaded. No live MLflow service has been validated.
