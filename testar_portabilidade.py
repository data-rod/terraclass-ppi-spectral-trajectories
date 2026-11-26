"""Verify all-candidate application and exact winner IDs on another platform."""
from pathlib import Path
import argparse,json,platform,time
import pandas as pd
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from nucleo import atributos

def check(work,output):
    started=time.monotonic();work=Path(work);info=json.loads((work/'model/model.json').read_text())
    fitted=joblib.load(work/'model/classifier.joblib')['model']
    candidates=pd.concat([pd.read_parquet(p) for p in sorted((work/'candidates').glob('13-*.parquet'))],ignore_index=True)
    with threadpool_limits(limits=2):p=fitted.predict_proba(atributos(candidates)[0])[:,1]
    f=candidates.assign(probability=p);accepted=f[f.probability>=info['threshold']]
    selected=accepted.sort_values(['date','classe','votes','pixel'],ascending=[True,True,False,True]).drop_duplicates(['date','classe'])
    expected=pd.read_parquet(work/'results/representatives-13.parquet')
    assert selected.candidate_id.tolist()==expected.candidate_id.tolist()
    error=float(np.max(np.abs(selected.probability.to_numpy()-expected.probability.to_numpy())))
    assert error<=1e-7
    result=dict(platform=platform.platform(),python=platform.python_version(),candidates=len(candidates),accepted=len(accepted),selected=len(selected),winner_ids_match=True,max_probability_difference=error,tolerance=1e-7,seconds=time.monotonic()-started)
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',default='work');p.add_argument('--output',default='portability.json');a=p.parse_args();check(a.work,a.output)
