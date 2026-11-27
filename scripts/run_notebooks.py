"""Execute all notebooks; store executed notebooks and HTML under outputs/."""
import argparse,os
from pathlib import Path
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    os.environ['RBC_DATA_ROOT']=str(a.data_root.resolve())
    from terraclass_ppi.data_io import prepare_reference
    os.environ['RBC_OUTPUT']=str(prepare_reference(a.data_root))
    from terraclass_ppi.notebook_runner import run
    run(Path(__file__).resolve().parents[1],a.resume)
