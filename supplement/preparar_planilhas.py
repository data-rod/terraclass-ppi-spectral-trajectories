"""Prepare reader tables from the archived supplementary results."""
from pathlib import Path
import json
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DATA=HERE/'suplemento'
DROP={'run_id','analysis_id','experiment_id','label_source','label_sample','group','evaluation_status','reference_label'}
CLASSES={1:'VNFP',2:'VNFS',9:'SIL'}
LABELS={'compatible':'C','incompatible':'NC'}
NAMES={
 'classe':'Classe','name':'Nome','date':'Data','year':'Ano','position':'Posição no ano',
 'days_since_previous':'Dias desde a data anterior','pixel':'Posição na grade','row':'Linha na grade','col':'Coluna na grade',
 'x':'Coordenada X (m)','y':'Coordenada Y (m)','tile':'Tile BDC','votes':'Votos PPI',
 'candidate_id':'Identificador do candidato','label':'Julgamento humano','evaluation_label':'Julgamento da avaliação',
 'observed':'Observação disponível','predicted':'Classificação predita','probability':'Probabilidade predita',
 'threshold':'Limiar','fold':'Partição','outer_fold':'Partição externa','seed':'Semente',
 'window':'Janela sazonal','band':'Banda','domain':'Domínio espectral','band_domain':'Banda ou domínio',
 'FS':'Força sazonal (FS)','FT':'Força de tendência (FT)','metric':'Métrica',
 'pixels':'Pixels no núcleo','candidates':'Candidatos PPI','training':'Exemplos de desenvolvimento',
 'positive':'Exemplos C','negative':'Exemplos NC','accepted':'Candidatos aceitos',
 'representatives':'Representantes','external_compatible':'Representantes C na avaliação externa',
 'median_km':'Deslocamento mediano (km)','maximum_km':'Deslocamento máximo (km)',
 'consecutive_same':'Repetições consecutivas','unique_positions':'Posições distintas','returns':'Retornos',
 'max_recurrence':'Máxima recorrência','distance_km':'Deslocamento (km)','elapsed_days':'Intervalo (dias)',
 'n':'Número de observações','minimum':'Mínimo','q25':'Primeiro quartil','median':'Mediana','q75':'Terceiro quartil','maximum':'Máximo',
 'kde_bandwidth':'Largura de banda da densidade','n_valid':'Pixels válidos','n_voted':'Pixels com votos PPI',
 'n_compatible':'Candidatos aceitos','state':'Estado do processamento','noise_pairs':'Pares de vizinhos',
 'intrinsic_dimension':'Dimensão estimada','suggested_endmembers':'Componentes retidos',
 'identity_noise_fallback':'Uso de ruído identidade','false_alarm_probability':'Probabilidade de falso alarme',
 'mnf_eigenvalue_floor':'Piso dos autovalores MNF','nwhfc_relative_ridge':'Regularização relativa NWHFC',
 'chosen':'Configuração escolhida','order':'Ordem da configuração','n_training':'Exemplos no treinamento',
 'n_test':'Exemplos na avaliação','n_test_groups':'Grupos na avaliação','selected':'Representantes selecionados',
 'ap':'Precisão média (AP)','roc_auc':'Área sob a curva ROC','tn':'Verdadeiros NC','fp':'Falsos C','fn':'Falsos NC','tp':'Verdadeiros C',
 'precision':'Precisão positiva','recall':'Sensibilidade','specificity':'Especificidade','predicted_positive':'Decisões positivas',
 'class_a':'Classe A','class_b':'Classe B','value_a':'Valor da classe A','value_b':'Valor da classe B',
 'signed_difference':'Diferença A menos B','absolute_difference':'Diferença absoluta',
 'difference_7':'Diferença na janela 7','difference_35':'Diferença na janela 35',
 'change_signed':'Mudança da diferença com sinal','change_absolute':'Mudança da diferença absoluta',
 'strict_order_preserved':'Ordenação estrita preservada','signed_difference_monotonic':'Diferença com sinal monotônica',
 'absolute_difference_monotonic':'Diferença absoluta monotônica','largest_class':'Classe de maior FS na banda',
 'domain_median_largest':'Classe de maior FS no domínio','lag':'Defasagem','correlation':'Correlação','pairs':'Pares observados',
 'n_observed':'Datas observadas','FS_range':'Amplitude de FS','FT_range':'Amplitude de FT',
 'seasonal_nrmse':'REQM sazonal normalizada','trend_nrmse':'REQM da tendência normalizada',
 'residual_nrmse':'REQM residual normalizada','phase_ratio':'Razão da dispersão interanual (35/7)',
 'seasonal_phase_between_cycles_sd_median':'Dispersão interanual sazonal',
 'value':'Reflectância observada','filled':'Reflectância usada no ajuste','trend':'Tendência','seasonal':'Sazonalidade','residual':'Resíduo',
 'SCL':'Categoria SCL','CLEAROB':'Observações claras (CLEAROB)','PROVENANCE':'Origem da aquisição (PROVENANCE)',
}
for field,part in [('trend','tendência'),('seasonal','sazonalidade'),('residual','resíduo')]:
    for suffix,label in [('sd','Desvio-padrão'),('p95_p05','Amplitude P95 menos P05'),('harmonic_r2','R² do harmônico anual'),
                         ('harmonic_amplitude','Amplitude do harmônico anual'),('rmse_vs_7','REQM em relação à janela 7'),
                         ('corr_vs_7','Correlação com a janela 7')]:
        NAMES[field+'_'+suffix]=label+' da '+part if field!='residual' else label+' do resíduo'
    NAMES['var_'+field]='Variância da '+part if field!='residual' else 'Variância do resíduo'
