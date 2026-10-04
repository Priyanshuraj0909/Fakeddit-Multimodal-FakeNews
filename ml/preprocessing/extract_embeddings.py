"""Extract paired CLIP features from a local dataset and local image directory."""
import argparse
import json
from pathlib import Path
import numpy as np
from ml.preprocessing.image_input import decode_image, MAX_IMAGE_BYTES
from ml.models.clip_encoder import ClipEncoder
from ml.utils.contracts import digest_file, PREPROCESSING, validate_manifest, validate_labels
from ml.training.train_text import read_split


def extract(dataset, images, encoder_directory, output, labels, label_source, encoder=None):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output folder is not empty; choose a new extraction directory")
    validate_labels(labels)
    if not label_source.strip():
        raise ValueError("Specify the source used to verify the label mapping")
    frame = read_split(dataset, "clean_title", "2_way_label")
    if "image_path" not in frame:
        raise ValueError("Dataset must contain image_path relative to --images")
    root = Path(images).resolve()
    encoder = encoder or ClipEncoder(encoder_directory)
    rows, visual, language, errors = [], [], [], []
    for _, row in frame.iterrows():
        try:
            path = (root / str(row["image_path"])).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Image path leaves the image directory")
            if path.stat().st_size > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds 10 MB")
            image = decode_image(path.read_bytes())
            try:
                image_features, text_features = encoder.encode(row["clean_title"], image)
            finally:
                image.close()
            item = row.to_dict()
            item["image_sha256"] = digest_file(path)
            rows.append(item)
            visual.append(image_features[0]); language.append(text_features[0])
        except (OSError, ValueError) as error:
            errors.append({"id": str(row["id"]), "reason": str(error)})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "skipped.json").write_text(json.dumps(errors, indent=2) + "\n")
    if not rows:
        raise ValueError("No valid paired samples; see skipped.json")
    import pandas as pd
    retained = pd.DataFrame(rows)
    if set(retained["2_way_label"]) != {0, 1}:
        raise ValueError("Retained samples must include both labels; inspect skipped.json")
    # Only identifiers, text, labels and content hash enter the aligned records.
    retained[["id", "clean_title", "2_way_label", "image_sha256"]].to_csv(output / "posts.csv", index=False)
    for name, arrays in (("image", visual), ("text", language)):
        np.savez_compressed(output / f"{name}.npz", ids=np.asarray(retained["id"].astype(str), dtype=str), embeddings=np.asarray(arrays))
    manifest = validate_manifest({"schema_version": 1, "task": "fakeddit_binary",
        "labels": labels, "label_source": label_source, "encoder_sha256": encoder.fingerprint,
        "preprocessing": PREPROCESSING, "encoder_packages": encoder.packages, "widths": {"image": len(visual[0]), "text": len(language[0])}})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"retained": len(rows), "skipped": len(errors)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "images", "encoder", "output", "labels", "label-source"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.dataset, args.images, args.encoder, args.output,
                             json.loads(Path(args.labels).read_text()), args.label_source), indent=2))


if __name__ == "__main__":
    main()
