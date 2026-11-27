# Basin map

Open study_area.qgz with QGIS 3.44. Layer paths are relative to this directory. The data/ folder contains the small cartographic inputs; styles/ contains the Dark2 styles for cores and representative positions. Class colors are VNFP #1B9E77, VNFS #7570B3 and SIL #D95F02; point shapes are circle, square and triangle, with white outlines.

The print layout includes basin location, eligible cores, representative recurrence, legend, north arrow, scale and coordinate grid. It uses the values in ../config/visual.json. Export settings are PNG 600 dpi and vector PDF/SVG. The SVG export uses outlined text.

To regenerate, run build_map.py with the Python supplied by QGIS. On Windows, for example: `& 'C:/Program Files/QGIS 3.44.0/bin/python-qgis.bat' qgis/build_map.py`. The default export folder is outputs/figures/ in the code root. RBC_MAP_OUTPUT can select another destination. The script updates the project layout and portable styles.

Refinements of the map must preserve the class definitions, coordinate system and represented universes. Recurrence counts dates returning to a position, including non-consecutive returns; it is distinct from the permanence of the mapped class.

## Applied layout values

Positions and dimensions below are in millimetres from the upper-left corner of the page. These values are already applied by layout.py and stored in the project.

| Item | Position x, y | Width × height or setting |
|---|---|---|
| Page | 0, 0 | 190 × 108 mm |
| Main map | 9.5, 2.0 | 115.5 × 95.5 mm; basin extent expanded by 10% |
| Regional inset | 129.0, 2.0 | 59.0 × 36.5 mm; geographic bounds −52.5, −10.2, −40.5, 0.8 |
| North arrow | 115.0, 4.5 | 7.5 × 9.5 mm; true north linked to the main map |
| Scale bar | 12.0, 88.5 | Two segments of 5 km; 1.6 mm bar height; 7.5 pt text |
| Coordinate annotations | Left and bottom of main map | EPSG:4674; 0.10° intervals; degrees and minutes; 7 pt |
| Main map frame | Main map boundary | 0.30 mm stroke |
| Class legend | 129.0, 45.5 | 59.0 × 5.0 mm heading; rows start at y=55.2 with 5.5 mm spacing |
| Representative symbol outlines | Class legend and points | White; 0.24 mm |
| Recurrence legend | Heading at 129.0, 78.0 | Examples for 1, 10 and 34 dates; diameter = 1.15 × sqrt(frequency) mm |
| Projection and source credits | 129.0, 96.5 | 59.0 × 10.5 mm; 6.8 pt |

The text family is Times New Roman. The north arrow uses a built-in QGIS resource. SVG text is exported as outlines; the class-core layer retains its raster representation. Edit labels, symbols and map placement in the QGIS project. Its cartographic data are included here, so opening the map does not require the large offline archive.
