# Data formats and units

The root selected by RBC_DATA_ROOT contains `data/` and `models/`. Public calculation inputs have a single authoritative path. CSV column names and Parquet dtypes retain their scientific meanings from the acquisition and analysis pipeline.

## Spatial and observation inputs

`data/derived/spatial/` contains the basin, core mask, pixel index, catalog, spatial metadata, NWHFC table and class dimensions. The pixel index uses canonical row-major order; `pixel`, `row` and `col` locate cells on the common grid. Classes are VNFP (1), VNFS (2) and SIL (9). The spatial JSON defines the grid and coordinate reference system. The catalog has 184 composition dates and assets from two BDC tiles.

The unchanged offline ZIP is imported to `data/raw/observations/` and `data/raw/terraclass/`. Observation arrays have one row per eligible cell, ten integer band fields, SCL, CLEAROB, PROVENANCE and a Boolean validity field. Multiplication by 0.0001 converts integer band values to reflectance. Each array has an acquisition receipt. TerraClass crops cover 2016, 2018, 2020, 2022 and 2024.

## Candidates and judgments

`data/derived/candidates/candidates_seed13.parquet`, and the corresponding seed29 and seed47 files, preserve all original columns and the order of the sorted source partitions. Each Parquet row group contains one class/date combination. `partition_index.csv` provides seed, class, date, row group, row offset and count. Each of the 519 processable groups per seed has 20,000 PPI votes. Runtime checkpoint partitions are local outputs, not additional public data copies.

Candidate identifiers link class, date and grid cell. The ten original reflectances are preserved. The classifier uses 17 predictors built by `terraclass_ppi.features.atributos`; coordinates, class, date and votes are excluded.

`data/derived/labels/development.csv` contains 2,422 development judgments. `representative_reference.csv` contains the external representative reference; its 58 evaluation-only judgments remain outside development. The operational classifier is `models/operational.joblib`, with metadata in `models/operational.json`. Five external classifiers are under `models/external/`. Only load joblib files from a trusted distribution.

## Representatives, components and summaries

`data/derived/representatives/` holds selected candidate spectra and locations. The seed-13 table has 519 rows, 173 per class. `data/derived/temporal/metrics_seed13.csv` has 270 rows: three classes × ten bands × nine windows. FS and FT are unitless strength measures on the 173 observed dates. Seed29 and seed47 preserve their supplemental window-7 analyses.

`data/derived/temporal/components_seed13.parquet` contains all 270 fits on the 184-position calendar, including observed values, interpolated values and additive components. Reflectance, trend, seasonal and residual components share the reflectance unit. Missing observed reflectance remains missing; interpolation supports the fit only. Distances are in kilometres.

`data/derived/summaries/strength_by_domain.csv` stores domain medians. `global_by_window.csv` has a two-line header for statistics across the 30 series. `table_s2_window7.csv` is Supplementary Table S2, covering ten bands and four domains for window 7. Additional CSVs describe availability, distributions, comparisons and residual diagnostics. Their exported Excel versions provide Portuguese labels and data dictionaries.

`data/provenance/table_paths.json` resolves table basenames to canonical inputs. `runtime_paths.json` defines the isolated working view used by the verified execution routes. It is generated from these canonical inputs; it does not supply alternative calculation values.

The `components_window7_seed13.parquet` reference retains the original single-window model/STL output schema for comparison by the quick route. Corresponding seed29 and seed47 references preserve their window-7 analyses. These differ in schema and universe from the 270-fit table, which also includes filled values.

The `evaluation_status` value `needs_human_label` records the original sampling status of the 58 evaluation-only examples. Final human judgments are in `evaluation_label`; this status does not indicate unresolved public labels. The original model identifiers are explained in `data/provenance/model_identifiers.json`, including the assessment receipt checksum, which refers to assessment.json rather than to the public judgment CSV.
