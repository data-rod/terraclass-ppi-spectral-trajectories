"""Generate diagnostics, tables and print figures from reconstructed model outputs.

Human labels and candidate inputs come from --reference-work when absent from
the reconstructed directory. Figures use the reconstructed representatives,
metrics and freshly calculated held-out predictions.
"""
from pathlib import Path
import argparse
import gc
import json
import shutil
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from analise import splits
from dados import HERE, sha
from nucleo import BANDAS, atributos
from modelagem_nucleo import choose_representatives, group_ids


def build(work, reference, output):
    work, reference, output = map(lambda p: Path(p).resolve(), (work, reference, output))
    if output.exists():
        raise FileExistsError('Use a new product directory to preserve previous results.')
    output.mkdir(parents=True)
    data = pd.read_csv(work/'model/training.csv', keep_default_na=False, float_precision='round_trip')
    candidate_dir = work/'candidates' if (work/'candidates').is_dir() else reference/'candidates'
    candidates = pd.concat([pd.read_parquet(p) for p in sorted(candidate_dir.glob('13-*.parquet'))], ignore_index=True)
    assert len(candidates) == 213647 and candidates.candidate_id.is_unique
    assert candidates.groupby(['date', 'classe']).votes.sum().eq(20000).all()
    ordered = candidates.set_index('candidate_id').loc[data.candidate_id]
    x, _ = atributos(ordered)
    y = data.label.eq('compatible').to_numpy(int)
    groups = group_ids(data).to_numpy()
    records = []
    with threadpool_limits(limits=2):
        for fold, (_, test) in enumerate(splits(y, groups, 5), 1):
            folder = work/f'evaluation/fold_{fold}'
            fitted = joblib.load(folder/'classifier.joblib')
            threshold = json.loads((folder/'inner/selection.json').read_text())['chosen']['threshold']
            probability = fitted.predict_proba(x[test])[:, 1]
            records.append(pd.DataFrame(dict(candidate_id=data.iloc[test].candidate_id.to_numpy(),
                observed=y[test], probability=probability, threshold=threshold,
                fold=fold, outer_fold=fold, predicted=(probability >= threshold).astype(int))))
        prediction = pd.concat(records, ignore_index=True)
        operational = joblib.load(work/'model/classifier.joblib')
        probabilities = operational['model'].predict_proba(atributos(candidates)[0])[:, 1]
        all_candidates, selected = choose_representatives(candidates, probabilities, operational['threshold'], 0)
    expected = pd.read_parquet(work/'results/representatives-13.parquet')
    a = selected.sort_values(['date','classe']).reset_index(drop=True)
    b = expected.sort_values(['date','classe']).reset_index(drop=True)
    assert a.candidate_id.tolist() == b.candidate_id.tolist()
    np.testing.assert_allclose(a.probability, b.probability, rtol=0, atol=1e-7)
    flat = output/'dados'
    flat.mkdir()
    prediction.to_csv(flat/'outer_predictions.csv', index=False)
    data.to_csv(flat/'training.csv', index=False)
    for name in ['representatives-13.parquet','metrics-13.csv','distances-13.csv']:
        shutil.copy2(work/'results'/name, flat/name)
    shutil.copy2(work/'spatial.json', flat/'spatial.json')
    coverage = pd.read_csv(work/'results/coverage-13.csv')
    counts = all_candidates.groupby(['date','classe']).size().rename('new_voted').reset_index()
    accepted = all_candidates[all_candidates.probability >= operational['threshold']].groupby(['date','classe']).size().rename('new_compatible').reset_index()
    coverage = coverage.merge(counts, on=['date','classe'], how='left').merge(accepted, on=['date','classe'], how='left')
    coverage['n_voted'] = coverage.new_voted.fillna(0).astype(int)
    coverage['n_compatible'] = coverage.new_compatible.fillna(0).astype(int)
    ready = coverage.n_voted.gt(0)
    coverage.loc[ready, 'state'] = np.where(coverage.loc[ready, 'n_compatible'].gt(0), 'selected', 'no_compatible_candidate')
    coverage = coverage.drop(columns=['new_voted','new_compatible'])
    assert coverage.n_compatible.sum() == 56475
    coverage.to_csv(flat/'coverage-13.csv', index=False)
    from diagnostico_stl import main as diagnostics
    diagnostic_dir = output/'diagnosticos'
    diagnostics(diagnostic_dir, work=work)
    shutil.copy2(diagnostic_dir/'componentes_270_ajustes.parquet', flat/'componentes_270_ajustes.parquet')
    diag = pd.read_csv(diagnostic_dir/'tabelas/diagnosticos_270_ajustes.csv')
    diag.groupby(['domain','window','classe'])[['FS','FT']].median().reset_index().to_csv(output/'dominios.csv', index=False)
    sensitivity = []
    for (cl, band), g in diag.groupby(['classe','band']):
        first = g[g.window.eq(7)].iloc[0]
        last = g[g.window.eq(35)].iloc[0]
        row = dict(classe=int(cl), band=band, FS_range=g.FS.max()-g.FS.min(), FT_range=g.FT.max()-g.FT.min())
        for component in ['seasonal','trend','residual']:
            row[component+'_nrmse'] = last[component+'_rmse_vs_7']/first[component+'_sd']
        row['phase_ratio'] = last.seasonal_phase_between_cycles_sd_median/first.seasonal_phase_between_cycles_sd_median
        sensitivity.append(row)
    pd.DataFrame(sensitivity).to_csv(output/'sensibilidade_componentes.csv', index=False)
    classes = [(1,'VNFP'),(2,'VNFS'),(9,'SIL')]
    reference_labels = pd.read_csv(reference/'evaluation/reference.csv')
    spatial = json.loads((work/'spatial.json').read_text())
    rows = []
    for cl, name in classes:
        labels = data[data.classe.eq(cl)]
        q = coverage[coverage.classe.eq(cl)]
        rows.append(dict(classe=cl,name=name,pixels=spatial['pixels'][str(cl)],candidates=int(q.n_voted.sum()),
            training=len(labels),positive=int(labels.label.eq('compatible').sum()),negative=int(labels.label.eq('incompatible').sum()),
            accepted=int(q.n_compatible.sum()),representatives=int(expected.classe.eq(cl).sum()),
            external_compatible=int((reference_labels.classe.eq(cl)&reference_labels.evaluation_label.eq('compatible')).sum())))
    pd.DataFrame(rows).to_csv(output/'tabela_1.csv', index=False)
    rows = []
    initial = diag[diag.window.eq(7)]
    for name in list(BANDAS)+['VIS','RE','NIR','SWIR']:
        g = initial[initial.band.eq(name)] if name in BANDAS else initial[initial.domain.eq(name)]
        row = {'band_domain':name}
        for metric in ['FS','FT']:
            for cl, _ in classes:
                row[f'{metric}_{cl}'] = float(g[g.classe.eq(cl)][metric].median())
        rows.append(row)
    pd.DataFrame(rows).to_csv(output/'tabela_2.csv', index=False)
    comparisons = []
    for filename, keys in [('dominios.csv',['domain','window','classe']),('sensibilidade_componentes.csv',['classe','band']),
                           ('tabela_1.csv',['classe']),('tabela_2.csv',['band_domain'])]:
        observed = pd.read_csv(output/filename).sort_values(keys).reset_index(drop=True)
        baseline = pd.read_csv(reference/'artigo'/filename).sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(observed, baseline, check_exact=False, rtol=0, atol=1e-8)
        comparisons.append(filename)
    representative_count=len(selected)
    del candidates, ordered, x, all_candidates, selected, probabilities, operational, fitted
    gc.collect()
    subprocess.run([sys.executable,str(HERE/'editorial_figures/scripts/figuras_3_4_5.py'),
                    '--data',str(flat),'--output',str(output/'figuras')], check=True)
    report = dict(verified=True, model=json.loads((work/'model/model.json').read_text())['analysis_id'],
        input_representatives_sha256=sha(work/'results/representatives-13.parquet'),
        tables_compared=comparisons, tolerance=1e-8, predictions_recomputed=True,
        accepted_candidates=int(coverage.n_compatible.sum()), representatives=representative_count,
        figure_input_origin='reconstructed representatives, predictions and STL diagnostics')
    (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Reconstructed products verified:', output, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--reference-work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.work,args.reference_work,args.output)
