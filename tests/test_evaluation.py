"""Synthetic contract fixtures; these tests do not establish real benchmark metrics."""
import numpy as np
import pytest
from ml.evaluation.reliability import reliability
from scripts.evaluate_verification import evaluate
from scripts.audit_generalization import fingerprint, near_overlap


def test_reliability_accounts_for_abstention_and_empty_coverage():
    result = reliability(np.array([0, 1, 0, 1]), np.array([.1, .9, .4, .6]), [True, False, True, True])
    assert result['selective_classification'][0]['coverage'] == .75
    assert result['selective_classification'][-1]['accuracy'] is None
    assert sum(item['count'] for item in result['reliability_bins']) == 4
    with pytest.raises(ValueError):
        reliability([0, 1], [.1, float('nan')])


def test_evidence_evaluation_requires_real_reference_claims_and_unique_citations():
    record = {'id': 'fixture', 'report': {'verification': {'claims': [{'verdict': 'supported', 'evidence_ids': [1]}], 'sources': [{'id': 1}]}},
              'reviews': [{'claim_index': 0, 'expected_verdict': 'contradicted', 'citations': [{'source_id': 1, 'supports_assessment': False}]}]}
    result = evaluate([record])
    assert result['claim_verdict_accuracy'] == 0
    assert result['citation_support_rate'] == 0
    with pytest.raises(ValueError):
        evaluate([record, record])
    record['reviews'][0]['citations'][0]['source_id'] = 2
    with pytest.raises(ValueError):
        evaluate([record])


def test_lexical_audit_handles_short_titles_and_matching_fingerprints():
    value = fingerprint('A sufficiently long headline for a lexical overlap test')
    assert fingerprint('Too short') is None
    assert near_overlap([value, None], [value, None])['candidate_overlap_rows'] == 1


def test_unseen_groups_exclude_training_validation_and_unknown_identities():
    import pandas as pd
    from scripts.evaluate_shift import unseen_mask, summarize
    reference = pd.DataFrame({'author': ['training-author', 'validation-author']})
    query = pd.DataFrame({'author': ['training-author', 'validation-author', 'new-author', '[deleted]', None]})
    assert unseen_mask(reference, query, 'author').tolist() == [False, False, True, False, False]
    assert summarize(pd.DataFrame(), [])['status'] == 'unavailable'
    frame = pd.DataFrame({'id':['one','two'], '2_way_label':[0,1]})
    result = summarize(frame, [0,0])
    assert result['rows'] == 2 and result['accuracy'] == .5
    assert result['error_count'] == 1
    assert result['first_20_error_ids'] == [{'id':'two', 'expected':1, 'predicted':0}]


def test_pilot_downloads_are_limited_to_public_reddit_image_hosts():
    from scripts.prepare_paired_pilot import allowed, fetch
    assert allowed('https://preview.redd.it/example.jpg')
    for url in ('http://preview.redd.it/x', 'https://preview.redd.it.evil.example/x', 'https://user:secret@preview.redd.it/x', 'https://preview.redd.it:123/x', 'https://preview.redd.it:invalid/x', 'https://127.0.0.1/x', None):
        assert not allowed(url)
    _, content, _, error = fetch({'id':'../outside', 'image_url':'https://preview.redd.it/x'})
    assert content is None and error['reason'] == 'ValueError'


def test_evidence_review_worksheet_never_generates_reference_labels(tmp_path):
    import json
    from scripts.create_evidence_review import worksheet
    path=tmp_path/'report.json'
    path.write_text(json.dumps({'verification':{'status':'completed','claims':[{'verdict':'supported','evidence_ids':[1]}],'sources':[{'id':1}]}}))
    records=worksheet([path])
    assert records[0]['reviews'][0]['expected_verdict'] is None
    assert records[0]['reviews'][0]['citations'][0]['supports_assessment'] is None
    with pytest.raises(ValueError):
        evaluate(records)
