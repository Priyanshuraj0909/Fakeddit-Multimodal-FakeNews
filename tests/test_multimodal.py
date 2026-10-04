"""Synthetic and mocked regressions; no downloaded checkpoint/benchmark claims."""
from io import BytesIO
import json
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app
from ml.inference import multimodal
from ml.preprocessing.image_input import decode_image, MAX_IMAGE_BYTES
from ml.utils.contracts import PREPROCESSING, check_content_disjoint, encoder_fingerprint
from ml.preprocessing.extract_embeddings import extract
from ml.training.train_multimodal import train, validate_splits

client = TestClient(app)


def png():
    out = BytesIO()
    Image.new("RGB", (8, 8), "red").save(out, format="PNG")
    return out.getvalue()


def test_pair_input_validation_and_missing_checkpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKEDDIT_MULTIMODAL_DIR", str(tmp_path))
    assert client.post("/api/predict/multimodal", data={"text": "headline"}).status_code == 422
    for text in ("", " ", "x" * 10001):
        assert client.post("/api/predict/multimodal", data={"text": text}, files={"image": ("x.png", png(), "image/png")}).status_code == 422
    for data, mime in ((b"", "image/png"), (b"broken", "image/png"), (b"<svg/>", "image/svg+xml"), (png(), "video/mp4")):
        assert client.post("/api/predict/multimodal", data={"text": "headline"}, files={"image": ("x", data, mime)}).status_code == 415
    response = client.post("/api/predict/multimodal", data={"text": "headline"}, files={"image": ("x.png", png(), "image/png")})
    assert response.status_code == 503
    assert "missing_artifacts" in response.json()["detail"]


def test_upload_limit_including_raw_body():
    response = client.post("/api/predict/multimodal", data={"text": "headline"}, files={"image": ("x.png", b"x" * (MAX_IMAGE_BYTES + 1), "image/png")})
    assert response.status_code == 413
    response = client.post("/api/predict/multimodal", content=b"x" * (MAX_IMAGE_BYTES + 128 * 1024 + 1))
    assert response.status_code == 413


def test_mocked_pair_api_and_inference_failure(monkeypatch):
    monkeypatch.setattr(multimodal, "status", lambda: {"available": True, "status": "ready"})
    captured = {}
    def predict(text, image):
        captured.update(text=text, mode=image.mode, size=image.size)
        return {"mode": "trained_multimodal", "label": "Fixture class 1", "scores": {"Fixture class 0": .2, "Fixture class 1": .8},
                "note": "MOCKED MODEL: integration fixture only", "image_assessed": True}
    monkeypatch.setattr(multimodal, "predict_pair", predict)
    response = client.post("/api/predict/multimodal", data={"text": "  headline  "}, files={"image": ("x.png", png(), "image/png")})
    assert response.status_code == 200
    assert captured == {"text": "headline", "mode": "RGB", "size": (8, 8)}
    assert response.json()["image_assessed"] is True
    def broken(*_):
        raise RuntimeError("Private checkpoint failure")
    monkeypatch.setattr(multimodal, "predict_pair", broken)
    response = client.post("/api/predict/multimodal", data={"text": "headline"}, files={"image": ("x.png", png(), "image/png")})
    assert response.status_code == 503
    assert "Private checkpoint" not in response.text


def test_pixel_limit_and_decoder():
    decoded = decode_image(png())
    assert decoded.mode == "RGB"
    decoded.close()
    out = BytesIO()
    Image.new("1", (5000, 5000)).save(out, "PNG")
    with pytest.raises(ValueError, match="megapixel"):
        decode_image(out.getvalue())


def test_duplicate_content_detection():
    a = pd.DataFrame({"clean_title": ["A HEADLINE"], "image_sha256": ["a" * 64]})
    b = pd.DataFrame({"clean_title": ["  a   headline "], "image_sha256": ["b" * 64]})
    with pytest.raises(ValueError, match="clean_title"):
        check_content_disjoint([a, b])
    b["clean_title"] = ["Different"]
    b["image_sha256"] = ["a" * 64]
    with pytest.raises(ValueError, match="image_sha256"):
        check_content_disjoint([a, b])


def make_splits(tmp_path):
    manifest = {"schema_version": 1, "task": "fakeddit_binary", "labels": {"0": "Fixture class 0", "1": "Fixture class 1"},
                "label_source": "Synthetic test fixture, not Fakeddit", "preprocessing": PREPROCESSING,
                "encoder_packages": {"torch": "fixture", "transformers": "fixture"},
                "encoder_sha256": "a" * 64, "widths": {"image": 2, "text": 2}}
    folders = []
    for number, split in enumerate(("train", "validation", "test")):
        folder = tmp_path / split; folder.mkdir()
        ids = np.asarray([f"{split}-{i}" for i in range(12)])
        labels = np.arange(12) % 2
        pd.DataFrame({"id": ids, "clean_title": [f"{split} unique {i}" for i in range(12)], "2_way_label": labels,
                      "image_sha256": [f"{number * 12 + i:064x}" for i in range(12)]}).to_csv(folder / "posts.csv", index=False)
        for modality in ("image", "text"):
            np.savez(folder / f"{modality}.npz", ids=ids, embeddings=np.column_stack([labels, 1-labels]).astype(float))
        (folder / "manifest.json").write_text(json.dumps(manifest))
        folders.append(folder)
    return folders


