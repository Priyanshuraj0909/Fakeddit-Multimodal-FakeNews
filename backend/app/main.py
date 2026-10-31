"""Lightweight API deployable without heavyweight research dependencies."""
from pathlib import Path
import json
import os
import logging
from importlib.util import find_spec
from functools import lru_cache
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.app.schemas.text import TextInput
from backend.app.schemas.detection import DetectionInput
from backend.app.services import verification
from backend.app.core.rate_limit import ResearchLimit, research_identity
from backend.app.core.observability import RequestTelemetry
from backend.app.core.tracing import stage, attributes, configuration as tracing_configuration, current_trace_id
from ml.inference import portable_text
from starlette.concurrency import run_in_threadpool

from backend.app.services.signals import analyze
from ml.inference import multimodal
from backend.app.api.uploads import router as upload_router, UploadBodyLimit, image_upload_limit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = ROOT / "models/exported/text-baseline"
MODEL_DIR = Path(os.environ.get("FAKEDDIT_MODEL_DIR", str(DEFAULT_MODEL_DIR)))
app = FastAPI(title="Fakeddit Fake News Detector API", version="2.4.0")
logger = logging.getLogger(__name__)
research_limit = ResearchLimit()
app.add_middleware(UploadBodyLimit)
app.add_middleware(CORSMiddleware,
                   allow_origins=[origin.strip() for origin in os.environ.get('FAKEDDIT_CORS_ORIGINS', 'https://priyanshuraj0909.github.io').split(',') if origin.strip()],
                   allow_methods=['GET', 'HEAD', 'POST'], allow_headers=['Content-Type'],
                   expose_headers=['x-request-id', 'x-trace-id'], allow_credentials=False)
app.add_middleware(RequestTelemetry)
app.include_router(upload_router)


def clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(422, "Enter a headline or article.")
    return value


def use_portable():
    return MODEL_DIR == DEFAULT_MODEL_DIR and 'FAKEDDIT_MODEL_DIR' not in os.environ and portable_text.RELEASE.is_file()


@app.get("/api/health")
@app.head("/api/health", include_in_schema=False)
def health():
    if use_portable():
        try:
            portable_text.load_release(str(portable_text.RELEASE))
            return {"status": "ok", "model_available": True, "model_status": "ready", "model_kind": "portable_fakeddit_text", "version": "2.4.0"}
        except (ValueError, OSError, KeyError):
            return {"status": "ok", "model_available": False, "model_status": "invalid_artifacts", "version": "2.4.0"}
    dependencies = all(find_spec(name) is not None for name in ("joblib", "sklearn", "numpy", "scipy"))
    artifacts = all((MODEL_DIR / name).is_file() for name in ("model.joblib", "metrics.json"))
    reason = "missing_artifacts" if not artifacts else "missing_dependencies" if not dependencies else "ready"
    if reason == "ready":
        try:
            load_model(str(MODEL_DIR))
        except Exception:
            logger.exception("Text checkpoint readiness failed")
            reason = "invalid_artifacts"
    return {"status": "ok", "model_available": reason == "ready", "model_status": reason, "version": "2.4.0"}


@app.get("/api/capabilities")
def capabilities():
    model = health()
    pair_model = multimodal.status()
    return {
        "text_analysis": True,
        "text_classifier": {"available": model["model_available"], "status": model["model_status"]},
        "media_inspection": "browser_local",
        "multimodal_classifier": pair_model,
        "image_inference": pair_model["available"],
        "video_inference": False,
        "fact_verification": verification.configuration()['available'],
        "verification": verification.configuration(),
        "research_quota": research_limit.status(),
        "tracing": tracing_configuration(),
        "news_detection": True,
        "limits": {"text_characters": 10000, "image_bytes": 10 * 1024 * 1024, "inference_image_bytes": image_upload_limit(), "video_bytes": 50 * 1024 * 1024},
        "note": "Reports describe language and supplied media metadata. They do not establish factual truth.",
    }


