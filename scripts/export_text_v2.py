"""Export a promotion-eligible local linear candidate to compact safe JSON."""
import argparse
import gzip
import json
from pathlib import Path
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from ml.training.improve_text import probabilities
from ml.inference import portable_text
from ml.utils.contracts import digest_file


def export(directory,output):
    directory,output=Path(directory),Path(output)
    if output.exists():raise ValueError('Preserve existing releases; choose a new output')
    report=json.loads((directory/'evaluation.json').read_text())
    if not report['eligible_for_promotion']:raise ValueError('Candidate failed a prespecified promotion gate')
    if digest_file(directory/'model.joblib')!=report['selection']['model_sha256']:raise ValueError('Frozen candidate hash changed')
    model=joblib.load(directory/'model.joblib')
    coefficients=model['classifier'].coef_[0]
    if model['ratio'] is not None:coefficients=coefficients*model['ratio']
    branches=[];offset=0
    for name,key,analyzer,ngrams in [('word','word','word',[1,2]),('character','char','char_wb',[3,5])]:
        vector=model[key]
        if vector is None:continue
        if not vector.sublinear_tf or vector.norm!='l2' or vector.strip_accents is not None or vector.analyzer!=analyzer or list(vector.ngram_range)!=ngrams:
            raise ValueError('Unsupported feature preprocessing for portable export')
        branches.append({'name':name,'analyzer':analyzer,'ngram_range':ngrams,
                         'features':{term:[float(vector.idf_[index]),float(coefficients[offset+index])] for term,index in vector.vocabulary_.items()}})
        offset+=len(vector.vocabulary_)
    if offset!=len(coefficients) or list(model['classifier'].classes_)!=[0,1]:raise ValueError('Feature/class alignment mismatch')
    metrics={'test_accuracy':report['candidate']['accuracy'],'test_macro_f1':report['candidate']['macro_f1'],
             'validation_macro_f1':model['parameters']['validation_macro_f1'],'selected_C':model['parameters']['C'],
             'rows':{'train':model['parameters']['training_rows'],'validation':15000,'test':report['candidate']['rows']}}
    data={'schema':'fakeddit_tfidf_linear_v2','release':'text-v2','labels':portable_text.LABELS,
          'model':'Fakeddit word + character TF-IDF / Logistic Regression' if model['char'] is not None else 'Fakeddit TF-IDF linear classifier',
          'intercept':float(model['classifier'].intercept_[0]),'branches':branches,'metrics':metrics,
          'provenance':{'evaluation_sha256':digest_file(directory/'evaluation.json'),'model_sha256':digest_file(directory/'model.joblib'),
                        'selection':report['selection'],'dataset':report['training_provenance']['dataset']}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as stream:
        stream.write(json.dumps(data,sort_keys=True,separators=(',',':')).encode())
    portable_text.load_release.cache_clear()
    validation=pd.read_csv('data/processed/text-release-v1/validation.csv')
    texts=validation['clean_title'].head(500).tolist()+['NASA\tconfirms   the Moon is made of cheese.','Scientists discover\na new species in the rainforest.']
    expected=probabilities(model,texts)
    errors=[];skipped=0;times=[]
    for text,target in zip(texts,expected):
        start=perf_counter();actual=portable_text.predict(text,output);times.append((perf_counter()-start)*1000)
        if not actual['probabilities']:
            skipped+=1;continue
        errors.append(float(np.max(np.abs(np.array(list(actual['probabilities'].values()))-target))))
    if len(errors)<200 or max(errors)>1e-10:
        output.unlink()
        raise ValueError('Portable parity failed or insufficient usable parity inputs')
    result={'output':str(output),'sha256':digest_file(output),'bytes':output.stat().st_size,'parity':{'inputs':len(texts),'compared':len(errors),'abstained':skipped,'maximum_probability_error':max(errors),'source':'First 500 validation headlines plus whitespace cases; no model selection uses this check'},
            'warm_inference_ms':{'rows':len(times)-1,'median':float(np.median(times[1:])),'p95':float(np.percentile(times[1:],95))},'metrics':metrics}
    (directory/'portable_export.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True);parser.add_argument('--output',required=True)
    export(**vars(parser.parse_args()))
