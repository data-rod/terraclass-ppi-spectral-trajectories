"""Regenerate the ten supplementary STL atlas pages from current components."""
from pathlib import Path
import argparse
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D

from terraclass_ppi.paths import output_root, CONFIG
from terraclass_ppi.data_io import table_directory
OUT=output_root()
c=pd.read_parquet(table_directory()/'componentes_270_ajustes.parquet');c['date']=pd.to_datetime(c.date)
windows=[7,9,11,13,15,21,25,31,35]
bands=['B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12']
names={1:'VNFP',2:'VNFS',9:'SIL'}
visual=json.loads((CONFIG/'visual.json').read_text(encoding='utf-8'))
class_colors={item['code']:item['color'] for item in visual['classes']}
colors={w:plt.cm.viridis((i+1)/10) for i,w in enumerate(windows)};colors[7]='#171717'
plt.rcParams.update({'font.family':'Times New Roman','mathtext.fontset':'stix','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=OUT/'figuras_regeneradas')
args=parser.parse_args()
destination=args.output.resolve();destination.mkdir(parents=True,exist_ok=True)
with PdfPages(destination/'atlas_componentes_todas_janelas.pdf') as pdf:
 for band in bands:
  fig,axes=plt.subplots(4,3,figsize=(11.7,8.3),sharex=True,sharey='row',layout='constrained')
  for j,cl in enumerate(names):
   for i,(field,label) in enumerate([('value','Reflectância'),('trend','Tendência'),('seasonal','Sazonal'),('residual','Resíduo')]):
    ax=axes[i,j]
    for w in ([7] if field=='value' else windows[::-1]):
     g=c[(c.classe==cl)&(c.band==band)&(c.window==w)].sort_values('date')
     values=g[field].where(g.observed) if field in ['value','residual'] else g[field]
     ax.plot(g.date,values,color=class_colors[cl] if field=='value' else colors[w],lw=1.05 if w==7 else .7,alpha=1 if w==7 else .7,label=str(w),marker='.' if field=='value' else None,ms=2)
    if i==0:ax.set_title(names[cl],color=class_colors[cl],fontweight='bold')
    if j==0:ax.set_ylabel(label)
    if field in ['seasonal','residual']:ax.axhline(0,color='#aaa',lw=.4,zorder=-1)
    ax.set_xlim(pd.Timestamp('2017-01-01'),pd.Timestamp('2024-12-18'))
    if i==3:
     ax.set_xticks(pd.to_datetime(['2017-01-01','2019-01-01','2021-01-01','2024-12-18']),labels=['2017','2019','2021','2024'])
  fig.legend(handles=[Line2D([],[],color=colors[w],label=str(w),lw=1) for w in windows],loc='outside lower center',ncol=9,title='Janela sazonal — referência 7 em preto',frameon=False)
  fig.suptitle(f'{band} — STL robusta, período 23, tendência 45 e passa-baixa 25\nReflectância e resíduos nas datas observadas; componentes no calendário completo',fontsize=12)
  pdf.savefig(fig);plt.close(fig)
print(f'Ten STL atlas pages written to {destination}.')
