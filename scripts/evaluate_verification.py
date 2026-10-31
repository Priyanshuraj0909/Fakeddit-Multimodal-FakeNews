"""Score exported reports against human-reviewed claims; never invent reference labels."""
import argparse
import json
from pathlib import Path
from collections import Counter
from datetime import datetime
from statistics import median
import math

VERDICTS = {'supported', 'contradicted', 'mixed', 'insufficient_evidence'}


def evaluate(records, require_independent=False):
    total = correct = citation_count = citation_supported = 0
    seen = set()
    statuses, reasons, durations = Counter(), Counter(), []
    reviewed_with_provenance = 0
    available_citations = 0
    for record in records:
        identity = record['id']
        if identity in seen:
            raise ValueError('Duplicate review ID')
        seen.add(identity)
        verification = (record.get('report') or {}).get('verification', {})
        statuses[verification.get('status', 'transport_error' if record.get('run_status') == 'transport_error' else 'unknown')] += 1
        if verification.get('reason'):
            reasons[verification['reason']] += 1
        duration = record.get('duration_ms')
        if duration is not None:
            if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
                raise ValueError('Duration must be finite nonnegative milliseconds')
            durations.append(duration)
        metadata = record.get('review_metadata') or {}
        provenance = (isinstance(metadata.get('reviewer_id'), str) and bool(metadata['reviewer_id'].strip())
                      and metadata.get('independent') is True and isinstance(metadata.get('reviewed_at'), str))
        if provenance:
            try:
                stamp = datetime.fromisoformat(metadata['reviewed_at'].replace('Z', '+00:00'))
                provenance = stamp.tzinfo is not None
            except ValueError:
                provenance = False
        if require_independent and record.get('reviews') and not provenance:
            raise ValueError('Independent review requires reviewer ID, timezone-aware reviewed_at and independent=true')
        claims = verification.get('claims', [])
        reviewed = set()
        for review in record['reviews']:
            index = review['claim_index']
            if type(index) is not int or index < 0 or index >= len(claims) or index in reviewed:
                raise ValueError('Review must identify one unique existing claim')
            reviewed.add(index)
            expected = review['expected_verdict']
            if expected not in VERDICTS:
                raise ValueError('Invalid human reference verdict')
            if claims[index].get('verdict') not in VERDICTS:
                raise ValueError('Invalid recorded claim verdict')
            total += 1
            reviewed_with_provenance += bool(provenance)
            correct += claims[index]['verdict'] == expected
            sources = {s['id'] for s in verification['sources']}
            available_citations += len(set(claims[index]['evidence_ids']))
            reviewed_citations = set()
            for citation in review.get('citations', []):
                source_id = citation['source_id']
                if (source_id not in claims[index]['evidence_ids'] or source_id not in sources
                        or source_id in reviewed_citations or type(citation['supports_assessment']) is not bool):
                    raise ValueError('Citation review must reference one retrieved citation and a human boolean assessment')
                reviewed_citations.add(source_id)
                citation_count += 1
                citation_supported += citation['supports_assessment']
    service_runs = statuses['completed'] + statuses['unavailable'] + statuses['transport_error']
    return {'status': 'evaluated' if total else 'unavailable', 'reason': None if total else 'no_reviewed_claims',
            'reports': len(seen), 'report_statuses': dict(statuses), 'unavailable_reasons': dict(reasons),
            'service_runs': service_runs,
            'service_unavailable_fraction': (statuses['unavailable'] + statuses['transport_error'])/service_runs if service_runs else None,
            'reviewed_claims': total, 'reviews_with_provenance': reviewed_with_provenance,
            'claim_verdict_accuracy': correct/total if total else None,
            'reviewed_citations': citation_count, 'citation_support_rate': citation_supported/citation_count if citation_count else None,
            'citation_review_coverage': citation_count/available_citations if available_citations else None,
            'latency_ms': {'rows':len(durations), 'median':median(durations) if durations else None,
                           'p95_nearest_rank':sorted(durations)[math.ceil(.95*len(durations))-1] if durations else None},
            'note': 'Scores use supplied reference judgments only. Reviewer metadata is an attestation, not proof of human independence. Status/latency include unavailable runs; retrieval recall is not measured.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', required=True, help='JSONL of reports and human reviews; see docs/EVALUATION.md')
    parser.add_argument('--output', required=True)
    parser.add_argument('--require-independent', action='store_true', help='Require reviewer provenance for every reviewed report')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Choose a new output; existing evaluation records are preserved')
    result = evaluate([json.loads(line) for line in Path(args.reviews).read_text().splitlines() if line.strip()], args.require_independent)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
