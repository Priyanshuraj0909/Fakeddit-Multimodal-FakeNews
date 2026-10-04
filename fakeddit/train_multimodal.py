"""Train XGBoost on aligned pre-extracted image and text embeddings."""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

from fakeddit.train_text import check_disjoint, read_split


def load_split(folder):
    folder = Path(folder)
    frame = read_split(folder / "posts.csv", "clean_title", "2_way_label")
    arrays = []
    for modality in ("image", "text"):
        with np.load(folder / f"{modality}.npz", allow_pickle=False) as archive:
            ids, embeddings = archive["ids"].astype(str), archive["embeddings"]
            if not np.array_equal(ids, frame["id"].astype(str).to_numpy()):
                raise ValueError(f"{folder}/{modality}: embedding IDs do not match CSV row order")
            if (
                embeddings.ndim != 2
                or embeddings.shape[1] == 0
                or len(embeddings) != len(frame)
                or not np.issubdtype(embeddings.dtype, np.number)
                or np.iscomplexobj(embeddings)
                or not np.isfinite(embeddings).all()
            ):
                raise ValueError(f"{folder}/{modality}: invalid embedding shape or non-finite values")
            arrays.append(embeddings)
    return frame, np.concatenate(arrays, axis=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "validation", "test"):
        parser.add_argument(f"--{split}", required=True)
    parser.add_argument("--output", default="artifacts/multimodal")
    args = parser.parse_args()
    splits = [load_split(folder) for folder in (args.train, args.validation, args.test)]
    check_disjoint([frame for frame, _ in splits])
    (training, x_train), (validation, x_validation), (test, x_test) = splits
    if len({x.shape[1] for _, x in splits}) != 1:
        raise ValueError("Embedding feature widths differ across splits")
    model = XGBClassifier(tree_method="hist", device="cpu", n_estimators=2000, max_depth=6,
                          learning_rate=0.03, early_stopping_rounds=50, random_state=42, eval_metric="logloss")
    model.fit(x_train, training["2_way_label"], eval_set=[(x_validation, validation["2_way_label"])], verbose=False)
    predicted = model.predict(x_test)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    model.save_model(output / "model.json")
    metrics = {"test_accuracy": accuracy_score(test["2_way_label"], predicted), "best_iteration": model.best_iteration,
               "classification_report": classification_report(test["2_way_label"], predicted, output_dict=True, zero_division=0),
               "feature_count": x_train.shape[1], "seed": 42,
               "note": "Image/text embeddings only; metadata omitted to reduce source shortcuts."}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
