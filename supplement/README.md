# Reproduzir o material suplementar

Esta pasta reúne as tabelas de origem, os componentes, os métodos editáveis e os geradores do suplemento. O arquivo `rbc-supplement.zip` contém os documentos de leitura: PDF, planilhas Excel e figuras.

Na raiz do código, use o ambiente científico declarado em `requirements-win.lock` e instale as dependências adicionais:

```text
python -m pip install -r supplement/requirements-print.txt
python reproduzir_suplemento.py --output suplemento-regenerado
```

A pasta de saída deve ser nova. O comando confere as tabelas arquivadas, regenera as comparações, figuras, atlas, PDF e quatro planilhas Excel. Os originais permanecem preservados. Não são refeitos o treinamento do classificador nem os ajustes STL; os componentes e resultados arquivados fornecem as entradas.

Os métodos do PDF são incorporados de `fontes/metodos_suplementares_r12.pdf`. O arquivo DOCX correspondente permite edição. Uma alteração nesse texto exige exportar novamente o PDF dos métodos antes da montagem.

A montagem do PDF principal utiliza Times New Roman em `C:/Windows/Fonts`, conforme a composição do suplemento. A execução foi conferida no Windows. Os dados das planilhas são preparados por `preparar_planilhas.py`, que identifica explicitamente os campos técnicos mantidos apenas nas tabelas de origem. `exportar_planilhas.py` usa esses mesmos dados para escrever os arquivos Excel.

Código: MIT. Documentação e resultados dos autores: CC BY 4.0. Os produtos de terceiros conservam os termos descritos em `LICENSING.md`.
