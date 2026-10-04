# Fakeddit Research Studio

A runnable web application and reproducible training tools for the original Fakeddit multimodal fake-news research project. The seven original Colab notebooks and results workbook are preserved.

## What works now

- Responsive text explorer with descriptive writing indicators, examples, validation, and downloadable JSON reports.
- Local image preview, dimensions, and a visual-context investigation guide. Images stay in the browser.
- FastAPI health, analysis, prediction, and interactive documentation endpoints.
- Trainable TF-IDF/logistic regression baseline and ID-aligned image/text XGBoost pipeline.
- Automated API, training-artifact, split-overlap, and embedding-alignment checks, with GitHub Actions CI.

**Model status:** No original dataset, embeddings, or trained classifier was included in the repository. The deployed explorer does not label news as real/fake. Trained text classification activates only after you train and install artifacts. Multimodal inference and automatic image verification are not implemented. The original reported **93.9% accuracy** is historical and has not been independently reproduced; it is not the accuracy of the web app.

## Run the app

Use Python 3.12. On this Mac, `/usr/local/bin/python3.12` is available.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.index:app --reload
```

Open http://127.0.0.1:8000. API documentation is at `/docs`. In VS Code, install the recommended Python/Jupyter extensions and select `.venv` as your interpreter.

## Train a text baseline

Download the dataset from the [official Fakeddit repository](https://github.com/entitize/Fakeddit), following its usage guidance. Use its separate training, validation, and public test files. The official multimodal-only samples are required for comparisons with the original multimodal benchmark.

```bash
python -m pip install -r requirements-training.txt
python -m fakeddit.train_text \
  --train data/multimodal_train.tsv \
  --validation data/multimodal_validate.tsv \
  --test data/multimodal_test_public.tsv
```

Inputs must include `id`, `clean_title`, and `2_way_label` with both binary classes. The pipeline rejects missing fields, duplicate IDs, and cross-split ID overlap. It fits TF-IDF on training only, selects regularization on validation, then evaluates the selected model on test. Artifacts are saved to `artifacts/text-baseline/model.joblib` and `metrics.json`; restart the API after training. Dataset classes remain named 0/1 so no unverified label meaning is assumed.

Only load joblib artifacts created by your own pipeline. Record the environment used for training with `python -m pip freeze > artifacts/text-baseline/environment.txt`. For inference install the matching NumPy, SciPy, scikit-learn, and joblib versions; `requirements-training.txt` supplies these locally. The lightweight hosted app intentionally omits them while no model is installed.

## Train on multimodal embeddings

Each split directory needs:

- `posts.csv` with `id`, `clean_title`, `2_way_label`.
- `image.npz` and `text.npz`, each containing `ids` (string array) and `embeddings` (finite 2-D numeric array).

Embedding IDs must match CSV IDs in exactly the same order. Use embeddings from the same encoder and preprocessing across every split. Original notebook NPY arrays lack IDs; recover the corresponding IDs from extraction records before converting them to this format.

```bash
python -m fakeddit.train_multimodal \
  --train data/embeddings/train \
  --validation data/embeddings/validation \
  --test data/embeddings/test
```

This CPU-compatible XGBoost model uses validation for early stopping and writes `artifacts/multimodal/model.json` and test metrics. It excludes author/subreddit metadata to reduce source shortcuts. Mac users need `brew install libomp` for XGBoost. This command trains from pre-extracted embeddings; it does not download images or implement an online multimodal predictor.

## Original notebooks

| File | Purpose |
| --- | --- |
| `01_resnet_img_processing.ipynb` | ResNet image feature extraction |
| `02_roberta_txt_embeddings.ipynb` | RoBERTa text features |
| `03_resnet18_Tabular+Image+Text_traning.ipynb` | Image/text/tabular classifier comparisons |
| `04_DeepFusionNet_resNet_train.ipynb` | Deep fusion experiments |
| `05_ViT_B_32_extracting_features.ipynb` | CLIP ViT-B/32 extraction |
| `06_clip_fussions_models+train.ipynb` | CLIP fusion experiments |
| `07_XGBoost_clip_best_model.ipynb` | XGBoost and metadata experiments |

For notebook work, install `requirements-local.txt`. The original requirements are preserved in `requirements-research.txt`. These historical notebooks still use Colab/Drive paths and some CUDA assumptions; they are experiment records, not the new local entrypoint.

## Tests

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

The tiny synthetic training fixture tests software behavior only. It is not a benchmark or a shipped model.

## Deployment

The project supports Vercel FastAPI deployment using `pyproject.toml` and `vercel.json`. Application dependencies are deliberately separate from PyTorch/CLIP research dependencies. Link this GitHub repository in Vercel for automatic deployments on pushes to `main`. The default deployment serves the explorer with trained prediction unavailable. To host an actual classifier, supply verified model artifacts and matching inference dependencies; larger CLIP models need suitable dedicated compute.

`data/`, `artifacts/`, environments, and secrets are ignored by Git. The app has no database and does not persist submitted text. Hosting providers may retain request metadata in platform logs.

## Project analysis

See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for original reproducibility issues and [docs/VERIFICATION.md](docs/VERIFICATION.md) for verification results. Dataset labels reflect a research benchmark, not independent fact verification.