NAMES['residual_rmse']='REQM residual'
for n in [1,23,46]:
    NAMES[f'residual_lag{n}']=f'Correlação residual, defasagem {n}'
    NAMES[f'residual_lag{n}_pairs']=f'Pares observados, defasagem {n}'
for f in ['FS','FT']:
    for cl in CLASSES:NAMES[f'{f}_{cl}']=f'{f} — {CLASSES[cl]}'

SPECS=[
 ('01_Selecao_e_avaliacao.xlsx',[
  ('Universos','tabela_1.csv'),('Configurações','configuracoes_internas.csv'),('Avaliação externa','candidate_external_metrics.csv'),
  ('Julgamentos','training.csv'),('Referência humana','reference.csv'),('Predições externas','outer_predictions.csv'),('Partições externas','outer_partitions.csv')]),
 ('02_Representantes_e_espectros.xlsx',[
  ('Representantes','representantes.csv'),('Distribuições','distribuicoes_reflectancia.csv'),('Recorrência','conferencia_posicoes_deslocamentos.csv'),
  ('Deslocamentos','distances-13.csv'),('Disponibilidade','coverage-13.csv'),('Calendário','calendario.csv'),('Exemplo B08','sequencia_B08.csv')]),
 ('03_Forcas_e_sensibilidade.xlsx',[
  ('Forças por domínio','dominios.csv'),('Forças por banda','metrics-13.csv'),('Sensibilidade','sensibilidade_componentes.csv'),
  ('Comparações entre classes','comparacoes_classes_dominios_janelas.csv'),('Diferenças entre extremos','comparacoes_classes_extremos_janelas.csv'),
  ('Exceções por banda','diferencas_bandas_e_sintese_dominio.csv'),('Ordenações','ordenacoes.csv'),
  ('Resumo por classe','resumo_classe_janela.csv'),('Resumo das janelas','resumo_por_janela.csv'),
  ('Diagnósticos','diagnosticos_270_ajustes.csv'),('Correlações dos resíduos','correlacao_residual_lags_1_46.csv'),
  ('Tabela S2, janela 7','tabela_S2_forcas_janela7.csv')]),
]

def label(column):
    if column in NAMES:return NAMES[column]
    if column.startswith('B') and column[1:].replace('A','').isdigit():return column+' (reflectância)'
    raise KeyError('Missing reader label: '+column)

def description(column):
    if column in {'x','y'}:return 'Centro do pixel em Albers equivalente, GRS80; origem 12° S, meridiano 54° O, paralelos 2° S e 22° S, falsos leste/norte 5.000.000/10.000.000 m.'
    if column=='classe':return 'VNFP: vegetação natural florestal primária; VNFS: vegetação natural florestal secundária; SIL: silvicultura.'
    if column in {'label','evaluation_label','predicted','observed'}:return 'C: compatível; NC: não compatível. Em componentes temporais, a disponibilidade é indicada por Sim/Não.'
    if column=='probability':return 'Probabilidade da classe compatível calculada pelo classificador. A referência humana é apresentada em coluna própria.'
    if column=='FS':return 'Força sazonal; variância amostral calculada nas 173 datas observadas. Consultar a Seção S4 do PDF.'
    if column=='FT':return 'Força de tendência; variância amostral calculada nas 173 datas observadas. Consultar a Seção S4 do PDF.'
    if column=='value':return 'Reflectância nas datas observadas; célula vazia nas lacunas do calendário.'
    if column=='filled':return 'Reflectância após preenchimento das lacunas, usada somente para viabilizar o ajuste STL.'
    if column=='phase_ratio':return 'Dispersão interanual sazonal na janela 35 dividida pela dispersão na janela 7.'
    if column.endswith('_nrmse'):return 'REQM entre as janelas 35 e 7, dividida pelo desvio-padrão do componente na janela 7.'
    if column=='seasonal_phase_between_cycles_sd_median':return 'Mediana dos 23 desvios-padrão entre os oito anos para a mesma posição do ciclo anual.'
    if column=='window':return 'Comprimento da janela sazonal STL: 7, 9, 11, 13, 15, 21, 25, 31 ou 35.'
    if column.startswith('B') or column in {'trend','seasonal','residual'}:return 'Reflectância de superfície ou componente aditivo na mesma unidade adimensional.'
    if column=='candidate_id':return 'Identificador rastreável composto por data, código da classe e posição na grade.'
    if column=='tile':return 'Código do tile BDC com seis dígitos; zero inicial preservado.'
    if column=='threshold':return 'Limiar da probabilidade de compatibilidade usado na seleção; não é julgamento humano.'
    if column=='name':return 'Sigla da classe em Universos; identificador da configuração em Configurações.'
    if column=='state':return 'Estado registrado da combinação classe–data ou do ajuste. Não altera os valores observados.'
    return label(column)+'. Definição e procedimento nas Seções S1–S4 do PDF suplementar.'

