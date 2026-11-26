"""Rebuild grouped evaluation and the operational model from published human labels."""
from pathlib import Path
import json,shutil,time,platform
from importlib.metadata import version
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits,threadpool_info
from dados import HERE,sha,CFG
from nucleo import atributos
from analise import splits
from modelagem_nucleo import inner_search,params,group_ids,choose_representatives,classification_scores,save

def reproduce(source,target,complete=False,candidate_dir=None,all_seeds=False):
    source,target=Path(source).resolve(),Path(target).resolve()
    if source==target or source in target.parents and target.name=='work':raise ValueError('Use a separate reproduction directory')
    target.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    inputs=[source/'model/training.csv',source/'model/model.json',source/'evaluation/reference.csv',HERE/'modelagem_representantes_v3.json',HERE/'classifier.json',HERE/'nucleo.py',HERE/'analise.py',HERE/'modelagem_nucleo.py',HERE/'ppi.py',HERE/'ppi_paralelo.py',Path(__file__)]
    inputs += [source/n for n in ['catalog.parquet','spatial.json','pixels.parquet','nwhfc.parquet','dimensions.json']]
    inputs += [HERE/'backend_numerico.py']
    inputs += [HERE/name for name in ['config.json','dados.py','offline.py','vigente.py']]
    inputs += [source/'results'/name for name in ['representatives-13.parquet','metrics-13.csv','coverage-13.csv']]
    inputs += [source/f'evaluation/fold_{fold}'/name for fold in range(1,6) for name in ['selected.parquet','labelled_test_predictions.csv']]
    inputs += sorted((source/'candidates').glob('13-*.parquet'))
    if candidate_dir is not None:
        inputs += sorted(Path(candidate_dir).resolve().glob('13-*.parquet'))
    inputs += sorted((source/'observations').glob('*.json'))
    compiled=np.show_config(mode='dicts').get('Build Dependencies',{})
    environment=dict(python=platform.python_version(),system=platform.system(),packages={p:version(p) for p in ['numpy','scipy','pandas','pyarrow','scikit-learn','statsmodels']},
        compiled={k:{field:compiled.get(k,{}).get(field) for field in ['name','version']} for k in ['blas','lapack']},
        native=[dict(api=b.get('internal_api'),version=b.get('version')) for b in threadpool_info()],effective_fit_threads=2)
    spec=dict(files={str(p.resolve()):sha(p) for p in inputs},environment=environment,complete=complete,all_seeds=all_seeds)
    marker=target/'inputs.json'
    if marker.exists() and json.loads(marker.read_text())!=spec:raise ValueError('Changed inputs or code: use a new output directory')
    save(marker,spec)
    for name in ['catalog.parquet','spatial.json','basin.gpkg','nucleos.tif','pixels.parquet','nwhfc.parquet','dimensions.json']:
        if (source/name).exists():shutil.copy2(source/name,target/name)
    if complete:
        from backend_numerico import require_ppi_backend
        require_ppi_backend()
        import offline,ppi
        offline.OUT=source;offline.verify_spatial()
        # Local observation arrays and receipts are immutable shared inputs.
        (target/'observations').mkdir(exist_ok=True)
        import os
        for p in (source/'observations').glob('*'):
            dest=target/'observations'/p.name
            if not dest.exists():
                try:os.link(p,dest)
                except OSError:shutil.copy2(p,dest)
        ppi.OUT=target;ppi.dimensions()
        from ppi_paralelo import run
        run(target,workers=min(2,max(1,(os.cpu_count() or 2)//2)),seeds=CFG['seeds'] if all_seeds else [13])
        candidates_dir=target/'candidates'
    else:candidates_dir=Path(candidate_dir) if candidate_dir is not None else source/'candidates'
    candidates=pd.concat([pd.read_parquet(p) for p in sorted(candidates_dir.glob('13-*.parquet'))],ignore_index=True)
    assert len(candidates)==213647 and candidates.candidate_id.is_unique
    assert candidates.groupby(['date','classe']).votes.sum().eq(20000).all()
    data=pd.read_csv(source/'model/training.csv',keep_default_na=False,float_precision='round_trip')
    assert data.candidate_id.is_unique and len(data)==2422
    # Published spectra must match the rebuilt candidate IDs and reflectances.
    rebuilt=candidates.set_index('candidate_id').loc[data.candidate_id]
    from nucleo import BANDAS
    np.testing.assert_allclose(rebuilt[list(BANDAS)],data[list(BANDAS)],atol=1e-15,rtol=0)
    config=json.loads((HERE/'modelagem_representantes_v3.json').read_text());metadata=json.loads((source/'model/model.json').read_text())
    x,features=atributos(rebuilt);cx,_=atributos(candidates);y=data.label.eq('compatible').to_numpy(int);groups=group_ids(data).to_numpy()
    reference=pd.read_csv(source/'evaluation/reference.csv');all_reps=[];scores=[]
    heldout=reference[reference.reference_label.isna()].candidate_id
    assert len(heldout)==58 and not set(heldout)&set(data.candidate_id)
    with threadpool_limits(limits=2):
        for fold,(train,test) in enumerate(splits(y,groups,5),1):
            folder=target/f'evaluation/fold_{fold}';assert not set(groups[train])&set(groups[test])
            chosen=inner_search(data.iloc[train].reset_index(drop=True),x[train],y[train],groups[train],config,folder/'inner')
            fitted=HistGradientBoostingClassifier(**params(config,config['parameters_to_compare'][chosen['order']])).fit(x[train],y[train])
            mask=group_ids(candidates).isin(set(groups[test])).to_numpy()
            pred,reps=choose_representatives(candidates[mask],fitted.predict_proba(cx[mask])[:,1],chosen['threshold'],fold)
            expected=pd.read_parquet(source/f'evaluation/fold_{fold}/selected.parquet')
            assert reps.candidate_id.tolist()==expected.candidate_id.tolist()
            np.testing.assert_allclose(reps.probability,expected.probability,rtol=0,atol=1e-7)
            expected_test=pd.read_csv(source/f'evaluation/fold_{fold}/labelled_test_predictions.csv')
            assert expected_test.candidate_id.tolist()==data.iloc[test].candidate_id.tolist()
            test_probabilities=fitted.predict_proba(x[test])[:,1]
            np.testing.assert_allclose(test_probabilities,expected_test.probability,atol=1e-7,rtol=0)
            np.testing.assert_allclose(chosen['threshold'],expected_test.threshold.iloc[0],atol=1e-7,rtol=0)
            reps.to_parquet(folder/'selected.parquet',index=False);joblib.dump(fitted,folder/'classifier.joblib')
            score=classification_scores(y[test],fitted.predict_proba(x[test])[:,1],chosen['threshold']);scores.append(dict(fold=fold,threshold=chosen['threshold'],**score));all_reps.append(reps)
            save(target/'progress.json',dict(completed_external_folds=fold,total=5,elapsed_seconds=time.monotonic()-started))
        reps=pd.concat(all_reps,ignore_index=True)
        labels=reference.set_index('candidate_id').evaluation_label
        compatible=int(reps.candidate_id.map(labels).eq('compatible').sum());assert len(reps)==519 and compatible==502
        chosen=inner_search(data,x,y,groups,config,target/'inner_operational')
        np.testing.assert_allclose(chosen['threshold'],metadata['threshold'],rtol=0,atol=1e-7)
        fitted=HistGradientBoostingClassifier(**params(config,config['parameters_to_compare'][chosen['order']])).fit(x,y)
        pred,reps=choose_representatives(candidates,fitted.predict_proba(cx)[:,1],chosen['threshold'],0)
    expected=pd.read_parquet(source/'results/representatives-13.parquet')
    assert reps.candidate_id.tolist()==expected.candidate_id.tolist()
    np.testing.assert_allclose(reps.probability,expected.probability,rtol=0,atol=1e-7)
    (target/'model').mkdir(exist_ok=True);(target/'results').mkdir(exist_ok=True)
    joblib.dump(dict(model=fitted,**metadata),target/'model/classifier.joblib');shutil.copy2(source/'model/model.json',target/'model/model.json');data.to_csv(target/'model/training.csv',index=False)
    reps['analysis_id']=metadata['analysis_id'];reps.to_parquet(target/'results/representatives-13.parquet',index=False)
    shutil.copy2(source/'results/coverage-13.csv',target/'results/coverage-13.csv')
    import analise
    old=analise.OUT;analise.OUT=target
    try:analise.temporal(reps,13,CFG['windows'])
    finally:analise.OUT=old
    expected=pd.read_csv(source/'results/metrics-13.csv');actual=pd.read_csv(target/'results/metrics-13.csv')
    pd.testing.assert_frame_equal(expected,actual,check_exact=False,atol=1e-8,rtol=0)
    if complete and all_seeds:
        from vigente import supplementary
        supplementary(target,target)
    pd.DataFrame(scores).to_csv(target/'evaluation/candidate_metrics.csv',index=False)
    save(target/'verification.json',dict(verified=True,spatial_and_PPI_rebuilt=complete,prebuilt_PPI_inputs_supplied=candidate_dir is not None,external_compatible=compatible,external_selected=519,operational_selected=len(reps),analysis_id=metadata['analysis_id'],probability_tolerance=1e-7,STL_tolerance=1e-8,evaluation_only_58_excluded=True,environment=environment,elapsed_seconds=time.monotonic()-started,reference_inputs_unchanged=all(sha(Path(p))==v for p,v in spec['files'].items())))
    print('Current procedure reproduced:',target,flush=True)
