"""Verify the spatial reconstruction from the archived thematic windows."""
import json

import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
from scipy.ndimage import binary_erosion

from terraclass_ppi.spatial import CFG, OUT, whole_window


def verify_spatial():
    meta = json.loads((OUT/"spatial.json").read_text(encoding="utf-8"))
    basin = gpd.read_file(OUT/"basin.gpkg")
    windows = OUT/"terraclass"
    with rio.open(windows/f"{CFG['years'][0]}.tif") as first:
        thematic_crs = first.crs
        win = whole_window(basin.to_crs(thematic_crs).total_bounds,first.transform,2)
        target = rio.windows.transform(win,first.transform)
        shape = int(win.height),int(win.width)
    permanent = None
    for year in CFG["years"]:
        with rio.open(windows/f"{year}.tif") as src:
            a = np.zeros(shape,dtype="uint8")
            reproject(src.read(1),a,src_transform=src.transform,src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=target,dst_crs=thematic_crs,
                      dst_nodata=0,resampling=Resampling.nearest)
        permanent = a if permanent is None else np.where(permanent==a,permanent,0)
    crs = rio.CRS.from_wkt(meta["crs"])
    transform = rio.Affine(*meta["transform"])
    shape = meta["height"],meta["width"]
    inside = geometry_mask(basin.to_crs(crs).geometry,shape,transform,invert=True)
    mask = np.zeros(shape,dtype="uint8")
    for c in map(int,CFG["classes"]):
        eroded = binary_erosion(permanent==c,structure=np.ones((3,3)),border_value=0)
        result = np.zeros(shape,dtype="uint8")
        reproject(eroded.astype("uint8"),result,src_transform=target,src_crs=thematic_crs,
                  dst_transform=transform,dst_crs=crs,resampling=Resampling.nearest)
        select = result.astype(bool)&inside
        if (mask[select]!=0).any():
            raise ValueError("Overlapping classes")
        mask[select] = c
    with rio.open(OUT/"nucleos.tif") as expected:
        np.testing.assert_array_equal(mask,expected.read(1))
    import pandas as pd
    index = pd.read_parquet(OUT/"pixels.parquet")
    pixels = np.flatnonzero(mask)
    np.testing.assert_array_equal(index.pixel.to_numpy(),pixels)
    np.testing.assert_array_equal(index.classe.to_numpy(),mask.ravel()[pixels])
    print(f"Offline reconstruction matched all {len(pixels):,} spatial cells",flush=True)

