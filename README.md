# Forest reflectance trajectories in the Maranhão Amazon

This repository contains the code for selecting forest reflectance observations with the Pixel Purity Index (PPI) and analysing their temporal variation in ottobasin 722936, western Maranhão, Brazil. The three TerraClass classes are primary natural forest vegetation (VNFP), secondary natural forest vegetation (VNFS) and silviculture (SIL). Each observation contains ten reflectances from one selected pixel. Its location can change between dates.

The analysis first transforms the spectra by Minimum Noise Fraction (MNF), identifies PPI candidates and classifies their spectral compatibility with photosynthetically active vegetation. The accepted candidate with the highest PPI supplies the observation. Seasonal-Trend decomposition using LOESS (STL) describes the resulting series.

## Data and environment

Run commands from this directory. Extract the reference archive here to populate `work/` for the quick route. Add the offline-input archive for complete reconstruction and the notebooks that inspect thematic windows and observation arrays. The reference contains candidates, human labels, the model and temporal results. The offline inputs contain the thematic windows and observation arrays. `DATA_FORMATS.md` explains their fields and identifiers.

Use Python 3.13 in a separate environment. Install `requirements-win.lock` on Windows or `requirements-linux.lock` on Linux. Exact MNF–PPI reconstruction additionally requires NumPy 2.1.3 linked to Intel MKL 2023.1. The runtime backend check prevents an incompatible reconstruction.

For model fitting and STL on Windows, create a virtual environment and install the locked packages:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-win.lock
```

For complete MNF–PPI reconstruction, create a separate Conda environment with the native builds:

```text
conda create -p .full-env --file environment-native-win.explicit
conda activate ./.full-env
python -m pip install -r requirements-win.lock
```

Retain the Conda NumPy/SciPy builds when installing the remaining packages. `environment-full-mkl.yml` lists the native constraints. `RELEASE_STATUS.json` records the Windows environments and completed checks. Linux dependencies are supplied, but execution on Linux has not been tested.

## Reproduction routes

The quick route recalculates STL components and metrics from the selected representatives:

```text
python vigente.py quick --work work
```

Add `--all-seeds` to verify the supplementary seeds 29 and 47 as well as primary seed 13. The nine seasonal windows are applied to seed 13; supplementary seeds use window 7.

To reproduce grouped model selection, external evaluation and the operational classifier from the archived candidates and human labels:

```text
python vigente.py model --work work --output-dir rebuilt-model
```

The complete route also reconstructs thematic masks and MNF–PPI candidates. Run it in the compatible MKL environment:

```text
python vigente.py complete --work work --output-dir rebuilt-complete
```

Keep regenerated outputs separate from reference inputs. Modeling and PPI stages use checkpoints; retain their input receipts when resuming. The verification report distinguishes completed model evaluation from complete spatial and PPI reconstruction.

## Products from reconstructed outputs

After the model or complete route, regenerate diagnostics, tables and print figures:

```text
python vigente.py products --work rebuilt-complete --source-work work --output-dir rebuilt-products
```

Use `rebuilt-model` instead of `rebuilt-complete` when starting from the model-only reproduction. The command recomputes held-out predictions and accepted-candidate counts, uses the shared STL function for 270 fits, compares the resulting tables with the reference, and passes the reconstructed data to the print-figure generator. Its output directory must be new. Set `RBC_PRODUCTS_DIR` to this directory to inspect these results in notebooks 06 and 07.

## Notebooks and figures

Start with notebook 00 to choose an environment and reproduction route. Notebooks 01–04 examine the spatial inputs, quality records, candidates and grouped evaluation. Notebook 05 recalculates STL; notebooks 06–07 compare seasonal windows and generate figures. Executed copies and HTML are in `executed/`.

The complete notebooks require both data archives. The command-line quick route requires only the reference archive. Model fitting and PPI reconstruction are run through the explicit terminal commands above; the notebooks inspect their outputs.

Regenerate print figures from the supplied tables:

```text
python editorial_figures/scripts/figuras_3_4_5.py
```

Open `editorial_figures/index.html` to find PNG, SVG and PDF files. The portable QGIS project is `editorial_figures/SIG/Mapa_RBC_oficial.qgz`; its map generator runs with QGIS Python. Class colours follow Dark2: VNFP #1B9E77, VNFS #7570B3 and SIL #D95F02.

## Methods and licenses

`METHODOLOGY.md` defines the scientific procedure; `LABELING_PROTOCOL.md` explains the human reference and optional annotation panel. The 58 evaluation-only judgments remain outside development. Temporal metrics use the originally observed dates; endpoint shading is a visual indication.

Software is licensed under MIT. Original study documentation and author-created data are licensed under CC BY 4.0. Source products retain their applicable terms; see `LICENSING.md`. `CITATION.cff` identifies the software version and authors.