def test_per_modality_dimensions_even_when_total_matches(tmp_path):
    folders = make_splits(tmp_path)
    ids = np.asarray([f"test-{i}" for i in range(12)])
    np.savez(folders[2] / "image.npz", ids=ids, embeddings=np.ones((12, 1)))
    np.savez(folders[2] / "text.npz", ids=ids, embeddings=np.ones((12, 3)))
    with pytest.raises(ValueError, match="Individual modality"):
        validate_splits(folders)


def test_reject_encoder_or_label_mismatch(tmp_path):
    folders = make_splits(tmp_path)
    path = folders[2] / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["encoder_sha256"] = "b" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differ across splits"):
        validate_splits(folders)


def test_small_xgboost_pipeline_and_mock_encoder_inference(tmp_path, monkeypatch):
    folders = make_splits(tmp_path)
    output = tmp_path / "checkpoint"
    metrics = train(*folders, output, compare=True, estimators=12)
    assert "macro_f1" in metrics and "confusion_matrix" in metrics
    assert set(metrics["ablations"]) == {"image_only", "text_only"}
    assert (output / "test_errors.json").is_file()
    class FakeEncoder:
        def __init__(self, *_): pass
        def encode(self, *_): return [np.asarray([[0., 1.]]), np.asarray([[0., 1.]])]
    from ml.models import clip_encoder
    monkeypatch.setattr(clip_encoder, "ClipEncoder", FakeEncoder)
    monkeypatch.setenv("FAKEDDIT_MULTIMODAL_DIR", str(output))
    monkeypatch.setenv("FAKEDDIT_ENCODER_DIR", str(tmp_path))
    multimodal.load_pipeline.cache_clear()
    result = multimodal.predict_pair("fixture", None)
    assert result["mode"] == "trained_multimodal"
    assert sum(result["scores"].values()) == pytest.approx(1)
    (output / "model.json").write_text("{}")
    multimodal.load_pipeline.cache_clear()
    with pytest.raises(ValueError, match="checksum"):
        multimodal.load_pipeline(str(output), str(tmp_path))
    multimodal.load_pipeline.cache_clear()


def test_extraction_records_skips_and_safe_paths(tmp_path):
    images = tmp_path / "images"; images.mkdir()
    (images / "one.png").write_bytes(png()); (images / "two.png").write_bytes(png())
    dataset = tmp_path / "data.csv"
    pd.DataFrame({"id": ["001", "002", "003", "004"], "clean_title": ["one", "two", "missing", "escape"],
                  "2_way_label": [0,1,0,1], "image_path": ["one.png", "two.png", "missing.png", "../outside.png"]}).to_csv(dataset, index=False)
    class FakeEncoder:
        fingerprint = "a" * 64
        packages = {"torch": "fixture", "transformers": "fixture"}
        def encode(self, *_): return [np.asarray([[1., 0.]]), np.asarray([[0., 1.]])]
    output = tmp_path / "features"
    result = extract(dataset, images, None, output, {"0": "Fixture 0", "1": "Fixture 1"}, "Synthetic", encoder=FakeEncoder())
    assert result == {"retained": 2, "skipped": 2}
    with np.load(output / "image.npz", allow_pickle=False) as archive:
        assert archive["ids"].tolist() == ["001", "002"]
    assert len(json.loads((output / "skipped.json").read_text())) == 2


def test_encoder_fingerprint_detects_changes(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "weights.safetensors").write_bytes(b"fixture")
    before = encoder_fingerprint(tmp_path)
    (tmp_path / "weights.safetensors").write_bytes(b"changed")
    assert encoder_fingerprint(tmp_path) != before


def test_pair_preparation_records_missing_and_ambiguous_images(tmp_path):
    from ml.datasets.prepare_pairs import prepare
    images = tmp_path / "images"; images.mkdir()
    for name in ("001.png", "002.jpg", "004.png", "004.jpg"):
        (images / name).write_bytes(png())
    dataset = tmp_path / "source.tsv"
    pd.DataFrame({"id": ["001", "002", "003", "004"], "clean_title": ["one", "two", "three", "four"],
                  "2_way_label": [0,1,0,1]}).to_csv(dataset, sep="\t", index=False)
    output = tmp_path / "paired.csv"
    assert prepare(dataset, images, output) == {"paired": 2, "skipped": 2}
    assert pd.read_csv(output, dtype={"id": str})["id"].tolist() == ["001", "002"]
    with pytest.raises(ValueError, match="already exists"):
        prepare(dataset, images, output)


def test_vercel_limit_is_distinct_from_local_preview_limit(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    data = client.get("/api/capabilities").json()
    assert data["limits"]["image_bytes"] == MAX_IMAGE_BYTES
    assert data["limits"]["inference_image_bytes"] == 4 * 1024 * 1024
    response = client.post("/api/predict/multimodal", data={"text": "headline"},
                           files={"image": ("large.png", b"x" * (4 * 1024 * 1024 + 1), "image/png")})
    assert response.status_code == 413
