"""Fit and compare representative time series using grouped evaluation and STL."""
import json

import joblib

import numpy as np

import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier

from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score, roc_curve

from sklearn.model_selection import StratifiedGroupKFold

from statsmodels.tsa.seasonal import STL

from threadpoolctl import threadpool_limits

from dados import CFG, HERE, OUT, json_save, sha

from nucleo import BANDAS, atributos

DOMAINS = dict(zip(BANDAS,["VIS"]*3+["RE"]*3+["NIR"]*2+["SWIR"]*2))

def splits(y,groups,n):
    plan = list(StratifiedGroupKFold(n_splits=n,shuffle=True,random_state=13).split(
        np.zeros(len(y)),y,groups))
    for train,test in plan:
        if (np.unique(y[train]).size != 2 or np.unique(y[test]).size != 2
                or set(groups[train]) & set(groups[test])):
            raise ValueError(f"Label more groups with both categories before running {n} folds")
    return plan

def select(seed):
    model = joblib.load(OUT/"model"/"classifier.joblib")
    coverage = pd.read_parquet(OUT/"nwhfc.parquet")
    meta = json.loads((OUT/"spatial.json").read_text(encoding="utf-8"))
    if model["run_id"] != meta["run_id"]:
        raise ValueError("Classifier is from another run")
    directory = OUT/"results"
    directory.mkdir(exist_ok=True)
    rows, diagnostics = [], []
    with threadpool_limits(limits=2):
        for unit in coverage.itertuples():
            entry = dict(date=unit.date,classe=unit.classe,state=unit.state,n_valid=unit.n_valid,
                         n_voted=0,n_compatible=0)
            if unit.state=="ready":
                f = pd.read_parquet(OUT/"candidates"/f"{seed}-{unit.date}-{unit.classe}.parquet")
                if not f.run_id.eq(model["run_id"]).all() or f.votes.sum()!=2*CFG["projections"]:
                    raise ValueError("Candidate integrity error")
                probabilities = model["model"].predict_proba(atributos(f)[0])[:,1]
                f["probability"] = probabilities
                f["analysis_id"] = model["analysis_id"]
                compatible = f[f.probability>=model["threshold"]].sort_values(
                    ["votes","pixel"],ascending=[False,True])
                entry.update(n_voted=len(f),n_compatible=len(compatible),
                             state="selected" if len(compatible) else "no_compatible_candidate")
                if len(compatible):
                    rows.append(compatible.iloc[0].to_dict())
            diagnostics.append(entry)
    frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["date","classe",*BANDAS])
    frame.to_parquet(directory/f"representatives-{seed}.parquet",index=False)
    pd.DataFrame(diagnostics).to_csv(directory/f"coverage-{seed}.csv",index=False)
    return frame

def strength(signal,residual):
    denom = np.var(signal+residual,ddof=1)
    return np.nan if denom<=1e-15 else max(0,1-np.var(residual,ddof=1)/denom)

def stl(series,window):
    y = series.to_numpy(dtype=float)
    mask = np.isfinite(y)
    n = int(mask.sum())
    empty = np.full(len(y),np.nan)
    status = "ok"
    if n < CFG["stl"]["period"]*2:
        status = "insufficient_observations"
    elif np.ptp(y[mask])<=1e-12:
        status = "constant"
    metrics = dict(state=status,n_observed=n,FS=np.nan,FT=np.nan,
                   var_trend=np.nan,var_seasonal=np.nan,var_residual=np.nan)
    if status != "ok":
        return empty,empty,empty,metrics
    filled = series.interpolate(method="time",limit_direction="both").to_numpy()
    fitted = STL(filled,**(CFG["stl"]|dict(seasonal=window))).fit()
    trend,seasonal,resid = fitted.trend,fitted.seasonal,fitted.resid
    np.testing.assert_allclose(trend+seasonal+resid,filled,rtol=0,atol=1e-8)
    t,s,r = trend[mask],seasonal[mask],resid[mask]
    metrics.update(FS=strength(s,r),FT=strength(t,r),var_trend=np.var(t,ddof=1),
                   var_seasonal=np.var(s,ddof=1),var_residual=np.var(r,ddof=1))
    return trend,seasonal,resid,metrics

