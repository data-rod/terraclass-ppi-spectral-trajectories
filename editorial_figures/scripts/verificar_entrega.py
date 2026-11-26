"""Check the official print bundle and build its catalogue and manifest."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageOps
from pypdf import PdfReader, PdfWriter

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
CONFIG = json.loads((BASE/'config_visual.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ORIGIN=json.loads((BASE/'documentacao/origem.json').read_text(encoding='utf-8'))
assert all(sha(BASE/p) == h for p,h in ORIGIN['source_hashes'].items())
assert sha(BASE/'figuras/distribuicoes_reflectancia.csv') == ORIGIN['reflectance_statistics_sha256']
with zipfile.ZipFile(BASE/'SIG/Mapa_RBC_oficial.qgz') as z:
    tree = ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.qgs'))))
sources = [e.text for e in tree.findall('.//projectlayers/maplayer/datasource')]
assert sources and all(s.startswith('./dados/') for s in sources)
figures = [
    ('1', 'figura_1_mapa', 'Mapa da bacia, núcleos e representantes'),
    ('3', 'figura_3_espectros_deslocamentos', 'Perfis espectrais e deslocamentos'),
    ('4', 'figura_4_distribuicoes_reflectancia', 'Distribuições das reflectâncias'),
    ('5', 'figura_5_sensibilidade', 'Sensibilidade de F_S e F_T'),
    ('S1', 'figura_S1_classificacao_disponibilidade', 'Classificação e disponibilidade'),
    ('S2', 'figura_S2_decomposicao_completa', 'Decomposição completa da janela 7'),
]
rows=[]
writer=PdfWriter()
cards=[]
for label,stem,title in figures:
    png,pdf,svg=[BASE/'figuras'/f'{stem}.{ext}' for ext in ['png','pdf','svg']]
    with Image.open(png) as im:
        dpi=im.info.get('dpi')
        assert dpi and min(dpi)>599 and max(dpi)<601, (stem,dpi)
        width,height=im.size
    page=PdfReader(pdf)
    assert len(page.pages)==1
    assert '<svg' in svg.read_text(encoding='utf-8')
    assert not ET.parse(svg).findall('.//{http://www.w3.org/2000/svg}text'), 'SVG must outline text'
    writer.append(str(pdf),outline_item=f'Figura {label} - {title}')
    rows.append(dict(figura=label,arquivo=stem,width_px=width,height_px=height,dpi=600,width_cm=round(width/600*2.54,2),height_cm=round(height/600*2.54,2),png_sha256=sha(png),pdf_sha256=sha(pdf),svg_sha256=sha(svg)))
    cards.append(f'<article><h2>Figura {label} — {title}</h2><a href="figuras/{stem}.png"><img src="figuras/{stem}.png" alt="Figura {label}: {title}"></a><p><a download href="figuras/{stem}.png">PNG 600 dpi</a> · <a download href="figuras/{stem}.svg">SVG vetorial</a> · <a href="figuras/{stem}.pdf">PDF vetorial</a></p><small>{width} × {height} px; {width/600*2.54:.1f} × {height/600*2.54:.1f} cm a 600 dpi.</small></article>')
with (BASE/'Figuras_RBC_impressao.pdf').open('wb') as f: writer.write(f)
with (BASE/'documentacao/resolucao_das_figuras.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Figuras oficiais RBC — Dark2</title><style>body{font:17px/1.5 system-ui,sans-serif;max-width:1250px;margin:30px auto;padding:0 20px;color:#203039;background:#f5f7f8}h1{font-size:1.8em}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:22px}article{padding:18px;background:white;border:1px solid #d8e0e5;border-radius:8px}h2{font-size:1.05em}img{width:100%;height:300px;object-fit:contain}a{color:#125f77}code{font-size:.95em}small{color:#4b5b64}@media(max-width:550px){section{display:block}article{margin:15px 0}}</style><h1>Figuras oficiais RBC — Dark2</h1><p>VNFP <code>#1B9E77</code> círculo; VNFS <code>#7570B3</code> quadrado; SIL <code>#D95F02</code> triângulo.</p><p>PNGs exportados diretamente a 600 dpi; SVGs com texto convertido em traçados; PDFs vetoriais com fontes incorporadas. Para composição final, prefira os arquivos vetoriais.</p><p><a href="Figuras_RBC_impressao.pdf">Conjunto em PDF</a> · <a href="SIG/Mapa_RBC_oficial.qgz">Projeto QGIS</a> · <a href="documentacao/resolucao_das_figuras.csv">Dimensões e hashes</a></p><section>'''+''.join(cards)+'''</section><p>As camadas vetoriais usam SIRGAS 2000 (EPSG:4674). A bacia é identificada como ANA/BHO 2017. O ano IBGE 2024 provém do nome da camada de origem; não foi confirmado por metadados externos.</p></html>'''
(BASE/'index.html').write_text(html,encoding='utf-8')
(BASE/'LEIA_PRIMEIRO.txt').write_text('''FIGURAS OFICIAIS RBC — DARK2 — 25/11/2026

Abra index.html para visualizar e baixar cada figura.
PNG: 600 dpi, exportados diretamente do código, sem ampliação de bitmap.
SVG: vetorial, textos convertidos em traçados para preservar a aparência sem instalar fontes.
PDF: vetorial, adequado para composição/impressão. O mapa contém a máscara raster em sua resolução cartográfica original; exportar a 600 dpi não acrescenta detalhe ao dado de 10 m.
Não ampliar PNG além do tamanho físico registrado em documentacao/resolucao_das_figuras.csv quando for necessário manter 600 dpi. Para redimensionar, use SVG ou PDF e confira a legibilidade na dimensão final.

PALETA OFICIAL DESTE PROJETO
VNFP #1B9E77 círculo; VNFS #7570B3 quadrado; SIL #D95F02 triângulo.
Fonte: ColorBrewer Dark2, Harrower e Brewer (2003), doi:10.1179/000870403235002042.
É a paleta adotada no estudo, e não a paleta institucional do TerraClass.
Configuração única: config_visual.json, lida pelos dois geradores.

CONTEÚDO
Figuras 1, 3, 4, 5, S1 e S2 em PNG/PDF/SVG.
SIG/Mapa_RBC_oficial.qgz: mapa com layout de impressão; caminhos relativos. Extraia todo o ZIP antes de abrir. Layout: Figura 1 - RBC (Dark2).
SIG/estilos: simbologia QML para núcleos e representantes.
Dados necessários para os gráficos estão em dados; dados do mapa em SIG/dados.
scripts/figuras_3_4_5.py gera os gráficos a partir das tabelas em dados/.

REPRODUZIR
Em ambiente Python científico compatível com os locks em documentacao:
python scripts/figuras_3_4_5.py
No Python do QGIS 3.44:
python SIG/regenerar_mapa.py
No Windows, também pode usar o python-qgis.bat da instalação QGIS.
Para identidade tipográfica ao regenerar, instale Times New Roman. Os SVGs entregues usam traçados, sem depender dessa instalação para visualização.
Nenhum modelo ou ajuste STL é refeito pelos geradores de figuras; os dados científicos de entrada permanecem preservados. Windows/QGIS 3.44 foram executados nesta entrega; não se declara teste em Linux.

CONFERÊNCIA
SHA256SUMS.txt registra todos os arquivos distribuídos, exceto o próprio manifesto.
documentacao/verificacao.json registra as verificações. Resoluções e dimensões em CSV.
O sistema de coordenadas das camadas vetoriais foi conferido como SIRGAS 2000 (EPSG:4674). A bacia é identificada como ANA/BHO 2017; o ano IBGE 2024 foi informado no nome da camada de origem e não teve sua versão confirmada por metadados externos.
''',encoding='utf-8')
record={'date':'2026-11-25','palette':CONFIG,'figures':rows,'data_unchanged':True,'reflectance_statistics_identical':True,'relative_QGIS_sources':sources,'n_representatives':519,'n_per_class':173,'n_STL_panels':90,'svg_text_outlined':True}
(BASE/'documentacao/verificacao.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'figures':len(rows),'png_resolution_dpi':600,'data_unchanged':True,'dimensions':rows},ensure_ascii=False))

manifest_files = sorted(p for p in BASE.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt" and not any(part in {"__pycache__", ".ipynb_checkpoints"} for part in p.parts))
(BASE/"SHA256SUMS.txt").write_text("".join(f"{sha(p)}  {p.relative_to(BASE).as_posix()}\n" for p in manifest_files), encoding="utf-8")