def table(frame,sheet,source,component=False):
    omitted=[c for c in frame.columns if c in DROP]
    frame=frame.drop(columns=omitted).copy()
    if source=='tabela_1.csv' and 'name' in frame:
        frame=frame.drop(columns=['name']);omitted.append('name')
    # Start observation tables with the date, class and measured quantities.
    leading=[c for c in ['date','classe','band','window','label','evaluation_label','observed','predicted',
                        'value','filled','trend','seasonal','residual',
                        'B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12'] if c in frame]
    if not component:frame=frame[leading+[c for c in frame.columns if c not in leading]]
    if source=='configuracoes_internas.csv':
        configurations={0:'31 folhas / 20 exemplos / L2 1',1:'15 folhas / 20 exemplos / L2 1',
                        2:'15 folhas / 30 exemplos / L2 3',3:'7 folhas / 40 exemplos / L2 5'}
        frame['name']=frame['order'].map(configurations)
        frame=frame[['name']+[c for c in frame if c!='name']]
    if source=='coverage-13.csv':
        technical={'correlation_eigenvalues','covariance_eigenvalues','thresholds','noise_model'}
        omitted += [c for c in frame.columns if c in technical]
        frame=frame.drop(columns=list(technical & set(frame.columns)))
    original=list(frame.columns)
    for col in original:
        if col=='classe':frame[col]=frame[col].map(CLASSES)
        elif col in {'label','evaluation_label'}:frame[col]=frame[col].map(LABELS)
        elif col=='tile':frame[col]=frame[col].map(lambda x:f'{int(x):06}')
        elif col in {'observed','predicted'} and not component:
            frame[col]=frame[col].map({0:'NC',1:'C'})
        elif pd.api.types.is_bool_dtype(frame[col]):frame[col]=frame[col].map({True:'Sim',False:'Não'})
        elif col=='largest_class' or col=='domain_median_largest':
            if pd.api.types.is_numeric_dtype(frame[col]):frame[col]=frame[col].map(CLASSES)
    # Values remain typed; formatting is applied only when writing Excel.
    columns=['Configuração (folhas / mínimo / L2)' if source=='configuracoes_internas.csv' and c=='name' else label(c) for c in original]
    # Preserve native numeric values instead of applying display rounding.
    rows=[]
    for row in frame.itertuples(index=False,name=None):
        rows.append([None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v.isoformat() if isinstance(v,pd.Timestamp) else v for v in row])
    return dict(name=sheet,source=source,columns=columns,original_columns=original,rows=rows,omitted_columns=omitted,
                descriptions=[description(c) for c in original])

def prepare():
    books=[]
    for filename,spec in SPECS:
        tables=[]
        for sheet,source in spec:
            if source=='resumo_por_janela.csv':
                f=pd.read_csv(DATA/source,header=[0,1],index_col=0)
                f.columns=[label(a)+' — '+{'median':'mediana','min':'mínimo','max':'máximo'}[b] for a,b in f.columns]
                f=f.reset_index().rename(columns={f.index.name or 'index':'Janela sazonal'})
                t=dict(name=sheet,source=source,columns=f.columns.tolist(),original_columns=f.columns.tolist(),
                       rows=[[None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v for v in r] for r in f.itertuples(index=False,name=None)],
                       omitted_columns=[],descriptions=['Síntese entre as 30 séries na janela indicada.']*len(f.columns))
            else:t=table(pd.read_csv(DATA/source),sheet,source)
            tables.append(t)
        books.append(dict(filename=filename,tables=tables))
    components=pd.read_parquet(DATA/'componentes_270_ajustes.parquet')
    tables=[]
    for cl,name in CLASSES.items():
        tables.append(table(components[components.classe==cl].copy(),name,'componentes_270_ajustes.parquet',component=True))
    books.append(dict(filename='04_Componentes_temporais.xlsx',tables=tables))
    return books

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    for book in prepare():
        (a.output/(Path(book['filename']).stem+'.json')).write_text(json.dumps(book,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        print(book['filename'],sum(len(t['rows']) for t in book['tables']),'rows',flush=True)
