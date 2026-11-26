"""Read the extracted portable QGIS bundle and check layers and symbols."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import json
from qgis.core import QgsApplication,QgsProject,QgsVectorLayer

BASE=Path(__file__).resolve().parents[1]
config=json.loads((BASE/'config_visual.json').read_text(encoding='utf-8'))
app=QgsApplication([],False);app.initQgis()
p=QgsProject.instance()
assert p.read(str(BASE/'SIG/Mapa_RBC_oficial.qgz'))
assert Path(p.homePath()).resolve()==(BASE/'SIG').resolve(),p.homePath()
details=[]
for layer in p.mapLayers().values():
    assert layer.isValid(),layer.name()
    file=Path(layer.source().split('|')[0]).resolve()
    assert file.is_relative_to(BASE.resolve()),str(file)
    count=sum(1 for _ in layer.getFeatures()) if isinstance(layer,QgsVectorLayer) else None
    details.append({'layer':layer.name(),'count':count,'source':str(file.relative_to(BASE.resolve()))})
    if '|layername=posicoes' in layer.source():
        for category in layer.renderer().categories():
            c=next(c for c in config['classes'] if c['code']==category.value())
            assert category.symbol().color().name().upper()==c['color']
            assert abs(category.symbol().symbolLayer(0).strokeWidth()-0.24)<1e-8
assert p.layoutManager().layoutByName('Figura 1 - RBC (Dark2)') is not None
print(json.dumps({'portable_QGIS_read':True,'layers':details,'preset_home':p.presetHomePath()},ensure_ascii=False))
