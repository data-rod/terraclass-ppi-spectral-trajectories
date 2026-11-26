# Data formats and identifiers

Commands run from the code directory. Extract the reference archive and the offline-input archive into this directory so both populate `work/`.

## Spatial and temporal indices

`work/pixels.parquet` contains eligible cells in canonical spatial order. `pixel` is the row-major cell index in the common basin grid; `classe` identifies VNFP (1), VNFS (2) or silviculture (9). Grid dimensions, transform, coordinate reference system and processing identifier are in `work/spatial.json`. The basin and class-core mask are supplied as `basin.gpkg` and `nucleos.tif`.

`work/catalog.parquet` identifies source assets by tile and composition date. There are 184 calendar positions between 2017 and 2024. The source tile records provenance; candidates are calculated for the whole basin by class and date.

## Observation arrays

Each composition has a NumPy structured array and a JSON acquisition receipt under `work/observations/`. Array rows follow the eligible-cell index. The ten band fields store the source integer values; multiply by 0.0001 to obtain reflectance. SCL records the scene classification, CLEAROB counts clear observations, and PROVENANCE identifies the acquisition used in the composite. The retained SCL codes are 4 (vegetation), 5 (non-vegetated surface), 6 (water) and 7 (unclassified); `valid` records eligibility for that date. Supplementary Section S1 describes these quality fields. Receipts contain the processing identifier and SHA-256 of the array.

Use `numpy.load(path, mmap_mode='r', allow_pickle=False)` to read an array without loading the whole time series. Missing files or failed integrity checks are execution errors, distinct from dates with no valid observations.

## Candidates and human labels

`work/candidates/<seed>-<date>-<class>.parquet` contains all positive-vote PPI candidates. Candidate and pixel identifiers link spectra to dates, classes and locations. Votes sum to 20,000 within each processed class–date combination. Spectral features are computed from the ten original reflectances by `nucleo.atributos`; PPI and coordinates are excluded from classifier inputs.

`work/model/training.csv` supplies the 2,422 development labels. `work/evaluation/reference.csv` supplies the human reference used to assess externally selected representatives. The 58 evaluation-only judgments are excluded from development. Human judgments are published inputs; reproduction does not require new annotation.

In `reference.csv`, `reference_label` contains the 461 judgments already available for the withheld groups. `evaluation_label` contains the final judgment for every selected representative, including the 58 evaluation-only cases. The retained `evaluation_status` value `needs_human_label` identifies those 58 cases when the reference was assembled; it does not indicate a missing final judgment. Label-source fields in the development table record how examples entered the human reference and are not classifier predictors.

## Representatives and temporal results

`work/results/representatives-13.parquet` records the selected candidate for each processable class–date combination, including spectrum, location, PPI and classifier score. The corresponding `coverage-13.csv` distinguishes successful selection, no valid pixels, insufficient pixels and no accepted candidate.

The primary results contain 519 representatives: 173 dates for each class. The 30 band series use all 184 calendar positions for STL fitting; the original observation mask restricts metrics to observed dates. Component tables retain value, trend, seasonal and residual fields. Seasonal and trend strength are calculated for the nine seasonal windows; domain summaries are medians over their correlated bands.

Seeds 29 and 47 are supplementary verification. Their results use the same classifier and operational threshold as seed 13. They do not change the primary article's seed.

## Recomputed outputs

Model and complete-reconstruction commands require a separate output directory. Their verification report records comparisons actually performed, numerical tolerances, environment and elapsed time. A report with `spatial_and_PPI_rebuilt: false` does not certify full MNF–PPI reconstruction.
