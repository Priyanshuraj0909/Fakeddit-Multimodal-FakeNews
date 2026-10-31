"""Download a small reproducible research pilot from official Reddit image URLs.

Uses existing independent release splits, preserves IDs, and excludes exact image
hash overlap. Images and texts remain in ignored data directories, never Git.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import sys
from urllib.parse import urlparse
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from ml.preprocessing.image_input import decode_image, MAX_IMAGE_BYTES
from ml.training.train_text import read_split, check_disjoint
from ml.utils.contracts import digest_file, check_content_disjoint

HOSTS = {'i.redd.it', 'preview.redd.it', 'external-preview.redd.it'}


class RedditOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise ValueError('Redirect leaves approved Reddit image hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def allowed(url):
    if not isinstance(url, str):
        return False
    try:
        parsed=urlparse(url)
        return parsed.scheme == 'https' and parsed.hostname in HOSTS and not parsed.username and not parsed.password and parsed.port in (None,443)
    except ValueError:
        return False


def fetch(row):
    try:
        if not re.fullmatch(r'[a-z0-9]+', str(row['id'])):
            raise ValueError('Expected a Reddit post ID')
        if not allowed(row['image_url']):
            raise ValueError('Image host outside approved Reddit image hosts')
        opener=urllib.request.build_opener(RedditOnlyRedirect())
        request=urllib.request.Request(row['image_url'], headers={'User-Agent':'Fakeddit-research-pilot/1.0'})
        with opener.open(request, timeout=12) as response:
            raw=response.read(MAX_IMAGE_BYTES+1)
        image=decode_image(raw)
        try:
            if min(image.size) < 64:
                raise ValueError('Image too small for pilot')
        finally:
            image.close()
        return row, raw, hashlib.sha256(raw).hexdigest(), None
    except (OSError,ValueError) as error:
        return row, None, None, {'id':str(row['id']), 'reason':type(error).__name__, 'http_status':getattr(error,'code',None)}


def prepare(raw, prepared, output, train=600, validation=200, test=200):
    output=Path(output)
    if output.exists():
        raise ValueError('Choose a new output directory to preserve prior pilot provenance')
    output.mkdir(parents=True)
    images=output/'images'; images.mkdir()
    hashes, frames, details, skipped = set(), [], {}, []
    for name,original,target in [('train','train',train),('validation','validate',validation),('test','test_public',test)]:
        if target < 2 or target % 2:
            raise ValueError('Pilot sizes must be positive even counts >=2')
        path=Path(prepared)/f'{name}.csv'
        frame=read_split(path,'clean_title','2_way_label')
        source=Path(raw)/f'multimodal_{original}.tsv'
        meta=pd.read_csv(source,sep='\t',usecols=['id','image_url'],dtype={'id':'string'})
        frame=frame.merge(meta,on='id',how='left',validate='one_to_one')
        retained=[]
        for label in (0,1):
            candidates=frame.loc[frame['2_way_label'].eq(label)].sample(frac=1,random_state=42)
            candidates=candidates.loc[candidates['image_url'].map(allowed)].head(target*4).to_dict('records')
            accepted=0
            with ThreadPoolExecutor(max_workers=6) as pool:
                # Small ordered batches bound outstanding downloads and preserve seeded order.
                for start in range(0,len(candidates),6):
                    batch=candidates[start:start+min(6,target//2-accepted)]
                    for row,content,digest,error in pool.map(fetch,batch):
                        if error:
                            skipped.append({'split':name,**error})
                            continue
                        if digest in hashes:
                            skipped.append({'split':name,'id':str(row['id']),'reason':'duplicate_image_sha256'})
                            continue
                        filename=str(row['id'])+'.img'
                        (images/filename).write_bytes(content)
                        hashes.add(digest)
                        retained.append({'id':str(row['id']),'clean_title':row['clean_title'],'2_way_label':label,'image_path':filename,'image_sha256':digest})
                        accepted+=1
                    if accepted == target//2:
                        break
            if accepted != target//2:
                raise ValueError(f'Only {accepted} eligible images for {name} class {label}; cannot complete requested balanced pilot')
        selected=pd.DataFrame(retained).sample(frac=1,random_state=42)
        selected.to_csv(output/f'{name}.csv',index=False)
        frames.append(selected)
        details[name]={'rows':len(selected),'prepared_sha256':digest_file(path),'raw_sha256':digest_file(source),'pilot_csv_sha256':digest_file(output/f'{name}.csv')}
        print(json.dumps({'split':name,'retained':len(selected)}),flush=True)
    check_disjoint(frames); check_content_disjoint(frames)
    report={'prepared_at':datetime.now(timezone.utc).isoformat(),'seed':42,'splits':details,'skipped':skipped,
            'protocol':'Balanced small pilot, seeded candidate batches within each existing official prepared split; retrievable Reddit-hosted images; exact image hashes excluded across all splits.',
            'limitations':['Availability and hosting selection bias; not representative of the full dataset.','No semantic or perceptual image deduplication is claimed.','Small balanced pilot metrics cannot be compared directly to text-v1 natural class proportions.','Images may contain watermarks, deletion notices or changed content; human inspection remains required.']}
    (output/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',default='data/raw'); parser.add_argument('--prepared',default='data/processed/text-release-v1')
    parser.add_argument('--output',required=True)
    for name,default in [('train',600),('validation',200),('test',200)]:parser.add_argument('--'+name,type=int,default=default)
    prepare(**vars(parser.parse_args()))
