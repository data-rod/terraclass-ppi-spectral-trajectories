"""Check archived eligibility against retained values and per-asset nodata."""
from pathlib import Path
import argparse,json,time
import numpy as np
import pandas as pd
from terraclass_ppi.spatial import CFG,sha
from terraclass_ppi.spectral import BANDAS

def verify(work,output):
    work=Path(work).resolve();started=time.monotonic()
    pixels=pd.read_parquet(work/'pixels.parquet')
    positions={tile:np.flatnonzero(pixels.tile.eq(tile)) for tile in pixels.tile.unique()}
    records=[]
    for path in sorted((work/'observations').glob('*.npy')):
        receipt=json.loads(path.with_suffix('.json').read_text())
        assert sha(path)==receipt['sha256']
        data=np.load(path,mmap_mode='r',allow_pickle=False)
        valid=np.ones(len(data),dtype=bool)
        for asset in receipt['assets']:
            if asset['asset']=='PROVENANCE':continue
            idx=positions[asset['tile']];values=data[asset['asset']][idx]
            valid[idx]&=np.isfinite(values)
            if asset['nodata'] is not None:valid[idx]&=values!=asset['nodata']
        valid&=~np.isin(data['SCL'],CFG['scl_excluded']) & (data['CLEAROB']>0)
        np.testing.assert_array_equal(valid,data['valid'])
        assert int(valid.sum())==receipt['valid']
        records.append(dict(date=path.stem,n_valid=int(valid.sum()),mask_matches=True))
    assert len(records)==184
    report=dict(verified=True,dates=184,all_masks_match=True,scope='Archived spectral values, SCL, CLEAROB and per-asset nodata; source raster internal masks are not re-downloaded.',seconds=time.monotonic()-started,dates_checked=records)
    Path(output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('All 184 archived quality masks match retained values and source nodata',flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.work,a.output)
