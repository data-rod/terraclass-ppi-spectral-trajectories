# Reprodução das trajetórias espectrais

Comece pelo notebook 00 ou pelo README.md. Os arquivos de referência e de entradas offline devem ser extraídos nesta pasta, formando `work/`. O documento DATA_FORMATS.md descreve os campos, unidades e identificadores.

O percurso rápido recalcula componentes e forças STL a partir dos representantes selecionados. O comando de modelagem refaz a avaliação agrupada e o classificador operacional com os candidatos e rótulos arquivados. O percurso completo também reconstrói máscaras e candidatos MNF–PPI; sua execução exige NumPy 2.1.3 com Intel MKL 2023.1.

Os comandos, arquivos de ambiente e saídas estão descritos no README.md. Consulte RELEASE_STATUS.json para identificar as verificações concluídas nesta versão. Os relatórios de execução distinguem a reprodução do modelo daquela que também recalcula MNF–PPI.

Os oito notebooks e suas versões HTML apresentam as etapas e os resultados. As figuras de impressão e o projeto QGIS estão em editorial_figures/. O suplemento contém a especificação dos métodos e as tabelas e componentes por banda e janela.

O código segue a licença MIT; a documentação e os dados autorais seguem CC BY 4.0. Os termos dos produtos de terceiros estão em LICENSING.md.
