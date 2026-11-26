import math
from pathlib import Path
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCentroidFillSymbolLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemPicture,
    QgsLayoutItemPolygon,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPalettedRasterRenderer,
    QgsPrintLayout,
    QgsProject,
    QgsProperty,
    QgsRectangle,
    QgsRendererCategory,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QPointF, Qt
from qgis.PyQt.QtGui import QColor, QFont, QPolygonF

p = QgsProject.instance()
ctx = p.transformContext()
root = Path(p.homePath())


def find_layer(substr):
    for lyr in p.mapLayers().values():
        if substr in lyr.source().replace("\\", "/"):
            return lyr
    raise RuntimeError(f"Camada não encontrada no projeto aberto: {substr}")


# Locate the basin, class-core and representative layers in the project.
br = find_layer("uf_brasil_generalizada_500m")
b = find_layer("bacia_722936")
rs = find_layer("nucleos_terraclass_2016_2024.tif")
pts = find_layer("posicoes")

# Paleta ColorBrewer Dark2 (Harrower e Brewer, 2003)
import json
visual = json.loads((root.parent / "config_visual.json").read_text(encoding="utf-8"))
classes = [(c["code"], c["name"], c["color"], c["qgis_marker"]) for c in visual["classes"]]

# Simbologia das UFs + rotulos SIGLA_UF
br.setRenderer(
    QgsCategorizedSymbolRenderer(
        "SIGLA_UF",
        [
            QgsRendererCategory(
                c,
                QgsFillSymbol.createSimple({
                    "color": "#B4C3CE" if c == "MA" else "#EFF2F4",
                    "outline_color": "#7F8E96",
                    "outline_width": "0.14",
                }),
                c,
            )
            for c in sorted(set(f["SIGLA_UF"] for f in br.getFeatures()))
        ],
    )
)
pal = QgsPalLayerSettings()
pal.fieldName = "SIGLA_UF"
pal.enabled = True
uf_fmt = QgsTextFormat()
uf_fmt.setFont(QFont("Times New Roman", 7))
uf_fmt.setSize(7)
uf_fmt.setColor(QColor("#435058"))
pal.setFormat(uf_fmt)
br.setLabeling(QgsVectorLayerSimpleLabeling(pal))
br.setLabelsEnabled(True)
br.triggerRepaint()

# Simbologia do limite da bacia
b.renderer().setSymbol(
    QgsFillSymbol.createSimple({"style": "no", "outline_color": "#263238", "outline_width": "0.34"})
)
b.triggerRepaint()

# Simbologia dos nucleos (raster)
rs.setRenderer(
    QgsPalettedRasterRenderer(
        rs.dataProvider(),
        1,
        [QgsPalettedRasterRenderer.Class(c, QColor(col), name) for c, name, col, _ in classes],
    )
)
rs.triggerRepaint()

# Simbologia dos pontos representantes (contorno branco 0,24 mm + area proporcional)
cats = []
for c, name, col, shape in classes:
    sym = QgsMarkerSymbol.createSimple({
        "name": shape,
        "color": col,
        "outline_color": "#FFFFFF",
        "outline_width": "0.24",
        "size": "1.15",
    })
    sym.setDataDefinedSize(QgsProperty.fromExpression('1.15 * sqrt("frequencia")'))
    cats.append(QgsRendererCategory(c, sym, name))
pts.setRenderer(QgsCategorizedSymbolRenderer("classe", cats))
pts.triggerRepaint()

# Camada auxiliar de centroide da bacia para o encarte regional
loc_name = "Localização regional da bacia"
existing_loc = p.mapLayersByName(loc_name)
if existing_loc:
    loc = existing_loc[0]
else:
    loc = QgsVectorLayer(str(root / "dados/cartografia.gpkg") + "|layername=bacia_722936", loc_name, "ogr")
    p.addMapLayer(loc)
