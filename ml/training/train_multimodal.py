"""Train and evaluate XGBoost on strictly aligned, reproducible CLIP features."""
import argparse
import json
from pathlib import Path
from importlib.metadata import version
import numpy as np
from ml.evaluation.metrics import evaluate
from xgboost import XGBClassifier
from ml.models.classifier import build_classifier
from ml.models.fusion_model import fuse_features
from ml.training.train_text import check_disjoint, read_split
from ml.utils.contracts import check_content_disjoint, read_manifest, digest_file


def load_split(folder):
    folder = Path(folder)
    frame = read_split(folder / "posts.csv", "clean_title", "2_way_label")
    arrays, widths = [], {}
    for modality in ("image", "text"):
        with np.load(folder / f"{modality}.npz", allow_pickle=False) as archive:
            ids, embeddings = archive["ids"].astype(str), archive["embeddings"]
            if not np.array_equal(ids, frame["id"].astype(str).to_numpy()):
                raise ValueError(f"{folder}/{modality}: embedding IDs do not match CSV row order")
            if (embeddings.ndim != 2 or embeddings.shape[1] == 0 or len(embeddings) != len(frame)
                    or not np.issubdtype(embeddings.dtype, np.number) or np.iscomplexobj(embeddings)
                    or not np.isfinite(embeddings).all()):
                raise ValueError(f"{folder}/{modality}: invalid embedding shape or non-finite values")
            widths[modality] = embeddings.shape[1]
            arrays.append(embeddings)
    frame.attrs["widths"] = widths
    return frame, fuse_features(*arrays)


def validate_splits(folders):
    manifests = [read_manifest(Path(folder) / "manifest.json") for folder in folders]
    if any(manifest != manifests[0] for manifest in manifests[1:]):
        raise ValueError("Encoder, labels, preprocessing, or dimensions differ across splits")
    splits = [load_split(folder) for folder in folders]
    for frame, _ in splits:
        if frame.attrs["widths"] != manifests[0]["widths"]:
            raise ValueError("Individual modality dimensions differ from the encoder manifest")
        hashes = frame.get("image_sha256")
        if hashes is None or hashes.isna().any() or not hashes.astype(str).str.fullmatch(r"[0-9a-f]{64}").all():
            raise ValueError("Every paired record requires an image_sha256 content hash")
    for frame, embeddings in splits:
        boundary = frame.attrs["widths"]["image"]
        for features in (embeddings[:, :boundary], embeddings[:, boundary:]):
            if not np.allclose(np.linalg.norm(features, axis=1), 1, atol=1e-4):
                raise ValueError("Embeddings must use the recorded L2 normalization")
    check_disjoint([frame for frame, _ in splits])
    check_content_disjoint([frame for frame, _ in splits])
    return splits, manifests[0]




def train(train_folder, validation_folder, test_folder, output, compare=False, estimators=2000):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output folder is not empty; preserve the existing checkpoint and choose a new directory")
    splits, manifest = validate_splits([train_folder, validation_folder, test_folder])
    (training, x_train), (validation, x_validation), (test, x_test) = splits
    model = build_classifier(estimators)
    model.fit(x_train, training["2_way_label"], eval_set=[(x_validation, validation["2_way_label"])], verbose=False)
    predicted = model.predict(x_test)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    model.save_model(output / "model.json")
    manifest = {**manifest, "model_sha256": digest_file(output / "model.json"),
                "packages": {name: version(name) for name in ("xgboost", "numpy", "scikit-learn")}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    metrics = {**evaluate(test, predicted), "best_iteration": model.best_iteration,
               "validation": evaluate(validation, model.predict(x_validation)), "seed": 42,
               "feature_count": x_train.shape[1], "rows": {name: len(frame) for name, (frame, _) in zip(("train", "validation", "test"), splits)},
               "note": "Image/text features only; test data never used for early stopping. Scores are not calibrated truth probabilities."}
    if compare:
        boundary = manifest["widths"]["image"]
        metrics["ablations"] = {}
        for name, features in (("image_only", slice(0, boundary)), ("text_only", slice(boundary, None))):
            baseline = XGBClassifier(**model.get_params())
            baseline.fit(x_train[:, features], training["2_way_label"],
                         eval_set=[(x_validation[:, features], validation["2_way_label"])], verbose=False)
            metrics["ablations"][name] = evaluate(test, baseline.predict(x_test[:, features]))
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    errors = [{"id": str(row["id"]), "expected": int(row["2_way_label"]), "predicted": int(pred)}
              for (_, row), pred in zip(test.iterrows(), predicted) if int(row["2_way_label"]) != int(pred)]
    (output / "test_errors.json").write_text(json.dumps(errors, indent=2) + "\n")
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "validation", "test"):
        parser.add_argument(f"--{split}", required=True)
    parser.add_argument("--output", default="models/exported/multimodal")
    parser.add_argument("--compare", action="store_true", help="Evaluate image-only and text-only ablations")
    args = parser.parse_args()
    print(json.dumps(train(args.train, args.validation, args.test, args.output, args.compare), indent=2))


if __name__ == "__main__":
    main()
