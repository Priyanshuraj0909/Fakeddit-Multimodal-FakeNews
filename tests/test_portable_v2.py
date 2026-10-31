"""Synthetic feature/parity fixtures; no research accuracy is inferred from these tests."""
from collections import Counter
import gzip
import json
import numpy as np
import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from ml.training.improve_text import candidates,probabilities
from ml.inference import portable_text


@pytest.mark.parametrize('text',['a I x','NASA\tconfirms   moon\nnews','Café naïve scientists','  two\u2003words! ','', 'emoji 🙂 fragment'])
def test_character_features_match_sklearn_including_short_words_and_unicode(text):
    vector=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True)
    assert portable_text.feature_counts(text,'char_wb')==Counter(vector.build_analyzer()(text))


@pytest.mark.parametrize('mode',['word_char','nb_word'])
def test_portable_probabilities_match_real_sklearn_word_character_and_nb_models(tmp_path,mode):
    texts=['Café scientists document a species in the rainforest '+str(i) if i%2 else 'Fabricated imaginary rumor about a cheese moon '+str(i) for i in range(24)]
    frame=pd.DataFrame({'id':[str(i) for i in range(24)],'clean_title':texts,'2_way_label':[i%2 for i in range(24)]})
    model,_=candidates(frame,frame,mode,regularizations=(1.,),balanced=True)
    coefficients=model['classifier'].coef_[0]
    if model['ratio'] is not None:coefficients=coefficients*model['ratio']
    branches=[];offset=0
    for name,key,analyzer,ngrams in [('word','word','word',[1,2]),('character','char','char_wb',[3,5])]:
        vector=model[key]
        if vector is None:continue
        branches.append({'name':name,'analyzer':analyzer,'ngram_range':ngrams,
                         'features':{term:[float(vector.idf_[index]),float(coefficients[offset+index])] for term,index in vector.vocabulary_.items()}})
        offset+=len(vector.vocabulary_)
    data={'schema':'fakeddit_tfidf_linear_v2','release':'synthetic-test','labels':portable_text.LABELS,
          'intercept':float(model['classifier'].intercept_[0]),'branches':branches,
          'metrics':{'test_accuracy':.5,'test_macro_f1':.5,'rows':{'test':2}}}
    path=tmp_path/'synthetic.json.gz'
    with gzip.open(path,'wt') as stream:json.dump(data,stream)
    samples=['Café scientists\tdocument a new species', 'Fabricated  imaginary rumor\nabout cheese moon',*texts[:4]]
    expected=probabilities(model,samples)
    for text,target in zip(samples,expected):
        result=portable_text.predict(text,path)
        assert result['probabilities']
        np.testing.assert_allclose(list(result['probabilities'].values()),target,atol=1e-12)
        assert result['release']=='synthetic-test'
    data['branches'][0]['analyzer']='unsupported'
    invalid=tmp_path/'invalid.json.gz'
    with gzip.open(invalid,'wt') as stream:json.dump(data,stream)
    with pytest.raises(ValueError,match='branch'):portable_text.load_release(str(invalid))


def test_historical_v1_artifact_remains_readable():
    path=portable_text.RELEASE.parent/'text-v1.json.gz'
    result=portable_text.predict('Scientists discover a new species in the rainforest',path)
    assert result['release']=='text-v1'
    assert result['metrics']['test_accuracy']==pytest.approx(.8064666666666667)
