"""Capture real verification runs for later independent review; never create gold labels."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter, sleep
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from backend.app.schemas.detection import DetectionInput


def load_cases(path, maximum=100):
    if not 1 <= maximum <= 100:
        raise ValueError('Choose 1–100 cases per run')
    cases, seen = [], set()
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row=json.loads(line)
        if not isinstance(row.get('id'), str) or not row['id'].strip() or row['id'] in seen:
            raise ValueError('Cases require unique nonempty string IDs')
        seen.add(row['id'])
        payload=DetectionInput.model_validate({key:row[key] for key in ('text','source_url','publication_date') if key in row})
        if not payload.text.strip():
            raise ValueError('Each case must contain a real submitted claim')
        cases.append({'id':row['id'], 'payload':payload.model_dump()})
        if len(cases)>maximum:
            raise ValueError('Case file exceeds the requested maximum; provide a bounded input file')
    if not cases:
        raise ValueError('Provide actual cases; no synthetic benchmark cases are generated')
    return cases


def capture(cases, output, base_url, interval=13, client=None):
    parsed=urlparse(base_url)
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost'}):
        raise ValueError('Use HTTPS or a local development server')
    if parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Use an API origin without credentials, path, query or fragment')
    if interval<13:
        raise ValueError('Use at least 13 seconds between calls to respect per-client research limits')
    output=Path(output)
    manifest=output.with_suffix(output.suffix+'.manifest.json')
    if output.exists() or manifest.exists():
        raise ValueError('Choose a new output to preserve previous run data')
    own_client=client is None
    client=client or httpx.Client(timeout=65,follow_redirects=False)
    try:
        metadata={'captured_at':datetime.now(timezone.utc).isoformat(),'requested_cases':len(cases),
                  'attempted_cases':0,'independently_reviewed_claims':0,'status':'unavailable','reason':None,
                  'reference_metrics':None,'note':'Run outcomes measure service behavior; evidence correctness requires independent review.'}
        output.parent.mkdir(parents=True,exist_ok=True)
        try:
            response=client.get(base_url.rstrip('/')+'/api/capabilities')
            response.raise_for_status()
            data=response.json()
            capability=data.get('verification') if isinstance(data,dict) else None
            if not isinstance(capability,dict) or type(capability.get('available')) is not bool:
                raise ValueError('Invalid verification configuration response')
        except (httpx.HTTPError,ValueError):
            metadata.update(status='unavailable',reason='preflight_failed')
            manifest.write_text(json.dumps(metadata,indent=2)+'\n')
            return metadata
        metadata.update(status='unavailable' if capability['available'] is not True else 'capturing',
                        reason=capability.get('status') if capability['available'] is not True else None)
        if capability.get('available') is not True:
            manifest.write_text(json.dumps(metadata,indent=2)+'\n')
            return metadata
        reasons=Counter()
        with output.open('x') as stream:
            for index,case in enumerate(cases):
                if index:
                    sleep(interval)
                start=perf_counter()
                response=None
                try:
                    response=client.post(base_url.rstrip('/')+'/api/detect',json=case['payload'])
                    response.raise_for_status()
                    report=response.json()
                    verification=report.get('verification',{})
                    if verification.get('status') not in {'completed','unavailable'}:
                        raise ValueError('API returned an invalid verification status')
                except (httpx.HTTPError, ValueError):
                    row={'id':case['id'],'submission':case['payload'],'report':None,'run_status':'transport_error',
                         'http_status':response.status_code if response is not None else None,
                         'duration_ms':(perf_counter()-start)*1000,'reviews':[]}
                    stream.write(json.dumps(row)+'\n'); stream.flush()
                    metadata['attempted_cases']+=1
                    reasons['transport_error']+=1
                    metadata.update(status='stopped',reason='transport_error')
                    break
                row={'id':case['id'],'submission':case['payload'],'report':report,'duration_ms':(perf_counter()-start)*1000,
                     'request_id':response.headers.get('x-request-id'),'trace_id':response.headers.get('x-trace-id'),
                     'reviews':[], 'review_metadata':{'reviewer_id':None,'reviewed_at':None,'independent':None}}
                stream.write(json.dumps(row)+'\n'); stream.flush()
                metadata['attempted_cases']+=1
                reasons[verification.get('reason') or verification['status']]+=1
                if verification['status']=='unavailable':
                    metadata.update(status='stopped',reason=verification.get('reason','unavailable'))
                    break
            else:
                metadata['status']='captured_pending_review'
        metadata['outcomes']=dict(reasons)
        manifest.write_text(json.dumps(metadata,indent=2)+'\n')
        return metadata
    finally:
        if own_client:
            client.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',required=True,help='JSONL: unique id, actual text, optional source_url/publication_date')
    parser.add_argument('--output',required=True,help='Use ignored artifacts/ for submitted content and run outputs')
    parser.add_argument('--base-url',default='https://fakeddit-multimodal-fakenews.vercel.app')
    parser.add_argument('--maximum',type=int,default=100)
    args=parser.parse_args()
    cases=load_cases(args.cases,args.maximum)
    print(json.dumps(capture(cases,args.output,args.base_url)))
