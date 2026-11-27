"""Build a Portuguese offline labeling panel from acquired PPI candidates."""
from terraclass_ppi.data_io import iter_candidate_groups
import json

import numpy as np
import pandas as pd
from PIL import Image
from pyproj import Transformer

from terraclass_ppi.spatial import CFG, HERE, OUT
from terraclass_ppi.spectral import BANDAS, atributos


def painel():
    target = OUT/"painel"
    target.mkdir(exist_ok=True)
    context = target/"contexto"
    context.mkdir(exist_ok=True)
    files = list(iter_candidate_groups(OUT/"candidates",13))
    if not files:
        raise ValueError("No reference candidates")
    spatial = json.loads((OUT/"spatial.json").read_text(encoding="utf-8"))
    frames, timeline = [], []
    coverage = pd.read_parquet(OUT/"nwhfc.parquet",columns=["date","classe","n_valid","state"])
    ready = coverage[coverage.state.eq("ready")]
    expected = {f"13-{r.date}-{r.classe}.parquet" for r in ready.itertuples()}
    if {name for name, _ in files} != expected:
        raise ValueError("Conclua os candidatos PPI da execução antes de gerar o painel.")
    n_valid = ready.set_index(["date","classe"]).n_valid.to_dict()
    for partition_name, group in files:
        selected = group.query("label_sample")
        if not 1 <= len(selected) <= 4 or not group.run_id.eq(spatial["run_id"]).all():
            raise ValueError(f"Inventário de candidatos inválido: {partition_name}")
        frames.append(selected)
        date, classe = str(group.date.iloc[0]), int(group.classe.iloc[0])
        matrix, names = atributos(group)
        entry = dict(date=date,classe=classe,n_voted=len(group),n_valid=int(n_valid[date,classe]))
        for name in ("evi","bsi"):
            values = matrix[:,names.index(name)]
            values = values[np.isfinite(values)]
            entry[name+"_median"] = float(np.median(values)) if len(values) else None
            entry[name+"_std"] = float(np.std(values,ddof=1)) if len(values)>1 else None
        spectra = group[list(BANDAS)].to_numpy()
        order = np.argsort(matrix[:,names.index("evi")],kind="stable")
        take = np.linspace(0,len(order)-1,min(24,len(order)),dtype=int)
        entry["context_spectra"] = spectra[order[take]].tolist()
        entry["mean_spectrum"] = spectra.mean(axis=0).tolist()
        timeline.append(entry)
    sample = pd.concat(frames,ignore_index=True).sort_values(
        ["date","classe","votes","pixel"],ascending=[True,True,False,True])
    pixels = pd.read_parquet(OUT/"pixels.parquet")
    transform = Transformer.from_crs(spatial["crs"],"EPSG:4326",always_xy=True)
    sample["lon"],sample["lat"] = transform.transform(sample.x.to_numpy(),sample.y.to_numpy())
    images = np.full((spatial["height"],spatial["width"],3),22,dtype=np.uint8)
    for date,group in sample.groupby("date"):
        data = np.load(OUT/"observations"/f"{date}.npy",mmap_mode="r")
        images.fill(22)
        valid = data["valid"]
        rgb = np.column_stack([data[b][valid] for b in ("B04","B03","B02")])
        rgb = (np.clip(rgb*CFG["scale"]/0.24,0,1)**0.65*255).astype("uint8")
        images[pixels.row.to_numpy()[valid],pixels.col.to_numpy()[valid]] = rgb
        for item in group.itertuples():
            y,x = item.row,item.col
            patch = np.full((65,65,3),22,dtype="uint8")
            y0,y1,x0,x1 = max(0,y-32),min(images.shape[0],y+33),max(0,x-32),min(images.shape[1],x+33)
            patch[y0-y+32:y1-y+32,x0-x+32:x1-x+32] = images[y0:y1,x0:x1]
            name = f"{date}-{item.classe}-{item.pixel}.png"
            Image.fromarray(patch).resize((260,260),Image.Resampling.NEAREST).save(context/name)
    sample.to_csv(target/"amostra.csv",index=False)
    page = (HERE/"templates/labeling_panel.html").read_text(encoding="utf-8")
    payload = json.dumps(dict(run=spatial["run_id"],classes=CFG["classes"],bands=BANDAS,
                         rows=sample.to_dict("records"),timeline=timeline),ensure_ascii=False,allow_nan=False).replace("<","\\u003c")
    pending = target/"index.pending"
    pending.write_text(page.replace("/*PAYLOAD*/null",payload),encoding="utf-8")
    pending.replace(target/"index.html")
    print(f"Panel: {len(sample)} candidates in {sample.groupby(['classe','date']).ngroups} groups",flush=True)

