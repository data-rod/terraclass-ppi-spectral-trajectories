"""Schedule independent dates using the shared MNF–PPI implementation."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,os,time
import pandas as pd

def worker(args):
    work,date,seeds,dims=args
    os.environ['RBC_OUTPUT']=work
    import terraclass_ppi.ppi as ppi
    ppi.OUT=Path(work);ppi.candidates(seeds,only_dates={date},dimension_values=dims)
    return date

def run(work,workers=2,seeds=(13,)):
    from terraclass_ppi.backend import require_ppi_backend
    backend=require_ppi_backend()
    work=Path(work).resolve();dims=json.loads((work/'dimensions.json').read_text())
    (work/'ppi-backend.json').write_text(json.dumps(dict(native_backend=backend,worker_thread_limit=2,seeds=list(seeds)),indent=2),encoding='utf-8')
    from terraclass_ppi.spatial import CFG
    dates=sorted(pd.read_parquet(work/'catalog.parquet').date.unique())
    started=time.monotonic();done=0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(worker,(str(work),d,list(seeds),dims)) for d in dates]
        for f in as_completed(futures):
            date=f.result();done+=1
            (work/'ppi-progress.json').write_text(json.dumps(dict(completed_dates=done,total_dates=len(dates),last_date=str(date),seconds=time.monotonic()-started,workers=workers)),encoding='utf-8')
    return len(dates)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--all-seeds',action='store_true');a=p.parse_args();run(a.work,a.workers,(13,29,47) if a.all_seeds else (13,))
