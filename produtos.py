"""Recompute STL metrics and components and compare them with the archived reference."""
import json

import shutil

import geopandas as gpd

import matplotlib

import matplotlib.pyplot as plt

from matplotlib.colors import ListedColormap, BoundaryNorm

import numpy as np

import pandas as pd

import rasterio

from rasterio.plot import plotting_extent

from dados import CFG, OUT

from nucleo import BANDAS

PALETTE = ["#005500","#0fc80f","#a8a800"]

def quick(seeds=None):
    if seeds is None:
        from verificar_sincronizacao import verify_sync
        verify_sync()
        seeds=CFG['seeds']
    from analise import temporal
    directory = OUT/"results"
    for seed in seeds:
        path = directory/f"representatives-{seed}.parquet"
        expected_path = directory/f"metrics-{seed}.csv"
        baseline = pd.read_csv(expected_path)
        target = OUT/"quick-check"
        target.mkdir(exist_ok=True)
        # Run the same functions in a separate output directory.
        import analise
        shutil.copy2(OUT/"catalog.parquet",target/"catalog.parquet")
        (target/"results").mkdir(exist_ok=True)
        shutil.copy2(directory/f"coverage-{seed}.csv",target/"results"/f"coverage-{seed}.csv")
        original = analise.OUT
        try:
            analise.OUT = target
            temporal(pd.read_parquet(path),seed,CFG["windows"] if seed==13 else [CFG["stl"]["seasonal"]])
        finally:
            analise.OUT = original
        actual = pd.read_csv(target/"results"/expected_path.name)
        pd.testing.assert_frame_equal(baseline,actual,check_exact=False,rtol=0,atol=1e-8)
        component_name=f"components-{seed}.parquet"
        expected_components=pd.read_parquet(directory/component_name).sort_values(['classe','band','date']).reset_index(drop=True)
        actual_components=pd.read_parquet(target/'results'/component_name).sort_values(['classe','band','date']).reset_index(drop=True)
        pd.testing.assert_frame_equal(expected_components,actual_components,check_exact=False,rtol=0,atol=1e-8)
        print(f"Verified temporal metrics and components for seed {seed}")