@app.get('/api/model-card')
def model_card():
    """Release facts, distinct from runtime readiness and live evidence verification."""
    provenance_path = ROOT / 'docs' / portable_text.MANIFEST_FILENAME
    if not provenance_path.is_file():
        raise HTTPException(status_code=503, detail='Model release provenance is unavailable')
    provenance = json.loads(provenance_path.read_text())
    evaluation_path = ROOT / 'docs/TEXT_RELIABILITY_EVALUATION.json'
    evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.is_file() else None
    shift_path = ROOT / 'docs/TEXT_SHIFT_EVALUATION.json'
    shift = json.loads(shift_path.read_text()) if shift_path.is_file() else None
    improvement_path = ROOT / 'docs/TEXT_MODEL_V2_EVALUATION.json'
    improvement = json.loads(improvement_path.read_text()) if improvement_path.is_file() else None
    pilot_path = ROOT / 'docs/MULTIMODAL_PILOT_EVALUATION.json'
    pilot = json.loads(pilot_path.read_text()) if pilot_path.is_file() else None
    comparison_path = ROOT / 'docs/MULTIMODAL_PILOT_COMPARISON.json'
    comparison = json.loads(comparison_path.read_text()) if comparison_path.is_file() else None
    return {'release': provenance['release'], 'metrics': provenance['metrics'],
            'dataset': provenance['provenance']['dataset'], 'artifact_sha256': provenance['artifact']['sha256'],
            'runtime': health(), 'score_type': 'uncalibrated_model_scores',
            'reliability_evaluation': evaluation,
            'shift_evaluation': shift,
            'historical_evaluation_releases': {'reliability_evaluation': 'text-v1', 'shift_evaluation': 'text-v1'},
            'accuracy_improvement': improvement,
            'offline_multimodal_pilot': ({'status': pilot['status'], 'production_model_changed': False,
                                          'metrics': pilot['metrics'], 'resources': pilot['resources'],
                                          'comparison': comparison, 'limitations': pilot['limitations']} if pilot else None),
            'limitations': ['English Reddit headlines; not validated for full articles or other languages.',
                            'Dataset labels do not establish factual truth.',
                            'Source-label shortcuts and time shift limit generalization; review the recorded stress tests.',
                            'No evaluated paired image release is bundled.',
                            'The linked calibration and original shift reports concern text-v1; text-v2 scores remain uncalibrated.',
                            'Historical test data was reused for regression evaluation; fresh external factual accuracy remains unmeasured.']}



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
    if list(classes) != [0, 1] or any(str(int(c)) not in metadata["labels"] for c in classes):
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
@stage('model.classify')
def predict(payload: TextInput):
    text = clean_text(payload.text)
    readiness = health()
    if not readiness["model_available"]:
        raise HTTPException(503, f"Text classifier unavailable: {readiness['model_status']}. The text explorer remains available.")
    try:
        if use_portable():
            return {"mode": "portable_text", **portable_text.predict(text)}
        model, metadata = load_model(str(MODEL_DIR))
        import numpy as np
        probabilities = np.asarray(model.predict_proba([text])[0], dtype=float)
        if (probabilities.shape != (2,) or not np.isfinite(probabilities).all()
                or (probabilities < 0).any() or (probabilities > 1).any()
                or not np.isclose(probabilities.sum(), 1)):
            raise ValueError("Model returned invalid probabilities")
        labels = metadata["labels"]
        return {"mode": "trained_text_baseline", "label": labels[str(int(model.classes_[np.argmax(probabilities)]))],
                "probabilities": {labels[str(int(c))]: float(p) for c, p in zip(model.classes_, probabilities)},
                "score_type": "uncalibrated_model_scores",
                "note": "Dataset classification is not a fact-check. This text-only baseline is separate from the original CLIP experiments."}
    except Exception:
        logger.exception("Trained model inference failed")
        raise HTTPException(503, "Model artifacts or inference dependencies are incomplete.")


@app.post('/api/detect')
async def detect_news(payload: DetectionInput, request: Request):
    text = clean_text(payload.text)
    if payload.source_url and not verification.safe_url(payload.source_url):
        raise HTTPException(422, 'Use a public HTTP or HTTPS source URL.')
    if payload.publication_date:
        from datetime import date
        try:
            date.fromisoformat(payload.publication_date)
        except ValueError:
            raise HTTPException(422, 'Publication date must use YYYY-MM-DD.')
    try:
        headline = next(line.strip() for line in text.splitlines() if line.strip())[:400]
        prediction = await run_in_threadpool(predict, TextInput(text=headline))
        model = {"status": "ready", **{key: value for key, value in prediction.items() if key != 'mode'}}
        model['assessed_text'] = headline
    except HTTPException:
        model = {"status": "unavailable", "label": "Model unavailable", "probabilities": {},
                 "note": "No trained model prediction could be produced."}
    config = verification.configuration()
    research_start = perf_counter()
    identity = research_identity(request)
    with stage('verification') as span:
        with stage('research.quota'):
            permitted = not config['available'] or await run_in_threadpool(research_limit.allow, identity)
        if not permitted:
            evidence = verification.unavailable(research_limit.failure_reason)
        else:
            evidence = await verification.verify(text, payload.source_url, payload.publication_date)
        attributes(span, **{'operation.status': evidence['status'], 'operation.reason': evidence.get('reason', 'completed'),
                             'source.count': len(evidence.get('sources', [])), 'claim.count': len(evidence.get('claims', []))})
    logging.getLogger('fakeddit.requests').info(json.dumps({
        'event': 'verification_result', 'request_id': getattr(request.state, 'request_id', None), 'trace_id': current_trace_id(),
        'status': evidence.get('status'), 'reason': evidence.get('reason'),
        'duration_ms': round((perf_counter()-research_start)*1000, 2)}))
    return {"mode": "news_detection", "model_assessment": model, "verification": evidence,
            "note": "Model prediction and source verification answer different questions. A model score is not a factual verdict."}


@app.get("/")
@app.head("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "frontend/index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "frontend/favicon.svg", media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
