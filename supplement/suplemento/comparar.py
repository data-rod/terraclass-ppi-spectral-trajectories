"""Regenerate class/domain/window comparisons from the archived STL metrics."""
from pathlib import Path
import itertools
import numpy as np,pandas as pd

def generate(folder):
 names={1:'VNFP',2:'VNFS',9:'SIL'}
 metrics=pd.read_csv(folder/'metrics-13.csv')
 dom=metrics.groupby(['domain','window','classe'])[['FS','FT']].median().reset_index()
 rows=[];summaries=[];exceptions=[]
 for metric,domain in itertools.product(['FS','FT'],['VIS','RE','NIR','SWIR']):
  g=dom[dom.domain==domain].pivot(index='window',columns='classe',values=metric).sort_index()
  for a,b in [(1,2),(1,9),(2,9)]:
   delta=g[a]-g[b]
   for w,d in delta.items():rows.append(dict(metric=metric,domain=domain,class_a=names[a],class_b=names[b],window=int(w),value_a=g.loc[w,a],value_b=g.loc[w,b],signed_difference=d,absolute_difference=abs(d)))
   inc=np.diff(delta.to_numpy());abs_inc=np.diff(np.abs(delta.to_numpy()))
   summaries.append(dict(metric=metric,domain=domain,class_a=names[a],class_b=names[b],difference_7=delta.loc[7],difference_35=delta.loc[35],change_signed=delta.loc[35]-delta.loc[7],change_absolute=abs(delta.loc[35])-abs(delta.loc[7]),strict_order_preserved=bool(np.sign(delta).nunique()==1),signed_difference_monotonic=bool(np.all(inc>=0) or np.all(inc<=0)),absolute_difference_monotonic=bool(np.all(abs_inc>=0) or np.all(abs_inc<=0))))
 for domain,expected in [('VIS',2),('RE',1),('NIR',1),('SWIR',2)]:
  g=metrics[metrics.domain==domain].pivot(index=['band','window'],columns='classe',values='FS')
  for (band,w),v in g[g.idxmax(axis=1)!=expected].iterrows():exceptions.append(dict(domain=domain,band=band,window=int(w),largest_class=names[int(v.idxmax())],domain_median_largest=names[expected]))
 for values,name in [(rows,'comparacoes_classes_dominios_janelas.csv'),(summaries,'comparacoes_classes_extremos_janelas.csv'),(exceptions,'diferencas_bandas_e_sintese_dominio.csv')]:pd.DataFrame(values).to_csv(folder/name,index=False)
 return dom,rows,summaries,exceptions

if __name__=='__main__':
 folder=Path(__file__).resolve().parent
 if not (folder/'metrics-13.csv').exists():raise FileNotFoundError('metrics-13.csv must accompany this script')
 _,rows,summaries,exceptions=generate(folder)
 print(f'{len(rows)} comparisons; {len(summaries)} endpoint summaries; {len(exceptions)} band/window exceptions to the domain-median order.')
