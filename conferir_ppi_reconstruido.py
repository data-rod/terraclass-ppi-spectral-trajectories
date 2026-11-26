"""Compare every regenerated PPI candidate, then refit against rebuilt inputs."""
from pathlib import Path
import argparse,json,time
import numpy as np
import pandas as pd
from dados import sha

def verify(source,rebuilt,output):
    source,rebuilt,output=map(lambda x:Path(x).resolve(),(source,rebuilt,output))
    expected=list(sorted((source/'candidates').glob('13-*.parquet')))
    actual=list(sorted((rebuilt/'candidates').glob('13-*.parquet')))
    assert len(expected)==len(actual)==519
    hashes={};records={}
    for p in expected:
        q=rebuilt/'candidates'/p.name
        a=pd.read_parquet(p);b=pd.read_parquet(q)
        pd.testing.assert_frame_equal(a.reset_index(drop=True),b.reset_index(drop=True),check_exact=True)
        assert b.votes.sum()==20000
        hashes[p.name]=sha(q);seed=p.name.split('-')[0];records[seed]=records.get(seed,0)+len(b)
    assert json.loads((source/'dimensions.json').read_text())==json.loads((rebuilt/'dimensions.json').read_text())
    a=pd.read_parquet(source/'nwhfc.parquet');b=pd.read_parquet(rebuilt/'nwhfc.parquet')
    pd.testing.assert_frame_equal(a,b,check_exact=True)
    for key in ['date','classe','n_valid','state','noise_pairs','intrinsic_dimension','suggested_endmembers']:
        pd.testing.assert_series_equal(a[key],b[key],check_dtype=False)
    proof=dict(verified=True,seed=13,candidate_files=519,vote_conservation=True,all_candidates_match_exactly=True,candidate_records_by_seed=records,dimensions_match=True,NWHFC_match=True,supplementary_seeds='model application and temporal verification; full PPI reconstruction optional',files=hashes)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(proof,indent=2),encoding='utf-8');print('All 519 primary-seed regenerated candidate tables match exactly',flush=True)
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--rebuilt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--refit-output',type=Path)
    a=p.parse_args();verify(a.source,a.rebuilt,a.output)
    if a.refit_output:
        from reproducao_modelagem import reproduce
        reproduce(a.source,a.refit_output,candidate_dir=a.rebuilt/'candidates')
