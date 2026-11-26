"""Regenerate the supplementary PDF, Excel tables and figures from archived results."""
from pathlib import Path
import argparse,shutil,subprocess,sys,tempfile

HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True,help='New directory for the PDF, Excel tables and figures')
    a=p.parse_args();dest=a.output.resolve()
    if dest.exists():raise FileExistsError('Choose a new output directory: '+str(dest))
    source=HERE/'supplement'
    with tempfile.TemporaryDirectory(prefix='rbc-supplement-') as tmp:
        work=Path(tmp)/'supplement';shutil.copytree(source,work,ignore=shutil.ignore_patterns('__pycache__'))
        def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=work,check=True)
        run('suplemento/verificar.py')
        run('suplemento/comparar.py')
        run('suplemento/figuras.py','--data',work/'suplemento','--output',work/'figuras')
        run('suplemento/atlas.py','--output',work/'figuras')
        run('gerar_suplemento.py')
        staged=Path(tmp)/'reader';(staged/'Planilhas').mkdir(parents=True);(staged/'Figuras').mkdir()
        run('exportar_planilhas.py','--output',staged/'Planilhas')
        run('guia_leitura.py','--output',staged/'00_Guia_de_leitura.pdf')
        shutil.copy2(work/'Suplemento_RBC_r12.pdf',staged/'Suplemento_RBC_r12.pdf')
        for stem in ['figura_S1_classificacao_disponibilidade','figura_S2_decomposicao_completa']:
            for suffix in ['.pdf','.png','.svg']:shutil.copy2(work/'figuras'/(stem+suffix),staged/'Figuras'/(stem+suffix))
        shutil.copy2(work/'figuras/atlas_componentes_todas_janelas.pdf',staged/'Figuras/atlas_componentes_todas_janelas.pdf')
        shutil.copytree(staged,dest)
    print('Supplementary reading files written to '+str(dest))

if __name__=='__main__':main()
