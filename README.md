# TerraClass PPI spectral trajectories

This software reproduces the selection and comparison of moving spectral extremes in ottobasin 722936, western Maranhão, Brazil. It compares primary natural forest vegetation (VNFP), secondary natural forest vegetation (VNFS) and silviculture (SIL) from 2017 to 2024. The primary analysis has 519 representatives, 30 spectral series and nine seasonal windows.

## Read the supporting material

The accompanying Zenodo deposit supplies the supplementary PDF and four Excel workbooks individually. Start with `Material_Suplementar_RBC.pdf`. The workbooks cover selection and evaluation, representative spectra, seasonal and trend strengths, and temporal components. `figuras_e_atlas.zip` contains print figures and the nine-window atlas.

Supporting data record: [10.5281/zenodo.24546365](https://doi.org/10.5281/zenodo.24546365). This repository contains supporting software; the manuscript is distributed separately by its authors.

## Install

Use Python 3.13 and the pinned packages in `requirements.txt`. The commands below use PowerShell, from the extracted code directory.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

The pip environment supports the model and temporal routes from archived candidates. Complete MNF–PPI reconstruction requires **NumPy 2.1.3 linked to Intel MKL 2023.1**, as specified in `environments/mnf-ppi.yml` and the Windows native lock. The backend check rejects other numerical builds for that route. `docs/REPRODUCTION.md` explains the distinction.

## Prepare data

Extract `dados_derivados_e_modelos.zip` into a separate directory, such as `../dataset`. It must contain `data/` and `models/` directly. Set the data and output roots explicitly:

```powershell
$env:RBC_DATA_ROOT = (Resolve-Path ../dataset).Path
$env:RBC_OUTPUT_ROOT = Join-Path (Get-Location) outputs
python scripts/prepare_inputs.py --data-root $env:RBC_DATA_ROOT
```

Preparation creates an isolated working view under `outputs/reference/`. It uses local hard links where supported, with a copy fallback. Calculation outputs stay outside the canonical dataset. Historical execution filenames occur only in this local working view so the verified calculations retain their input contracts. All public candidate data are stored once, in three consolidated Parquets.

## Reproduce

```powershell
# Recalculate components and strengths from archived representatives, all three seeds.
python scripts/run_pipeline.py quick --data-root $env:RBC_DATA_ROOT --all-seeds

# Refit model selection, grouped external evaluation and the operational classifier.
python scripts/run_pipeline.py model --data-root $env:RBC_DATA_ROOT --output-dir outputs/model

# Regenerate the print figures and reader supplement from the canonical tables.
python scripts/build_figures.py --output outputs/figures
python -m pip install -r environments/requirements-print.txt
python scripts/build_supplement.py --data-root $env:RBC_DATA_ROOT --output outputs/supplement
```

Use a new output directory for each model or complete run. For complete reconstruction, first activate the MKL environment and import the unchanged offline archive:

```powershell
python scripts/prepare_inputs.py --data-root $env:RBC_DATA_ROOT --offline-zip ../rbc-offline-inputs.zip
python scripts/run_pipeline.py complete --data-root $env:RBC_DATA_ROOT --output-dir outputs/complete
```

Set `$env:RBC_PPI_WORKERS = "1"` before the complete command to process one date at a time and reduce concurrent memory use. The numerical functions and their two-thread BLAS limit remain the same. An interrupted run can reuse its completed checkpoints when the recorded inputs, code and environment match.

Temporary candidate partitions serve as local checkpoints during reconstruction. The consolidated published candidates are read by logical class/date group. No worker appends to a shared Parquet. Reproduction receipts include code, inputs and environment; checkpoints from another code or data state must use a new output directory.

The eight source notebooks explain and check each stage. Import the offline data and build the figures first. Notebook 01 also displays `outputs/figures/figura_1_mapa.svg`: extract it from `figuras_e_atlas.zip`, or regenerate it through QGIS as described below. Then run `python scripts/run_notebooks.py --data-root $env:RBC_DATA_ROOT`. Executed notebooks, HTML and their execution record remain under `outputs/notebooks/`. Use a fresh output folder after changing the data or environment.

## Map and human judgments

Open `qgis/study_area.qgz` in QGIS 3.44. Its small cartographic inputs and styles accompany the project. `qgis/build_map.py` regenerates Figure 1 with the shared Dark2 palette. Run it using QGIS Python; see `qgis/README.md`.

`python scripts/build_labeling_panel.py --data-root $env:RBC_DATA_ROOT` regenerates the offline C/NC panel after offline inputs are imported. Export judgments before moving the page. The published development and evaluation judgments are already in the data archive. New annotations are separate inputs and do not change the published model automatically.

## Documentation, license and funding

`docs/METHODOLOGY.md` describes the method; `docs/DATA_FORMATS.md` defines the inputs and tables; `docs/LABELING_PROTOCOL.md` describes the human reference. Original supplementary methods are editable in `docs/supplement/methods.docx`.

Code: MIT. Applicable original documentation and data: CC BY 4.0. TerraClass inputs and derivative masks: CC BY-SA 4.0. Sentinel, BDC, ANA and IBGE source materials retain their terms; see `LICENSING.md` and `LICENSE-DATA`.

Funding: Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq), Projeto Geotec, grant **400048/2026-4**. Cite the software authors in `CITATION.cff` and the data record version used.
