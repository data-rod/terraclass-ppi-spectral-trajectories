"""Current reproducibility interface: frozen development, grouped selection and STL.

Reference inputs are read from --work; regenerated results use a separate folder.
"""
from pathlib import Path
import argparse,json,os,shutil

def supplementary(work,source):
    import pandas as pd
    work,source=Path(work).resolve(),Path(source).resolve()
    (work/'candidates').mkdir(exist_ok=True)
    for p in (source/'candidates').glob('*.parquet'):
        dest=work/'candidates'/p.name
        if not dest.exists():shutil.copy2(p,dest)
    for name in ['nwhfc.parquet','dimensions.json','catalog.parquet','spatial.json']:
        if not (work/name).exists():shutil.copy2(source/name,work/name)
    import terraclass_ppi.temporal as analise
    before=analise.OUT;analise.OUT=work
    try:
        for seed in [29,47]:
            reps=analise.select(seed);analise.temporal(reps,seed,[7])
            ref=pd.read_parquet(work/'results/representatives-13.parquet')
            match=ref[['date','classe','candidate_id']].merge(reps[['date','classe','candidate_id']],on=['date','classe'],how='outer',suffixes=('_reference','_other'))
            match['same_pixel']=match.candidate_id_reference.eq(match.candidate_id_other)
            match.to_csv(work/f'results/representative_agreement-{seed}.csv',index=False)
    finally:analise.OUT=before
    import terraclass_ppi.validation as sync
    sync.OUT=work;sync.verify_sync()

def quick(work,all_seeds=False):
    os.environ['RBC_OUTPUT']=str(Path(work).resolve())
    from terraclass_ppi.products_reference import quick as check
    check(None if all_seeds else [13])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['supplementary','quick','products','panel','model','complete'])
    p.add_argument('--work',type=Path);p.add_argument('--source-work',type=Path)
    p.add_argument('--data-root',type=Path)
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--all-seeds',action='store_true')
    a=p.parse_args()
    if a.data_root:
        from terraclass_ppi.data_io import prepare_reference
        a.work=prepare_reference(a.data_root)
    if a.work is None:p.error('--data-root or --work is required')
    os.environ['RBC_OUTPUT']=str(a.work.resolve())
    if a.stage=='supplementary':
        if not a.source_work:p.error('--source-work is required')
        supplementary(a.work,a.source_work)
    elif a.stage=='quick':quick(a.work,a.all_seeds)
    elif a.stage=='panel':
        from terraclass_ppi.labeling import painel
        painel()
    elif a.stage=='products':
        if not a.source_work or not a.output_dir:
            p.error('products requires --source-work for the archived reference and --output-dir for new products')
        from terraclass_ppi.products_rebuilt import build
        build(a.work,a.source_work,a.output_dir)
    else:
        if not a.output_dir:p.error('--output-dir is required; reference inputs are never overwritten')
        from terraclass_ppi.reproduction import reproduce
        reproduce(a.work,a.output_dir,complete=a.stage=='complete',all_seeds=a.all_seeds)

if __name__=='__main__':main()
