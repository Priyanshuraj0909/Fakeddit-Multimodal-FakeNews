"""Train a text baseline using independent train, validation, and test files."""
import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


def read_split(path, text_column, label_column):
    frame = pd.read_csv(path, sep="\t" if str(path).endswith(".tsv") else ",", dtype={"id": "string"})
    missing = {text_column, label_column, "id"} - set(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if frame[[text_column, label_column, "id"]].isna().any().any():
        raise ValueError(f"{path}: missing text, label, or ID")
    if frame["id"].astype(str).duplicated().any():
        raise ValueError(f"{path}: duplicate post IDs")
    if not frame[label_column].isin([0, 1]).all() or set(frame[label_column]) != {0, 1}:
        raise ValueError(f"{path}: expected both binary labels 0 and 1")
    if frame[text_column].astype(str).str.strip().eq("").any():
        raise ValueError(f"{path}: empty text")
    return frame


def check_disjoint(frames):
    for i, left in enumerate(frames):
        for right in frames[i + 1:]:
            if set(left["id"].astype(str)) & set(right["id"].astype(str)):
                raise ValueError("Post IDs overlap across train/validation/test splits")


def train(train_path, validation_path, test_path, output, text_column="clean_title", label_column="2_way_label"):
    frames = [read_split(p, text_column, label_column) for p in (train_path, validation_path, test_path)]
    check_disjoint(frames)
    training, validation, test = frames
    candidates = []
    for regularization in (0.1, 1.0, 10.0):
        model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=100000, sublinear_tf=True)),
                          ("classifier", LogisticRegression(C=regularization, max_iter=1000, random_state=42))])
        model.fit(training[text_column], training[label_column])
        score = accuracy_score(validation[label_column], model.predict(validation[text_column]))
        candidates.append((score, regularization, model))
    score, regularization, model = max(candidates, key=lambda item: item[0])
    predicted = model.predict(test[text_column])
    metrics = {"model": "TF-IDF + LogisticRegression", "seed": 42, "selected_C": regularization,
               "validation_accuracy": score, "test_accuracy": accuracy_score(test[label_column], predicted),
               "classification_report": classification_report(test[label_column], predicted, output_dict=True, zero_division=0),
               "confusion_matrix": confusion_matrix(test[label_column], predicted).tolist(),
               "labels": {"0": "Dataset class 0", "1": "Dataset class 1"},
               "rows": {name: len(frame) for name, frame in zip(("train", "validation", "test"), frames)},
               "text_column": text_column, "label_column": label_column}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output / "model.joblib")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "validation", "test"):
        parser.add_argument(f"--{split}", required=True)
    parser.add_argument("--output", default="artifacts/text-baseline")
    parser.add_argument("--text-column", default="clean_title")
    parser.add_argument("--label-column", default="2_way_label")
    args = parser.parse_args()
    print(json.dumps(train(args.train, args.validation, args.test, args.output, args.text_column, args.label_column), indent=2))


if __name__ == "__main__":
    main()
