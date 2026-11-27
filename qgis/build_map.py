"""Regenerate the basin map with the central RBC visual configuration."""
from pathlib import Path
import os
import json
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from qgis.core import QgsApplication, QgsProject, QgsLayoutExporter, Qgis
from qgis.PyQt.QtGui import QFont, QFontDatabase

root = Path(__file__).resolve().parent
config = json.loads((root.parent / 'config/visual.json').read_text(encoding='utf-8'))
app = QgsApplication([], False)
app.initQgis()
fontdir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
for name in ['times.ttf', 'timesbd.ttf', 'timesi.ttf']:
    if (fontdir / name).exists():
        QFontDatabase.addApplicationFont(str(fontdir / name))
app.setFont(QFont('Times New Roman', 9))
p = QgsProject.instance()
assert p.read(str(root / 'study_area.qgz'))
p.setPresetHomePath('')
assert all(layer.isValid() for layer in p.mapLayers().values())
exec(compile((root / 'layout.py').read_text(encoding='utf-8'), str(root / 'layout.py'), 'exec'), globals())
layout.renderContext().setDpi(config['print_dpi'])
assert not north.isMissingImage()
p.setFileName(str(root / 'study_area.qgz'))
assert p.write()
from portability import make_portable
make_portable(root / 'study_area.qgz')
out = Path(os.environ.get('RBC_MAP_OUTPUT',root.parent / 'outputs/figures'))
out.mkdir(parents=True,exist_ok=True)
export = QgsLayoutExporter(layout)
image = QgsLayoutExporter.ImageExportSettings()
image.dpi = config['print_dpi']
assert export.exportToImage(str(out / 'figura_1_mapa.png'), image) == 0
pdf = QgsLayoutExporter.PdfExportSettings()
pdf.dpi = config['print_dpi']
pdf.forceVectorOutput = True
assert export.exportToPdf(str(out / 'figura_1_mapa.pdf'), pdf) == 0
svg = QgsLayoutExporter.SvgExportSettings()
svg.dpi = config['print_dpi']
svg.forceVectorOutput = True
svg.textRenderFormat = Qgis.TextRenderFormat.AlwaysOutlines
assert export.exportToSvg(str(out / 'figura_1_mapa.svg'), svg) == 0
# Portable QML files for reuse of the class styles.
styles = root / 'styles'
styles.mkdir(exist_ok=True)
for layer, name in [(rs, 'nucleos_Dark2'), (pts, 'representantes_Dark2')]:
    layer.saveNamedStyle(str(styles / (name + '.qml')))
print(json.dumps({'dpi': config['print_dpi'], 'size_mm': [190,108], 'north_valid': True, 'all_layers_valid': True, 'project': str(p.fileName())}, ensure_ascii=False))
