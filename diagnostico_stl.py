"""Calculate STL component diagnostics using the shared fitting function.

Read representatives and reference metrics from --work; write diagnostics
and comparison reports to --output-dir.
"""
from pathlib import Path
import argparse,json,hashlib,sys,platform
from datetime import datetime,timezone
from importlib.metadata import version
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from statsmodels.tsa.seasonal import STL
from analise import stl, strength
from dados import CFG,OUT,HERE

WINDOWS=[7,9,11,13,15,21,25,31,35]
NAMES={1:'VNFP',2:'VNFS',9:'SIL'}
BANDS=['B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def lag_corr(x,observed,lag):
    keep=observed[lag:] & observed[:-lag]
    a,b=x[:-lag][keep],x[lag:][keep]
    return (float(np.corrcoef(a,b)[0,1]) if len(a)>2 and np.std(a)>0 and np.std(b)>0 else np.nan),int(keep.sum())

def harmonic(x,observed):
    t=np.arange(len(x),dtype=float)[observed]
    design=np.column_stack([np.ones(len(t)),np.sin(2*np.pi*t/23),np.cos(2*np.pi*t/23)])
    y=x[observed];coeff=np.linalg.lstsq(design,y,rcond=None)[0]
    total=np.sum((y-y.mean())**2)
    r2=float(max(0,1-np.sum((y-design@coeff)**2)/total)) if total>1e-20 else np.nan
    return r2,float(np.hypot(coeff[1],coeff[2]))

def main(target,work=None):
    global OUT
    if work is not None: OUT=Path(work).resolve()
    target=Path(target).resolve();target.mkdir(parents=True,exist_ok=True)
    for name in ['figuras','tabelas']: (target/name).mkdir(exist_ok=True)
    inputs=[OUT/'results/components-13.parquet',OUT/'results/metrics-13.csv',
            OUT/'results/representatives-13.parquet',OUT/'model/model.json',
            HERE/'analise.py',HERE/'config.json',Path(__file__)]
    receipts={str(p.relative_to(HERE.parent)) if p.is_relative_to(HERE.parent) else str(p):sha(p) for p in inputs}
    spec=dict(inputs=receipts,windows=WINDOWS,period=23,trend=45,low_pass=25,robust=True,
              environment={p:version(p) for p in ['numpy','pandas','scipy','statsmodels','matplotlib']})
    run_id=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
    state=target/'execucao.json'
    if state.exists():
        old=json.loads(state.read_text(encoding='utf-8'))
        if old['run_id']!=run_id:raise ValueError('Existing diagnostic belongs to other inputs or code; use another directory.')
    state.write_text(json.dumps(spec|dict(run_id=run_id,started_utc=datetime.now(timezone.utc).isoformat(),stage='running'),indent=2),encoding='utf-8')
    source=pd.read_parquet(inputs[0]);reference=pd.read_csv(inputs[1])
    rows=[];components=[];maxerr=0.;maxmetric=0.;maxcomponent=0.
    calendar=source[['date']].drop_duplicates().sort_values('date');dates=pd.DatetimeIndex(pd.to_datetime(calendar.date))
    assert len(dates)==184
    for (c,b),f in source.groupby(['classe','band'],sort=True):
        f=f.assign(date=pd.to_datetime(f.date)).set_index('date').reindex(dates)
        obs=f.observed.to_numpy(dtype=bool);y=pd.Series(f.value.to_numpy(),index=dates)
        assert obs.sum()==173 and np.array_equal(obs,np.isfinite(y))
        filled=y.interpolate(method='time',limit_direction='both').to_numpy()
        base=None
        for w in WINDOWS:
            t,s,r,m=stl(y,w)
            assert m['state']=='ok'
            error=float(np.max(np.abs(t+s+r-filled)));maxerr=max(maxerr,error)
            expected=reference[(reference.classe==c)&(reference.band==b)&(reference.window==w)].iloc[0]
            for key in ['FS','FT','var_trend','var_seasonal','var_residual']:
                delta=abs(float(m[key])-float(expected[key]));maxmetric=max(maxmetric,delta)
                np.testing.assert_allclose(m[key],expected[key],rtol=0,atol=1e-8)
            if w==7:
                base=(t.copy(),s.copy(),r.copy())
                for key,a in zip(['trend','seasonal','residual'],base):
                    maxcomponent=max(maxcomponent,float(np.max(np.abs(a-f[key].to_numpy()))))
                    np.testing.assert_allclose(a,f[key],atol=1e-8,rtol=0)
            row=dict(classe=int(c),band=b,domain=f.domain.iloc[0],window=w,**m)
            row.update(residual_rmse=float(np.sqrt(np.mean(r[obs]**2))))
            for label,x,bx in zip(['trend','seasonal','residual'],[t,s,r],base):
                row[label+'_sd']=float(np.std(x[obs],ddof=1))
                row[label+'_p95_p05']=float(np.percentile(x[obs],95)-np.percentile(x[obs],5))
                row[label+'_harmonic_r2'],row[label+'_harmonic_amplitude']=harmonic(x,obs)
                row[label+'_rmse_vs_7']=float(np.sqrt(np.mean((x[obs]-bx[obs])**2)))
                row[label+'_corr_vs_7']=float(np.corrcoef(x[obs],bx[obs])[0,1])
            for lag in [1,23,46]:row[f'residual_lag{lag}'],row[f'residual_lag{lag}_pairs']=lag_corr(r,obs,lag)
            phase=s.reshape(8,23)
            row['seasonal_phase_between_cycles_sd_median']=float(np.median(np.std(phase,axis=0,ddof=1)))
            rows.append(row)
            components.append(pd.DataFrame(dict(classe=int(c),band=b,window=w,date=dates,
                value=y.to_numpy(),observed=obs,filled=filled,trend=t,seasonal=s,residual=r)))
    diag=pd.DataFrame(rows);comp=pd.concat(components,ignore_index=True)
    assert len(diag)==270 and len(comp)==49680
    diag.to_csv(target/'tabelas/diagnosticos_270_ajustes.csv',index=False)
    comp.to_parquet(target/'componentes_270_ajustes.parquet',index=False)
    keys=['FS','FT','residual_sd','residual_rmse','residual_lag1','residual_lag23','residual_lag46',
          'residual_harmonic_r2','seasonal_sd','trend_sd','seasonal_corr_vs_7',
          'seasonal_rmse_vs_7','seasonal_phase_between_cycles_sd_median']
    diag.groupby('window')[keys].agg(['median','min','max']).to_csv(target/'tabelas/resumo_por_janela.csv')
    diag.groupby(['classe','window'])[keys].median().to_csv(target/'tabelas/resumo_classe_janela.csv')
    dom=diag.groupby(['domain','window','classe'])[['FS','FT']].median().reset_index()
    dom.to_csv(target/'tabelas/dominios.csv',index=False)
    ranking=[]
    for (d,w),g in dom.groupby(['domain','window']):
        ranking.append(dict(domain=d,window=int(w),FS=' > '.join(g.sort_values('FS',ascending=False).classe.map(NAMES)),
                            FT=' > '.join(g.sort_values('FT',ascending=False).classe.map(NAMES))))
    pd.DataFrame(ranking).to_csv(target/'tabelas/ordenacoes.csv',index=False)
    pd.DataFrame(dict(date=dates,year=dates.year,position=np.arange(184)%23,
                     days_since_previous=pd.Series(dates).diff().dt.days)).to_csv(target/'tabelas/calendario.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,
                         'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    colors={w:plt.cm.viridis((i+1)/10) for i,w in enumerate(WINDOWS)};colors[7]='#171717'
    with PdfPages(target/'figuras/atlas_componentes_todas_janelas.pdf') as pdf:
        for band in BANDS:
            fig,axes=plt.subplots(4,3,figsize=(11.7,8.3),sharex=True,sharey='row',layout='constrained')
            for j,c in enumerate(NAMES):
                for i,(field,label) in enumerate([('value','Reflectância'),('trend','Tendência'),('seasonal','Sazonal'),('residual','Resíduo')]):
                    ax=axes[i,j]
                    for w in ([7] if field=='value' else WINDOWS[::-1]):
                        g=comp[(comp.classe==c)&(comp.band==band)&(comp.window==w)].sort_values('date')
                        values=g[field].where(g.observed) if field in ['value','residual'] else g[field]
                        ax.plot(g.date,values,color=colors[w],lw=1.05 if w==7 else .7,alpha=1 if w==7 else .7,
                                label=str(w),marker='.' if field=='value' else None,ms=2)
                    if i==0:ax.set_title(NAMES[c])
                    if j==0:ax.set_ylabel(label)
                    if field in ['seasonal','residual']:ax.axhline(0,color='#aaa',lw=.4,zorder=-1)
            handles,labels=axes[1,0].get_legend_handles_labels()
            fig.legend(handles[::-1],labels[::-1],loc='outside lower center',ncol=9,title='Janela sazonal · 7 em preto',frameon=False)
            fig.suptitle(f'{band} · STL robusto · período 23 · tendência 45 · passa-baixa 25\nObservações e resíduos somente nas datas observadas; componentes ajustados no calendário completo',fontsize=12)
            pdf.savefig(fig);fig.savefig(target/f'figuras/atlas_{band}.png',dpi=150);fig.savefig(target/f'figuras/atlas_{band}.svg')
            plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(13,9),layout='constrained')
    for ax,key,title in zip(axes,['FS','residual_sd','residual_lag23','residual_harmonic_r2'],
                             ['Força sazonal','DP do resíduo','Correlação residual · lag 23','R² harmônico anual no resíduo']):
        mat=diag.pivot(index=['classe','band'],columns='window',values=key).reindex(pd.MultiIndex.from_product([NAMES,BANDS]))
        vmin,vmax=(-1,1) if key=='residual_lag23' else (0,float(np.nanmax(mat)))
        im=ax.imshow(mat,aspect='auto',vmin=vmin,vmax=vmax,cmap='RdBu_r' if key=='residual_lag23' else 'viridis')
        ax.set_xticks(range(9),WINDOWS,rotation=90);ax.set_yticks(range(30),[NAMES[c]+' '+b for c,b in mat.index],fontsize=7)
        ax.set_title(title,fontsize=9);ax.set_xlabel('Janela sazonal')
        for cut in [9.5,19.5]:ax.axhline(cut,color='white',lw=1)
        fig.colorbar(im,ax=ax,orientation='horizontal',pad=.02,shrink=.8)
    fig.suptitle('Diagnósticos descritivos nas observações originais · 30 séries × 9 janelas')
    fig.savefig(target/'figuras/sintese_diagnosticos.png',dpi=160);fig.savefig(target/'figuras/sintese_diagnosticos.svg');plt.close(fig)
    # Show the complete lag profile at the initial configuration without p-values.
    records=[];fig,axes=plt.subplots(1,3,figsize=(12,3.5),sharey=True,layout='constrained')
    for ax,c in zip(axes,NAMES):
        for b in BANDS:
            g=comp[(comp.classe==c)&(comp.band==b)&(comp.window==7)].sort_values('date')
            vals=[]
            for lag in range(1,47):
                corr,pairs=lag_corr(g.residual.to_numpy(),g.observed.to_numpy(),lag);vals.append(corr)
                records.append(dict(classe=c,band=b,lag=lag,correlation=corr,pairs=pairs))
            ax.plot(range(1,47),vals,lw=.8,label=b)
        ax.axvline(23,color='black',ls=':',lw=.8);ax.axhline(0,color='#888',lw=.5)
        ax.set(title=NAMES[c],xlabel='Passos do calendário',ylim=(-1,1))
    axes[0].set_ylabel('Correlação residual entre pares observados');axes[-1].legend(ncol=2,fontsize=6)
    fig.savefig(target/'figuras/correlacao_residual_lags.png',dpi=160);fig.savefig(target/'figuras/correlacao_residual_lags.svg');plt.close(fig)
    pd.DataFrame(records).to_csv(target/'tabelas/correlacao_residual_lags_1_46.csv',index=False)
    defaults=STL(np.arange(184,dtype=float),period=23,robust=True).config
    assert defaults['seasonal']==7 and defaults['trend']==45 and defaults['low_pass']==25
    validation=dict(run_id=run_id,series=30,fits=270,component_rows=len(comp),max_reconstruction_error=maxerr,
        max_difference_existing_metrics=maxmetric,max_difference_existing_components=maxcomponent,
        defaults_for_period23=defaults,all_diagnostics_finite=bool(np.isfinite(diag.select_dtypes('number')).all().all()),
        calendar_steps_days=pd.Series(dates).diff().dt.days.value_counts().sort_index().to_dict(),
        visual_atlas_pages=10,source_inputs_unchanged=all(sha(HERE.parent/p)==h for p,h in receipts.items()),
        seasonal_windows_larger_than_eight_available_cycles=[w for w in WINDOWS if w>8],
        inferential_tests=False,optimized_window=False)
    (target/'verificacao.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    state.write_text(json.dumps(spec|dict(run_id=run_id,completed_utc=datetime.now(timezone.utc).isoformat(),stage='complete'),indent=2),encoding='utf-8')
    print(json.dumps(validation,indent=2),flush=True)
    print(diag.groupby('window')[['FS','FT','residual_lag1','residual_lag23','residual_harmonic_r2']].median().to_string(),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=OUT/'stl_diagnostics')
    parser.add_argument('--work',type=Path,default=OUT)
    args=parser.parse_args();main(args.output_dir,work=args.work)
