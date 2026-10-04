"""Lightweight API deployable without heavyweight research dependencies."""
from pathlib import Path
import json
import os
import logging
from importlib.util import find_spec
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.fakeddit.signals import analyze

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path(os.environ.get("FAKEDDIT_MODEL_DIR", str(ROOT / "artifacts/text-baseline")))
app = FastAPI(title="FakeEdit Research API", version="2.0.0")
logger = logging.getLogger(__name__)


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


def clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(422, "Enter a headline or article.")
    return value


@app.get("/api/health")
@app.head("/api/health", include_in_schema=False)
def health():
    dependencies = all(find_spec(name) is not None for name in ("joblib", "sklearn", "numpy", "scipy"))
    artifacts = all((MODEL_DIR / name).is_file() for name in ("model.joblib", "metrics.json"))
    reason = "missing_artifacts" if not artifacts else "missing_dependencies" if not dependencies else "ready"
    if reason == "ready":
        try:
            load_model(str(MODEL_DIR))
        except Exception:
            reason = "invalid_artifacts"
    return {"status": "ok", "model_available": reason == "ready", "model_status": reason, "version": "2.0.0"}


@app.get("/api/capabilities")
def capabilities():
    model = health()
    return {
        "text_analysis": True,
        "text_classifier": {"available": model["model_available"], "status": model["model_status"]},
        "media_inspection": "browser_local",
        "image_inference": False,
        "video_inference": False,
        "fact_verification": False,
        "limits": {"text_characters": 10000, "image_bytes": 10 * 1024 * 1024, "video_bytes": 50 * 1024 * 1024},
        "note": "Reports describe language and supplied media metadata. They do not establish factual truth.",
    }



@app.post("/api/analyze")
def inspect_text(payload: TextInput):
    return analyze(clean_text(payload.text))


@lru_cache(maxsize=1)
def load_model(directory: str):
    # Only load artifacts created by your own training pipeline; joblib is executable.
    import joblib
    path = Path(directory)
    metadata = json.loads((path / "metrics.json").read_text())
    if not isinstance(metadata.get("labels"), dict):
        raise ValueError("Missing model label mapping")
    model = joblib.load(path / "model.joblib")
    classes = getattr(model, "classes_", [])
    if len(classes) < 2 or any(str(int(c)) not in metadata["labels"] for c in classes):
        raise ValueError("Model classes do not match the label mapping")
    if any(not isinstance(metadata["labels"][str(int(c))], str) for c in classes):
        raise ValueError("Invalid model labels")
    import numpy as np
    probabilities = np.asarray(model.predict_proba(["Model readiness check"]), dtype=float)
    if (probabilities.shape != (1, len(classes)) or not np.isfinite(probabilities).all()
            or (probabilities < 0).any() or (probabilities > 1).any()
            or not np.isclose(probabilities.sum(), 1)):
        raise ValueError("Invalid model probabilities")
    return model, metadata


@app.post("/api/predict")
def predict(payload: TextInput):
    text = clean_text(payload.text)
    if not health()["model_available"]:
        raise HTTPException(503, "No trained model is installed. The text explorer remains available.")
    try:
        model, metadata = load_model(str(MODEL_DIR))
        probabilities = model.predict_proba([text])[0]
        labels = metadata["labels"]
        return {"mode": "trained_text_baseline", "label": labels[str(int(model.predict([text])[0]))],
                "probabilities": {labels[str(int(c))]: float(p) for c, p in zip(model.classes_, probabilities)},
                "note": "Dataset classification is not a fact-check. This text-only baseline is separate from the original CLIP experiments."}
    except Exception:
        logger.exception("Trained model inference failed")
        raise HTTPException(503, "Model artifacts or inference dependencies are incomplete.")


@app.get("/")
@app.head("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "frontend/index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "frontend/favicon.svg", media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
