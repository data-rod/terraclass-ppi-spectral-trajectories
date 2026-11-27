"""Prepare an isolated working view and optional frozen offline inputs."""
import argparse
from pathlib import Path
from terraclass_ppi.data_io import prepare_reference,import_offline

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--offline-zip',type=Path)
    a=p.parse_args()
    print(import_offline(a.offline_zip,a.data_root) if a.offline_zip else prepare_reference(a.data_root))
