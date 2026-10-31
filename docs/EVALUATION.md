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

A 64-bit lexical SimHash audit found **3 candidate test overlaps** among 10,969 eligible test headlines (minimum five tokens, word/unigram-bigram sets, Hamming distance ≤3). These are candidates requiring review, not proven duplicates or evidence that all other examples are independent. Existing official splits are preserved. The observational audit itself does not measure disjoint or temporal performance. A subsequent exploratory stress evaluation is described below; semantic-duplicate and fresh external evaluation remain pending.

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

A small real paired pilot is now evaluated, as detailed below. It uses identical paired IDs across modalities and records class recall, macro F1, latency, memory, and error IDs. Full-corpus evaluation and deployment remain pending.

A learned image–headline consistency classifier and NewsCLIPpings evaluation remain pending. Low CLIP similarity alone must not create a fake verdict. OCR extracts text for subsequent review; it does not assess image authenticity or consistency.

## Optional experiment tracking

Install `mlflow-skinny` from requirements-observability.txt in the offline training environment, then set `FAKEDDIT_MLFLOW_URI` to your tracking service. Text and paired training hooks record nested metrics, split fingerprints, parameters, and evaluation reports; paired runs include the encoder fingerprint and manifest. Error reports contain IDs and expected/predicted dataset labels. Raw datasets, full weights and submitted news are not automatically uploaded. No live MLflow service has been validated.

## Exploratory generalization stress tests — 2026-10-31

[TEXT_SHIFT_EVALUATION.json](TEXT_SHIFT_EVALUATION.json) records real measurements, input/model hashes, uncertainty intervals, class recall, and representative error IDs. Frozen text-v1 is evaluated on test authors/domains absent from both training and validation. Author-only: 7,214 rows, 79.75% accuracy, 0.7972 macro F1. Domain-only: 346 rows, 78.90%, 0.7410. Both: 155 rows, 72.26%, 0.6697. These small, differently composed subsets cannot be treated as a representative external benchmark.

A fresh TF-IDF + Logistic Regression baseline was fitted using 86,726 pre-2018 training rows. C was selected solely on 8,536 pre-2018 validation rows. On 6,406 later test examples, accuracy was **56.40%** and macro F1 **0.5535**. The cutoff was fixed before examining this experiment's scores; the experiment is exploratory and reuses a previously evaluated test dataset. This is a separate chronological model; production stays unchanged. The result demonstrates a time-shift weakness and motivates a new external test corpus.

```bash
.venv/bin/python scripts/evaluate_shift.py --output artifacts/shift-reproduction.json
```

The script verifies the frozen model and prepared splits against recorded release hashes, preserves all original splits, excludes unknown/deleted identities from unseen-group denominators, and fits preprocessing only on earlier training examples. No raw text is written into the public result.

## Real paired pilot and reproducibility — 2026-10-31

[MULTIMODAL_PILOT_EVALUATION.json](MULTIMODAL_PILOT_EVALUATION.json) records 600/200/200 balanced samples drawn in seeded candidate batches from the existing independent official text splits. Image URLs are restricted to HTTPS Reddit image hosts; redirects stay on those hosts, decoded images have byte/pixel limits, IDs remain intact, and duplicate exact image hashes are rejected across splits. 79 attempted downloads/duplicates were skipped; image availability creates selection bias. No semantic/perceptual deduplication or exhaustive placeholder-image review is claimed.

The official openai/clip-vit-base-patch32 snapshot is pinned to revision 3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268. The downloader checks the published LFS weight hash, loads only tensor weights with torch.load(weights_only=True), and converts to safetensors. Inference still requires local files and never downloads weights. Extraction uses the explicitly selected slow processor, CPU and one PyTorch thread. An initial four-thread run encountered a native-process fault; the recorded one-thread full evaluation completed. Exact package versions, encoder fingerprints, split hashes and checkpoint hashes are in the report.

Test macro F1: text-only 0.6995, image-only 0.6248, combined 0.7247. See the report for class recall, confusion matrices, validation metrics and error IDs. All modalities use the same retained test examples; validation controls early stopping. Raw texts, images, embeddings and full checkpoints are not committed. The pilot is not a production model release and does not replace text-v1.

[MULTIMODAL_PILOT_COMPARISON.json](MULTIMODAL_PILOT_COMPARISON.json) reproduces the fixed text-only baseline and compares paired predictions with the combined model. Macro-F1 difference +0.0251 has paired-bootstrap 95% interval [-0.0300, 0.0801] over 2,000 resamples (seed 42). Combined-only correct: 18; text-only correct: 13; exact two-sided McNemar p=0.4731. This small pilot does not demonstrate a reliable image benefit. Bootstrap uncertainty excludes training, source-cluster and availability-selection uncertainty.

