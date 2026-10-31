"""Safe, dependency-free inference for evaluated TF-IDF linear releases."""
from collections import Counter
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import re

TOKEN = re.compile(r"(?u)\b\w\w+\b")
RELEASE = Path(__file__).resolve().parents[2] / "backend/app/models/releases/text-v2.json.gz"
MANIFEST_FILENAME = 'TEXT_MODEL_V2_RELEASE.json'
LABELS = {"0": "Likely fake / misleading", "1": "Likely real"}


def _valid_features(features):
    return (isinstance(features, dict) and bool(features) and
            all(isinstance(term, str) and isinstance(weights, list) and len(weights) == 2
                and all(type(value) in (float, int) and math.isfinite(value) for value in weights)
                and weights[0] > 0 for term, weights in features.items()))


@lru_cache(maxsize=4)
def load_release(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        data = json.load(stream)
    schema = data.get('schema')
    if data.get('labels') != LABELS or schema not in {'fakeddit_tfidf_logistic_v1', 'fakeddit_tfidf_linear_v2'}:
        raise ValueError('Unsupported portable model')
    if schema == 'fakeddit_tfidf_logistic_v1':
        if not _valid_features(data.get('features')):
            raise ValueError('Invalid TF-IDF feature weights')
    else:
        branches = data.get('branches')
        if not isinstance(branches, list) or not 1 <= len(branches) <= 2:
            raise ValueError('Invalid portable feature branches')
        names = set()
        for branch in branches:
            name = branch.get('name')
            expected = {'word': ('word', [1, 2]), 'character': ('char_wb', [3, 5])}.get(name)
            if (expected is None or name in names or (branch.get('analyzer'), branch.get('ngram_range')) != expected
                    or not _valid_features(branch.get('features'))):
                raise ValueError('Invalid portable feature branch')
            names.add(name)
        if 'word' not in names:
            raise ValueError('A word vocabulary is required for usability checks')
    if type(data.get('intercept')) not in (float, int) or not math.isfinite(data['intercept']):
        raise ValueError('Invalid model intercept')
    metrics = data.get('metrics', {})
    if not isinstance(metrics, dict) or type(metrics.get('rows', {}).get('test')) is not int or metrics['rows']['test'] <= 0:
        raise ValueError('Missing evaluated release provenance')
    if any(type(metrics.get(key)) not in (int, float) or not 0 <= metrics[key] <= 1 for key in ['test_accuracy', 'test_macro_f1']):
        raise ValueError('Invalid release evaluation metrics')
    return data


def feature_counts(text, analyzer):
    if analyzer == 'word':
        words = TOKEN.findall(text.lower())
        return Counter(words + [f'{a} {b}' for a, b in zip(words, words[1:])])
    counts = Counter()
    for word in text.lower().split():
        padded = ' ' + word + ' '
        for width in range(3, 6):
            # Match sklearn char_wb, including short words counted once.
            counts.update(padded[offset:offset+width] for offset in range(max(1, len(padded)-width+1)))
            if len(padded) <= width:
                break
    return counts


def _contributions(text, branch):
    features = branch['features']
    weighted = [(term, (1 + math.log(count)) * features[term][0], features[term][1])
                for term, count in feature_counts(text, branch['analyzer']).items() if term in features]
    norm = math.sqrt(sum(value*value for _, value, _ in weighted))
    if not norm:
        return []
    return [(('character fragment: ' + repr(term)) if branch['analyzer'] == 'char_wb' else term,
             value*coefficient/norm) for term, value, coefficient in weighted]


def predict(text, path=None):
    data = load_release(str(path or RELEASE))
    branches = data.get('branches') or [{'name': 'word', 'analyzer': 'word', 'features': data['features']}]
    words = TOKEN.findall(text.lower())
    word_features = next(branch['features'] for branch in branches if branch['analyzer'] == 'word')
    coverage = sum(word in word_features for word in words) / max(1, len(words))
    contributions = [item for branch in branches for item in _contributions(text, branch)]
    if not contributions or len(words) < 3 or coverage < .2:
        return {'status': 'abstained', 'label': 'Not enough usable English text', 'probabilities': {},
                'reason': 'Enter a specific English headline. The model cannot assess this input reliably.',
                'metrics': data['metrics'], 'release': data.get('release', 'text-v1'), 'note': 'No model verdict was issued.'}
    logit = data['intercept'] + sum(value for _, value in contributions)
    real = 1 / (1 + math.exp(-max(-700, min(700, logit))))
    uncertain = max(real, 1-real) < .65
    return {'status': 'uncertain' if uncertain else 'ready', 'label': 'Uncertain' if uncertain else LABELS[str(int(real >= .5))],
            'probabilities': {LABELS['0']: 1-real, LABELS['1']: real},
            'score_type': 'uncalibrated_model_scores', 'model': data.get('model', 'Fakeddit TF-IDF + Logistic Regression'),
            'release': data.get('release', 'text-v1'), 'metrics': data['metrics'], 'coverage': round(coverage, 3),
            'signals': [{'term': term, 'direction': 'real' if value > 0 else 'fake', 'contribution': round(value, 4)}
                        for term, value in sorted(contributions, key=lambda item: abs(item[1]), reverse=True)[:6]],
            'note': 'English Reddit-headline classifier. Dataset patterns can disagree with facts; scores are uncalibrated and do not establish truth.'}
