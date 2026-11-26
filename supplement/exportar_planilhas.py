"""Export the supplementary reader tables to Excel without running new analyses."""
from pathlib import Path
from datetime import datetime
import argparse
import xlsxwriter
from preparar_planilhas import prepare

def export(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for book in prepare():
        w=xlsxwriter.Workbook(output/book['filename'])
        base={'font_name':'Arial','font_size':10,'font_color':'#162D39'}
        normal=w.add_format(base);number=w.add_format({**base,'num_format':'0.000000'})
        integer=w.add_format({**base,'num_format':'#,##0'});date=w.add_format({**base,'num_format':'dd/mm/yyyy'})
        header=w.add_format({**base,'bold':True,'bg_color':'#234454','font_color':'#FFFFFF','text_wrap':True,'valign':'vcenter'})
        wrap=w.add_format({**base,'text_wrap':True,'valign':'vcenter'})
        dictionary=[['Aba','Coluna','Significado','Tabela de origem']]
        for ti,t in enumerate(book['tables']):
            s=w.add_worksheet(t['name']);s.hide_gridlines(2);s.freeze_panes(1,1);s.set_row(0,44)
            for j,(column,key) in enumerate(zip(t['columns'],t['original_columns'])):
                vals=[r[j] for r in t['rows'] if r[j] is not None]
                isint=bool(vals) and all(not isinstance(v,(int,float)) or float(v).is_integer() for v in vals)
                fmt=date if key=='date' else integer if isint and any(isinstance(v,(int,float)) for v in vals) else number if any(isinstance(v,(int,float)) for v in vals) else normal
                width=35 if key=='candidate_id' else 14 if key=='date' else min(29,max(15,len(column)*.67))
                s.set_column(j,j,width,fmt)
                s.write(0,j,column,header)
                for i,r in enumerate(t['rows'],1):
                    v=r[j]
                    if v is None:continue
                    if key=='date':s.write_datetime(i,j,datetime.fromisoformat(v),date)
                    elif isinstance(v,str):s.write_string(i,j,v,fmt)
                    else:s.write(i,j,v,fmt)
                dictionary.append([t['name'],column,t['descriptions'][j],t['source']])
            s.add_table(0,0,len(t['rows']),len(t['columns'])-1,{'name':f'Dados{ti}','style':None,'columns':[{'header':c,'header_format':header} for c in t['columns']]})
            if t['name'] in ['VNFP','VNFS','SIL']:s.set_tab_color({'VNFP':'#1B9E77','VNFS':'#7570B3','SIL':'#D95F02'}[t['name']])
            if t['omitted_columns']:dictionary.append([t['name'],'Metadados técnicos','Identificadores de execução e campos auxiliares permanecem nas tabelas do pacote de código. Colunas: '+', '.join(t['omitted_columns']),t['source']])
        dictionary.extend([
            ['Todas','Células vazias','Valores ausentes na tabela de origem. Não foram substituídos por zero.','Material suplementar RBC r12'],
            ['Todas','Precisão','Seis casas decimais são exibidas; os valores numéricos arquivados são preservados na precisão disponível no Excel.','Material suplementar RBC r12']])
        s=w.add_worksheet('Dicionário');s.hide_gridlines(2);s.freeze_panes(1,0)
        for j,width in enumerate([30,40,95,47]):s.set_column(j,j,width)
        for i,row in enumerate(dictionary):s.write_row(i,0,row,header if i==0 else wrap);s.set_row(i,24 if i==0 else 45)
        w.set_properties({'title':book['filename'].replace('_',' ').replace('.xlsx',''),'author':'Rodrigo Lacerda Brito Neto e colaboradores','comments':'Tabelas do material suplementar RBC r12.'})
        w.close();print(book['filename'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();export(a.output)
