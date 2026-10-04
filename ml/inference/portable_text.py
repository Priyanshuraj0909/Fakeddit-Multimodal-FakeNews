"""Safe, dependency-free inference for an evaluated TF-IDF/logistic release."""
from collections import Counter
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import re

TOKEN = re.compile(r"(?u)\b\w\w+\b")
RELEASE = Path(__file__).resolve().parents[2] / "backend/app/models/releases/text-v1.json.gz"


@lru_cache(maxsize=4)
def load_release(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        data = json.load(stream)
    features = data.get("features", {})
    if data.get("schema") != "fakeddit_tfidf_logistic_v1" or data.get("labels") != {"0": "Likely fake / misleading", "1": "Likely real"}:
        raise ValueError("Unsupported portable model")
    if not isinstance(features, dict) or not features or any(not isinstance(term, str) or not isinstance(weights, list) or len(weights) != 2 or
                           any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in weights)
                           or weights[0] <= 0 for term, weights in features.items()):
        raise ValueError("Invalid TF-IDF feature weights")
    if not isinstance(data.get("intercept"), (float, int)) or not math.isfinite(data["intercept"]):
        raise ValueError("Invalid model intercept")
    metrics = data.get('metrics', {})
    if not isinstance(metrics, dict) or not isinstance(metrics.get('rows', {}).get('test'), int) or metrics['rows']['test'] <= 0:
        raise ValueError('Missing evaluated release provenance')
    if any(not isinstance(metrics.get(key), (int, float)) or not 0 <= metrics[key] <= 1 for key in ['test_accuracy', 'test_macro_f1']):
        raise ValueError('Invalid release evaluation metrics')
    return data


def predict(text, path=RELEASE):
    data = load_release(str(path))
    words = TOKEN.findall(text.lower())
    counts = Counter(words + [f"{a} {b}" for a, b in zip(words, words[1:])])
    weighted = [(term, (1 + math.log(count)) * data["features"][term][0], data["features"][term][1])
                for term, count in counts.items() if term in data["features"]]
    norm = math.sqrt(sum(value * value for _, value, _ in weighted))
    coverage = sum(word in data["features"] for word in words) / max(1, len(words))
    if not norm or len(words) < 3 or coverage < 0.2:
        return {"status": "abstained", "label": "Not enough usable English text", "probabilities": {},
                "reason": "Enter a specific English headline. The model cannot assess this input reliably.",
                "metrics": data["metrics"], "note": "No model verdict was issued."}
    contributions = [(term, value * coefficient / norm) for term, value, coefficient in weighted]
    logit = data["intercept"] + sum(value for _, value in contributions)
    real = 1 / (1 + math.exp(-max(-700, min(700, logit))))
    probability = max(real, 1-real)
    uncertain = probability < 0.65
    return {"status": "uncertain" if uncertain else "ready", "label": "Uncertain" if uncertain else data["labels"][str(int(real >= 0.5))],
            "probabilities": {data["labels"]["0"]: 1-real, data["labels"]["1"]: real},
            "score_type": "uncalibrated_model_scores", "model": "Fakeddit TF-IDF + Logistic Regression",
            "metrics": data["metrics"], "coverage": round(coverage, 3),
            "signals": [{"term": term, "direction": "real" if value > 0 else "fake", "contribution": round(value, 4)}
                        for term, value in sorted(contributions, key=lambda x: abs(x[1]), reverse=True)[:6]],
            "note": "English Reddit-headline baseline. Dataset patterns can disagree with facts; scores are uncalibrated and do not establish truth."}
