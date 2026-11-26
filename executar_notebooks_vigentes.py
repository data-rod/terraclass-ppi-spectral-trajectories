"""Execute every notebook in a fresh pinned-environment kernel and export HTML."""
from pathlib import Path
import argparse,json,sys,time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
from datetime import datetime

def code_seconds(book):
    total=0.0
    for c in book.cells:
        stamp=c.get('metadata',{}).get('execution',{})
        if c.cell_type=='code' and 'iopub.status.busy' in stamp and 'iopub.status.idle' in stamp:
            total+=(datetime.fromisoformat(stamp['iopub.status.idle'])-datetime.fromisoformat(stamp['iopub.status.busy'])).total_seconds()
    return total

def run(root,resume=False):
    root=Path(root).resolve();dest=root/'executed';dest.mkdir(exist_ok=True);records=[]
    for p in sorted((root/'notebooks').glob('*.ipynb')):
        started=time.monotonic();book=nbformat.read(p,as_version=4)
        done=dest/p.name
        if resume and done.exists():
            previous=nbformat.read(done,as_version=4)
            if [c.source for c in previous.cells]==[c.source for c in book.cells] and all(c.get('execution_count') is not None for c in previous.cells if c.cell_type=='code'):
                assert not any(o.output_type=='error' for c in previous.cells if c.cell_type=='code' for o in c.get('outputs',[]))
                records.append(dict(notebook=p.name,executed=True,html=(dest/p.with_suffix('.html').name).exists(),reused_matching_sources=True,code_cell_seconds=code_seconds(previous)));continue
        manager=KernelManager(kernel_name='python3');manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
        client=NotebookClient(book,km=manager,timeout=900,resources={'metadata':{'path':str(root)}})
        try:client.execute()
        finally:
            if manager.has_kernel:manager.shutdown_kernel(now=True)
        assert not any(o.output_type=='error' for c in book.cells if c.cell_type=='code' for o in c.get('outputs',[]))
        nbformat.write(book,dest/p.name)
        html,_=HTMLExporter().from_notebook_node(book);(dest/p.with_suffix('.html').name).write_text(html,encoding='utf-8')
        records.append(dict(notebook=p.name,executed=True,html=True,seconds=time.monotonic()-started,code_cell_seconds=code_seconds(book),code_cells=sum(c.cell_type=='code' for c in book.cells)))
        (dest/'execution.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print(p.name,'executed',flush=True)
    assert len(records)==8
    (dest/'execution.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    (root/'NOTEBOOK_EXECUTION.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--resume',action='store_true');a=p.parse_args();run(a.directory,a.resume)