cent = QgsCentroidFillSymbolLayer()
cent.setSubSymbol(
    QgsMarkerSymbol.createSimple({
        "name": "circle",
        "size": "2.4",
        "color": "#1F3A52",
        "outline_color": "#FFFFFF",
        "outline_width": "0.25",
    })
)
s_loc = QgsFillSymbol()
s_loc.changeSymbolLayer(0, cent)
loc.renderer().setSymbol(s_loc)
p.layerTreeRoot().findLayer(loc.id()).setItemVisibilityChecked(False)

# Cria ou substitui o layout de impressão
layout_name = "Figura 1 - RBC (Dark2)"
mgr = p.layoutManager()
old = mgr.layoutByName(layout_name)
if old:
    mgr.removeLayout(old)

layout = QgsPrintLayout(p)
layout.initializeDefaults()
layout.setName(layout_name)
layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190, 108))


def put(item, x, y, w, h):
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(x, y))
    item.attemptResize(QgsLayoutSize(w, h))
    return item


def add_label(txt, x, y, w, h, size=8.5, bold=False, italic=False, color="#111111", halign=Qt.AlignLeft):
    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(txt)
    font = QFont("Times New Roman", int(round(size)), QFont.Bold if bold else QFont.Normal)
    font.setPointSizeF(size)
    font.setItalic(italic)
    lbl.setFont(font)
    lbl.setFontColor(QColor(color))
    lbl.setHAlign(halign)
    return put(lbl, x, y, w, h)


def add_map(x, y, w, h, crs, layers, ext):
    m = put(QgsLayoutItemMap(layout), x, y, w, h)
    m.setCrs(crs)
    m.setLayers(layers)
    m.setKeepLayerSet(True)
    m.zoomToExtent(ext)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.30))
    return m


# Mapa Principal
extent = QgsCoordinateTransform(b.crs(), rs.crs(), ctx).transformBoundingBox(b.extent())
extent.scale(1.10)
main = add_map(9.5, 2.0, 115.5, 95.5, rs.crs(), [pts, b, rs], extent)

# Grade Geografica SIRGAS 2000 (EPSG:4674)
grid = QgsLayoutItemMapGrid("Grade Geográfica", main)
main.grids().addGrid(grid)
grid.setEnabled(True)
grid.setCrs(QgsCoordinateReferenceSystem("EPSG:4674"))
grid.setStyle(QgsLayoutItemMapGrid.FrameAnnotationsOnly)
grid.setFrameStyle(QgsLayoutItemMapGrid.ExteriorTicks)
grid.setFrameWidth(1.2)
grid.setFramePenSize(0.25)
grid.setFramePenColor(QColor("#333333"))
grid.setIntervalX(0.10)
grid.setIntervalY(0.10)
grid.setAnnotationEnabled(True)
grid.setAnnotationFormat(QgsLayoutItemMapGrid.DegreeMinute)
grid.setAnnotationPrecision(0)
grid.setAnnotationDisplay(QgsLayoutItemMapGrid.LatitudeOnly, QgsLayoutItemMapGrid.Left)
grid.setAnnotationDisplay(QgsLayoutItemMapGrid.LongitudeOnly, QgsLayoutItemMapGrid.Bottom)
grid.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Right)
grid.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Top)
grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Left)
grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Bottom)
grid.setAnnotationFrameDistance(1.0)
gfmt = QgsTextFormat()
gfmt.setFont(QFont("Times New Roman", 7))
gfmt.setSize(7)
gfmt.setColor(QColor("#222222"))
grid.setAnnotationTextFormat(gfmt)

# Seta de Norte nativa (sincronizada ao Norte Verdadeiro)
north = QgsLayoutItemPicture(layout)
north.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
north.setLinkedMap(main)
north.setNorthMode(QgsLayoutItemPicture.TrueNorth)
put(north, 115.0, 4.5, 7.5, 9.5)

