"""Create unlabeled review worksheets from report exports or captured-run JSONL.

Reference verdicts/support judgments remain null until independently reviewed.
Unavailable/transport runs are retained with no review labels for service metrics.
"""
import argparse
import json
from pathlib import Path


def worksheet(paths):
    records, seen = [], set()
    for path in paths:
        path=Path(path)
        inputs=[json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.suffix=='.jsonl' else [json.loads(path.read_text())]
        for item in inputs:
            captured='report' in item and 'id' in item
            report=item.get('report') if captured else item
            verification=(report or {}).get('verification',{})
            if not captured and (verification.get('status')!='completed' or not verification.get('claims')):
                raise ValueError('Standalone worksheets require a completed report with retrieved claims')
            identity=item['id'] if captured else f'review-{len(records)+1:04d}'
            if identity in seen:
                raise ValueError('Duplicate review ID across inputs')
            seen.add(identity)
            record=dict(item) if captured else {'id':identity,'report':report}
            record.update(review_metadata={'reviewer_id':None,'reviewed_at':None,'independent':None},
                          review_instructions='Independently inspect the original claim and cited sources. Fill expected_verdict and supports_assessment; do not derive reference labels from the system verdict.',
                          reviews=[{'claim_index':i,'expected_verdict':None,
                                    'citations':[{'source_id':source,'supports_assessment':None} for source in claim.get('evidence_ids',[])]}
                                   for i,claim in enumerate(verification.get('claims',[]))] if verification.get('status')=='completed' else [])
            records.append(record)
    if not records:
        raise ValueError('At least one exported report or captured run is required')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',nargs='+',required=True,help='Exported report JSON files or captured batch JSONL')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    output=Path(args.output)
    if output.exists():
        raise ValueError('Choose a new output to preserve existing human reviews')
    records=worksheet(args.reports)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(''.join(json.dumps(record)+'\n' for record in records))
    print(json.dumps({'reports':len(records),'reference_labels':'unavailable_pending_independent_review','output':str(output)}))
