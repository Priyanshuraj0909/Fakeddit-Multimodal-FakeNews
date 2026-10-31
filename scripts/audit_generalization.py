"""Audit prepared release IDs against raw metadata without modifying benchmark splits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from ml.training.train_text import read_split, check_disjoint
from ml.utils.contracts import check_content_disjoint, digest_file


def fingerprint(text):
    tokens = re.findall(r'\w+', str(text).casefold())
    if len(tokens) < 5:
        return None
    # SimHash is a lexical candidate detector, not a semantic equivalence test.
    terms = set(tokens + [' '.join(pair) for pair in zip(tokens, tokens[1:])])
    vector = [0]*64
    for term in terms:
        value = int.from_bytes(hashlib.blake2b(term.encode(), digest_size=8).digest(), 'big')
        for bit in range(64):
            vector[bit] += 1 if (value >> bit) & 1 else -1
    return sum(1 << bit for bit, value in enumerate(vector) if value >= 0)


def near_overlap(reference, query):
    index = {}
    for value in reference:
        if value is not None:
            for band in range(4):
                index.setdefault((band, (value >> (band*16)) & 65535), set()).add(value)
    matches = eligible = 0
    for value in query:
        if value is None:
            continue
        eligible += 1
        candidates = set()
        for band in range(4):
            candidates.update(index.get((band, (value >> (band*16)) & 65535), ()))
        matches += any((value ^ candidate).bit_count() <= 3 for candidate in candidates)
    return {'eligible_query_rows': eligible, 'candidate_overlap_rows': matches,
            'fraction': matches/eligible if eligible else None}


def audit(raw, prepared, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new audit output')
    frames, sources = [], {}
    for name, original in [('train', 'train'), ('validation', 'validate'), ('test', 'test_public')]:
        path = Path(prepared)/f'{name}.csv'
        frame = read_split(path, 'clean_title', '2_way_label')
        source = Path(raw)/f'multimodal_{original}.tsv'
        metadata = pd.read_csv(source, sep='\t', usecols=['id', 'author', 'domain', 'subreddit', 'created_utc'], dtype={'id': 'string'})
        frame = frame.merge(metadata, on='id', how='left', validate='one_to_one', indicator=True)
        if not frame['_merge'].eq('both').all():
            raise ValueError('Prepared IDs missing from original metadata')
        frames.append(frame)
        sources[name] = {'prepared_sha256': digest_file(path), 'raw_sha256': digest_file(source), 'rows': len(frame)}
    check_disjoint(frames)
    check_content_disjoint(frames)
    result = {'evaluated_at': datetime.now(timezone.utc).isoformat(), 'splits': sources, 'group_overlap': {}, 'metadata_shortcut_baselines': {}, 'time_ranges': {}}
    for column in ('author', 'domain', 'subreddit'):
        training = set(frames[0][column].dropna().astype(str)) - {'[deleted]', '[removed]', ''}
        result['group_overlap'][column] = {}
        for name, frame in zip(('validation', 'test'), frames[1:]):
            valid = frame[column].notna() & ~frame[column].isin(['[deleted]', '[removed]', ''])
            seen = valid & frame[column].isin(training)
            result['group_overlap'][column][name] = {'known_group_rows': int(valid.sum()), 'seen_in_train_rows': int(seen.sum()), 'fraction_of_known': float(seen.sum()/valid.sum()) if valid.any() else None}
        if column != 'author':
            # Train-only group-majority classifier diagnoses source shortcuts; never selects the deployed model.
            majority = frames[0].groupby(column)['2_way_label'].mean().ge(.5).astype(int)
            fallback = int(frames[0]['2_way_label'].mean() >= .5)
            predictions = frames[2][column].map(majority).fillna(fallback).astype(int)
            result['metadata_shortcut_baselines'][column] = {'test_accuracy': float(accuracy_score(frames[2]['2_way_label'], predictions)), 'test_macro_f1': float(f1_score(frames[2]['2_way_label'], predictions, average='macro'))}
    for name, frame in zip(('train', 'validation', 'test'), frames):
        times = pd.to_datetime(frame['created_utc'], unit='s', utc=True, errors='coerce')
        result['time_ranges'][name] = {'minimum': times.min().isoformat(), 'maximum': times.max().isoformat(), 'missing': int(times.isna().sum())}
    signatures = [[fingerprint(text) for text in frame['clean_title']] for frame in frames]
    result['lexical_near_duplicate_candidates'] = {name: near_overlap(signatures[0], values) for name, values in zip(('validation', 'test'), signatures[1:])}
    result['limitations'] = ['Observational audit; existing official splits are preserved.',
                            'SimHash uses word/unigram-bigram sets, 64 bits, Hamming distance <=3, minimum five tokens. Candidates need human review; this is not semantic deduplication.',
                            'Group overlap is not a source/author-disjoint benchmark; no such performance is claimed.',
                            'Metadata-majority baselines are fitted on training only; metadata is not used by the deployed classifier.']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'group_overlap': result['group_overlap'], 'metadata_shortcut_baselines': result['metadata_shortcut_baselines']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', default='data/raw')
    parser.add_argument('--prepared', default='data/processed/text-release-v1')
    parser.add_argument('--output', required=True)
    audit(**vars(parser.parse_args()))
