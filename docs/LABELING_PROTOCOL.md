# Human spectral judgments

The published labels are fixed reproduction inputs. Reproducing the reported results does not require another annotation session. `data/derived/labels/development.csv` contains the 2,422 development examples; `data/derived/labels/representative_reference.csv` contains the representative evaluation reference. The 58 evaluation-only examples must remain outside development.

Candidates are judged for spectral compatibility with photosynthetically active vegetation, considering visible absorption, the red-edge rise and elevated near-infrared reflectance. The Portuguese panel displays individual and overlaid spectra, RGB context and quality fields. An uncertain judgment is a temporary state and is resolved before fitting. RGB darkness outside the valid thematic core does not by itself identify a missing spectrum at the selected cell.

To regenerate the original PPI-ranked sample panel, unpack both data archives and run `python scripts/build_labeling_panel.py --data-root ../dataset`. Open `outputs/reference/painel/index.html`. The sample contains the highest-vote candidate and up to three further candidates separated by at least 2 degrees in spectral angle. It is a subset of the development base, which also includes representative-prioritized examples. Candidate identifiers and label-source columns preserve that distinction.

The panel starts without automatic decisions and supports compatible, incompatible and uncertain judgments, comments, CSV export and import. Browser storage is local to the page and browser. Export the CSV before moving or clearing the panel. New judgments do not modify the published model, training data or reference results automatically; they are separate inputs for a future study version.
