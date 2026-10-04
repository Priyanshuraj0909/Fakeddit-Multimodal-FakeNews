import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import main as index
from ml.training.train_multimodal import load_split
from ml.training.train_text import check_disjoint, read_split, train

client = TestClient(index.app)


def test_api_validation_and_signal_mode():
    assert client.get('/').status_code == 200
    assert client.get('/static/src/pages/workspace.js').status_code == 200
    assert client.get('/static/src/components/workspace.css').status_code == 200
    for text in ('', '   ', 'x' * 10001):
        assert client.post('/api/analyze', json={'text': text}).status_code == 422
    data = client.post('/api/analyze', json={'text': 'SHOCKING discovery!!!'}).json()
    assert data['mode'] == 'descriptive'
    assert data['verdict'] == 'Not assessed'
    assert data['exclamation_count'] == 3
    assert data['phrases'] == ['shocking']


def test_public_routes_support_availability_checks():
    for path in ('/', '/api/health'):
        response = client.head(path)
        assert response.status_code == 200
        assert response.content == b''


def test_missing_model(monkeypatch, tmp_path):
    monkeypatch.setattr(index, 'MODEL_DIR', tmp_path)
    assert client.get('/api/health').json()['model_available'] is False
    assert client.post('/api/predict', json={'text': 'Some news'}).status_code == 503


def test_reject_overlapping_ids():
    with pytest.raises(ValueError, match='overlap'):
        check_disjoint([pd.DataFrame({'id': ['a']}), pd.DataFrame({'id': ['a']})])


def test_embedding_alignment(tmp_path):
    pd.DataFrame({'id': ['a','b'], 'clean_title': ['first','second'], '2_way_label': [0,1]}).to_csv(tmp_path/'posts.csv',index=False)
    np.savez(tmp_path/'image.npz', ids=np.array(['b','a']), embeddings=np.ones((2,3)))
    with pytest.raises(ValueError, match='row order'):
        load_split(tmp_path)


def test_training_artifact_and_prediction(tmp_path, monkeypatch):
    # Synthetic data verifies the pipeline only; no benchmark claim is made.
    paths = []
    for split in ('train','validation','test'):
        path = tmp_path / f'{split}.csv'
        pd.DataFrame({'id':[f'{split}-{i}' for i in range(12)],
                      'clean_title':[('imaginary fabricated story' if i%2 == 0 else 'documented observed report') + f' {split} example {i}' for i in range(12)],
                      '2_way_label':[i%2 for i in range(12)]}).to_csv(path,index=False)
        paths.append(path)
    output = tmp_path / 'model'
    metrics = train(*paths, output)
    assert metrics['rows'] == {'train':12,'validation':12,'test':12}
    assert (output/'model.joblib').is_file()
    assert json.loads((output/'metrics.json').read_text())['seed'] == 42
    monkeypatch.setattr(index,'MODEL_DIR',output)
    index.load_model.cache_clear()
    response = client.post('/api/predict',json={'text':'documented observed report'})
    assert response.status_code == 200
    assert sum(response.json()['probabilities'].values()) == pytest.approx(1)
    index.load_model.cache_clear()


def test_corrupt_model_returns_service_error(monkeypatch, tmp_path):
    (tmp_path / 'model.joblib').write_bytes(b'not a valid artifact')
    (tmp_path / 'metrics.json').write_text('{"labels": {"0": "Class 0", "1": "Class 1"}}')
    monkeypatch.setattr(index, 'MODEL_DIR', tmp_path)
    index.load_model.cache_clear()
    assert client.get('/api/health').json()['model_status'] == 'invalid_artifacts'
    assert client.get('/api/capabilities').json()['text_classifier']['available'] is False
    assert client.post('/api/predict', json={'text': 'Some headline'}).status_code == 503
    index.load_model.cache_clear()


def test_preserve_post_ids_with_leading_zeros(tmp_path):
    path = tmp_path / 'posts.csv'
    path.write_text('id,clean_title,2_way_label\n001,first post,0\n002,second post,1\n')
    assert read_split(path, 'clean_title', '2_way_label')['id'].tolist() == ['001', '002']


def test_emphasis_matching_does_not_match_inside_words():
    data = client.post('/api/analyze', json={'text': 'The secretary discussed developments.'}).json()
    assert data['phrases'] == []


def test_capabilities_do_not_claim_missing_inference(monkeypatch, tmp_path):
    monkeypatch.setattr(index, 'MODEL_DIR', tmp_path)
    data = client.get('/api/capabilities').json()
    assert data['text_analysis'] is True
    assert data['media_inspection'] == 'browser_local'
    assert data['text_classifier'] == {'available': False, 'status': 'missing_artifacts'}
    assert data['image_inference'] is False
    assert data['video_inference'] is False
    assert data['fact_verification'] is False
    assert data['limits']['image_bytes'] == 10 * 1024 * 1024


def test_invalid_prediction_scores_return_service_error(monkeypatch):
    class BrokenModel:
        classes_ = np.array([0, 1])
        def predict_proba(self, _):
            return [[float("nan"), 0.5]]
    monkeypatch.setattr(index, 'health', lambda: {"model_available": True, "model_status": "ready"})
    monkeypatch.setattr(index, 'load_model', lambda _: (BrokenModel(), {"labels": {"0": "Class 0", "1": "Class 1"}}))
    response = client.post('/api/predict', json={'text': 'Some headline'})
    assert response.status_code == 503
