import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.core.rate_limit import ResearchLimit
from backend.app.services import verification
from ml.inference import portable_text

client = TestClient(main.app)


def test_combined_detector_runs_actual_release_without_groq_key(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.delenv('FAKEDDIT_MODEL_DIR', raising=False)
    report = client.post('/api/detect', json={'text': 'Scientists discover a new species in the rainforest'}).json()
    assert report['mode'] == 'news_detection'
    assert report['model_assessment']['status'] in {'ready', 'uncertain'}
    assert sum(report['model_assessment']['probabilities'].values()) == pytest.approx(1)
    assert report['model_assessment']['metrics']['rows']['test'] == 15000
    assert report['verification']['verdict'] == 'not_checked'
    assert report['verification']['reason'] == 'missing_api_key'


def test_detector_rejects_empty_text_private_sources_and_invalid_dates():
    for patch in [{'text': ' '}, {'source_url': 'http://127.0.0.1/admin'}, {'source_url': 'javascript:alert(1)'}, {'publication_date': '2026-99-99'}]:
        assert client.post('/api/detect', json={'text': 'A specific headline', **patch}).status_code == 422


def test_portable_release_abstains_on_empty_features_and_short_inputs():
    for text in ['a', 'xyzqwertylkjhn zxcvbnmqwert asdfghjklqwert']:
        result = portable_text.predict(text)
        assert result['status'] == 'abstained'
        assert result['probabilities'] == {}


def test_model_output_and_verified_evidence_are_kept_separate(monkeypatch):
    async def verified(*_):
        return {'status': 'completed', 'verdict': 'contradicted', 'summary': 'Counter-evidence found',
                'claims': [], 'sources': [], 'provider': 'Groq'}
    monkeypatch.setattr(verification, 'verify', verified)
    response = client.post('/api/detect', json={'text': 'NASA confirms the Moon is made of cheese.'})
    assert response.status_code == 200
    assert response.json()['verification']['verdict'] == 'contradicted'
    assert 'probabilities' in response.json()['model_assessment']


def test_only_executed_browser_sources_can_be_cited():
    message = {'content': 'See https://invented.example/story', 'executed_tools': [
        {'browser_results': [{'url': 'https://nasa.gov/moon', 'title': 'Moon facts', 'content': 'The Moon is rocky.'},
                             {'url': 'http://localhost/admin', 'title': 'Private', 'content': 'private'}]},
        {'search_results': {'results': [{'url': 'https://nasa.gov/moon', 'title': 'Duplicate', 'content': 'same'}]}}
    ]}
    sources = verification.collect_sources(message)
    assert len(sources) == 1
    assert sources[0]['url'] == 'https://nasa.gov/moon'
    with pytest.raises(ValueError, match='not retrieved'):
        verification.grounded_report({'summary': 'Summary', 'claims': [{'statement': 'Claim', 'verdict': 'supported', 'explanation': 'Reason', 'evidence_ids': [2]}]}, sources)


def test_uncited_claim_cannot_be_shown_as_supported():
    result = verification.grounded_report({'summary': 'Limited findings', 'claims': [
        {'statement': 'A claim', 'verdict': 'supported', 'explanation': 'No actual evidence', 'evidence_ids': []}]}, [])
    assert result['verdict'] == 'insufficient_evidence'
    assert result['claims'][0]['verdict'] == 'insufficient_evidence'


def test_partial_article_evidence_cannot_confirm_whole_article():
    sources = [{'id': 1, 'url': 'https://example.com/evidence', 'title': 'Evidence', 'publisher': 'example.com', 'content': 'Evidence'}]
    result = verification.grounded_report({'summary': 'One unresolved claim', 'claims': [
        {'statement': 'Established claim', 'verdict': 'supported', 'explanation': 'Documented', 'evidence_ids': [1]},
        {'statement': 'Unresolved claim', 'verdict': 'insufficient_evidence', 'explanation': 'Missing', 'evidence_ids': []}]}, sources)
    assert result['verdict'] == 'insufficient_evidence'
    assert 'content' not in result['sources'][0]


def test_groq_search_then_structured_assessment(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only-key')
    calls = []
    async def fake_request(_client, payload):
        calls.append(payload)
        if len(calls) == 1:
            return {'executed_tools': [{'type': 'browser_search', 'browser_results': [
                {'url': 'https://science.nasa.gov/moon/', 'title': 'Moon', 'content': 'The Moon is made of rock.'}]}]}
        return {'content': json.dumps({'summary': 'NASA describes a rocky Moon.', 'claims': [
            {'statement': 'Moon is made of cheese', 'verdict': 'contradicted', 'explanation': 'NASA describes rock.', 'evidence_ids': [1]}]})}
    monkeypatch.setattr(verification, 'groq_request', fake_request)
    report = asyncio.run(verification.verify('The Moon is made of cheese'))
    assert report['verdict'] == 'contradicted'
    assert calls[0]['tool_choice'] == 'required'
    assert calls[0]['tools'] == [{'type': 'browser_search'}]
    assert 'response_format' not in calls[0]
    assert calls[1]['response_format']['json_schema']['strict'] is True
    assert 'tools' not in calls[1]


def test_provider_failure_preserves_model_and_does_not_invent_verdict(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only-key')
    monkeypatch.setattr(main, 'research_limit', ResearchLimit())
    async def broken(*_):
        raise httpx.ReadTimeout('test timeout')
    monkeypatch.setattr(verification, 'research', broken)
    report = client.post('/api/detect', json={'text': 'Scientists discover a new species in the rainforest'}).json()
    assert report['model_assessment']['status'] in {'ready', 'uncertain'}
    assert report['verification']['verdict'] == 'not_checked'
    assert report['verification']['reason'] == 'timeout'


def test_bounded_research_rate_limit():
    limit = ResearchLimit(maximum=2, capacity=2)
    assert limit.allow('a') and limit.allow('a')
    assert not limit.allow('a')
    assert limit.allow('b') and limit.allow('c')
    assert len(limit.entries) == 2
