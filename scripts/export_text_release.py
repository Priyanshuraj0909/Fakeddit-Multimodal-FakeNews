"""Export trusted local sklearn training artifacts to a portable evaluated release."""
import argparse
import gzip
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
from ml.inference.portable_text import predict, load_release


def export(directory, provenance, output, parity_texts):
    directory, output = Path(directory), Path(output)
    model = joblib.load(directory / "model.joblib")
    vectorizer, classifier = model.named_steps["tfidf"], model.named_steps["classifier"]
    metadata = json.loads((directory / "metrics.json").read_text())
    if (vectorizer.ngram_range != (1, 2) or not vectorizer.sublinear_tf or vectorizer.norm != "l2"
            or vectorizer.strip_accents is not None or list(classifier.classes_) != [0, 1]):
        raise ValueError("Model cannot be represented by the portable inference contract")
    data = {"schema": "fakeddit_tfidf_logistic_v1", "labels": metadata["labels"],
            "intercept": float(classifier.intercept_[0]),
            "features": {term: [float(vectorizer.idf_[index]), float(classifier.coef_[0, index])]
                         for term, index in vectorizer.vocabulary_.items()},
            "metrics": {key: metadata[key] for key in ["test_accuracy", "test_macro_f1", "validation_macro_f1", "rows", "selected_C"]},
            "provenance": json.loads(Path(provenance).read_text())}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stable bytes for a reproducible release checksum.
    with output.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as stream:
        stream.write(json.dumps(data, separators=(",", ":"), sort_keys=True).encode())
    load_release.cache_clear()
    maximum_error = 0.0
    for text, expected in zip(parity_texts, model.predict_proba(parity_texts)):
        result = predict(text, output)
        if result["probabilities"]:
            actual = list(result["probabilities"].values())
            maximum_error = max(maximum_error, float(np.max(np.abs(expected-actual))))
    if maximum_error > 1e-10:
        output.unlink()
        raise ValueError(f"Portable inference parity failed: {maximum_error}")
    return {"output": str(output), "bytes": output.stat().st_size, "max_probability_error": maximum_error, "metrics": data["metrics"]}


if __name__ == "__main__":
    import pandas as pd
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--provenance', required=True)
    parser.add_argument('--parity-dataset', required=True)
    parser.add_argument('--output', default='backend/app/models/releases/text-v1.json.gz')
    args = parser.parse_args()
    texts = pd.read_csv(args.parity_dataset)['clean_title'].head(200).tolist()
    print(json.dumps(export(args.directory, args.provenance, args.output, texts), indent=2))
