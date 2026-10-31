"""Create an unlabeled human-review worksheet from exported completed reports.

Reference verdicts/support judgments are deliberately null until independently
reviewed. This tool never turns model output or user feedback into gold labels.
"""
import argparse
import json
from pathlib import Path


def worksheet(paths):
    records=[]
    for index,path in enumerate(paths):
        report=json.loads(Path(path).read_text())
        verification=report.get('verification',{})
        if verification.get('status')!='completed' or not verification.get('claims'):
            raise ValueError('Review worksheets require completed reports with retrieved claims')
        records.append({'id':f'review-{index+1:04d}', 'report':report,
                        'review_instructions':'Independently inspect the original claim and cited sources. Fill expected_verdict and supports_assessment; never copy the system verdict as a reference without review.',
                        'reviews':[{'claim_index':i,'expected_verdict':None,
                                    'citations':[{'source_id':source,'supports_assessment':None} for source in claim.get('evidence_ids',[])]}
                                   for i,claim in enumerate(verification['claims'])]})
    if not records:
        raise ValueError('At least one completed report is required')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',nargs='+',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    output=Path(args.output)
    if output.exists():
        raise ValueError('Choose a new output to preserve existing human reviews')
    records=worksheet(args.reports)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(''.join(json.dumps(record)+'\n' for record in records))
    print(json.dumps({'reports':len(records),'reference_labels':'unavailable_pending_human_review','output':str(output)}))
