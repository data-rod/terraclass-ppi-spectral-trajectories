from __future__ import annotations
import numpy as np
import pandas as pd
BANDAS=('B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12')
from statistics import NormalDist
LOTE_PADRAO=512; TETO_MB=128
def pares_vizinhos(linear: np.ndarray, largura: int, total: int):
    """Return same-class horizontal and vertical neighbour pairs.

    linear contains canonical grid indices; returned arrays index its rows."""
    posicao = np.full(total, -1, dtype=np.int32)
    posicao[linear] = np.arange(len(linear), dtype=np.int32)
    coluna = linear % largura
    direita = linear[coluna < largura - 1] + 1
    j_dir = posicao[direita]
    i_dir = posicao[direita - 1]
    ok = j_dir >= 0
    horizontal = (i_dir[ok], j_dir[ok])
    abaixo = linear[linear + largura < total] + largura
    j_bai = posicao[abaixo]
    i_bai = posicao[abaixo - largura]
    ok = j_bai >= 0
    vertical = (i_bai[ok], j_bai[ok])
    return (horizontal, vertical)

def covariancia_de_ruido(X: np.ndarray, valido: np.ndarray, pares) -> tuple[np.ndarray, int]:
    """Estimate noise covariance from valid neighbour differences.

    Return half their sample covariance and the pair count. If the number of pairs is no greater
    than the number of bands, return identity covariance and record the count."""
    blocos = []
    for i, j in pares:
        ambos = valido[i] & valido[j]
        if ambos.sum() == 0:
            continue
        blocos.append(X[j[ambos]] - X[i[ambos]])
    if not blocos:
        return (np.eye(X.shape[1]), 0)
    diferencas = np.concatenate(blocos, axis=0)
    if len(diferencas) <= X.shape[1]:
        return (np.eye(X.shape[1]), int(len(diferencas)))
    return (np.cov(diferencas, rowvar=False) / 2.0, int(len(diferencas)))