def temporal(representatives,seed,windows):
    directory = OUT/"results"
    dates = pd.DatetimeIndex(sorted(pd.read_parquet(OUT/"catalog.parquet").date.unique()))
    components, metrics, distances = [],[],[]
    for c in map(int,CFG["classes"]):
        selected = representatives[representatives.classe==c].copy()
        selected["date"] = pd.to_datetime(selected.date)
        selected = selected.sort_values("date").set_index("date")
        if len(selected)>1:
            dist = np.hypot(selected.x.diff(),selected.y.diff())/1000
            gap = selected.index.to_series().diff().dt.days
            distances.append(pd.DataFrame(dict(date=selected.index,classe=c,distance_km=dist,elapsed_days=gap)))
        for band in BANDAS:
            series = selected[band].reindex(dates).astype(float)
            for window in windows:
                t,s,r,info = stl(series,window)
                meta = dict(classe=c,band=band,domain=DOMAINS[band],seed=seed,window=window)
                metrics.append(meta|info)
                if window==CFG["stl"]["seasonal"]:
                    components.append(pd.DataFrame(meta|dict(date=dates,value=series.to_numpy(),
                        observed=series.notna().to_numpy(),trend=t,seasonal=s,residual=r)))
    table = pd.DataFrame(metrics)
    table.to_csv(directory/f"metrics-{seed}.csv",index=False)
    table.groupby(["seed","window","classe","domain"])[["FS","FT"]].median().reset_index().to_csv(
        directory/f"domains-{seed}.csv",index=False)
    pd.concat(components,ignore_index=True).to_parquet(directory/f"components-{seed}.parquet",index=False)
    if distances:
        pd.concat(distances,ignore_index=True).dropna().to_csv(directory/f"distances-{seed}.csv",index=False)
    coverage = pd.read_csv(directory/f"coverage-{seed}.csv")
    coverage["month"] = pd.to_datetime(coverage.date).dt.month
    coverage.groupby(["classe","month","state"]).size().rename("dates").reset_index().to_csv(
        directory/f"monthly-{seed}.csv",index=False)

def analyze(seeds):
    for seed in seeds:
        temporal(select(seed),seed,CFG["windows"] if seed==13 else [CFG["stl"]["seasonal"]])
    if len(seeds)>1:
        inventories = {}
        for seed in seeds:
            by_group = {}
            for path in (OUT/"candidates").glob(f"{seed}-*.parquet"):
                f = pd.read_parquet(path,columns=["date","classe","pixel"])
                by_group[(f.date.iloc[0],int(f.classe.iloc[0]))] = set(f.pixel)
            inventories[seed] = by_group
        rows = []
        for seed in seeds:
            if seed==13:
                continue
            for (date,c),ref in inventories[13].items():
                other = inventories[seed][(date,c)]
                rows.append(dict(seed=seed,date=date,classe=c,n_reference=len(ref),n_other=len(other),
                                 jaccard=len(ref & other)/len(ref | other)))
        pd.DataFrame(rows).to_csv(OUT/"results"/"candidate_overlap.csv",index=False)
        ref = pd.read_parquet(OUT/"results"/"representatives-13.parquet")
        for seed in seeds:
            if seed==13:
                continue
            other = pd.read_parquet(OUT/"results"/f"representatives-{seed}.parquet")
            match = ref[["date","classe","candidate_id"]].merge(
                other[["date","classe","candidate_id"]],on=["date","classe"],how="outer",
                suffixes=("_reference","_other"))
            match["same_pixel"] = match.candidate_id_reference.eq(match.candidate_id_other)
            match.to_csv(OUT/"results"/f"representative_agreement-{seed}.csv",index=False)

