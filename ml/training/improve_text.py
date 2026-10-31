"""Validation-selected word/character linear candidates; no test-driven tuning."""
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


def vectorizers(mode):
    word=TfidfVectorizer(ngram_range=(1,2),max_features=40000 if mode=='baseline' else 100000,
                         min_df=1 if mode=='baseline' else 2,sublinear_tf=True,dtype=np.float64)
    char=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=100000,min_df=3,sublinear_tf=True,dtype=np.float64) if mode=='word_char' else None
    return word,char


def matrix(model,texts):
    pieces=[model['word'].transform(texts)]
    if model['char'] is not None:pieces.append(model['char'].transform(texts))
    values=hstack(pieces,format='csr') if len(pieces)>1 else pieces[0]
    return values.multiply(model['ratio']).tocsr() if model['ratio'] is not None else values


def build_features(training,validation,mode):
    word,char=vectorizers(mode)
    pieces=[word.fit_transform(training['clean_title'])]
    val=[word.transform(validation['clean_title'])]
    if char is not None:
        pieces.append(char.fit_transform(training['clean_title']));val.append(char.transform(validation['clean_title']))
    x=hstack(pieces,format='csr') if len(pieces)>1 else pieces[0]
    v=hstack(val,format='csr') if len(val)>1 else val[0]
    ratio=None
    if mode=='nb_word':
        labels=training['2_way_label'].to_numpy()
        positive=np.asarray(x[labels==1].sum(axis=0)).ravel()+1
        negative=np.asarray(x[labels==0].sum(axis=0)).ravel()+1
        ratio=np.log((positive/positive.sum())/(negative/negative.sum()))
        x=x.multiply(ratio).tocsr();v=v.multiply(ratio).tocsr()
    return {'word':word,'char':char,'ratio':ratio},x,v


def candidates(training,validation,mode,regularizations=(.3,1.,3.),balanced=False):
    model,x,v=build_features(training,validation,mode)
    records=[];best=None
    for c in regularizations:
        classifier=LogisticRegression(C=c,max_iter=1000,solver='liblinear',random_state=42,class_weight='balanced' if balanced else None)
        classifier.fit(x,training['2_way_label'])
        predictions=classifier.predict(v)
        score=float(f1_score(validation['2_way_label'],predictions,average='macro',zero_division=0))
        record={'mode':mode,'C':c,'class_weight':'balanced' if balanced else None,'validation_macro_f1':score,
                'validation_accuracy':float(accuracy_score(validation['2_way_label'],predictions)),
                'training_rows':len(training),'word_features':len(model['word'].vocabulary_),
                'character_features':len(model['char'].vocabulary_) if model['char'] is not None else 0}
        records.append(record)
        if best is None or score>best[0]:best=(score,{**model,'classifier':classifier,'parameters':record})
    return best[1],records


def predict(model,texts):
    return model['classifier'].predict(matrix(model,texts))


def probabilities(model,texts):
    return model['classifier'].predict_proba(matrix(model,texts))
