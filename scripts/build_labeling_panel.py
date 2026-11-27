"""Generate the offline C/NC panel from archived candidates and image inputs."""
import argparse,os
from pathlib import Path
from terraclass_ppi.data_io import prepare_reference
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-root',type=Path,required=True);a=p.parse_args()
    os.environ['RBC_OUTPUT']=str(prepare_reference(a.data_root))
    from terraclass_ppi.labeling import painel
    painel()
