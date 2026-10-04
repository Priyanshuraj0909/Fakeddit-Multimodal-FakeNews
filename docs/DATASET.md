# Dataset contracts

Obtain data from the [Fakeddit publisher](https://github.com/entitize/Fakeddit); no dataset is bundled or automatically downloaded. scripts/download_data.py accepts an explicit direct HTTPS URL and refuses to overwrite files.

Raw CSV/TSV splits require id, clean_title and 2_way_label, with binary labels and unique nonempty IDs. Verify class semantics against the publisher rather than assuming 0/1 meanings. Keep train, validation and test independent. Use multimodal samples for paired benchmark evaluation.

Put raw inputs in data/raw, paired CSVs/features in data/processed, and small local examples in data/samples. scripts/preprocess.py pairs maps image filename stems to post IDs, rejects ambiguous matches, and records missing-image exclusions. Embedding extraction records missing/corrupt inputs, image SHA256, aligned IDs and a strict manifest.

Each extracted split contains posts.csv, image.npz, text.npz and manifest.json. Individual modality dimensions, local encoder fingerprint, dependency versions, preprocessing and label provenance must match. Training rejects cross-split IDs and exact repeated text/image content. Near-duplicate and author-disjoint checks remain future work. See TRAINING.md for commands.
