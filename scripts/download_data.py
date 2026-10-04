"""Download a user-selected dataset file without assuming redistribution rights."""
import argparse
from pathlib import Path
import shutil
import urllib.request
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Direct HTTPS file URL obtained from the dataset publisher")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if urlparse(args.url).scheme != "https":
        parser.error("Use an HTTPS dataset URL")
    output = Path(args.output)
    if output.exists():
        parser.error("Output exists; choose a new filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(args.url, timeout=60) as response, output.open("xb") as target:
            shutil.copyfileobj(response, target)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    print(output)

if __name__ == "__main__":
    main()
