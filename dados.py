"""Prepare the spatial grid and retrieve Sentinel-2 observations."""
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio as rio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy.ndimage import binary_erosion

from nucleo import BANDAS

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
INPUT = Path(os.environ.get("RBC_INPUT", PROJECT))
OUT = Path(os.environ.get("RBC_OUTPUT", HERE / "work"))
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8-sig"))
ASSETS = (*BANDAS, "SCL", "CLEAROB", "PROVENANCE")
DTYPE = [(k, "<i2") for k in BANDAS] + [("SCL", "u1"), ("CLEAROB", "<u2"),
                                        ("PROVENANCE", "<i2"), ("valid", "?")]
ALBERS = "+proj=aea +lat_1=-2 +lat_2=-22 +lat_0=-12 +lon_0=-54 +ellps=GRS80 +units=m"
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="45",
           GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2",
           CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record(path, **meta):
    path = Path(path)
    return dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path), **meta)


def json_save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def whole_window(bounds, affine, margin=0):
    w = from_bounds(*bounds, affine)
    x, y = np.floor([w.col_off, w.row_off]).astype(int) - margin
    x1, y1 = np.ceil([w.col_off + w.width, w.row_off + w.height]).astype(int) + margin
    return Window(int(x), int(y), int(x1-x), int(y1-y))