def transformacao_mnf(X: np.ndarray, ruido: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the noise-whitened MNF basis and descending eigenvalues.

    X contains spectra by row. Eigenvalues of noise covariance are floored
    at 1e-12 before whitening."""
    valores, vetores = np.linalg.eigh((ruido + ruido.T) / 2.0)
    valores = np.maximum(valores, 1e-12)
    branqueamento = vetores @ np.diag(1.0 / np.sqrt(valores)) @ vetores.T
    branco = (X - X.mean(axis=0, keepdims=True)) @ branqueamento
    cov = np.cov(branco, rowvar=False)
    autovalores, autovetores = np.linalg.eigh((cov + cov.T) / 2.0)
    ordem = np.argsort(autovalores)[::-1]
    return (branqueamento @ autovetores[:, ordem], autovalores[ordem])

def escores_ppi(pixels: np.ndarray, projecoes: int, semente: int, lote: int=LOTE_PADRAO) -> np.ndarray:
    """Count minimum and maximum projections along seeded unit directions.

    Return one integer vote count per spectrum. Matrix products use float32;
    batch size limits the projected matrix to TETO_MB."""
    x = np.ascontiguousarray(pixels, dtype=np.float32)
    n, d = x.shape
    centrado = x - x.mean(axis=0, dtype=np.float64).astype(np.float32)
    centrado_t = np.ascontiguousarray(centrado.T)
    gerador = np.random.default_rng(int(semente))
    escores = np.zeros(n, dtype=np.int32)
    cabe = max(1, int(TETO_MB * 1024 * 1024 / (4 * max(1, n))))
    lote = max(1, min(int(lote), cabe))
    restam = int(projecoes)
    while restam > 0:
        b = min(lote, restam)
        direcoes = gerador.normal(size=(b, d))
        normas = np.linalg.norm(direcoes, axis=1, keepdims=True)
        direcoes = np.divide(direcoes, normas, out=np.zeros_like(direcoes), where=normas > 0)
        projetado = direcoes.astype(np.float32) @ centrado_t
        np.add.at(escores, np.argmax(projetado, axis=1), 1)
        np.add.at(escores, np.argmin(projetado, axis=1), 1)
        restam -= b
    return escores

def extremos(pixels: np.ndarray, escores: np.ndarray, quantos: int, ordem_mestra: np.ndarray, sam_duplicata: float=2.0) -> np.ndarray:
    """Choose voted spectra in PPI order with minimum angular separation.

    ordem_mestra resolves vote ties. sam_duplicata is in degrees; quantos
    limits the human-labeling sample, not the candidate inventory."""
    pool = np.flatnonzero(escores > 0)
    if len(pool) == 0:
        return np.empty(0, dtype=np.int64)
    pool = pool[np.lexsort((ordem_mestra[pool], -escores[pool]))]
    x = np.asarray(pixels, dtype=np.float64)
    escolhidos: list[int] = []
    for indice in pool:
        i = int(indice)
        if sam_duplicata > 0 and escolhidos:
            a = x[i]
            na = np.linalg.norm(a)
            perto = False
            for outro in escolhidos:
                b = x[outro]
                nb = np.linalg.norm(b)
                if na <= 0 or nb <= 0:
                    continue
                cos = float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))
                if np.degrees(np.arccos(cos)) < sam_duplicata:
                    perto = True
                    break
            if perto:
                continue
        escolhidos.append(i)
        if len(escolhidos) == int(quantos):
            break
    return np.asarray(escolhidos, dtype=np.int64)

def _regularize(matrix: np.ndarray) -> np.ndarray:
    """Add an isotropic ridge using the absolute mean trace as its scale.

    The scale is floored at 1e-12 before multiplication by 1e-8."""
    matrix = np.asarray(matrix, dtype=np.float64)
    matrix = (matrix + matrix.T) / 2.0
    scale = max(abs(float(np.trace(matrix))) / max(1, matrix.shape[0]), 1e-12)
    return matrix + np.eye(matrix.shape[0]) * scale * 1e-08

def nwhfc_dimension(pixels: np.ndarray, false_alarm_probability: float, noise_covariance: np.ndarray) -> dict:
    """Estimate dimension after noise whitening at the given false-alarm rate.

    Return the raw intrinsic dimension, its 2â€“band-count bounded suggestion,
    eigenvalues and thresholds. Class-level aggregation is performed in ppi.py."""
    x = np.asarray(pixels, dtype=np.float64)
    noise = _regularize(noise_covariance)
    values, vectors = np.linalg.eigh(noise)
    values = np.maximum(values, 1e-12)
    whitening = vectors @ np.diag(1.0 / np.sqrt(values)) @ vectors.T
    working = x @ whitening
    n = len(working)
    second_moment = working.T @ working / float(n)
    centered = working - np.mean(working, axis=0, keepdims=True)
    covariance = centered.T @ centered / float(max(1, n - 1))
    corr_values = np.linalg.eigvalsh(_regularize(second_moment))[::-1]
    cov_values = np.linalg.eigvalsh(_regularize(covariance))[::-1]
    corr_values = np.maximum(corr_values, 0.0)
    cov_values = np.maximum(cov_values, 0.0)
    differences = corr_values - cov_values
    sigma = np.sqrt(np.maximum(2.0 / n * (corr_values ** 2 + cov_values ** 2), 1e-24))
    z_score = NormalDist().inv_cdf(1.0 - float(false_alarm_probability))
    thresholds = z_score * sigma
    dimension = int(np.count_nonzero(differences > thresholds))
    return {'intrinsic_dimension': dimension, 'suggested_endmembers': max(2, min(x.shape[1], dimension)), 'false_alarm_probability': float(false_alarm_probability), 'correlation_eigenvalues': corr_values.tolist(), 'covariance_eigenvalues': cov_values.tolist(), 'thresholds': thresholds.tolist(), 'noise_model': 'nearest_spatial_sample_pair_covariance'}

def atributos(quadro):
    """Delegate construction of classification predictors to the feature module."""
    from terraclass_ppi.features import atributos as build
    return build(quadro)
