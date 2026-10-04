# Models

Text baseline: train-only TF-IDF plus logistic regression, regularization selected on validation. Output model.joblib and metrics.json under models/exported/text-baseline. Only load trusted joblib files.

Image/text representations: a shared local Hugging Face CLIP snapshot loaded using safetensors, CPU inference, normalized features and recorded preprocessing. TextModel and ImageModel expose the respective branches without loading separate encoder copies. Store the matching snapshot under models/checkpoints/clip.

Fusion: image-first concatenation validated by ml/models/fusion_model.py, followed by CPU XGBoost. Validation controls early stopping; test is evaluated separately. Output model.json, manifest.json, metrics.json and test_errors.json under models/exported/multimodal. Optional --compare evaluates image-only/text-only ablations.

The inference runtime validates checksums, encoder identity, package versions, modality widths and class mapping. Metrics include accuracy, macro F1, class reports and confusion matrices. Model scores are uncalibrated. Real artifacts are absent; no current accuracy claim is justified. Standalone image training, calibration and explainability remain pending.
