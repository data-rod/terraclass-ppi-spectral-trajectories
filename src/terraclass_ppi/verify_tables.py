"""Verify the supplied scientific tables, labels and temporal components."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from sklearn.metrics import confusion_matrix,average_precision_score,roc_auc_score

def verify(folder):
 rep=pd.read_parquet(folder/'representatives-13.parquet')
 train=pd.read_csv(folder/'training.csv');pred=pd.read_csv(folder/'outer_predictions.csv')
 ref=pd.read_csv(folder/'reference.csv');cov=pd.read_csv(folder/'coverage-13.csv')
 metrics=pd.read_csv(folder/'metrics-13.csv');comp=pd.read_parquet(folder/'componentes_270_ajustes.parquet')
 assert len(rep)==519 and rep.groupby('classe').size().tolist()==[173]*3
 assert rep.analysis_id.nunique()==1
 assert len(train)==len(pred)==2422 and train.label.value_counts().sort_values().tolist()==[515,1907]
 assert confusion_matrix(pred.observed,pred.predicted).ravel().tolist()==[1885,22,39,476]
 assert round(average_precision_score(pred.observed,pred.probability),4)==.9774
 assert round(roc_auc_score(pred.observed,pred.probability),4)==.9940
 exclusive=ref[ref.evaluation_status=='needs_human_label']
 assert len(exclusive)==58 and set(exclusive.candidate_id).isdisjoint(train.candidate_id)
 assert ref.groupby('classe').evaluation_label.apply(lambda s:s.eq('compatible').sum()).tolist()==[173,164,165]
 assert cov.n_voted.sum()==213647 and cov.n_compatible.sum()==56475
 delta=[]
 for (cl,b,w),g in comp.groupby(['classe','band','window']):
  obs=g[g.observed.astype(bool)];assert len(obs)==173 and len(g)==184
  r,s,t=obs.residual.to_numpy(),obs.seasonal.to_numpy(),obs.trend.to_numpy()
  expected=[max(0,1-np.var(r,ddof=1)/np.var(s+r,ddof=1)),max(0,1-np.var(r,ddof=1)/np.var(t+r,ddof=1))]
  row=metrics[(metrics.classe==cl)&(metrics.band==b)&(metrics.window==w)].iloc[0]
  delta.extend(abs(np.array(expected)-[row.FS,row.FT]))
  np.testing.assert_allclose(obs.trend+obs.seasonal+obs.residual,obs.value,rtol=0,atol=1e-12)
 assert len(delta)==540 and max(delta)<1e-12
 assert len(metrics)==270 and (metrics.FS>metrics.FT).all()
 for domain in ['NIR','RE']:
  v=metrics[metrics.domain==domain].groupby(['window','classe']).FS.median().unstack()
  assert (v[1]>v[2]).all() and (v[2]>v[9]).all()
 for row in pd.read_csv(folder/'distribuicoes_reflectancia.csv').itertuples():
  np.testing.assert_allclose(np.quantile(rep.loc[rep.classe==row.classe,row.band],[0,.25,.5,.75,1]),[row.minimum,row.q25,row.median,row.q75,row.maximum],rtol=0,atol=1e-12)
 table=pd.read_csv(folder/'tabela_S2_forcas_janela7.csv')
 for row in table.itertuples():
  g=metrics[metrics.window==7]
  if row.band_domain in ['VIS','RE','NIR','SWIR']:g=g[g.domain==row.band_domain].groupby('classe')[['FS','FT']].median()
  else:g=g[g.band==row.band_domain].set_index('classe')
  for field in ['FS','FT']:
   for cl in [1,2,9]:assert abs(getattr(row,f'{field}_{cl}')-g.loc[cl,field])<1e-12
 d=pd.read_csv(folder/'distances-13.csv')
 assert d.groupby('classe').distance_km.median().round(2).tolist()==[6.88,7.27,8.80]
 return {'analysis_id':rep.analysis_id.iloc[0],'representatives':519,'labels':2422,'evaluation_only_labels':58,'compatible_external':502,'STL_fits':270,'force_comparisons':540,'max_force_difference':float(max(delta)),'quantiles_checked':150,'S2_values_checked':84,'independent_training_run':False}

if __name__=='__main__':
 from terraclass_ppi.data_io import table_directory
 folder=table_directory()
 if not (folder/'training.csv').exists():raise FileNotFoundError('Scientific tables must accompany this script')
 report=verify(folder)
 print(json.dumps(report,indent=2))
