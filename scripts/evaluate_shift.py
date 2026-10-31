"""Exploratory author/domain holdouts and a separately retrained chronological baseline."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, f1_score
from ml.training.train_text import read_split, check_disjoint
from ml.utils.contracts import check_content_disjoint, digest_file

MISSING = {'', '[deleted]', '[removed]'}


def unseen_mask(reference, query, column):
    known = set(reference[column].dropna().astype(str)) - MISSING
    values = query[column]
    valid = values.notna() & ~values.astype(str).isin(MISSING)
    return valid & ~values.astype(str).isin(known)


def summarize(frame, predicted):
    if not len(frame):
        return {'status': 'unavailable', 'reason': 'No eligible held-out examples', 'rows': 0}
    labels = frame['2_way_label'].to_numpy()
    accuracy = float(accuracy_score(labels, predicted))
    n, z = len(labels), 1.96
    center = (accuracy + z*z/(2*n))/(1+z*z/n)
    radius = z*np.sqrt(accuracy*(1-accuracy)/n + z*z/(4*n*n))/(1+z*z/n)
    errors = [{'id': str(identity), 'expected': int(label), 'predicted': int(pred)} for identity, label, pred in zip(frame['id'], labels, predicted) if label != pred]
    return {'status': 'evaluated', 'rows': n, 'class_counts': {str(k): int(v) for k,v in frame['2_way_label'].value_counts().items()},
            'accuracy': accuracy, 'accuracy_wilson_95': [float(center-radius), float(center+radius)],
            'macro_f1': float(f1_score(labels, predicted, labels=[0, 1], average='macro', zero_division=0)),
            'classification_report': classification_report(labels, predicted, labels=[0, 1], output_dict=True, zero_division=0),
            'evaluated_ids_sha256': hashlib.sha256('\n'.join(sorted(frame['id'].astype(str))).encode()).hexdigest(),
            'error_count': len(errors), 'first_20_error_ids': errors[:20]}


def evaluate(raw, prepared, directory, output, cutoff='2018-01-01'):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new output; existing research records are preserved')
    root = Path(__file__).resolve().parents[1]
    provenance = json.loads((root/'docs/TEXT_RELIABILITY_EVALUATION.json').read_text())
    model_path = Path(directory)/'model.joblib'
    if digest_file(model_path) != provenance['model_sha256']:
        raise ValueError('Frozen checkpoint differs from recorded text-v1 provenance')
    frames, inputs = [], {}
    for name, original in [('train','train'), ('validation','validate'), ('test','test_public')]:
        path = Path(prepared)/f'{name}.csv'
        if digest_file(path) != provenance['splits'][name]['sha256']:
            raise ValueError(f'{name} differs from recorded model split')
        source = Path(raw)/f'multimodal_{original}.tsv'
        frame = read_split(path, 'clean_title', '2_way_label')
        metadata = pd.read_csv(source, sep='\t', usecols=['id','author','domain','created_utc'], dtype={'id':'string'})
        frame = frame.merge(metadata, on='id', how='left', validate='one_to_one', indicator=True)
        if not frame['_merge'].eq('both').all():
            raise ValueError('Raw metadata does not cover prepared IDs')
        frame['timestamp'] = pd.to_datetime(frame['created_utc'], unit='s', utc=True, errors='raise')
        if frame['timestamp'].isna().any():
            raise ValueError('Chronological evaluation requires complete timestamps')
        frames.append(frame)
        inputs[name] = {'prepared_sha256': digest_file(path), 'raw_sha256': digest_file(source), 'rows': len(frame)}
    check_disjoint(frames)
    check_content_disjoint(frames)
    training, validation, test = frames
    model = joblib.load(model_path)  # Trusted local checkpoint only.
    reference = pd.concat([training, validation], ignore_index=True)
    masks = {column: unseen_mask(reference, test, column) for column in ('author', 'domain')}
    masks['author_and_domain'] = masks['author'] & masks['domain']
    subgroup = {}
    for name, mask in masks.items():
        subset = test.loc[mask]
        subgroup[name] = summarize(subset, model.predict(subset['clean_title']) if len(subset) else [])
    date = pd.Timestamp(cutoff, tz='UTC')
    earlier_train = training.loc[training['timestamp'] < date]
    earlier_validation = validation.loc[validation['timestamp'] < date]
    future_test = test.loc[test['timestamp'] >= date]
    for frame in (earlier_train, earlier_validation, future_test):
        if set(frame['2_way_label']) != {0,1}:
            raise ValueError('Temporal subsets require both classes')
    candidates = []
    for regularization in (.1, 1., 10.):
        pipeline = Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=40000, sublinear_tf=True)),
                             ('classifier', LogisticRegression(C=regularization, max_iter=1000, random_state=42))])
        pipeline.fit(earlier_train['clean_title'], earlier_train['2_way_label'])
        score = float(f1_score(earlier_validation['2_way_label'], pipeline.predict(earlier_validation['clean_title']), average='macro', zero_division=0))
        candidates.append((score, regularization, pipeline))
    score, selected_c, temporal = max(candidates, key=lambda item: item[0])
    result = {'evaluated_at': datetime.now(timezone.utc).isoformat(), 'status': 'exploratory_evaluation', 'model_sha256': digest_file(model_path),
              'splits': inputs, 'frozen_release_unseen_groups': subgroup,
              'group_protocol': 'Test groups absent from BOTH training and validation; missing/deleted authors and missing domains excluded. Frozen release unchanged. Subgroups are not newly collected external data.',
              'temporal': {'cutoff_utc': date.isoformat(), 'seed': 42, 'max_features': 40000, 'selected_C': selected_c,
                           'selection': 'Highest validation macro F1 on pre-cutoff validation only',
                           'validation_candidates': [{'C': c, 'macro_f1': value} for value,c,_ in candidates],
                           'rows': {'train':len(earlier_train), 'validation':len(earlier_validation), 'test':len(future_test)},
                           'train_maximum': earlier_train['timestamp'].max().isoformat(),
                           'validation_maximum': earlier_validation['timestamp'].max().isoformat(),
                           'test_minimum': future_test['timestamp'].min().isoformat(),
                           'test': summarize(future_test, temporal.predict(future_test['clean_title']))},
              'limitations': ['Exploratory stress tests on previously used official release subsets; not new external validation.',
                              'Temporal model is fitted from scratch on pre-cutoff train only; TF-IDF is never fitted on validation/test.',
                              'Cutoff fixed at 2018-01-01 before this experiment; not optimized using test scores.',
                              'Author/domain subgroup performance can reflect label/composition shifts; small subgroups have wide uncertainty.',
                              'Subreddit labels and semantic near-duplicates may still introduce shortcuts.',
                              'No factual-truth, image, consistency, evidence-support or new production model accuracy is established.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', default='data/raw')
    parser.add_argument('--prepared', default='data/processed/text-release-v1')
    parser.add_argument('--directory', default='models/exported/text-release-v1')
    parser.add_argument('--output', required=True)
    args=parser.parse_args()
    report=evaluate(**vars(args))
    print(json.dumps({'output':args.output,'unseen_groups':{k:{x:v.get(x) for x in ('rows','accuracy','macro_f1')} for k,v in report['frozen_release_unseen_groups'].items()}, 'temporal': {k:report['temporal']['test'][k] for k in ('rows','accuracy','macro_f1')}}))
