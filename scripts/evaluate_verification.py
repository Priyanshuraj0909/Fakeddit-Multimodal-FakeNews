"""Score exported reports against human-reviewed claims; never invent reference labels."""
import argparse
import json
from pathlib import Path

VERDICTS = {'supported', 'contradicted', 'mixed', 'insufficient_evidence'}


def evaluate(records):
    total = correct = citation_count = citation_supported = 0
    seen = set()
    for record in records:
        identity = record['id']
        if identity in seen:
            raise ValueError('Duplicate review ID')
        seen.add(identity)
        claims = record['report']['verification']['claims']
        reviewed = set()
        for review in record['reviews']:
            index = review['claim_index']
            if type(index) is not int or index < 0 or index >= len(claims) or index in reviewed:
                raise ValueError('Review must identify one unique existing claim')
            reviewed.add(index)
            expected = review['expected_verdict']
            if expected not in VERDICTS:
                raise ValueError('Invalid human reference verdict')
            total += 1
            correct += claims[index]['verdict'] == expected
            sources = {s['id'] for s in record['report']['verification']['sources']}
            reviewed_citations = set()
            for citation in review.get('citations', []):
                source_id = citation['source_id']
                if (source_id not in claims[index]['evidence_ids'] or source_id not in sources
                        or source_id in reviewed_citations or type(citation['supports_assessment']) is not bool):
                    raise ValueError('Citation review must reference one retrieved citation and a human boolean assessment')
                reviewed_citations.add(source_id)
                citation_count += 1
                citation_supported += citation['supports_assessment']
    if not total:
        raise ValueError('At least one human-reviewed claim is required')
    return {'reports': len(seen), 'reviewed_claims': total, 'claim_verdict_accuracy': correct/total,
            'reviewed_citations': citation_count, 'citation_support_rate': citation_supported/citation_count if citation_count else None,
            'note': 'Only explicitly human-reviewed claims/citations are scored. This does not measure retrieval recall or unreviewed evidence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', required=True, help='JSONL of reports and human reviews; see docs/EVALUATION.md')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Choose a new output; existing evaluation records are preserved')
    result = evaluate([json.loads(line) for line in Path(args.reviews).read_text().splitlines() if line.strip()])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
