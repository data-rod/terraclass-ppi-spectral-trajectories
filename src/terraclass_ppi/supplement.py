"""Regenerate the PDF, spreadsheets and supplementary figures."""
import argparse,os,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();dest=a.output.resolve()
    if dest.exists():raise FileExistsError('Choose a new supplementary output directory')
    dest.mkdir(parents=True)
    env=os.environ.copy();env['RBC_DATA_ROOT']=str(a.data_root.resolve());env['RBC_SUPPLEMENT_OUTPUT']=str(dest)
    def run(module,*args):subprocess.run([sys.executable,'-m','terraclass_ppi.'+module,*map(str,args)],env=env,check=True)
    run('verify_tables')
    run('compare_classes')
    run('figures','--output',dest/'figuras')
    run('atlas','--output',dest/'figuras')
    run('supplement_pdf')
    run('tables','--output',dest/'Planilhas')
    print('Supplementary reading files written to',dest)
if __name__=='__main__':main()