# Barra de Escala interna
scale = QgsLayoutItemScaleBar(layout)
scale.setStyle("Single Box")
scale.applyDefaultSize()
scale.setLinkedMap(main)
scale.setUnits(QgsUnitTypes.DistanceKilometers)
scale.setUnitsPerSegment(5)
scale.setNumberOfSegments(2)
scale.setNumberOfSegmentsLeft(0)
scale.setUnitLabel("km")
scale.setHeight(1.6)
scale.setLineWidth(0.25)
sfmt = QgsTextFormat()
scale_font = QFont("Times New Roman", 7)
scale_font.setPointSizeF(7.5)
sfmt.setFont(scale_font)
sfmt.setSize(7.5)
sfmt.setColor(QColor("#111111"))
scale.setTextFormat(sfmt)
put(scale, 12.0, 88.5, 30.0, 8.0)

# Encarte Regional
mini = add_map(129.0, 2.0, 59.0, 36.5, br.crs(), [loc, br], QgsRectangle(-52.5, -10.2, -40.5, 0.8))
add_label("Maranhão, Brasil", 129.0, 39.2, 59.0, 5.0, size=8.5, bold=True)

# Legenda: Nucleos e representantes
add_label("Núcleos e representantes", 129.0, 45.5, 59.0, 5.0, size=9.5, bold=True)
add_label("Núcleo", 129.0, 50.8, 11.0, 4.0, size=7.2, italic=True, color="#444444")
add_label("Repr.", 140.2, 50.8, 10.0, 4.0, size=7.2, italic=True, color="#444444")

shape_map = {
    "circle": QgsLayoutItemShape.Ellipse,
    "square": QgsLayoutItemShape.Rectangle,
    "triangle": QgsLayoutItemShape.Triangle,
}
for j, (c, name, col, shape) in enumerate(classes):
    y = 55.2 + j * 5.5
    sw = QgsLayoutItemShape(layout)
    sw.setShapeType(QgsLayoutItemShape.Rectangle)
    sw.setSymbol(QgsFillSymbol.createSimple({"color": col, "outline_color": "#444444", "outline_width": "0.10"}))
    put(sw, 129.5, y + 0.8, 7.2, 3.3)

    mk = QgsLayoutItemShape(layout)
    mk.setShapeType(shape_map[shape])
    mk.setSymbol(QgsFillSymbol.createSimple({"color": col, "outline_color": "#FFFFFF", "outline_width": "0.24"}))
    put(mk, 141.2, y + 0.8, 3.2, 3.2)

    add_label(name, 148.0, y, 38.0, 5.0, size=8.5)

# Limite da bacia na legenda
b_sw = QgsLayoutItemShape(layout)
b_sw.setShapeType(QgsLayoutItemShape.Rectangle)
b_sw.setSymbol(QgsFillSymbol.createSimple({"style": "no", "outline_color": "#263238", "outline_width": "0.34"}))
put(b_sw, 129.5, 72.3, 7.2, 3.3)
add_label("Limite da ottobacia 722936", 139.0, 71.6, 48.0, 5.0, size=8.0)

# Escala visual proporcional (1, 10 e 34 datas)
add_label("Frequência de seleção (datas)", 129.0, 78.0, 59.0, 5.0, size=8.5, bold=True)
y_base = 91.2
for cx, freq in [(135.0, 1), (147.5, 10), (164.5, 34)]:
    diam = 1.15 * math.sqrt(freq)
    circ = QgsLayoutItemShape(layout)
    circ.setShapeType(QgsLayoutItemShape.Ellipse)
    circ.setSymbol(QgsFillSymbol.createSimple({"color": "#D8DEE3", "outline_color": "#333333", "outline_width": "0.22"}))
    put(circ, cx - diam / 2.0, y_base - diam, diam, diam)
    add_label(str(freq), cx - 4.0, y_base + 0.5, 8.0, 4.2, size=7.5, halign=Qt.AlignHCenter)

# Bloco de informacoes cartograficas e fontes
add_label(
    "Projeção: Cônica Equivalente de Albers (BDC)\n"
    "Datum: SIRGAS 2000 (GRS80) | Grade: EPSG:4674\n"
    "Fontes: ANA (2017), IBGE (2024), TerraClass (2016–2024)",
    129.0, 96.5, 59.0, 10.5, size=6.8, color="#333333",
)

mgr.addLayout(layout)
print(f"Layout de impressão gerado: {layout_name}")
