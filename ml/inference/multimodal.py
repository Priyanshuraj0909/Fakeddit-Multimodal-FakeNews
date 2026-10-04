"""Optional real multimodal inference; unavailable checkpoints never yield predictions."""
from functools import lru_cache
from pathlib import Path
import os
import logging
from importlib.util import find_spec
from ml.utils.contracts import read_manifest, digest_file

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def locations():
    return (Path(os.environ.get("FAKEDDIT_MULTIMODAL_DIR", ROOT / "models/exported/multimodal")),
            Path(os.environ.get("FAKEDDIT_ENCODER_DIR", ROOT / "models/checkpoints/clip")))


def status():
    model_dir, encoder_dir = locations()
    if not all((model_dir / name).is_file() for name in ("model.json", "manifest.json")):
        return {"available": False, "status": "missing_artifacts"}
    if not encoder_dir.is_dir():
        return {"available": False, "status": "missing_encoder"}
    if not all(find_spec(name) is not None for name in ("torch", "transformers", "xgboost", "numpy")):
        return {"available": False, "status": "missing_dependencies"}
    try:
        load_pipeline(str(model_dir), str(encoder_dir))
    except Exception:
        # Record the actual root cause server-side; never substitute a prediction.
        logger.exception("Multimodal checkpoint readiness failed")
        return {"available": False, "status": "invalid_artifacts"}
    return {"available": True, "status": "ready"}


@lru_cache(maxsize=1)
def load_pipeline(model_directory, encoder_directory):
    import numpy as np
    from xgboost import XGBClassifier
    from ml.models.clip_encoder import ClipEncoder
    model_directory = Path(model_directory)
    manifest = read_manifest(model_directory / "manifest.json")
    if manifest.get("model_sha256") != digest_file(model_directory / "model.json"):
        raise ValueError("Checkpoint checksum mismatch")
    encoder = ClipEncoder(encoder_directory, manifest["encoder_sha256"], manifest["encoder_packages"])
    model = XGBClassifier()
    model.load_model(model_directory / "model.json")
    if model.n_features_in_ != sum(manifest["widths"].values()) or not np.array_equal(model.classes_, [0, 1]):
        raise ValueError("Checkpoint dimensions/classes do not match its manifest")
    return model, encoder, manifest


def predict_pair(text, image):
    import numpy as np
    from ml.models.fusion_model import fuse_features
    model_dir, encoder_dir = locations()
    model, encoder, manifest = load_pipeline(str(model_dir), str(encoder_dir))
    visual, language = encoder.encode(text, image)
    if visual.shape != (1, manifest["widths"]["image"]) or language.shape != (1, manifest["widths"]["text"]):
        raise ValueError("Inference embedding dimensions do not match training")
    scores = np.asarray(model.predict_proba(fuse_features(visual, language))[0], dtype=float)
    if scores.shape != (2,) or not np.isfinite(scores).all() or (scores < 0).any() or (scores > 1).any() or not np.isclose(scores.sum(), 1):
        raise ValueError("Model returned invalid scores")
    winner = int(np.argmax(scores))
    return {"mode": "trained_multimodal", "label": manifest["labels"][str(winner)],
            "scores": {manifest["labels"][str(i)]: float(score) for i, score in enumerate(scores)},
            "task": manifest["task"], "label_source": manifest["label_source"],
            "note": "Text-and-image model assessment of dataset classes. Scores are not calibrated truth probabilities; verify external evidence.",
            "image_assessed": True}