Reproduce into new directories; the scripts preserve existing artifacts:

```bash
.venv/bin/python -m pip install -r requirements-multimodal.txt
.venv/bin/python scripts/prepare_paired_pilot.py --output data/processed/paired-pilot-reproduction
.venv/bin/python scripts/download_clip_snapshot.py --output models/checkpoints/clip-reproduction
.venv/bin/python scripts/run_paired_pilot.py \
  --paired data/processed/paired-pilot-reproduction \
  --encoder models/checkpoints/clip-reproduction \
  --features data/processed/paired-features-reproduction \
  --model models/exported/paired-model-reproduction \
  --output artifacts/paired-evaluation-reproduction.json
.venv/bin/python scripts/compare_paired_predictions.py \
  --features data/processed/paired-features-reproduction \
  --model models/exported/paired-model-reproduction \
  --report artifacts/paired-evaluation-reproduction.json \
  --output artifacts/paired-comparison-reproduction.json
```

Downloads require network access; the pinned CLIP snapshot is approximately 605 MB. Live image URLs can disappear or change, so seeds alone do not guarantee identical future retained IDs. Use recorded hashes for exact comparisons. CPU resource measurements cover a tiny warmed sample; peak RSS covers the entire extraction/training process.

## Independent evidence-review collection

After exporting actual completed evidence reports, create an unlabeled worksheet:

```bash
.venv/bin/python scripts/create_evidence_review.py \
  --reports artifacts/report-one.json artifacts/report-two.json \
  --output artifacts/review-worksheet.jsonl
```

Expected verdicts and citation support are deliberately null. An independent reviewer must inspect original claims and sources before filling them. The evaluator rejects unreviewed reference values. No independent human-reviewed corpus or evidence-quality score has been invented.

A learned image–headline consistency model remains pending. The official NewsCLIPpings repository requires its matched-pair annotations plus the corresponding VisualNews images/metadata or compatible published features. Fakeddit's fake/real labels do not supply this separate consistency target. The newly evaluated fusion model must not be presented as an image–headline consistency detector.

## Capturing and reviewing a real verification benchmark

No independently reviewed 100-claim corpus is available in this repository. A target size is not a completed dataset; expected verdicts, citation judgments and correctness metrics remain unavailable until supplied by independent reviewers.

Prepare an ignored JSONL file of actual cases, each with unique id, text and optional source_url/publication_date. The file is bounded to 1–100 cases. Then:

```bash
.venv/bin/python scripts/run_verification_batch.py \
  --cases artifacts/actual-cases.jsonl --maximum 100 \
  --output artifacts/verification-run.jsonl
.venv/bin/python scripts/create_evidence_review.py \
  --reports artifacts/verification-run.jsonl --output artifacts/review-worksheet.jsonl
# Independent reviewers fill reference judgments and reviewer provenance.
.venv/bin/python scripts/evaluate_verification.py \
  --reviews artifacts/review-worksheet.jsonl --require-independent \
  --output artifacts/reviewed-evaluation.json
```

The runner checks runtime configuration before paid calls, waits at least 13 seconds between calls, and stops at the first unavailable/transport failure. Output preserves actual elapsed time, request/trace IDs and submitted context. It writes an unavailable manifest without inventing reports when credentials are missing. Captured submissions and run data belong in ignored artifacts/, never Git. HTTP/network failures retain a transport-error record with report=null, not a fabricated verification response.

The worksheet accepts report JSON or captured JSONL, retains unavailable/transport runs and latency, and leaves expected_verdict/supports_assessment null. Fill review_metadata.reviewer_id, reviewed_at (timezone-aware) and independent=true after real independent review. Metadata records an attestation; it cannot prove that a reviewer is independent. The strict evaluator rejects missing provenance for reviewed claims and unfilled reference judgments. Legacy records can still be scored without the strict flag, but the output separately reports provenance coverage.

Evaluation reports reviewed-claim verdict agreement, citation support, citation-review coverage, all attempted service statuses/unavailable reasons, unavailable fraction and median/p95-nearest-rank latency. Unknown legacy statuses are excluded from the service-failure denominator. With no reviewed claims, correctness metrics are null and status is unavailable, even if service timing is measurable. These statistics do not establish retrieval recall or the correctness of unreviewed citations.

Re-ranking, ONNX quantization and C2PA remain later experiments/features. No production re-ranking model, quantized model or image-provenance judgment is claimed by this release; the immediate milestone is a reproducible, observable verification workflow.
