"""Estimate paired uncertainty for the fixed pilot's combined versus text-only result."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
from ml.models.classifier import build_classifier
from ml.training.train_multimodal import validate_splits
from ml.utils.contracts import digest_file


def compare(features,model,report,output):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new comparison output')
    source=json.loads(Path(report).read_text())
    splits,manifest=validate_splits([Path(features)/name for name in ('train','validation','test')])
    (training,x_train),(validation,x_val),(test,x_test)=splits
    boundary=manifest['widths']['image']
    baseline=build_classifier(400)
    baseline.fit(x_train[:,boundary:],training['2_way_label'],eval_set=[(x_val[:,boundary:],validation['2_way_label'])],verbose=False)
    text=baseline.predict(x_test[:,boundary:])
    combined=XGBClassifier();combined.load_model(Path(model)/'model.json')
    fused=combined.predict(x_test)
    y=test['2_way_label'].to_numpy()
    f1=lambda actual,pred:float(f1_score(actual,pred,labels=[0,1],average='macro',zero_division=0))
    if not np.isclose(f1(y,text),source['metrics']['ablations']['text_only']['macro_f1']) or not np.isclose(f1(y,fused),source['metrics']['macro_f1']):
        raise ValueError('Reproduced predictions do not match the recorded pilot metrics')
    rng=np.random.default_rng(42)
    differences=[]
    for _ in range(2000):
        indices=rng.integers(0,len(y),len(y))
        differences.append(f1(y[indices],fused[indices])-f1(y[indices],text[indices]))
    gained=int(((fused==y)&(text!=y)).sum())
    lost=int(((fused!=y)&(text==y)).sum())
    discordant=gained+lost
    result={'evaluated_at':datetime.now(timezone.utc).isoformat(),'pilot_report_sha256':digest_file(report),'rows':len(y),
            'comparison':'Fixed CLIP text-only versus fixed CLIP combined XGBoost on identical pilot test IDs',
            'macro_f1_delta':f1(y,fused)-f1(y,text),'paired_bootstrap':{'seed':42,'resamples':2000,'percentile_95_interval':[float(v) for v in np.percentile(differences,[2.5,97.5])]},
            'correctness_discordance':{'combined_only_correct':gained,'text_only_correct':lost,
                                      'exact_two_sided_mcnemar_p':float(binomtest(gained,discordant,.5).pvalue) if discordant else 1.},
            'limitations':['Exploratory uncertainty estimates on a small availability-selected balanced pilot, not external validation.',
                            'Bootstrap resamples paired examples; it does not capture training, source-cluster or dataset-selection uncertainty.',
                            'Models and hyperparameters are fixed; this comparison does not select or deploy a model.']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('features','model','report','output'):parser.add_argument('--'+name,required=True)
    compare(**vars(parser.parse_args()))
