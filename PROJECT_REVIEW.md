# Project review

Reviewed from the cloned source on 2026-10-04. This is a static review; training and reported accuracy were not reproduced.

## Original structure (before application updates)

Seven Colab notebooks implement ResNet image extraction, RoBERTa text extraction, tabular/image/text classifiers, deep fusion, CLIP feature extraction, fusion comparisons, and CLIP/XGBoost experiments. `results/multimodal_results-5.xlsx` contains saved experimental results. At the time of the original clone there was no standalone training pipeline or inference application. These have since been added; see the current audit below.

## Historical notebook findings

1. **Local execution is blocked by external data and Colab paths.** Notebooks read TSV/CSV datasets and NPY embeddings from several Google Drive directories. None of these inputs or saved models is tracked here. Drive mounts and notebook shell commands also need local equivalents.
2. **Test data influences model selection.** In notebook 07, cells 41 and 42 use `eval_set=[(X_test, y_test)]` with early stopping and then report metrics on the same test set. This compromises an independent final evaluation. Split validation data from training, select models on validation, and evaluate the test set once after selection.
3. **Metadata needs leakage checks.** The README reports perfect scores with subreddit features. This warrants investigating label/source shortcuts rather than attributing it only to overfitting. Author features also need evaluation with author-disjoint splits to measure generalization to unseen authors.
4. **Notebook state makes runs fragile.** Notebook 07 redefines `train_optimized_xgboost` and contains a diagnostic using `label`, while the training target is `2_way_label`. Notebook 01 reads Drive paths before an initial mount. A clean-kernel, ordered run is needed after refactoring.
5. **Feature alignment needs explicit verification.** Independently stored CSV rows and image/text arrays must share identical post IDs and ordering, especially after failed image downloads or concatenating extraction batches. Add alignment checks before training.
6. **Dependencies and hardware assumptions are incomplete.** Original requirements omit imports including LightGBM, Optuna, SciPy, and CLIP. Several cells request GPU-specific XGBoost settings. `requirements-local.txt` supplies the missing packages and notebook tools; dependency compatibility and local execution remain unverified.
7. **Documentation needs result provenance.** Several notebook filenames in the README summary differ from actual files. The reported 93.9% accuracy needs a precise configuration, split, seed, and metrics record; it should remain a historical reported result until independently reproduced.

## Suggested update sequence

1. Locate the original TSV datasets, cleaned CSVs, embeddings, and saved model; document their schemas and post IDs.
2. Extract notebook logic into configurable Python modules for paths, feature extraction, preprocessing, training, and evaluation. Preserve original notebooks as experiment records.
3. Introduce a training/validation/test protocol, train-only preprocessing, alignment checks, and author/subreddit leakage experiments.
4. Reproduce a text-only baseline and CLIP + XGBoost result with saved metrics and environment versions.
5. Build an inference demo after saving the model and its exact preprocessing artifacts.

## Changes made during setup

Corrected the clone URL and folder in the README, added local VS Code guidance and extension recommendations, added local notebook requirements, and ignored environments/data/generated embeddings. Original notebooks and recorded results are unchanged.

## Implemented updates

The repository now contains a FastAPI app, responsive text explorer, browser-only image preview, JSON reports, optional trained-text inference, separate application/research requirements, reproducible text training, and CPU XGBoost training from ID-aligned embeddings. New training tools use separate validation and test inputs and reject cross-split post overlap. CI covers the new code. Historical notebooks remain unchanged; their issues are documented rather than silently altering recorded experiments. See README.md for commands and docs/VERIFICATION.md for checks.

## Current application audit

See [docs/PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md) for real-world purpose, working features, fixed gaps, missing AI functionality, and completion prerequisites. Runtime code lives in backend/, with browser-local image/video inspection, media-only reports, verification context, and explicit capability/model readiness status.

The paired text + image inference/extraction path has since been added with checkpoint contracts and regression tests. See [docs/REPAIR_REPORT.md](docs/REPAIR_REPORT.md). Production model artifacts remain absent.


Structure updated 2026-10-05: see README.md and PLAN.md for current module locations and phase status. Dated historical findings above describe their original review context.
