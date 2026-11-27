"""Montar suplemento autônomo com métodos Word, tabelas e figuras vetoriais."""
from pathlib import Path
from io import BytesIO
import json,csv
import pandas as pd
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY,TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader,PdfWriter,Transformation

from terraclass_ppi.paths import CODE_ROOT, output_root
from terraclass_ppi.data_io import table_directory
import os
OUT=Path(os.environ.get('RBC_SUPPLEMENT_OUTPUT',output_root()/'supplement'))
OUT.mkdir(parents=True,exist_ok=True)
EVID=CODE_ROOT/'docs/supplement'
TABLES=table_directory()
pdfmetrics.registerFont(TTFont('TimesText','C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('TimesBold','C:/Windows/Fonts/timesbd.ttf'))
styles={
 'h':ParagraphStyle('h',fontName='TimesBold',fontSize=14,leading=18,spaceBefore=12,spaceAfter=12,keepWithNext=True),
 'sub':ParagraphStyle('sub',fontName='TimesBold',fontSize=11.5,leading=15,spaceBefore=12,spaceAfter=8,keepWithNext=True),
 'p':ParagraphStyle('p',fontName='TimesText',fontSize=10.5,leading=14,spaceAfter=9,alignment=TA_JUSTIFY,splitLongWords=True),
 'small':ParagraphStyle('small',fontName='TimesText',fontSize=9,leading=11.5,spaceAfter=7,splitLongWords=True),
 'cell':ParagraphStyle('cell',fontName='TimesText',fontSize=9,leading=11),
 'cellh':ParagraphStyle('cellh',fontName='TimesBold',fontSize=9,leading=11),
}
flow=[]
def p(s,kind='p'):flow.append(Paragraph(escape(s),styles[kind]))
def grid(rows,widths):
 data=[[Paragraph(escape(str(v)),styles['cellh' if i==0 else 'cell']) for v in row] for i,row in enumerate(rows)]
 t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf0ed')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cccccc')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 flow.extend([t,Spacer(1,12)])
def f(v,n=4):return f'{float(v):.{n}f}'.replace('.',',')

p('S5 Resultados e orientação de leitura','h')
p('A avaliação dos candidatos e a avaliação dos representantes utilizam predições externas. A seleção da configuração operacional na base completa é uma etapa interna distinta. Os componentes e as forças correspondem aos representantes operacionais da semente 13.')
p('Tabela S1 Comparação interna das configurações','sub')
p('Parâmetros na ordem máximo de folhas / mínimo de exemplos por folha / penalização L2. Os escores são predições fora do ajuste nas quatro partições internas da base completa de desenvolvimento. Todas as configurações atendem à precisão positiva mínima de 95%.')
choices=pd.read_csv(TABLES/'configuracoes_internas.csv').sort_values('order').to_dict('records')
rows=[['Folhas / mínimo / L2','Limiar','Precisão','Sensibilidade','AP','Positivos']]
for name,r in zip(['31 / 20 / 1','15 / 20 / 1','15 / 30 / 3','7 / 40 / 5'],choices):rows.append([name,*[f(r[k]) for k in ['threshold','precision','recall','ap']],str(r['predicted_positive'])])
grid(rows,[111,70,77,87,66,96])
p('A configuração 15 / 30 / 3 foi escolhida pela maior sensibilidade e ajustada com todos os 2.422 exemplos de desenvolvimento. Os hiperparâmetros e o limiar operacional constam da Seção S3. A escolha e o limiar são refeitos dentro de cada treinamento externo durante a avaliação do procedimento.')
p('Avaliação externa e disponibilidade','sub')
grid([['Classe','Compatíveis / avaliados','Proporção'],['VNFP','173 / 173','100,00%'],['VNFS','164 / 173','94,80%'],['SIL','165 / 173','95,38%'],['Total','502 / 519','96,72%']],[130,240,137])
p('A meta de 95% é global. As cinco partições externas produziram seleção nas 519 combinações processáveis. Na aplicação operacional, 173 das 184 datas por classe tiveram representante (94,02%). Nas 33 combinações sem representante, 31 não tinham pixels válidos e duas tinham quantidade insuficiente. Em 16/10/2017, havia 54 pixels válidos na VNFP, oito na VNFS e zero na SIL. Os campos de coverage_seed13.csv distinguem esses estados.')
p('C significa compatível e NC, não compatível na Figura S1. As linhas da matriz correspondem aos julgamentos humanos e as colunas, às predições externas. A matriz externa dos candidatos contém 1.885 verdadeiros negativos, 22 falsos positivos, 39 falsos negativos e 476 verdadeiros positivos. As tabelas outer_predictions.csv, outer_partitions.csv e representative_reference.csv permitem conferir os grupos e julgamentos. Os 58 rótulos exclusivos da avaliação não estão em development.csv. Na Figura S1, a completude mensal usa datas como denominador, e a disponibilidade espacial usa o total de pixels de cada núcleo, incluindo datas sem observação na mediana mensal.')
flow.append(PageBreak())
p('Tabela S2 Forças por banda e domínio na janela 7','h')
p('Força sazonal (Fₛ) e força de tendência (Fₜ) nas 173 datas observadas. As quatro últimas linhas são medianas entre bandas correlacionadas. Esta tabela permite consultar a configuração ilustrada na Figura S2; as comparações do artigo abrangem as nove janelas. Não há exclusão de extremidades.')
tab=pd.read_csv(TABLES/'tabela_S2_forcas_janela7.csv')
rows=[['Banda / domínio','Fₛ VNFP','Fₛ VNFS','Fₛ SIL','Fₜ VNFP','Fₜ VNFS','Fₜ SIL']]
for r in tab.itertuples():rows.append([r.band_domain,*[f(getattr(r,f'{metric}_{cl}')) for metric in ['FS','FT'] for cl in [1,2,9]]])
grid(rows,[105,67,67,67,67,67,67])
p('Os arquivos metrics_seed13.csv e strength_by_domain.csv apresentam as nove janelas. Os 270 ajustes completos estão em components_seed13.parquet. O arquivo calendar.csv contém as 184 posições e a máscara de observação pode ser recuperada do campo observed dos componentes.')
p('Alteração dos componentes e diagnóstico dos resíduos','sub')
sens=pd.read_csv(TABLES/'sensibilidade_componentes.csv').groupby('classe').median(numeric_only=True)
p('Entre as janelas 7 e 35, as medianas da REQM sazonal normalizada foram '+', '.join(f'{f(sens.loc[cl,"seasonal_nrmse"],3)} na {name}' for cl,name in [(1,'VNFP'),(2,'VNFS'),(9,'SIL')])+'. A normalização usa o desvio-padrão do respectivo componente na janela 7. As amplitudes de Fₛ e Fₜ e as razões de dispersão interanual por banda estão em component_sensitivity.csv.')
flow.append(PageBreak())
p('Tabela S3 Diferenças entre classes nas janelas extremas','h')
p('D é a mediana da classe A menos a mediana da classe B, calculada por domínio. O sinal estabelece a ordenação do par. Δ|D| = |D(35)| − |D(7)|: positivo indica aumento da diferença absoluta e negativo, redução. A tabela eletrônica class_domain_window_comparisons.csv contém 216 registros nas nove janelas.')
comp=pd.read_csv(TABLES/'comparacoes_classes_extremos_janelas.csv')
rows=[['Força','Domínio','Par A–B','D(7)','D(35)','Δ|D|']]
for r in comp.itertuples():rows.append([r.metric,r.domain,r.class_a+'–'+r.class_b,*[f(v) for v in [r.difference_7,r.difference_35,r.change_absolute]]])
grid(rows,[53,65,128,87,87,87])
p('No NIR e no red edge, a diferença de Fₛ entre VNFP e VNFS aumenta entre as janelas extremas, enquanto as diferenças VNFP–SIL e VNFS–SIL diminuem. Ordenações das medianas de domínio não são generalizadas para todas as bandas; band_domain_ordering_exceptions.csv documenta as exceções.')
flow.append(PageBreak())
p('Componentes, resíduos e reprodução','h')
diag=pd.read_csv(TABLES/'diagnosticos_270_ajustes.csv')
p('As correlações nas defasagens de 1, 23 e 46 utilizam 166, 148 e 125 pares observados por série, respectivamente. diagnostics_all_windows.csv, global_by_window.csv e class_by_window.csv conservam os diagnósticos por banda, classe e janela; residual_lag_correlations.csv permite examinar todas as defasagens.')
p('A dispersão interanual diminuiu nas 30 séries entre as janelas 7 e 35. As razões medianas entre bandas foram '+', '.join(f'{f(sens.loc[cl,"phase_ratio"],3)} na {name}' for cl,name in [(1,'VNFP'),(2,'VNFS'),(9,'SIL')])+'. A força sazonal superou a de tendência nos 270 ajustes. Os componentes preservam a reconstrução aditiva e as métricas usam apenas as datas originalmente observadas.')
p('Figura S1 Classificação e disponibilidade','sub')
p('Curvas precisão–sensibilidade e matriz dos candidatos nas predições externas; disponibilidade mensal das observações. Cada proporção conserva o denominador descrito na Seção S3. A figura é apresentada após as referências suplementares.')
p('Figura S2 Decomposição completa na janela 7','sub')
p('Tendência, sazonalidade e resíduo nas dez bandas das três classes, com janelas 7/45/25. Fₜ está anotado nos painéis de tendência e Fₛ nos de sazonalidade. As faixas cinzas assinalam as 22 posições de cada extremidade da tendência; todas as 173 datas observadas participam das métricas. A página vetorial ampliável permite consultar os 90 painéis. ')
p('Atlas A1–A10 Nove janelas por banda','sub')
p('As dez páginas seguintes ao conjunto de figuras apresentam B02, B03, B04, B05, B06, B07, B08, B8A, B11 e B12, nessa ordem. Cada página reúne reflectância, tendência, sazonalidade e resíduo nas três classes. As cores das curvas de componentes distinguem as nove janelas; os representantes são os mesmos em todas elas.')
p('Reprodução local','sub')
p('O README do depósito orienta a consulta das quatro planilhas e dos arquivos de figuras. O ZIP de código contém as instruções para reproduzir os cálculos e regenerar este suplemento a partir das tabelas de referência. Os julgamentos humanos publicados são entradas dessa reprodução. O projeto cartográfico portátil está na pasta qgis do código.')
model=json.loads((TABLES/'modelo_operacional_metadados.json').read_text(encoding='utf8'))
p('O limiar operacional é '+str(model['threshold']).replace('.',',')+'. A configuração e os identificadores de reprodução acompanham o modelo no ZIP de dados.','small')
flow.append(PageBreak())
p('S6 Referências do material suplementar','h')
for ref in json.loads((EVID/'references.json').read_text(encoding='utf8')):p(ref,'small')
guide=OUT/'supplementary_results.pdf'
SimpleDocTemplate(str(guide),pagesize=(595.28,841.89),leftMargin=44,rightMargin=44,topMargin=42,bottomMargin=44).build(flow)

def figure_page(path,label,caption,size):
 width,height=size;buf=BytesIO();c=Canvas(buf,pagesize=size)
 c.setFont('TimesBold',14);c.drawString(42,height-32,label)
 lines=[]
 from reportlab.lib.utils import simpleSplit
 lines=simpleSplit(caption,'TimesText',10,width-84)
 c.setFont('TimesText',10)
 for i,line in enumerate(lines):c.drawString(42,height-51-13*i,line)
 c.save();buf.seek(0)
 page=PdfReader(buf).pages[0]
 art=PdfReader(path).pages[0];aw=float(art.mediabox.width);ah=float(art.mediabox.height)
 avail_h=height-102-13*len(lines);scale=min((width-84)/aw,avail_h/ah)
 x=(width-aw*scale)/2;y=44+(avail_h-ah*scale)/2
 page.merge_transformed_page(art,Transformation().scale(scale).translate(x,y))
 return page

w=PdfWriter();w.append(PdfReader(EVID/'methods.pdf'));w.append(PdfReader(guide))
w.add_page(figure_page(OUT/'figuras/figura_S1_classificacao_disponibilidade.pdf','Figura S1 Classificação e disponibilidade','(a) Predições externas dos candidatos: curvas precisão–sensibilidade e matriz de confusão. C: compatível; NC: não compatível. Na matriz, as linhas são julgamentos humanos e as colunas são predições externas. (b) Completude mensal de datas e mediana da fração de pixels válidos por classe.',(841.89,595.28)))
w.add_page(figure_page(OUT/'figuras/figura_S2_decomposicao_completa.pdf','Figura S2 Componentes nas dez bandas e três classes','Janela sazonal 7, tendência 45 e passa-baixa 25. Fₜ na tendência e Fₛ na sazonalidade; métricas nas 173 observações. Faixas cinzas: indicação visual das extremidades. Página vetorial ampliável.',(841.89,1190.55)))
w.append(PdfReader(OUT/'figuras/atlas_componentes_todas_janelas.pdf'))
# Continuous supplementary numbering; the derived Word source has empty footers.
for i,page in enumerate(w.pages,1):
 width=float(page.mediabox.width);height=float(page.mediabox.height)
 buf=BytesIO();c=Canvas(buf,pagesize=(width,height))
 c.setFillColor(colors.black);c.setFont('TimesText',9);c.drawRightString(width-38,18,f'S{i}');c.save();buf.seek(0);page.merge_page(PdfReader(buf).pages[0])
w.add_metadata({'/Title':'Material suplementar RBC','/Subject':'Método completo e resultados das nove janelas; semente 13'})
with (OUT/'Material_Suplementar_RBC.pdf').open('wb') as file:w.write(file)
print(json.dumps(dict(methods_pages=len(PdfReader(EVID/'methods.pdf').pages),results_guide_pages=len(PdfReader(guide).pages),supplement_pages=len(w.pages)),indent=2))
