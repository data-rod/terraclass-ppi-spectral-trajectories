"""Reject mixed model generations before quick verification or full packaging."""
import json
import numpy as np
import pandas as pd
from terraclass_ppi.spatial import CFG,OUT,json_save

def verify_sync():
    model=json.loads((OUT/'model/model.json').read_text(encoding='utf-8'))
    reference=None;details={}
    for seed in CFG['seeds']:
        f=pd.read_parquet(OUT/'results'/f'representatives-{seed}.parquet')
        if not f.analysis_id.eq(model['analysis_id']).all():
            raise ValueError(f'Seed {seed}: stale classifier generation. Run scripts/run_pipeline.py supplementary in a separate model-output directory.')
        if not f.run_id.eq(model['run_id']).all() or (f.probability<model['threshold']).any():
            raise ValueError(f'Seed {seed}: invalid run or operational decision.')
        if f.duplicated(['classe','date']).any():raise ValueError('Duplicate representatives')
        if seed==13:reference=f
        else:
            a=pd.read_csv(OUT/'results'/f'representative_agreement-{seed}.csv')
            expected=reference[['date','classe','candidate_id']].merge(
                f[['date','classe','candidate_id']],on=['date','classe'],how='outer',
                suffixes=('_reference','_other'))
            merged=a.merge(expected,on=['date','classe'],suffixes=('_saved','_current'),validate='one_to_one')
            if len(merged)!=len(expected):raise ValueError('Incomplete agreement table')
            for key in ['candidate_id_reference','candidate_id_other']:
                if not merged[key+'_saved'].eq(merged[key+'_current']).all():
                    raise ValueError(f'Seed {seed}: stale agreement reference; regenerate supplementary outputs with scripts/run_pipeline.py supplementary.')
        m=pd.read_csv(OUT/'results'/f'metrics-{seed}.csv')
        d=pd.read_csv(OUT/'results'/f'domains-{seed}.csv')
        expected=m.groupby(['seed','window','classe','domain'])[['FS','FT']].median().reset_index()
        keys=['seed','window','classe','domain']
        pd.testing.assert_frame_equal(d.sort_values(keys).reset_index(drop=True),
            expected.sort_values(keys).reset_index(drop=True),check_exact=False,rtol=0,atol=1e-8)
        actual=pd.read_csv(OUT/'results'/f'distances-{seed}.csv')
        distances=[]
        for c,g in f.groupby('classe'):
            g=g.sort_values('date')
            for row in g.assign(distance_km=np.hypot(g.x.diff(),g.y.diff())/1000,
                elapsed_days=pd.to_datetime(g.date).diff().dt.days).dropna(subset=['distance_km']).itertuples():
                distances.append(dict(date=row.date,classe=c,distance_km=row.distance_km,elapsed_days=row.elapsed_days))
        keys=['classe','date']
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
            pd.DataFrame(distances).sort_values(keys).reset_index(drop=True),
            check_dtype=False,check_exact=False,rtol=0,atol=1e-8)
        details[str(seed)]={'representatives':len(f),'metrics':len(m),'analysis_id':model['analysis_id']}
        if seed!=13:details[str(seed)]['same_representatives']=int(a.same_pixel.sum())
    receipt=dict(verified=True,analysis_id=model['analysis_id'],threshold=model['threshold'],seeds=details)
    json_save(OUT/'results/synchronization.json',receipt)
    json_save(OUT/'results/verification_sensitivity.json',receipt|dict(scope='Supplementary seed verification only; primary article uses seed 13.'))
    print('Verified model generation, agreement references, domains and distances for seeds 13, 29 and 47',flush=True)
    return receipt

if __name__=='__main__':verify_sync()
