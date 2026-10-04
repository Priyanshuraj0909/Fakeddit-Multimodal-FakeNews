# Reproducible text + image training and inference

The core task is binary Fakeddit dataset classification using text and its associated image. Predictions are model assessments, not verified facts. The current repository does not contain real Fakeddit data, an encoder snapshot, or a trained production checkpoint. No large downloads or benchmark training were run during repairs.

## Prerequisites and local inputs

Use Python 3.12. On macOS install OpenMP for XGBoost:

```bash
brew install libomp
source .venv/bin/activate
python -m pip install -r requirements-multimodal.txt
```

This optional dependency group includes PyTorch/Transformers and may be large. It is not installed by the lightweight Vercel deployment.

Obtain legitimate data from [the original Fakeddit repository](https://github.com/entitize/Fakeddit), following its usage instructions. Keep independent train, validation, and test splits. Supply:

- `data/multimodal_train.tsv`, `data/multimodal_validate.tsv`, `data/multimodal_test_public.tsv` with `id`, `clean_title`, `2_way_label`.
- `data/images/` containing images whose filename stems exactly match post IDs, such as `001.jpg`. Leading zeros are preserved. Ambiguous/missing images are recorded and excluded.
- `models/checkpoints/clip/`: a complete **local Hugging Face CLIP snapshot**, for example the architecture of `openai/clip-vit-base-patch32`, containing model safetensors, config, image processor config, tokenizer files, and vocabulary. This snapshot must be acquired separately; the application never downloads it.
- `data/labels.json`: distinct names for numeric classes `"0"` and `"1"`, verified against the dataset you obtained. Do not guess true/false ordering. Record the dataset version/document used to verify that mapping.

Example JSON structure, using numeric names until semantic meanings are verified:

```json
{"0": "Dataset class 0", "1": "Dataset class 1"}
```

These numeric names preserve class identity; they do not claim either class is factual truth.

## 1. Pair records with local images

Run from repository root:

```bash
python -m ml.datasets.prepare_pairs --dataset data/multimodal_train.tsv --images data/images --output data/paired/train.csv
python -m ml.datasets.prepare_pairs --dataset data/multimodal_validate.tsv --images data/images --output data/paired/validation.csv
python -m ml.datasets.prepare_pairs --dataset data/multimodal_test_public.tsv --images data/images --output data/paired/test.csv
```

Inspect each `*.skipped.json`. Pairing is by post ID, never directory order. An output that already exists is not overwritten.

If filenames do not match IDs, supply your own CSV with `id,clean_title,2_way_label,image_path`. Paths must be relative to `data/images`; traversal and outside symlinks are rejected during extraction.

## 2. Extract aligned embeddings

The following commands load your local encoder on CPU. They can take substantial time on the full dataset; run them deliberately, starting with small independent subsets that retain both classes.

```bash
python -m ml.preprocessing.extract_embeddings --dataset data/paired/train.csv --images data/images --encoder models/checkpoints/clip --output data/embeddings/train --labels data/labels.json --label-source "Your verified dataset version and label documentation"
python -m ml.preprocessing.extract_embeddings --dataset data/paired/validation.csv --images data/images --encoder models/checkpoints/clip --output data/embeddings/validation --labels data/labels.json --label-source "Your verified dataset version and label documentation"
python -m ml.preprocessing.extract_embeddings --dataset data/paired/test.csv --images data/images --encoder models/checkpoints/clip --output data/embeddings/test --labels data/labels.json --label-source "Your verified dataset version and label documentation"
```

All splits must use the exact same label source string, mapping, snapshot, and dependency versions. Outputs include:

- `posts.csv`: retained post IDs, text, labels, and SHA-256 of the image bytes.
- `image.npz` and `text.npz`: embeddings and aligned string IDs, without pickle objects.
- `manifest.json`: task, verified mapping provenance, full encoder fingerprint, torch/transformers versions, preprocessing, modality widths, and feature order.
- `skipped.json`: missing, corrupt, oversized, unsafe, or unprocessable paired samples.

Shared preprocessing uses EXIF orientation correction, RGB conversion, first frame for animated images, the snapshot's image transforms/tokenizer, text stripping/truncation to the CLIP context length, and L2 normalization of each modality. Training and inference use the same module.

Extraction refuses nonempty output directories to avoid mixing stale and newly generated artifacts.

## 3. Train and evaluate

```bash
python -m ml.training.train_multimodal --train data/embeddings/train --validation data/embeddings/validation --test data/embeddings/test --output models/exported/multimodal --compare
```

Omit `--compare` to skip image-only/text-only ablation models. The combined model uses image embeddings followed by text embeddings; labels and metadata never enter the feature matrix.

Training rejects overlapping post IDs, identical normalized text, identical image bytes across splits, incompatible encoders/manifests, invalid arrays, non-normalized features, and mismatched **individual** modality dimensions. Near-duplicate images and semantically duplicated posts still need a separate deduplication audit.

Validation is used for early stopping. Test data is used for final metrics after fitting, not model selection. Outputs:

- `model.json`: XGBoost checkpoint.
- `manifest.json`: inference contract plus model checksum and training package versions.
- `metrics.json`: accuracy, macro-F1, per-class precision/recall/F1, confusion matrix, validation metrics, row counts, and optional ablations.
- `test_errors.json`: post IDs with expected/predicted numeric classes.

Results belong to the supplied dataset and splits. They do not reproduce the historical 93.9% claim automatically and do not establish performance on new domains. Model scores have not been calibrated as truth probabilities.

## 4. Enable local inference

Use the same torch/transformers versions recorded in the manifest and the exact encoder snapshot. Set paths before starting:

```bash
export FAKEDDIT_MULTIMODAL_DIR="$PWD/models/exported/multimodal"
export FAKEDDIT_ENCODER_DIR="$PWD/models/checkpoints/clip"
python -m uvicorn backend.app.main:app --reload --port 8005
```

Open http://127.0.0.1:8005. Once readiness validation passes, choose **Text + image classifier**, enter text, attach an image, and submit. Only that mode sends image bytes to the API. Video is never sent to the classifier.

Direct API check:

```bash
curl -X POST http://127.0.0.1:8005/api/predict/multimodal -F 'text=A headline to assess' -F 'image=@data/images/001.jpg'
```

The API decodes bytes rather than trusting filename/MIME alone, bounds request/image sizes, and returns explicit 422/415/413/503 errors. Inference supports Pillow-decodable PNG/JPEG/WebP/GIF/BMP/TIFF/AVIF, with a 20 megapixel limit. Other image formats can remain local metadata attachments; the inference route rejects unsupported codecs.

Missing/corrupt checkpoints, encoder fingerprint/version mismatches, wrong dimensions, and inference failures never produce replacement predictions. Errors are logged server-side. After changing artifacts, restart the process to clear model caches.

## Text-only fallback

The text classifier is a separate TF-IDF/logistic-regression pipeline, fitted on training data and selected by validation macro-F1:

```bash
python -m pip install -r requirements-training.txt
python -m ml.training.train_text --train data/multimodal_train.tsv --validation data/multimodal_validate.tsv --test data/multimodal_test_public.tsv --labels data/labels.json --label-source "Your verified dataset version and label documentation"
```

It saves its own metrics/errors/model and requires separate evaluation. It is never silently substituted for a text + image prediction. Legacy numeric-only label mappings are displayed as numeric classes.

## Deployment limits

The Vercel app now bundles the evaluated portable text-v1 baseline. Paired CLIP inference remains unavailable until compatible image/text checkpoints are installed. Full CLIP inference needs suitable compute and installed optional dependencies; no new paid service was provisioned.

[Vercel's request-body limit](https://vercel.com/docs/functions/limitations) is 4.5 MB. The app advertises a conservative 4 MB image inference limit on Vercel, leaving multipart headroom; local inference accepts 10 MB. Browser-local previews still allow 10 MB images and 50 MB videos. Configure model hosting separately after measuring resource needs.

## What was actually verified

Automated tests use generated images, synthetic independent splits, a small XGBoost model, and explicitly mocked CLIP/API output. They verify pairing, validation, contracts, evaluation output, and request/report integration. They do **not** verify a real pretrained encoder, real Fakeddit accuracy, tokenizer quality on every language, or full-dataset runtime.


Structure updated 2026-10-05: see README.md and PLAN.md for current module locations and phase status. Dated historical findings above describe their original review context.

## Reproduce text-v1

The three official Google Drive files (publisher README → v2 data → multimodal_only_samples) are named multimodal_train.tsv, multimodal_validate.tsv and multimodal_test_public.tsv. Put them in data/raw. Preparation validates that binary label 1 matches six-way class 0 (true) for every row, reserves earlier split IDs/content, removes exact duplicates, and samples fixed-seed subsets.

```bash
python scripts/prepare_text_release.py
python scripts/train.py text --train data/processed/text-release-v1/train.csv --validation data/processed/text-release-v1/validation.csv --test data/processed/text-release-v1/test.csv --labels data/processed/text-release-v1/labels.json --label-source https://github.com/entitize/Fakeddit/issues/14 --max-features 40000 --output models/exported/text-release-v1
python scripts/export_text_release.py --directory models/exported/text-release-v1 --provenance data/processed/text-release-v1/provenance.json --parity-dataset data/processed/text-release-v1/test.csv
```

Use a fresh output directory for repeat experiments. The portable export is intentionally versioned; datasets and joblib outputs are ignored. See MODEL.md and TEXT_MODEL_RELEASE.json for actual evaluation and limitations.
