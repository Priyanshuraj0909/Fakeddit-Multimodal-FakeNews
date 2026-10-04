"""Create deterministic headline subsets from official Fakeddit splits; record exclusions."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from ml.utils.contracts import digest_file


def prepare(raw, output, limits=(150000, 15000, 15000)):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a new empty output directory')
    output.mkdir(parents=True, exist_ok=True)
    seen_ids, seen_text = set(), set()
    records = {}
    for name, original, limit in zip(('train', 'validation', 'test'), ('train', 'validate', 'test_public'), limits):
        source = Path(raw) / f'multimodal_{original}.tsv'
        frame = pd.read_csv(source, sep='\t', usecols=['id', 'clean_title', '2_way_label', '6_way_label'], dtype={'id': str})
        if not (frame['2_way_label'] == (frame['6_way_label'] == 0).astype(int)).all():
            raise ValueError('Binary labels differ from the verified true class in 6-way labels')
        before = len(frame)
        frame = frame.dropna().copy()
        frame['clean_title'] = frame['clean_title'].astype(str).str.strip()
        frame['id'] = frame['id'].str.strip()
        frame = frame[frame['clean_title'].ne('') & frame['id'].ne('')]
        normalized = frame['clean_title'].str.casefold().str.replace(r'\s+', ' ', regex=True)
        frame = frame.assign(_normalized=normalized)
        frame = frame.drop_duplicates('id').drop_duplicates('_normalized')
        frame = frame[~frame['id'].isin(seen_ids) & ~frame['_normalized'].isin(seen_text)]
        # Reserve ALL clean earlier-split content, so sampling cannot hide leakage.
        seen_ids.update(frame['id']); seen_text.update(frame['_normalized'])
        eligible = len(frame)
        frame = frame.sample(n=min(limit, eligible), random_state=42)
        frame[['id', 'clean_title', '2_way_label']].to_csv(output / f'{name}.csv', index=False)
        records[name] = {'source': str(source), 'source_sha256': digest_file(source), 'original_rows': before,
                         'eligible_rows': eligible, 'excluded_rows': before-eligible, 'selected_rows': len(frame),
                         'class_counts': {str(k): int(v) for k,v in frame['2_way_label'].value_counts().items()}}
    provenance = {'dataset': 'Official Fakeddit v2 multimodal-only samples, text branch only',
                  'source': 'https://github.com/entitize/Fakeddit', 'seed': 42,
                  'labels': {'0': 'Likely fake / misleading', '1': 'Likely real'},
                  'label_source': 'https://github.com/entitize/Fakeddit/issues/14#issuecomment-815355653; all rows verified: binary 1 iff six-way label 0 (true)',
                  'sampling': 'Fixed-seed subsets within official splits after ID and normalized exact-text exclusion', 'splits': records}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    (output / 'labels.json').write_text(json.dumps(provenance['labels'])+'\n')
    return provenance

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', default='data/raw')
    parser.add_argument('--output', default='data/processed/text-release-v1')
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw, args.output), indent=2))
