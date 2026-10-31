"""Fit stronger lightweight text candidates and freeze selection before final testing.

The historical test is reused as a regression benchmark, not new external data.
"""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from ml.training.improve_text import candidates,predict
from ml.training.train_text import read_split,check_disjoint
from ml.utils.contracts import digest_file,check_content_disjoint
from scripts.prepare_text_release import prepare
from scripts.evaluate_shift import summarize,unseen_mask


def run(output,prepared):
    output=Path(output);prepared=Path(prepared)
    if output.exists():raise ValueError('Choose a new experiment directory')
    output.mkdir(parents=True)
    protocol={'started_at':datetime.now(timezone.utc).isoformat(),'seed':42,
              'selection':'Screen fixed candidates on original 150,000 train/15,000 validation, then refit winning architecture on all eligible official training rows. Select by validation macro F1 only.',
              'candidates':[{'mode':m,'balanced':b,'C':[.3,1.,3.]} for m,b in [('word',False),('word_char',False),('nb_word',False),('word_char',True)]],
              'promotion_gate':'Validation macro F1 and regression test accuracy/macro F1 must improve; paired bootstrap 95% accuracy-delta lower bound >0; neither test class recall may decline by more than 0.02; exploratory temporal macro F1 must not decline by more than 0.02 against an equal-data word baseline.',
              'limitations':['Historical test has been evaluated in prior releases; no newly collected independent labels are available.',
                             'Preprocessing and NB feature ratios are fitted only on training; source/author metadata is never used as a model feature.',
                             'Post-test outcomes cannot change candidate parameters; a failed promotion gate preserves the current deployed release.']}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    old=Path('data/processed/text-release-v1')
    training=read_split(old/'train.csv','clean_title','2_way_label')
    validation=read_split(old/'validation.csv','clean_title','2_way_label')
    baseline_manifest=json.loads(Path('docs/TEXT_MODEL_RELEASE.json').read_text())
    records=[];selected=None
    for mode,balanced in [('word',False),('word_char',False),('nb_word',False),('word_char',True)]:
        start=perf_counter()
        model,results=candidates(training,validation,mode,balanced=balanced)
        records.extend(results)
        if selected is None or model['parameters']['validation_macro_f1']>selected['parameters']['validation_macro_f1']:selected=model
        print(json.dumps({'screen':mode,'balanced':balanced,'best':model['parameters'],'seconds':perf_counter()-start}),flush=True)
        (output/'validation_search.json').write_text(json.dumps(records,indent=2)+'\n')
        gc.collect()
    # Larger training uses only the official train split; validation/test membership stays byte-identical.
    provenance=prepare('data/raw',prepared,limits=(10**9,15000,15000))
    for name in ('validation','test'):
        if digest_file(prepared/f'{name}.csv')!=digest_file(old/f'{name}.csv'):raise ValueError('Evaluation split changed')
    full=read_split(prepared/'train.csv','clean_title','2_way_label')
    p=selected['parameters']
    expanded,results=candidates(full,validation,p['mode'],balanced=p['class_weight']=='balanced')
    records.extend(results)
    print(json.dumps({'expanded':expanded['parameters']}),flush=True)
    if expanded['parameters']['validation_macro_f1']>selected['parameters']['validation_macro_f1']:selected=expanded
    p=selected['parameters']
    (output/'validation_search.json').write_text(json.dumps(records,indent=2)+'\n')
    joblib.dump(selected,output/'model.joblib')
    frozen={'frozen_at':datetime.now(timezone.utc).isoformat(),'parameters':selected['parameters'],'model_sha256':digest_file(output/'model.joblib'),
            'split_hashes':{name:digest_file(prepared/f'{name}.csv') for name in ('train','validation','test')}}
    (output/'selection_frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
    # No additional model/parameter selection below this point.
    test=read_split(prepared/'test.csv','clean_title','2_way_label')
    check_disjoint([full,validation,test]);check_content_disjoint([full,validation,test])
    baseline=joblib.load('models/exported/text-release-v1/model.joblib')
    actual=test['2_way_label'].to_numpy();before=baseline.predict(test['clean_title']);after=predict(selected,test['clean_title'])
    base_metrics=summarize(test,before);new_metrics=summarize(test,after)
    if not np.isclose(base_metrics['accuracy'],baseline_manifest['metrics']['test_accuracy']):raise ValueError('Baseline regression data mismatch')
    delta=(after==actual).astype(float)-(before==actual).astype(float)
    rng=np.random.default_rng(42);samples=[]
    for _ in range(20):samples.extend(delta[rng.integers(0,len(delta),size=(100,len(delta)))].mean(axis=1).tolist())
    interval=np.percentile(samples,[2.5,97.5]).tolist()
    gained=int(((after==actual)&(before!=actual)).sum());lost=int(((after!=actual)&(before==actual)).sum())
    # Equal-data chronological refits; architecture selection used full validation, so this is exploratory.
    raw_train=pd.read_csv('data/raw/multimodal_train.tsv',sep='\t',usecols=['id','created_utc','author','domain'],dtype={'id':'string'})
    raw_val=pd.read_csv('data/raw/multimodal_validate.tsv',sep='\t',usecols=['id','created_utc','author','domain'],dtype={'id':'string'})
    raw_test=pd.read_csv('data/raw/multimodal_test_public.tsv',sep='\t',usecols=['id','created_utc','author','domain'],dtype={'id':'string'})
    train_meta=full.merge(raw_train,on='id',validate='one_to_one');val_meta=validation.merge(raw_val,on='id',validate='one_to_one');test_meta=test.merge(raw_test,on='id',validate='one_to_one')
    cutoff=pd.Timestamp('2018-01-01',tz='UTC')
    earlier=train_meta.loc[pd.to_datetime(train_meta.created_utc,unit='s',utc=True)<cutoff]
    earlier_val=val_meta.loc[pd.to_datetime(val_meta.created_utc,unit='s',utc=True)<cutoff]
    future=test_meta.loc[pd.to_datetime(test_meta.created_utc,unit='s',utc=True)>=cutoff]
    temporal_base,_=candidates(earlier,earlier_val,'baseline')
    temporal_new,_=candidates(earlier,earlier_val,p['mode'],balanced=p['class_weight']=='balanced')
    time_base=summarize(future,predict(temporal_base,future['clean_title']));time_new=summarize(future,predict(temporal_new,future['clean_title']))
    reference=pd.concat([train_meta,val_meta],ignore_index=True)
    groups={}
    for column in ('author','domain'):
        mask=unseen_mask(reference,test_meta,column)
        groups[column]={'baseline':summarize(test_meta.loc[mask],before[mask]),'candidate':summarize(test_meta.loc[mask],after[mask])}
    recalls_ok=all(new_metrics['classification_report'][str(c)]['recall']>=base_metrics['classification_report'][str(c)]['recall']-.02 for c in (0,1))
    gates={'validation_improved':p['validation_macro_f1']>baseline_manifest['metrics']['validation_macro_f1'],
           'test_accuracy_improved':new_metrics['accuracy']>base_metrics['accuracy'],'test_macro_f1_improved':new_metrics['macro_f1']>base_metrics['macro_f1'],
           'paired_accuracy_interval_positive':interval[0]>0,'class_recall_noninferior':recalls_ok,
           'temporal_macro_f1_noninferior':time_new['macro_f1']>=time_base['macro_f1']-.02}
    result={'evaluated_at':datetime.now(timezone.utc).isoformat(),'protocol':protocol,'selection':frozen,'validation_search':records,
            'training_provenance':provenance,'baseline':base_metrics,'candidate':new_metrics,
            'paired_comparison':{'accuracy_delta':float(delta.mean()),'bootstrap_95_interval':interval,'bootstrap_resamples':2000,
                                 'new_only_correct':gained,'baseline_only_correct':lost,'mcnemar_exact_p':float(binomtest(gained,gained+lost,.5).pvalue) if gained+lost else 1.},
            'temporal':{'cutoff':'2018-01-01','training_rows':len(earlier),'validation_rows':len(earlier_val),'test_rows':len(future),
                        'baseline_parameters':temporal_base['parameters'],'candidate_parameters':temporal_new['parameters'],'baseline':time_base,'candidate':time_new,
                        'limitation':'Exploratory refits: architecture was selected using overall validation. C selection and preprocessing use earlier train/validation only; this is not a fresh external test.'},
            'unseen_groups':groups,'promotion_checks':gates,'eligible_for_promotion':all(gates.values()),
            'limitations':protocol['limitations']+['Distant Reddit labels/source shortcuts remain; metrics concern dataset classification, not factual truth.','Chronological and unseen-group subsets have been used in prior exploratory research.']}
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'candidate':new_metrics['accuracy'],'baseline':base_metrics['accuracy'],'macro_f1':new_metrics['macro_f1'],'temporal':time_new['macro_f1'],'gates':gates,'output':str(output)}),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--prepared',required=True)
    run(**vars(parser.parse_args()))
