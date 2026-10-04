"""Shared artifact contracts and leakage checks; no ML downloads."""
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1
PREPROCESSING = {
    "image": "exif_transpose_rgb_first_frame",
    "text": "strip_clip_tokenize_truncate",
    "normalization": "l2_per_modality",
    "feature_order": ["image", "text"],
}


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encoder_fingerprint(directory):
    directory = Path(directory)
    files = sorted(p for p in directory.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(directory).parts))
    if not files or not (directory / "config.json").is_file():
        raise ValueError("A local Hugging Face CLIP snapshot with config.json is required")
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(bytes.fromhex(digest_file(path)))
    return digest.hexdigest()


def validate_labels(labels):
    if (not isinstance(labels, dict) or set(labels) != {"0", "1"}
            or any(not isinstance(value, str) or not value.strip() for value in labels.values())
            or labels["0"] == labels["1"]):
        raise ValueError("Provide distinct verified labels for binary classes 0 and 1")
    return labels


def validate_manifest(manifest):
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("task") != "fakeddit_binary":
        raise ValueError("Unsupported checkpoint schema or classification task")
    validate_labels(manifest.get("labels"))
    if not isinstance(manifest.get("label_source"), str) or not manifest["label_source"].strip():
        raise ValueError("Record the source used to verify dataset label meanings")
    if manifest.get("preprocessing") != PREPROCESSING:
        raise ValueError("Incompatible preprocessing contract")
    fingerprint = manifest.get("encoder_sha256", "")
    if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
        raise ValueError("Missing encoder fingerprint")
    packages = manifest.get("encoder_packages", {})
    if set(packages) != {"torch", "transformers"} or any(not isinstance(value, str) or not value for value in packages.values()):
        raise ValueError("Record torch and transformers versions used for feature extraction")
    widths = manifest.get("widths", {})
    if set(widths) != {"image", "text"} or any(type(width) is not int or width < 1 for width in widths.values()):
        raise ValueError("Invalid modality dimensions")
    if widths["image"] != widths["text"]:
        raise ValueError("CLIP image and text projections must have equal dimensions")
    return manifest


def read_manifest(path):
    return validate_manifest(json.loads(Path(path).read_text()))


def check_content_disjoint(frames, text_column="clean_title", image_column="image_sha256"):
    """Reject exact normalized text and image duplicates across independent splits."""
    for column in (text_column, image_column):
        for i, left in enumerate(frames):
            if column not in left:
                continue
            a = left[column].astype(str)
            if column == text_column:
                a = a.str.strip().str.casefold().str.replace(r"\s+", " ", regex=True)
            for right in frames[i + 1:]:
                if column not in right:
                    continue
                b = right[column].astype(str)
                if column == text_column:
                    b = b.str.strip().str.casefold().str.replace(r"\s+", " ", regex=True)
                if set(a) & set(b):
                    raise ValueError(f"Duplicate {column} content across train/validation/test splits")
