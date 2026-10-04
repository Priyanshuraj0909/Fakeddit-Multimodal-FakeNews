"""Pair local images with Fakeddit post IDs without downloading data."""
import argparse
import json
from pathlib import Path
from ml.training.train_text import read_split


def prepare(dataset, images, output):
    frame = read_split(dataset, "clean_title", "2_way_label")
    root = Path(images).resolve()
    if not root.is_dir():
        raise ValueError("Choose an existing local image directory")
    index = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"}:
            index.setdefault(path.stem, []).append(path)
    rows, skipped = [], []
    for _, row in frame.iterrows():
        candidates = index.get(str(row["id"]), [])
        if len(candidates) != 1:
            skipped.append({"id": str(row["id"]), "reason": "missing image" if not candidates else "ambiguous image filenames"})
            continue
        path = candidates[0].resolve()
        if not path.is_relative_to(root):
            skipped.append({"id": str(row["id"]), "reason": "image path leaves image directory"})
            continue
        rows.append({"id": str(row["id"]), "clean_title": row["clean_title"], "2_way_label": int(row["2_way_label"]),
                     "image_path": path.relative_to(root).as_posix()})
    import pandas as pd
    output = Path(output)
    if output.exists():
        raise ValueError("Output already exists; choose a new paired dataset filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(output.suffix + ".skipped.json").write_text(json.dumps(skipped, indent=2) + "\n")
    if not rows or set(item["2_way_label"] for item in rows) != {0, 1}:
        raise ValueError("Paired records must contain both labels; inspect the skipped record file")
    pd.DataFrame(rows).to_csv(output, index=False)
    return {"paired": len(rows), "skipped": len(skipped)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "images", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.dataset, args.images, args.output), indent=2))


if __name__ == "__main__":
    main()