def catalog():
    df = pd.read_parquet(INPUT / CFG["catalog"])
    df = df[df.tile_id.astype(str).isin(CFG["tiles"])].copy()
    df["date"] = pd.to_datetime(df.date).dt.strftime("%Y-%m-%d")
    df = df[df.date.between("2017-01-01", "2024-12-31")]
    expected = set(df.date)
    if len(expected) != 184 or df.duplicated(["date", "tile_id"]).any():
        raise ValueError("Unexpected or duplicate dates")
    for _, group in df.groupby("tile_id"):
        if set(group.date) != expected:
            raise ValueError("Incomplete tile calendar")
    if len(df) != 368 or not all(set(ASSETS) <= json.loads(v).keys() for v in df.assets_json):
        raise ValueError("Missing tile or asset")
    return df.sort_values(["date", "tile_id"])


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    cat = catalog()
    roi_path = INPUT / "RBC/ROI/ROI_Otto_nv06.gpkg"
    roi = gpd.read_file(roi_path)
    if (len(roi) != 1 or not roi.geometry.is_valid.all()
            or str(roi.iloc[0].wts_cd_pfafstetterbasin) != CFG["basin"]
            or int(roi.iloc[0].wts_cd_pfafstetterbasincodelevel) != 6):
        raise ValueError("Unexpected basin")
    maps = [next((INPUT / CFG["terra"]).glob(f"AMZ.{year}.M*.tif")) for year in CFG["years"]]
    inputs = [record(roi_path, source="ANA BHO 2017", crs=str(roi.crs)),
              record(INPUT / CFG["catalog"], source="BDC S2-16D-2 catalog")]
    inputs += [record(p, source="TerraClass Amazônia", year=y,
                      provenance=("Local IDL geometry alignment, 2026-04-20, per source filename"
                                  if y == 2024 else "Local TerraClass archive"))
               for y, p in zip(CFG["years"], maps)]
    fingerprint = dict(inputs=inputs, config=CFG, assets=cat[["date","tile_id","assets_json"]].to_dict("records"),
                       code={n:sha(HERE/n) for n in ("dados.py", "nucleo.py", "ppi.py")})
    run_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    manifest = OUT / "spatial.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8"))["run_id"] != run_id:
            raise ValueError("Changed inputs/config/code. Set RBC_OUTPUT to a fresh directory.")
        return
    tile_meta = {}
    with rio.Env(**ENV):
        for row in cat.groupby("tile_id").head(1).itertuples():
            with rio.open(json.loads(row.assets_json)["B08"]) as src:
                tile_meta[row.tile_id] = (src.crs, src.transform, src.width, src.height)
    crs, ref, _, _ = tile_meta[CFG["tiles"][0]]
    poly = roi.to_crs(crs)
    window = whole_window(poly.total_bounds, ref)
    affine = rio.windows.transform(window, ref)
    height, width = int(window.height), int(window.width)
    inside = geometry_mask(poly.geometry, (height,width), affine, invert=True)
    tiles = np.zeros((height,width), dtype=np.uint8)
    offsets = {}
    for i, (tile, (crs_i, a, w, h)) in enumerate(tile_meta.items(), 1):
        col, row = (~affine) * (a.c, a.f)
        if (crs_i != crs or tuple(a)[:2] != (10.0,0.0) or a.d != 0 or a.e != -10
                or abs(col-round(col)) > 1e-7 or abs(row-round(row)) > 1e-7):
            raise ValueError("Incompatible BDC grid")
        col, row = round(col), round(row)
        block = tiles[max(0,row):min(height,row+h),max(0,col):min(width,col+w)]
        if block.any():
            raise ValueError("Overlapping BDC cells")
        block[:] = i
        offsets[tile] = dict(col=col,row=row,code=i,width=w,height=h)
    if (inside & (tiles == 0)).any():
        raise ValueError("Uncovered basin cells")
    with rio.open(maps[0]) as base:
        thematic_crs = base.crs
        win = whole_window(roi.to_crs(thematic_crs).total_bounds, base.transform, 2)
        target = rio.windows.transform(win, base.transform)
    crop_shape = (int(win.height),int(win.width))
    (OUT / "terraclass").mkdir(exist_ok=True)
    permanent = None
    for path, year, entry in zip(maps, CFG["years"], inputs[2:]):
        with rio.open(path) as src:
            bounds = rio.windows.bounds(Window(0,0,crop_shape[1],crop_shape[0]),target)
            sw = whole_window(transform_bounds(thematic_crs,src.crs,*bounds),src.transform,2)
            original = src.read(1, window=sw)
            source_transform = src.window_transform(sw)
            entry.update(crs=str(src.crs),transform=list(src.transform)[:6],unit="categorical code",
                         nodata=src.nodata)
            with rio.open(OUT/"terraclass"/f"{year}.tif","w",driver="GTiff",count=1,
                          dtype=original.dtype, width=original.shape[1],height=original.shape[0],
                          transform=source_transform,crs=src.crs,nodata=src.nodata,compress="deflate") as dst:
                dst.write(original,1)
            aligned = np.zeros(crop_shape, dtype=np.uint8)
            reproject(original,aligned,src_transform=source_transform,src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=target,dst_crs=thematic_crs,
                      dst_nodata=0,resampling=Resampling.nearest)
        permanent = aligned if permanent is None else np.where(permanent == aligned, permanent, 0)
    classes = np.zeros((height,width), dtype=np.uint8)
    for c in map(int,CFG["classes"]):
        eroded = binary_erosion(permanent == c, structure=np.ones((3,3)),border_value=0)
        aligned = np.zeros_like(classes)
        reproject(eroded.astype("uint8"),aligned,src_transform=target,src_crs=thematic_crs,
                  dst_transform=affine,dst_crs=crs,resampling=Resampling.nearest)
        select = aligned.astype(bool) & inside
        if (classes[select] != 0).any():
            raise ValueError("Overlapping classes")
        classes[select] = c
    with rio.open(OUT/"nucleos.tif","w",driver="GTiff",count=1,dtype="uint8",
                  width=width,height=height,transform=affine,crs=crs,nodata=0,compress="deflate") as dst:
        dst.write(classes,1)
    idx = np.flatnonzero(classes)
    rr, cc = np.divmod(idx,width)
    x,y = affine * (cc+0.5,rr+0.5)
    index = pd.DataFrame(dict(pixel=idx,row=rr,col=cc,x=x,y=y,classe=classes.ravel()[idx],
                              tile=np.array(["",*tile_meta])[tiles.ravel()[idx]]))
    index.to_parquet(OUT/"pixels.parquet",index=False)
    cat[["date","tile_id","assets_json"]].to_parquet(OUT/"catalog.parquet",index=False)
    roi.to_file(OUT/"basin.gpkg",layer="basin")
    meta = dict(run_id=run_id, area_attribute_km2=float(roi.iloc[0].wts_gm_area),
                area_albers_km2=float(roi.to_crs(ALBERS).area.iloc[0]/1e6),
                crs=crs.to_wkt(),transform=list(affine)[:6],width=width,height=height,
                tiles=offsets,inputs=inputs, pixels=index.classe.value_counts().sort_index().to_dict(),
                estimated_bytes=len(idx)*184*np.dtype(DTYPE).itemsize,
                assets=dict(collection="S2-16D-2",reflectance_scale=CFG["scale"],
                            reflectance_units="unitless", resolution_m=10, calendar=184))
    json_save(manifest,meta)
    print("Spatial preparation:",meta["pixels"],meta["estimated_bytes"],flush=True)


