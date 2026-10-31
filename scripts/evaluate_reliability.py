"""Evaluate a trusted baseline; fit/select calibration on disjoint validation halves only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from ml.evaluation.reliability import reliability
from ml.inference.portable_text import TOKEN
from ml.training.train_text import read_split, check_disjoint
from ml.utils.contracts import check_content_disjoint, digest_file


def evaluate(directory, train, validation, test, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new evaluation output; existing records are preserved')
    frames = [read_split(p, 'clean_title', '2_way_label') for p in (train, validation, test)]
    check_disjoint(frames)
    check_content_disjoint(frames)
    metadata = json.loads((Path(directory)/'metrics.json').read_text())
    if metadata['rows'] != dict(zip(('train', 'validation', 'test'), map(len, frames))):
        raise ValueError('Split sizes differ from the trained model provenance')
    model_path = Path(directory)/'model.joblib'
    model = joblib.load(model_path)  # Trusted locally trained checkpoints only.
    fit, select = train_test_split(np.arange(len(frames[1])), test_size=.5, stratify=frames[1]['2_way_label'], random_state=42)
    scores = model.decision_function(frames[1]['clean_title'])
    y_val = frames[1]['2_way_label'].to_numpy()
    calibrator = LogisticRegression(C=1e6, random_state=42).fit(scores[fit, None], y_val[fit])
    raw_validation = model.predict_proba(frames[1]['clean_title'])[:, 1]
    calibrated_validation = calibrator.predict_proba(scores[:, None])[:, 1]
    raw_selection = reliability(y_val[select], raw_validation[select])
    calibrated_selection = reliability(y_val[select], calibrated_validation[select])
    selected = 'sigmoid' if calibrated_selection['brier_score'] < raw_selection['brier_score'] else 'raw'
    test_scores = model.decision_function(frames[2]['clean_title'])
    raw_test = model.predict_proba(frames[2]['clean_title'])[:, 1]
    calibrated_test = calibrator.predict_proba(test_scores[:, None])[:, 1]
    vocabulary = model.named_steps['tfidf'].vocabulary_
    usable = []
    for text in frames[2]['clean_title']:
        tokens = TOKEN.findall(text.lower())
        usable.append(len(tokens) >= 3 and sum(word in vocabulary for word in tokens)/max(1, len(tokens)) >= .2)
    report = {'evaluated_at': datetime.now(timezone.utc).isoformat(), 'model_sha256': digest_file(model_path),
              'splits': {name: {'rows': len(frame), 'sha256': digest_file(path)} for name, frame, path in zip(('train', 'validation', 'test'), frames, (train, validation, test))},
              'protocol': 'Base model frozen. Sigmoid fitted on 7,500 stratified validation rows; raw/sigmoid selected by Brier score on the other 7,500. Test is evaluation only. No production model changed.',
              'seed': 42, 'calibration_fit_rows': len(fit), 'calibration_selection_rows': len(select), 'selected': selected,
              'selection': {'raw': raw_selection, 'sigmoid': calibrated_selection},
              'sigmoid': {'coefficient': float(calibrator.coef_[0, 0]), 'intercept': float(calibrator.intercept_[0])},
              'test': {'raw': reliability(frames[2]['2_way_label'].to_numpy(), raw_test, usable),
                       'sigmoid': reliability(frames[2]['2_way_label'].to_numpy(), calibrated_test, usable)},
              'limitations': ['Same held-out benchmark used for the recorded text-v1 release; not new external generalization evidence.',
                              'Calibration concerns dataset labels, not factual truth.', 'Production continues to use raw model scores and the existing 0.65 heuristic.',
                              'No near-duplicate, author-disjoint or temporal audit is implied.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'train', 'validation', 'test', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    result = evaluate(**vars(args))
    print(json.dumps({'selected': result['selected'], 'test_brier': {k: v['brier_score'] for k,v in result['test'].items()}, 'output': args.output}))
