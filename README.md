# Fakeddit Multimodal Fake News

Research and application code for classifying paired news text and images using the Fakeddit dataset. Original Colab experiments are preserved in `notebooks/` and historical results in `results/`.

The main news-detection mode provides **two separate assessments**:

1. **Trained Fakeddit prediction:** an evaluated TF-IDF/logistic-regression model predicts likely fake/misleading or likely real headline patterns, and abstains on unusable inputs. Borderline scores are marked uncertain.
2. **Groq claim verification:** browser research retrieves current sources, then a separate structured assessment checks up to five central claims. Reports show supported, contradicted, mixed or insufficient evidence and clickable source citations.

A compact evaluated text model is bundled; no raw dataset or heavyweight CLIP checkpoint is committed. The model was trained on 150,000 headlines and evaluated on an independent 15,000-headline subset: **80.65% accuracy, 0.803 macro-F1**. These are dataset metrics, not real-world truth accuracy. See [release provenance](docs/TEXT_MODEL_RELEASE.json).

Configure `GROQ_API_KEY` on the server to enable live evidence research. Without it, model predictions work and verification is explicitly marked not checked. Model and source results can disagree. Image/text CLIP inference still requires separately supplied artifacts; video remains preview only.

## Structure

```text
backend/app/      FastAPI entrypoint, API uploads, request schemas, services
backend/tests/    Backend regression tests
frontend/         HTML entrypoint, favicon and package manifest
frontend/src/     Pages, services, state hooks, utilities, styles, type contracts
ml/configs/       Pipeline configuration documentation
ml/datasets/      Local image/post pairing
ml/preprocessing/ Image decoding and CLIP extraction
ml/models/        Text/image encoder adapters, fusion, classifier
ml/training/      Text baseline and multimodal training
ml/evaluation/    Evaluation metrics
ml/inference/     Checkpoint-backed multimodal runtime
ml/utils/         Artifact and leakage contracts
data/             Ignored raw/processed/sample datasets
models/           Ignored encoder checkpoints and exported classifiers
scripts/          Setup, download, preprocessing, training, verification
tests/           ML, frontend and browser integration checks
docs/phases/     Phase deliverables and remaining prerequisites
notebooks/        Original research notebooks
results/          Historical experiment results
```

## Run locally

Requires Python 3.12 and Node 20+. On macOS XGBoost may require `brew install libomp`.

```bash
bash scripts/setup.sh
.venv/bin/python -m uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/docs. The frontend uses native JavaScript modules; no frontend bundler is required. Run `bash scripts/verify.sh` to verify Python and frontend behavior.

Set `GROQ_API_KEY` in Vercel Production and redeploy to activate source verification. The default Groq model is `openai/gpt-oss-20b`; supported browser-search and strict-output models are required. See [verification setup](docs/VERIFICATION_SETUP.md). Optional environment variables are documented in `.env.example`. Local Uvicorn does not automatically load that file: export the variables or pass `--env-file` with the required dotenv dependency. Relative model paths assume commands run from the repository root.

For containers, run `docker compose up --build`. The default image serves analysis and previews; trained inference requires installing the corresponding dependency group and mounting compatible artifacts. Container configuration is provided but must be validated on a host with Docker.

## Train

Obtain dataset files through the [Fakeddit publisher](https://github.com/entitize/Fakeddit) and verify the label mapping. Keep independent train, validation, and test splits. See [dataset contracts](docs/DATASET.md) and [complete training guide](docs/TRAINING.md).

```bash
.venv/bin/python -m pip install -r requirements-training.txt
.venv/bin/python scripts/train.py text --train data/raw/train.tsv --validation data/raw/validation.tsv --test data/raw/test.tsv
.venv/bin/python scripts/preprocess.py pairs --help
.venv/bin/python scripts/preprocess.py embeddings --help
.venv/bin/python scripts/train.py multimodal --help
```

Text artifacts default to `models/exported/text-baseline`; fusion artifacts to `models/exported/multimodal`; the local CLIP snapshot belongs in `models/checkpoints/clip`. Extraction and paired inference additionally require `requirements-multimodal.txt`. Never load untrusted joblib artifacts.

## Project guides

- [Master workflow](MASTER_ORCHESTRATOR.md), [plan](PLAN.md), [change log](CHANGELOG.md)
- [Architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [models](docs/MODEL.md)
- [Deployment](docs/DEPLOYMENT.md), [verification](docs/VERIFICATION.md)
- [Historical review](PROJECT_REVIEW.md), [audit](docs/PROJECT_AUDIT.md)

Owner: [Priyanshu Raj](https://github.com/Priyanshuraj0909). Research credit: Kai Nakamura, Sharon Levy, and William Yang Wang for Fakeddit. Dataset access and terms are controlled by the publisher.

## Reproduce the deployed text baseline

Download the three official multimodal-only TSV splits into data/raw. Run `scripts/prepare_text_release.py` to create fixed-seed subsets with ID and normalized exact-text exclusions. Train with `scripts/train.py text --max-features 40000`, and export with scripts/export_text_release.py. See docs/TEXT_MODEL_RELEASE.json for exact selected configuration and provenance. The deployment release is a 644 KiB gzip JSON file containing vocabulary, IDF and coefficients; inference requires no sklearn or unsafe deserialization. Full research checkpoints remain ignored.
