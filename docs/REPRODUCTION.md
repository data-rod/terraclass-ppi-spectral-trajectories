# Reproduction routes

The quick route refits STL from archived representatives and checks strengths and components at absolute tolerance 1e-8. With `--all-seeds`, it includes the primary nine-window analysis and the two supplemental seed/window-7 analyses.

The model route refits all four configurations with four internal and five grouped external partitions, then fits the operational classifier. It compares selected identifiers, held-out predictions and probabilities at tolerance 1e-7. It verifies the exclusion of the 58 evaluation-only judgments. Inputs, code and environment are recorded in the output directory.

The complete route first verifies spatial masks from the five offline crops, estimates noise and dimensions, and rebuilds all 519 processable seed-13 MNF–PPI groups. It requires the NumPy/MKL reference environment. Its guard remains mandatory because seeded random projections use the numerical MNF eigenvector frame. It then follows the same grouped model and STL route. Full candidate equality is checked separately with `python -m terraclass_ppi.compare_ppi --source outputs/reference --rebuilt outputs/complete --output outputs/ppi_comparison.json`.

After a successful complete run, execute `python scripts/run_pipeline.py products --work outputs/complete --source-work outputs/reference --output-dir outputs/rebuilt_products`. It recomputes predictions, diagnostic summaries and figures and compares four tables. Set RBC_PRODUCTS_DIR to that directory before running the sensitivity and product notebooks to inspect rebuilt products instead of canonical summaries.

Use the Windows pip locks for model and temporal work, or the native Conda lock for complete reconstruction. `environments/model-stl.yml` specifies the pip-based route; `mnf-ppi.yml` preserves the numerical constraint. Linux requirements are supplied for installation reference; their presence is not evidence of execution on Linux.

The notebooks check the archived state and shared functions. They do not launch complete PPI reconstruction. Import the offline inputs before running notebook 01. Its map display requires Figure 1 SVG in outputs/figures, supplied in figuras_e_atlas.zip or regenerated through QGIS. Executed copies, HTML and the execution record are local outputs. Regenerate source notebooks with `python -m terraclass_ppi.notebooks` after changing the explanatory source. The resume option checks matching notebook sources; use a fresh output directory when inputs or the environment change.

The supplementary builder requires ReportLab, pypdf and XlsxWriter, listed in `environments/requirements-print.txt`. It reads canonical data, generates figures and spreadsheets, and joins the editable methods PDF to the result pages and atlas. Windows printing uses installed Times New Roman. QGIS regeneration uses its own Python environment and the portable cartographic inputs.

Validation distinguishes exact equality of candidate records, numerical comparisons with stated tolerances, successful execution and visual inspection.

Configuration roles: `config/estimator_defaults.json` supplies the base estimator parameters; `config/classifier.json` supplies grouping, model-selection rules, fixed parameters and the four configurations to compare. The selected operational parameters and threshold are recorded in `models/operational.json`.
