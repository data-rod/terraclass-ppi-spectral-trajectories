"""Generate the eight source notebooks from their method descriptions."""
from pathlib import Path
import nbformat as n
SETUP="from pathlib import Path\nimport os,sys,json\nimport pandas as pd\nfrom IPython.display import display,SVG\nfrom terraclass_ppi.paths import CODE_ROOT as ROOT,output_root\nfrom terraclass_ppi.data_io import prepare_reference,table_directory,iter_candidate_groups\nWORK=Path(os.environ['RBC_OUTPUT']).resolve() if os.environ.get('RBC_OUTPUT') else prepare_reference()\nos.environ['RBC_OUTPUT']=str(WORK)\nFIGURES=output_root()/'figures'\nfrom terraclass_ppi.spatial import CFG\n"
BOOKS=[{'name': '00_guide',
  'title': 'Guide and environment',
  'intro': 'This notebook checks the Python environment used to reproduce the study. Read it '
           'before choosing the temporal check, model fitting or complete reconstruction. The data '
           'describe spectra selected separately for each forest class and date within ottobasin '
           '722936; selected pixels can move between dates.',
  'method_heading': 'Choose a reproduction route',
  'method': 'The quick route recalculates Seasonal-Trend decomposition using LOESS (STL) from the '
            'archived representatives and compares components and metrics with the reference. It '
            'needs `dados_derivados_e_modelos.zip`. Figure generation is a separate command, shown '
            'in notebook 07.\n'
            '\n'
            'The model route refits grouped model selection, external evaluation and the '
            'operational classifier from archived candidates and human labels. The complete route '
            'also reconstructs thematic masks and Minimum Noise Fraction–Pixel Purity Index '
            '(MNF–PPI) candidates; it additionally needs `rbc-offline-inputs.zip`.\n'
            '\n'
            'Run these commands from the extracted code directory, with the required environment '
            'active:\n'
            '\n'
            '```text\n'
            'python scripts/run_pipeline.py quick --data-root ../dataset\n'
            'python scripts/run_pipeline.py model --data-root ../dataset --output-dir '
            'rebuilt-model\n'
            'python scripts/run_pipeline.py complete --data-root ../dataset --output-dir '
            'rebuilt-complete\n'
            '```\n'
            '\n'
            'The first two routes use the scientific Python environment described in `README.md`. '
            'Complete MNF–PPI reconstruction requires NumPy 2.1.3 linked to Intel MKL 2023.1, '
            'supplied by the native Conda environment. The build check rejects a different '
            'linear-algebra backend. Input and code receipts identify executions that can be '
            'resumed.\n'
            '\n'
            'Primary results use seed 13. Adding `--all-seeds` to the quick command also checks '
            'supplementary seeds 29 and 47. Their temporal results use seasonal window 7; seed 13 '
            'uses all nine windows.',
  'code': 'import platform\n'
          'from importlib.metadata import version\n'
          'display(pd.Series({m:version(m) for m in '
          "['numpy','pandas','rasterio','scikit-learn','statsmodels']}))\n"
          'print(platform.platform(),sys.version)\n'
          'display(CFG)\n'
          '\n'
          'from threadpoolctl import threadpool_info\n'
          'display([{k:v for k,v in item.items() if k != "filepath"} for item in '
          'threadpool_info()])\n',
  'result_heading': 'Read the environment output',
  'interpretation': 'The environment output lists package versions, calendar parameters and the '
                    'numerical backends loaded in this kernel. Compare these with '
                    '`docs/REPRODUCTION.md` before starting a route. That document distinguishes '
                    'model reproduction from full MNF–PPI reconstruction and records the '
                    'environments actually tested. Human judgments are archived inputs; none of '
                    'these commands requires another annotation session.',
  'references': 'Package versions and installation: `README.md`, '
                '`environments/requirements-win.lock`, `environments/requirements-linux.lock`.'},
 {'name': '01_spatial',
  'title': 'Basin and permanent class cores',
  'intro': 'This notebook reconstructs the spatial eligibility mask from the five thematic windows '
           'and the basin geometry. It compares every cell with the archived mask and spatial '
           'index. Extract the reference and offline-input archives before running it.',
  'method_heading': 'Define eligible positions',
  'method': 'A position must retain the same TerraClass class in 2016, 2018, 2020, 2022 and 2024. '
            'The 3×3 erosion keeps positions whose eight neighbours also satisfy permanence. '
            'Nearest-neighbour reprojection transfers this mask to the 10 m Brazil Data Cube (BDC) '
            'grid; the cell centre determines whether a position belongs to the basin.\n'
            '\n'
            'The basin intersects tiles 029010 and 030010. Their adjacent cells are processed '
            'together for each class and date. The basin area is 459.97 km² in the Albers '
            'equal-area projection; the original vector attribute is 463.52 km².',
  'code': 'from terraclass_ppi.offline import verify_spatial\n'
          'verify_spatial()\n'
          "display(json.loads((WORK/'spatial.json').read_text())['pixels'])\n"
          "display(SVG(filename=str(FIGURES/'figura_1_mapa.svg')))\n",
  'result_heading': 'Check the mask and map',
  'interpretation': 'The comparison should find 1,648,550 eligible cells: 559,153 in primary '
                    'natural forest vegetation (VNFP), 573,001 in secondary natural forest '
                    'vegetation (VNFS), and 516,396 in silviculture (SIL). Figure 1 shows these '
                    'cores and the positions selected across dates. Marker frequency counts '
                    'returns to a position, including returns on non-consecutive dates.',
  'references': 'TerraClass and basin source identifiers: `work/spatial.json`. Raster '
                'reprojection: https://rasterio.readthedocs.io/en/stable/topics/reproject.html'},
 {'name': '02_observations',
  'title': 'Observation quality and provenance',
  'intro': 'This notebook checks the composition calendar and the integrity of archived '
           'observation arrays. It reads the local catalogue and acquisition receipts; it does not '
           'download satellite assets. The array checks require the offline-input archive.',
  'method_heading': 'Apply the quality fields',
  'method': 'The Scene Classification Layer (SCL) identifies vegetation (4), non-vegetated surface '
            '(5), water (6) and unclassified observations (7), the four categories retained before '
            'spectral classification. CLEAROB counts clear observations; PROVENANCE identifies the '
            'acquisition used in the composite. A pixel is eligible on a date when CLEAROB > 0, '
            'SCL is 4–7 and all ten band values are valid. Source integer values are converted to '
            'reflectance with factor 10⁻⁴.\n'
            '\n'
            'The structured NumPy arrays retain these source fields and a validity flag. Receipt '
            'hashes allow integrity checks without holding the full time series in memory. A '
            'missing or damaged input file is an execution error. Coverage records separately '
            'identify dates with no valid pixel, too few pixels to process, or no accepted '
            'spectral candidate.',
  'code': 'from terraclass_ppi.spatial import sha\n'
          "catalog=pd.read_parquet(WORK/'catalog.parquet')\n"
          "counts=catalog.groupby('tile_id').date.nunique()\n"
          'assert len(counts)==2 and counts.eq(184).all()\n'
          "display(catalog.groupby('tile_id').date.agg(['min','max','size']))\n"
          "receipts=sorted((WORK/'observations').glob('*.json'))\n"
          'if receipts:\n'
          "    expected_dates=set(pd.to_datetime(catalog.date).dt.strftime('%Y-%m-%d'))\n"
          "    assert {p.stem for p in receipts}==expected_dates, 'Observation inventory is "
          "incomplete'\n"
          '    for p in receipts:\n'
          '        info=json.loads(p.read_text());assert '
          "sha(p.with_suffix('.npy'))==info['sha256']\n"
          "    print(len(receipts),'observation arrays verified')\n"
          "else: print('Quick reference route: observation arrays belong to the separate "
          "offline-input archive.')\n"
          "display(pd.read_csv(WORK/'results/coverage-13.csv').groupby(['classe','state']).size())\n",
  'result_heading': 'Interpret availability',
  'interpretation': 'The catalogue contains 184 dates for each tile. There are 33 non-processable '
                    'class–date combinations across the three classes: 31 have no valid pixel and '
                    'two have fewer than 101. If the observation archive is absent, this notebook '
                    'reports that condition and checks only the catalogue and coverage tables; it '
                    'has not verified array integrity in that case.',
  'references': 'Brazil Data Cube collection and source assets: `work/catalog.parquet`; quality '
                'rules: `docs/METHODOLOGY.md`.'},
 {'name': '03_mnf_ppi',
  'title': 'MNF dimensionality and PPI candidates',
  'intro': 'This notebook examines the archived dimensionality estimates and verifies the '
           'candidate inventory. It checks vote conservation in every processed class–date '
           'combination. To recalculate the candidates from observations, use the complete '
           'terminal route in notebook 00.',
  'method_heading': 'Estimate noise and count extreme projections',
  'method': 'Noise covariance is estimated as half the sample covariance of differences between '
            'horizontally or vertically adjacent valid pixels of the same class. The Minimum Noise '
            'Fraction (MNF) transform uses this estimate to order spectral components. '
            'Noise-Whitened Harsanyi–Farrand–Chang (NWHFC) estimates use a false-alarm probability '
            'of 10⁻⁴. The median by class, rounded half up and limited to 2–10, determines how '
            'many components are retained.\n'
            '\n'
            'The Pixel Purity Index (PPI) uses 10,000 unit-length directions generated by '
            'normalizing Gaussian random vectors with seed 13. In each projection, the maximum and '
            'minimum each receive one vote. Thus the votes sum to 20,000 for every processed '
            'class–date combination. All positive-vote candidates retain their original ten-band '
            'spectra and locations. The canonical spatial order resolves ties.',
  'code': "display(json.loads((WORK/'dimensions.json').read_text()))\n"
          "files=list(iter_candidate_groups(WORK/'candidates',13))\n"
          "quality=pd.read_parquet(WORK/'nwhfc.parquet')\n"
          "ready=quality[quality.state.eq('ready')]\n"
          "expected={f'13-{r.date}-{r.classe}.parquet' for r in ready.itertuples()}\n"
          "assert len(expected)==519 and {name for name,_ in files}==expected, 'PPI inventory is "
          "incomplete'\n"
          'voted=0\n'
          'for _, f in files:\n'
          '    assert f.votes.sum()==20000 and f.votes.gt(0).all()\n'
          '    voted+=len(f)\n'
          'assert voted==213647\n'
          "print(len(files),'class–date combinations verified')\n"
          "display(pd.read_parquet(WORK/'nwhfc.parquet').groupby('classe').suggested_endmembers.agg(['min','median','max']))\n",
  'result_heading': 'Read the dimensionality and vote checks',
  'interpretation': 'The dimensionality estimates range from two to nine, and the median is six in '
                    'every class. The 519 processable combinations contain 213,647 positive-vote '
                    'candidates. The human labeling panel presents up to four candidates per '
                    'combination, chosen by PPI rank and angular separation; that display sample '
                    'is distinct from the six retained MNF components.',
  'references': 'Green et al. (1988), MNF: https://doi.org/10.1109/36.3001 . Chang and Du (2004), '
                'NWHFC: https://doi.org/10.1109/TGRS.2003.819189 . Boardman et al. (1995), PPI: '
                'https://ntrs.nasa.gov/citations/19950027316 . Parameters: `docs/METHODOLOGY.md` '
                'and `nucleo.py`.'},
 {'name': '04_classification',
  'title': 'Classification and representative evaluation',
  'intro': 'This notebook reads the archived grouped evaluation and operational model settings. It '
           'constructs the 17 predictors from the development spectra and checks the human '
           'reference totals. Model fitting itself is performed by the terminal model or complete '
           'route.',
  'method_heading': 'Evaluate candidates and the selected representatives',
  'method': 'The predictors are ten reflectances divided by the spectrum’s Euclidean norm, six '
            'spectral indices and log(1+norm). Five outer partitions group candidates by class and '
            'date to evaluate the procedure. Four inner partitions choose among four tree '
            'configurations and select the threshold with the highest sensitivity subject to '
            'positive precision ≥0.95 and at least 30 accepted examples.\n'
            '\n'
            'Each outer model classifies every candidate in its reserved groups. The accepted '
            'candidate with the highest PPI is then selected; a tie is resolved by the lowest '
            'canonical pixel index. Human judgments assess those selected representatives. The '
            'final operational model is fitted on 2,422 development examples. The 58 '
            'evaluation-only judgments remain outside that fit. The 95% compatibility target '
            'applies to the overall representative evaluation.',
  'code': 'from terraclass_ppi.spectral import atributos\n'
          "training=pd.read_csv(WORK/'model/training.csv')\n"
          'X,names=atributos(training);assert X.shape==(2422,17)\n'
          "display(pd.Series(names,name='Spectral predictors'))\n"
          "display(pd.read_csv(WORK/'evaluation/candidate_external_metrics.csv'))\n"
          "reference=pd.read_csv(WORK/'evaluation/reference.csv')\n"
          "display(reference.groupby('classe').evaluation_label.value_counts())\n"
          "assert reference.evaluation_label.eq('compatible').sum()==502\n"
          "print('External representative compatibility: 502/519 = 96.72%')\n"
          "display(json.loads((WORK/'model/model.json').read_text())['choice'])\n",
  'result_heading': 'Read the two evaluations',
  'interpretation': 'Candidate metrics describe predictions on labeled examples reserved from each '
                    'outer fit. The representative reference describes the output of '
                    'classification followed by highest-PPI selection: 502 of 519 representatives '
                    'were judged compatible (96.72%). The printed operational choice comes from '
                    'internal selection on the full development base; it is used to build the time '
                    'series.',
  'references': 'Friedman (2001), gradient boosting; Pedregosa et al. (2011), scikit-learn (full '
                'citations in `REFERENCES.md`). Cawley and Talbot (2010): '
                'https://www.jmlr.org/papers/v11/cawley10a.html . Threshold selection: '
                'https://scikit-learn.org/1.6/modules/classification_threshold.html'},
 {'name': '05_stl',
  'title': 'Representatives and STL components',
  'intro': 'This notebook recalculates the STL components and strengths from the seed-13 '
           'representatives and compares them with the archived reference. The check uses the same '
           'fitting function as the terminal route.',
  'method_heading': 'Fit the components and calculate their strengths',
  'method': 'Classical STL with robust weighting decomposes reflectance as Yₜ = Tₜ + Sₜ + Rₜ: '
            'trend, seasonal component and residual. The period is 23 calendar positions, the '
            'trend window is 45 and the low-pass window is 25; the local polynomial degree is one. '
            'Seasonal windows are 7, 9, 11, 13, 15, 21, 25, 31 and 35.\n'
            '\n'
            'Sample variances on the originally observed dates define seasonal strength F_S = '
            'max(0, 1 − Var(R)/Var(S+R)) and trend strength F_T = max(0, 1 − Var(R)/Var(T+R)). '
            'Time interpolation supplies the regular sequence needed for fitting. Interpolated '
            'positions are excluded from the strength calculations; all 173 observed dates per '
            'series are included.',
  'code': 'from terraclass_ppi.pipeline import quick\n'
          'quick(WORK,all_seeds=False)\n'
          "display(pd.read_csv(WORK/'results/domains-13.csv').query('window==7'))\n"
          "display(SVG(filename=str(FIGURES/'figura_S2_decomposicao_completa.svg')))\n",
  'result_heading': 'Interpret the component figure',
  'interpretation': 'The 519 selected spectra form 30 series: three classes and ten bands. The '
                    'displayed table summarises the window-7 strengths by spectral domain; the '
                    'figure shows its individual-band components. F_T is annotated in trend panels '
                    'and F_S in seasonal panels. Gray endpoint bands are visual indications; they '
                    'do not remove dates from the metrics. Window 7 is one of the nine examined '
                    'configurations and the reference for component differences.',
  'references': 'Cleveland et al. (1990), STL; Wang et al. (2006), strength measures: '
                'https://doi.org/10.1007/s10618-005-0039-x . Implementation: '
                'https://www.statsmodels.org/v0.14.4/generated/statsmodels.tsa.seasonal.STL.html'},
 {'name': '06_sensitivity',
  'title': 'Sensitivity to seasonal smoothing',
  'intro': 'This notebook compares the strengths and components across the nine seasonal windows. '
           'It reads archived tables by default. To inspect reconstructed tables, run the products '
           'command below and set RBC_PRODUCTS_DIR to its absolute output path before starting the '
           'kernel.',
  'method_heading': 'Compare windows with the same representatives',
  'method': 'The seasonal window smooths a given position of the annual cycle across years. '
            'Changing its length does not change which pixel supplies an observation. The '
            'representatives, annual period, trend and low-pass windows and robust weighting '
            'remain fixed.\n'
            '\n'
            'The tables report changes in seasonal and trend strength, component root mean square '
            'error relative to window 7, and interannual dispersion of the seasonal component. '
            'Domain summaries are medians over correlated bands in visible (VIS), red edge (RE), '
            'near infrared (NIR) and shortwave infrared (SWIR).\n'
            '\n'
            '```text\n'
            'python scripts/run_pipeline.py products --work outputs/complete --source-work '
            'outputs/reference --output-dir outputs/rebuilt_products\n'
            '```\n'
            '\n'
            'The output directory must be new. RBC_PRODUCTS_DIR selects that directory for this '
            'notebook; when it is unset, the notebook reads the canonical summary tables.',
  'code': "PRODUCTS=Path(os.environ['RBC_PRODUCTS_DIR']) if os.environ.get('RBC_PRODUCTS_DIR') "
          'else table_directory()\n'
          "d=pd.read_csv(PRODUCTS/'dominios.csv')\n"
          "display(d.pivot(index=['domain','window'],columns='classe',values=['FS','FT']))\n"
          "display(pd.read_csv(PRODUCTS/'sensibilidade_componentes.csv').groupby('classe').median(numeric_only=True))\n"
          "display(SVG(filename=str(FIGURES/'figura_5_sensibilidade.svg')))\n",
  'result_heading': 'Read magnitude and ordering together',
  'interpretation': 'The NIR and red-edge domain medians retain VNFP > VNFS > SIL for F_S in all '
                    'nine windows. Their magnitudes still vary with smoothing. The component table '
                    'summarises variation across bands within a class; those bands are not '
                    'independent replicates. The displayed figure comes from the same archived or '
                    'reconstructed product set as the tables.',
  'references': 'STL smoothing: Cleveland et al. (1990). Fixed settings and diagnostics: '
                '`docs/METHODOLOGY.md`; strength measures: '
                'https://doi.org/10.1007/s10618-005-0039-x .'},
 {'name': '07_products',
  'title': 'Figures and numerical summaries',
  'intro': 'This notebook generates print figures from a chosen set of tables and displays the '
           'corresponding strength table. It uses archived products unless RBC_PRODUCTS_DIR '
           'identifies the output of a completed products command.',
  'method_heading': 'Select the figure inputs',
  'method': 'To derive tables and diagnostics from a reconstructed model, run:\n'
            '\n'
            '```text\n'
            'python scripts/run_pipeline.py products --work outputs/complete --source-work '
            'outputs/reference --output-dir outputs/rebuilt_products\n'
            '```\n'
            '\n'
            'Set RBC_PRODUCTS_DIR to that output path before starting this kernel. The generator '
            'below then reads its `dados/` subdirectory and writes PNG, SVG and PDF figures under '
            '`outputs/figures/`. With RBC_PRODUCTS_DIR unset, the figure inputs are the canonical '
            'archived tables. The archived figure files remain unchanged.\n'
            '\n'
            'The products command compares four numerical tables with the reference and '
            'recalculates diagnostics through the shared scientific functions. Its absolute '
            'tolerances are 10⁻⁸ for STL and 10⁻⁷ for classifier scores. The notebook displays the '
            'selected product set; it does not refit the classifier or rerun PPI.',
  'code': 'import subprocess\n'
          "PRODUCTS=Path(os.environ['RBC_PRODUCTS_DIR']) if os.environ.get('RBC_PRODUCTS_DIR') "
          'else table_directory()\n'
          "command=[sys.executable,'-m','terraclass_ppi.figures','--output',str(FIGURES)]\n"
          "if os.environ.get('RBC_PRODUCTS_DIR'):command.extend(['--data',str(PRODUCTS/'dados')])\n"
          'subprocess.run(command,check=True)\n'
          "display(pd.read_csv(PRODUCTS/'table_s2_window7.csv'))\n"
          "display(SVG(filename=str(FIGURES/'figura_5_sensibilidade.svg')))\n",
  'result_heading': 'Check the table and figure',
  'interpretation': 'The strength table groups the ten bands and four spectral domains for window '
                    '7. Figure 5 compares F_S and F_T across all nine windows. '
                    '`outputs/notebooks/execution.json` records notebook execution, while '
                    '`outputs/` records the separate complete reconstruction and product checks.',
  'references': 'ColorBrewer: https://doi.org/10.1179/000870403235002042 . Scientific sources are '
                'cited in the notebooks for the corresponding processing stages.'}]

def build(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for item in BOOKS:
        cells=[n.v4.new_markdown_cell('# '+item['title']+'\n\n'+item['intro']),
               n.v4.new_code_cell(SETUP),
               n.v4.new_markdown_cell('## '+item['method_heading']+'\n\n'+item['method']),
               n.v4.new_code_cell(item['code']),
               n.v4.new_markdown_cell('## '+item['result_heading']+'\n\n'+item['interpretation']+'\n\n## References\n\n'+item['references'])]
        path=directory/(item['name']+'.ipynb')
        if path.exists():
            previous=n.read(path,as_version=4)
            for cell,prior in zip(cells,previous.cells):cell.id=prior.id
        book=n.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(name='python3',display_name='Python 3',language='python')))
        n.write(book,path)

if __name__=='__main__':
 from terraclass_ppi.paths import CODE_ROOT
 build(CODE_ROOT/'notebooks')
