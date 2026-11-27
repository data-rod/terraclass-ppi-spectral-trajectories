"""Read canonical data and prepare isolated local execution views."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import zipfile
import pandas as pd
import pyarrow.parquet as pq
from terraclass_ppi.paths import data_root, output_root

OFFLINE_SHA256='6ea169d848f92e50aabb2f329685f314b244d34191d8091e43390d404af4255a'

def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def candidate_files(directory,seed):
    directory=Path(directory)
    consolidated=directory/f'candidates_seed{seed}.parquet'
    return [consolidated] if consolidated.exists() else sorted(directory.glob(f'{seed}-*.parquet'))

def iter_candidate_groups(directory,seed,columns=None):
    """Yield groups in the original sorted-partition order, preserving row order."""
    files=candidate_files(directory,seed)
    if not files:raise FileNotFoundError(f'No candidates for seed {seed} in {directory}')
    if len(files)==1 and files[0].name.startswith('candidates_seed'):
        source=pq.ParquetFile(files[0])
        for i in range(source.num_row_groups):
            table=source.read_row_group(i,columns=columns)
            key=source.read_row_group(i,columns=['date','classe']).slice(0,1).to_pylist()[0]
            yield f"{seed}-{key['date']}-{key['classe']}.parquet",table.to_pandas()
    else:
        for path in files:yield path.name,pd.read_parquet(path,columns=columns)

def load_candidates(directory,seed,columns=None):
    return pd.concat([frame for _,frame in iter_candidate_groups(directory,seed,columns)],ignore_index=True)

def load_candidate_group(directory,seed,date,classe,columns=None):
    path=Path(directory)/f'candidates_seed{seed}.parquet'
    if path.exists():
        return pd.read_parquet(path,columns=columns,filters=[('date','=',str(date)),('classe','=',int(classe))])
    return pd.read_parquet(Path(directory)/f'{seed}-{date}-{classe}.parquet',columns=columns)

def consolidate_candidates(directory,seed,destination):
    """Consolidate completed checkpoints with a single writer."""
    files=sorted(Path(directory).glob(f'{seed}-*.parquet'))
    if len(files)!=519:raise ValueError('Expected 519 completed class/date checkpoints')
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    pending=destination.with_suffix('.pending')
    with pq.ParquetWriter(pending,pq.read_schema(files[0]),compression='zstd') as writer:
        for path in files:
            table=pq.read_table(path)
            if sum(table.column('votes').to_pylist())!=20000:raise ValueError(path.name)
            writer.write_table(table)
    pending.replace(destination)
    return destination

class TableDirectory:
    """Resolve historical table basenames to their sole canonical file."""
    def __init__(self,root=None):
        self.root=data_root(root)
        self.mapping=json.loads((self.root/'data/provenance/table_paths.json').read_text(encoding='utf-8'))
    def __truediv__(self,name):
        return self.root/self.mapping[Path(name).name]

def table_directory(root=None):return TableDirectory(root)

def _link(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if file_hash(source)!=file_hash(target):raise ValueError(f'Changed execution input: {target}')
        return
    try:os.link(source,target)
    except OSError:shutil.copy2(source,target)

def import_offline(archive,root=None):
    """Import the unchanged archive into data/raw, checking every member's CRC."""
    root=data_root(root);archive=Path(archive)
    if file_hash(archive)!=OFFLINE_SHA256:raise ValueError('Offline archive differs from the frozen inputs')
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            parts=Path(member.filename).parts
            if len(parts)<3 or parts[0]!='work' or parts[1] not in {'observations','terraclass'}:continue
            target=root/'data/raw'/Path(*parts[1:])
            target.parent.mkdir(parents=True,exist_ok=True)
            pending=target.with_suffix(target.suffix+'.pending')
            with source.open(member) as src,pending.open('wb') as out:shutil.copyfileobj(src,out)
            pending.replace(target)
    return prepare_reference(root)

def prepare_reference(root=None,destination=None):
    """Create a disposable working view; canonical data are never processing outputs."""
    root=data_root(root);os.environ['RBC_DATA_ROOT']=str(root)
    destination=Path(destination or output_root()/'reference').resolve()
    if destination==root or root in destination.parents:
        raise ValueError('Choose an execution directory outside the canonical dataset')
    mapping=json.loads((root/'data/provenance/runtime_paths.json').read_text(encoding='utf-8'))
    for name,relative in mapping.items():_link(root/relative,destination/name)
    for seed in [13,29,47]:
        _link(root/f'data/derived/candidates/candidates_seed{seed}.parquet',destination/f'candidates/candidates_seed{seed}.parquet')
    raw=root/'data/raw'
    if raw.exists():
        for path in raw.rglob('*'):
            if path.is_file():_link(path,destination/path.relative_to(raw))
    return destination
