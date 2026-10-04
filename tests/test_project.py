import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import index
from fakeddit.train_multimodal import load_split
from fakeddit.train_text import check_disjoint, read_split, train

client = TestClient(index.app)


def test_api_validation_and_signal_mode():
    assert client.get('/').status_code == 200
    assert client.get('/static/js/app.js').status_code == 200
    assert client.get('/static/css/workspace.css').status_code == 200
    for text in ('', '   ', 'x' * 10001):
        assert client.post('/api/analyze', json={'text': text}).status_code == 422
    data = client.post('/api/analyze', json={'text': 'SHOCKING discovery!!!'}).json()
    assert data['mode'] == 'descriptive'
    assert data['verdict'] == 'Not assessed'
    assert data['exclamation_count'] == 3
    assert data['phrases'] == ['shocking']


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
                      'clean_title':['imaginary fabricated story' if i%2 == 0 else 'documented observed report' for i in range(12)],
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
    assert client.post('/api/predict', json={'text': 'Some headline'}).status_code == 503
    index.load_model.cache_clear()


def test_preserve_post_ids_with_leading_zeros(tmp_path):
    path = tmp_path / 'posts.csv'
    path.write_text('id,clean_title,2_way_label\n001,first post,0\n002,second post,1\n')
    assert read_split(path, 'clean_title', '2_way_label')['id'].tolist() == ['001', '002']


def test_emphasis_matching_does_not_match_inside_words():
    data = client.post('/api/analyze', json={'text': 'The secretary discussed developments.'}).json()
    assert data['phrases'] == []