def acquire(workers=12, limit=None):
    spatial = json.loads((OUT/"spatial.json").read_text(encoding="utf-8"))
    index = pd.read_parquet(OUT/"pixels.parquet")
    cat = pd.read_parquet(OUT/"catalog.parquet")
    directory = OUT/"observations"
    directory.mkdir(exist_ok=True)
    windows = {}
    for tile, grid in spatial["tiles"].items():
        idx = np.flatnonzero(index.tile.to_numpy() == tile)
        r = index.row.to_numpy()[idx]-grid["row"]
        c = index.col.to_numpy()[idx]-grid["col"]
        window = Window(int(c.min()),int(r.min()),int(c.max()-c.min()+1),int(r.max()-r.min()+1))
        windows[tile] = (idx,r-int(window.row_off),c-int(window.col_off),window)

    def read(tile, key, href):
        idx,r,c,window = windows[tile]
        with rio.Env(**ENV), rio.open(href) as src:
            transform = rio.Affine(*spatial["transform"])
            offset = spatial["tiles"][tile]
            expected = transform * rio.Affine.translation(offset["col"],offset["row"])
            if not src.transform.almost_equals(expected,precision=1e-7) or src.crs != rio.CRS.from_wkt(spatial["crs"]):
                raise ValueError(f"Grid mismatch: {tile}/{key}")
            a = src.read(1,window=window,masked=True)[r,c]
            return idx,key,a.data,~np.ma.getmaskarray(a),dict(tile=tile,asset=key,dtype=src.dtypes[0],
                      nodata=src.nodata,transform=list(src.transform)[:6],shape=list(src.shape))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for number,(date,group) in enumerate(cat.groupby("date"),1):
            if limit is not None and number > limit:
                break
            path = directory/f"{date}.npy"
            marker = path.with_suffix(".json")
            if marker.exists():
                saved = json.loads(marker.read_text(encoding="utf-8"))
                if saved["run_id"] != spatial["run_id"] or saved["sha256"] != sha(path):
                    raise ValueError(f"Observation failed integrity check: {date}")
                continue
            futures = []
            for row in group.itertuples():
                urls = json.loads(row.assets_json)
                futures.extend(pool.submit(read,row.tile_id,key,urls[key]) for key in ASSETS)
            data = np.zeros(len(index),dtype=DTYPE)
            valid = np.ones(len(index),dtype=bool)
            metadata = []
            try:
                for f in futures:
                    idx,key,values,ok,entry = f.result()
                    target = np.iinfo(data.dtype[key])
                    if values.min() < target.min or values.max() > target.max:
                        raise ValueError(f"Asset cannot be represented losslessly: {key}")
                    data[key][idx] = values
                    if key != "PROVENANCE":
                        valid[idx] &= ok
                    metadata.append(entry)
            except Exception as exc:
                json_save(directory/f"{date}.failed.json",dict(date=date,error=type(exc).__name__))
                raise
            data["valid"] = valid & ~np.isin(data["SCL"],CFG["scl_excluded"]) & (data["CLEAROB"]>0)
            temp = path.with_suffix(".pending")
            with temp.open("wb") as stream:
                np.save(stream,data,allow_pickle=False)
            temp.replace(path)
            json_save(marker,record(path,run_id=spatial["run_id"],date=date,assets=metadata,
                                    valid=int(data["valid"].sum())))
            path.with_suffix(".failed.json").unlink(missing_ok=True)
            print(f"Acquisition {number}/184 {date}: {data['valid'].sum():,} valid",flush=True)

