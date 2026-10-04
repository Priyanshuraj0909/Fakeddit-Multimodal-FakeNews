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

from fakeddit.signals import analyze

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
def health():
    model_available = (
        (MODEL_DIR / "model.joblib").is_file()
        and (MODEL_DIR / "metrics.json").is_file()
        and all(find_spec(name) is not None for name in ("joblib", "sklearn", "numpy", "scipy"))
    )
    return {"status": "ok", "model_available": model_available, "version": "2.0.0"}


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
    return joblib.load(path / "model.joblib"), metadata


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
def home():
    return FileResponse(ROOT / "frontend/index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "frontend/favicon.svg", media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
