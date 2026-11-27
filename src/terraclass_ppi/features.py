"""Construct the 17 classification predictors."""
import numpy as np
import pandas as pd
from terraclass_ppi.spectral import BANDAS

def atributos(quadro: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Build 17 predictors from the ten reflectance columns.

    Return norm-normalized bands, six indices and log1p spectral magnitude,
    followed by their column names. Coordinates, dates and votes are excluded."""
    bruto = quadro[list(BANDAS)].to_numpy(float)
    norma = np.linalg.norm(bruto, axis=1, keepdims=True)
    forma = np.divide(bruto, norma, out=np.zeros_like(bruto), where=norma > 0)
    b = {nome: bruto[:, i] for i, nome in enumerate(BANDAS)}
    eps = 1e-09

    def razao(x, y):
        return (x - y) / (x + y + eps)
    indices = np.column_stack([razao(b['B08'], b['B04']), 2.5 * (b['B08'] - b['B04']) / (b['B08'] + 6 * b['B04'] - 7.5 * b['B02'] + 1 + eps), razao(b['B03'], b['B08']), razao(b['B08'], b['B05']), razao(b['B08'], b['B11']), (b['B11'] + b['B04'] - (b['B08'] + b['B02'])) / (b['B11'] + b['B04'] + (b['B08'] + b['B02']) + eps), np.log1p(norma.ravel())])
    nomes = [f'forma_{x}' for x in BANDAS] + ['ndvi', 'evi', 'ndwi', 'ndre', 'ndmi', 'bsi', 'log_brilho']
    return (np.column_stack([forma, indices]), nomes)
