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
