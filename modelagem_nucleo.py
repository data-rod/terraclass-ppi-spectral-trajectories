"""Shared grouped classification, threshold and representative-selection functions."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score,roc_auc_score,precision_recall_curve,confusion_matrix
from dados import HERE
from analise import splits

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.pending')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');temporary.replace(path)


def group_ids(frame):return frame.classe.astype(str)+':'+frame.date.astype(str)


def threshold(y,p,config):
    precision,recall,thresholds=precision_recall_curve(y,p)
    rows=[]
    for pr,re,t in zip(precision[:-1],recall[:-1],thresholds):
        predicted=int(np.count_nonzero(p>=t))
        if predicted>=config['inner_min_predicted_positive'] and pr>=config['inner_candidate_precision_goal']:
            rows.append((float(re),float(pr),float(t),predicted))
    if not rows:raise ValueError('No threshold satisfies the configured candidate precision and minimum positive count. Check the development labels and selection settings.')
    re,pr,t,n=max(rows)
    return dict(threshold=t,recall=re,precision=pr,predicted_positive=n,ap=float(average_precision_score(y,p)))


def params(config,choice):
    base=json.loads((HERE/'classifier.json').read_text(encoding='utf-8-sig'))
    base.update(config['immutable_parameters']);base.update({k:v for k,v in choice.items() if k!='name'})
    return base


def inner_search(data,x,y,groups,config,folder):
    folder.mkdir(parents=True,exist_ok=True)
    plan=splits(y,groups,config['inner_folds']);choices=[]
    partitions=[]
    for k,(train,test) in enumerate(plan,1):
        assert not set(groups[train])&set(groups[test])
        partitions.extend(dict(candidate_id=data.iloc[i].candidate_id,group=groups[i],inner_fold=k) for i in test)
    pd.DataFrame(partitions).to_csv(folder/'partitions.csv',index=False)
    for order,choice in enumerate(config['parameters_to_compare']):
        prediction_path=folder/(choice['name']+'_oof.csv')
        if prediction_path.exists():
            frame=pd.read_csv(prediction_path)
            assert frame.candidate_id.tolist()==data.candidate_id.tolist()
            p=frame.probability.to_numpy()
        else:
            p=np.full(len(data),np.nan)
            for k,(train,test) in enumerate(plan,1):
                model=HistGradientBoostingClassifier(**params(config,choice)).fit(x[train],y[train])
                p[test]=model.predict_proba(x[test])[:,1]
            assert np.isfinite(p).all()
            pd.DataFrame(dict(candidate_id=data.candidate_id,observed=y,probability=p)).to_csv(prediction_path,index=False)
        score=threshold(y,p,config)|dict(name=choice['name'],order=order)
        choices.append(score)
        print(f'  {folder.name} / {choice["name"]}: precision {score["precision"]:.4f}, recall {score["recall"]:.4f}',flush=True)
    chosen=max(choices,key=lambda r:(r['recall'],r['precision'],r['ap'],-r['order']))
    save(folder/'selection.json',dict(choices=choices,chosen=chosen,threshold_population='labelled development candidates, not selected representatives'))
    return chosen


def choose_representatives(frame,probabilities,t,fold):
    frame=frame.copy();frame['probability']=probabilities;frame['fold']=fold;frame['threshold']=t
    accepted=frame[frame.probability>=t].sort_values(['date','classe','votes','pixel'],ascending=[True,True,False,True])
    selected=accepted.drop_duplicates(['date','classe']).copy()
    return frame,selected


def classification_scores(y,p,t):
    tn,fp,fn,tp=confusion_matrix(y,p>=t,labels=[0,1]).ravel()
    return dict(ap=float(average_precision_score(y,p)),roc_auc=float(roc_auc_score(y,p)),tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp),precision=float(tp/(tp+fp)) if tp+fp else None,recall=float(tp/(tp+fn)),specificity=float(tn/(tn+fp)))
