"""Evaluate all CLIP/XGBoost modalities on the same small paired pilot.

Research-only output: no production model or deployment setting is changed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from ml.models.clip_encoder import ClipEncoder
from ml.preprocessing.extract_embeddings import extract
from ml.preprocessing.image_input import decode_image
from ml.training.train_multimodal import train
from ml.utils.contracts import digest_file


def run(paired, encoder, features, model, output):
    output=Path(output)
    if output.exists():
        raise ValueError('Choose a new report output')
    import torch
    torch.set_num_threads(1)
    labels={'0':'Likely fake / misleading','1':'Likely real'}
    label_source='Official Fakeddit v2: 2_way_label 1 iff 6_way_label 0; see docs/TEXT_MODEL_RELEASE.json'
    paired,features=Path(paired),Path(features)
    start=perf_counter()
    clip=ClipEncoder(encoder)
    load_seconds=perf_counter()-start
    extraction={}
    for split in ('train','validation','test'):
        start=perf_counter()
        result=extract(paired/f'{split}.csv',paired/'images',encoder,features/split,labels,label_source,encoder=clip)
        extraction[split]={**result,'seconds':perf_counter()-start,'posts_sha256':digest_file(features/split/'posts.csv')}
        print(json.dumps({'extraction':split,**extraction[split]}),flush=True)
    start=perf_counter()
    metrics=train(*(features/split for split in ('train','validation','test')),output=model,compare=True,estimators=400)
    training_seconds=perf_counter()-start
    from xgboost import XGBClassifier
    classifier=XGBClassifier(); classifier.load_model(Path(model)/'model.json')
    import pandas as pd
    posts=pd.read_csv(paired/'test.csv',dtype={'id':'string'})
    measured=[]
    for _,row in posts.head(6).iterrows():
        image=decode_image((paired/'images'/row['image_path']).read_bytes())
        try:
            start=perf_counter()
            visual,language=clip.encode(row['clean_title'],image)
            classifier.predict_proba(np.concatenate([visual,language],axis=1))
            measured.append((perf_counter()-start)*1000)
        finally:
            image.close()
    # First measurement is warm-up; sample is explicitly small and hardware-specific.
    timings=measured[1:]
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes=peak if sys.platform=='darwin' else peak*1024
    manifest=json.loads((Path(model)/'manifest.json').read_text())
    result={'evaluated_at':datetime.now(timezone.utc).isoformat(),'status':'exploratory_pilot','production_model_changed':False,
            'acquisition':json.loads((paired/'provenance.json').read_text()),'manifest':manifest,'metrics':metrics,
            'resources':{'hardware':platform.machine(),'platform':platform.system(),'device':'cpu','torch_threads':torch.get_num_threads(),
                         'encoder_load_seconds':load_seconds,'extraction':extraction,'training_and_ablations_seconds':training_seconds,
                         'end_to_end_latency':{'rows':len(timings),'warmup_rows':1,'includes':'Loaded CLIP text/image encoding plus combined XGBoost predict_proba; excludes network, decoding and model loading',
                                               'p50_ms':float(np.median(timings)),'p95_ms':float(np.percentile(timings,95))},
                         'process_peak_rss_bytes':int(peak_bytes),'encoder_safetensors_bytes':(Path(encoder)/'model.safetensors').stat().st_size,
                         'classifier_bytes':(Path(model)/'model.json').stat().st_size},
            'artifacts':{'metrics_sha256':digest_file(Path(model)/'metrics.json'),'manifest_sha256':digest_file(Path(model)/'manifest.json'),
                         'encoder_provenance':json.loads((Path(encoder)/'download-provenance.json').read_text()),
                         'first_20_error_ids':json.loads((Path(model)/'test_errors.json').read_text())[:20]},
            'limitations':['Small balanced availability-selected pilot; not a representative full Fakeddit benchmark or new release.',
                           'All three modalities use identical retained IDs and independent official splits; validation controls early stopping.',
                           'Exact image hashes and normalized text checked across splits; perceptual/semantic near duplicates and placeholders are not fully audited.',
                           'Latency sample is five warm CPU inferences; peak RSS covers the entire process, not incremental model memory.',
                           'No human-reviewed evidence accuracy, image authenticity or image-headline consistency is established.',
                           'Large CLIP artifacts remain offline; Vercel continues to serve the portable text classifier.']}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(output),'combined_macro_f1':metrics['macro_f1'],'ablations':{name:record['macro_f1'] for name,record in metrics['ablations'].items()},'resources':result['resources']}),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('paired','encoder','features','model','output'):parser.add_argument('--'+name,required=True)
    run(**vars(parser.parse_args()))
