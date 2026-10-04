# Pipeline configuration

CLIs expose paths through --help; scripts/train.py dispatches text or multimodal training and scripts/preprocess.py dispatches pairs or embeddings. Current training uses reproducible seed 42. Manifest files record actual encoder/preprocessing/label contracts. See docs/TRAINING.md; no undocumented config file overrides exist.
