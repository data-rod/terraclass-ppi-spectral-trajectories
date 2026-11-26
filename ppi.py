"""Recalculate MNF dimensionality and all positive PPI votes."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from dados import CFG, OUT, json_save, sha
from nucleo import (BANDAS, covariancia_de_ruido, escores_ppi, extremos,
                    nwhfc_dimension, pares_vizinhos, transformacao_mnf)


def inputs():
    meta = json.loads((OUT/"spatial.json").read_text(encoding="utf-8"))
    pixels = pd.read_parquet(OUT/"pixels.parquet")
    dates = sorted(pd.read_parquet(OUT/"catalog.parquet").date.unique())
    positions = {}
    for c in map(int,CFG["classes"]):
        take = np.flatnonzero(pixels.classe.to_numpy() == c)
        positions[c] = take, pares_vizinhos(pixels.pixel.to_numpy()[take],meta["width"],
                                          meta["width"]*meta["height"])
    return meta,pixels,dates,positions


def groups(only_dates=None):
    meta,pixels,dates,positions = inputs()
    with threadpool_limits(limits=2):
        for date in dates:
            if only_dates is not None and date not in only_dates:continue
            path = OUT/"observations"/f"{date}.npy"
            marker = path.with_suffix(".json")
            if not marker.exists():
                raise FileNotFoundError(f"Missing verified acquisition: {date}")
            receipt = json.loads(marker.read_text(encoding="utf-8"))
            if receipt["run_id"] != meta["run_id"] or receipt["sha256"] != sha(path):
                raise ValueError(f"Acquisition mismatch: {date}")
            data = np.load(path,mmap_mode="r",allow_pickle=False)
            for c,(take,pairs) in positions.items():
                valid = data["valid"][take]
                n = int(valid.sum())
                row = dict(date=date,classe=c,n_valid=n)
                if n < CFG["min_pixels"]:
                    row.update(state="no_valid_pixels" if n == 0 else "insufficient_pixels")
                    yield row,None,None,None
                    continue
                x = np.column_stack([data[b][take] for b in BANDAS]).astype("float64")*CFG["scale"]
                noise,pair_count = covariancia_de_ruido(x,valid,pairs)
                row.update(state="ready",noise_pairs=pair_count,identity_noise_fallback=pair_count<=len(BANDAS),
                           mnf_eigenvalue_floor=1e-12,nwhfc_relative_ridge=1e-8)
                selected = take[valid]
                loc = pixels.iloc[selected].reset_index(drop=True).copy()
                for field in ("SCL","CLEAROB","PROVENANCE"):
                    loc[field] = data[field][selected]
                yield row,x[valid],noise,loc


def dimensions():
    from backend_numerico import require_ppi_backend
    require_ppi_backend()
    rows = []
    for row,x,noise,_ in groups():
        if x is not None:
            row.update(nwhfc_dimension(x,CFG["pfa"],noise))
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_parquet(OUT/"nwhfc.parquet",index=False)
    ready = frame[frame.state=="ready"]
    medians = ready.groupby("classe").suggested_endmembers.median()
    if set(medians.index) != set(map(int,CFG["classes"])):
        raise ValueError("A class has no processable date")
    values = {str(c):int(np.clip(np.floor(v+0.5),2,10)) for c,v in medians.items()}
    json_save(OUT/"dimensions.json",values)
    return values


def candidates(seeds=(13,),only_dates=None,dimension_values=None):
    from backend_numerico import require_ppi_backend
    require_ppi_backend()
    dims = dimensions() if dimension_values is None else dimension_values
    meta,_,_,_ = inputs()
    target = OUT/"candidates"
    target.mkdir(exist_ok=True)
    for row,x,noise,loc in groups(only_dates):
        c,date = row["classe"],row["date"]
        if x is None:
            continue
        pending = [seed for seed in seeds if not (target/f"{seed}-{date}-{c}.parquet").exists()]
        if not pending:
            continue
        basis,_ = transformacao_mnf(x,noise)
        z = x @ basis[:,:dims[str(c)]]
        for seed in pending:
            votes = escores_ppi(z,CFG["projections"],seed)
            if votes.sum() != 2*CFG["projections"]:
                raise ValueError("PPI vote conservation failed")
            nonzero = np.flatnonzero(votes)
            labels = set(extremos(x,votes,4,loc.pixel.to_numpy(),2.0)) if seed==13 else set()
            result = loc.iloc[nonzero].copy()
            result[list(BANDAS)] = x[nonzero]
            result["votes"] = votes[nonzero]
            result["date"] = date
            result["seed"] = seed
            result["run_id"] = meta["run_id"]
            result["candidate_id"] = [f"{date}:{c}:{p}" for p in result.pixel]
            result["label_sample"] = [i in labels for i in nonzero]
            path = target/f"{seed}-{date}-{c}.parquet"
            tmp = path.with_suffix(".pending")
            result.to_parquet(tmp,index=False)
            tmp.replace(path)
        print(f"PPI {date} class {c}: {len(x):,} pixels",flush=True)

