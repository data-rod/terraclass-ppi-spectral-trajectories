"""Resolve code resources and explicitly configured data locations."""
from pathlib import Path
import os
import sysconfig

PACKAGE = Path(__file__).resolve().parent
_source_root = PACKAGE.parents[1]
CODE_ROOT = (_source_root if (_source_root/'config/experiment.json').is_file()
             else Path(sysconfig.get_path('data'))/'share/terraclass_ppi')
CONFIG = CODE_ROOT/'config'

def data_root(value=None):
    value = value or os.environ.get('RBC_DATA_ROOT')
    if not value:
        raise ValueError('Set RBC_DATA_ROOT or pass --data-root to the extracted data directory.')
    return Path(value).expanduser().resolve()

def output_root():
    return Path(os.environ.get('RBC_OUTPUT_ROOT',Path.cwd()/'outputs')).expanduser().resolve()
