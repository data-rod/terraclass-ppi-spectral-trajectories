"""Write the supplementary reading guide in PDF."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate(destination):
    regular=Path('C:/Windows/Fonts/times.ttf');bold=Path('C:/Windows/Fonts/timesbd.ttf')
    if not regular.exists():
        from matplotlib import font_manager
        regular=Path(font_manager.findfont('DejaVu Sans'));bold=Path(font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold')))
    pdfmetrics.registerFont(TTFont('GuideText',str(regular)));pdfmetrics.registerFont(TTFont('GuideBold',str(bold)))
    styles={
        'title':ParagraphStyle('title',fontName='GuideBold',fontSize=18,leading=21,spaceAfter=14),
        'h':ParagraphStyle('h',fontName='GuideBold',fontSize=12,leading=15,spaceBefore=12,spaceAfter=7),
        'p':ParagraphStyle('p',fontName='GuideText',fontSize=11,leading=14,spaceAfter=8),
        'small':ParagraphStyle('small',fontName='GuideText',fontSize=9,leading=12,spaceAfter=7),
    }
    flow=[]
    def p(s,style='p'):flow.append(Paragraph(s,styles[style]))
    p('Material suplementar: guia de leitura','title')
    p('Trajetórias de reflectância de pixels selecionados pelo Pixel Purity Index em classes florestais do TerraClass Amazônia em uma bacia no oeste do Maranhão')
    p('Documento principal','h')
    p('<b>Suplemento_RBC_r12.pdf</b> reúne os métodos completos (S1–S4), as tabelas e a apresentação dos resultados (S5), as referências (S6), as figuras S1 e S2 e o atlas das nove janelas sazonais. As páginas são numeradas de S1 a S23.')
    p('Planilhas','h')
    p('Na pasta <b>Planilhas</b>, os quatro arquivos Excel organizam as informações por assunto. A aba <b>Dicionário</b> identifica os campos, as unidades e as tabelas de origem. Os cabeçalhos permanecem visíveis durante a rolagem e as tabelas podem ser filtradas.')
    for title,text in [
        ('01_Selecao_e_avaliacao.xlsx','Universos da seleção, configurações do classificador, avaliação externa, julgamentos humanos, predições e partições.'),
        ('02_Representantes_e_espectros.xlsx','Reflectâncias e posições dos representantes, distribuições espectrais, disponibilidade, recorrência, deslocamentos e exemplo de B08.'),
        ('03_Forcas_e_sensibilidade.xlsx','Forças sazonal e de tendência nas nove janelas, comparações entre classes, diagnósticos dos componentes, correlações dos resíduos e tabela da janela 7.'),
        ('04_Componentes_temporais.xlsx','Reflectância, série usada no ajuste, tendência, sazonalidade e resíduo. Uma aba por classe, com as dez bandas e nove janelas. São 49.680 registros do calendário completo.')]:
        p('<b>'+title+'</b><br/>'+text,'small')
    p('As células vazias indicam ausência de valor na tabela de origem. A exibição com seis casas decimais não limita os valores armazenados à precisão exibida. As métricas utilizam as 173 datas observadas por classe; as posições preenchidas são identificadas nas séries do calendário completo.')
    p('Figuras','h')
    p('A pasta <b>Figuras</b> contém S1 (classificação e disponibilidade) e S2 (decomposição da janela 7) em PDF, PNG e SVG, além do atlas das nove janelas em PDF. Os PDFs e SVGs permitem ampliação. Os PNGs foram exportados a 600 dpi.')
    p('Reprodução e créditos','h')
    p('O código para regenerar o PDF, as planilhas e as figuras acompanha o pacote de código, em <b>supplement/</b>. Repositório: <link href="https://github.com/data-rod/terraclass-ppi-spectral-trajectories">github.com/data-rod/terraclass-ppi-spectral-trajectories</link>.','small')
    p('Documentação e resultados produzidos pelos autores: CC BY 4.0. As fontes mantêm seus termos e créditos. Dados TerraClass e derivados: CC BY-SA 4.0, com créditos TerraClass/INPE/Embrapa. Reflectâncias: Copernicus Sentinel e INPE/Brazil Data Cube. Delimitação hidrográfica: ANA. As referências completas estão no PDF suplementar.','small')
    p('Financiamento: Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq), Projeto Geotec, processo 400048/2026-4.','small')
    SimpleDocTemplate(str(destination),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=38,bottomMargin=35,title='Guia de leitura do material suplementar RBC r12',author='Rodrigo Lacerda Brito Neto e colaboradores').build(flow)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);generate(a.output)
