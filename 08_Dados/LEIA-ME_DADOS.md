# Dados

A base de logs do LMS (`Base-Anônima.xlsx` / `logs_lms.parquet`, 684.723 eventos de 203 alunos pseudonimizados) e os parquets derivados por evento **não estão neste repositório público**: pertencem à instituição parceira e foram usados com autorização apenas para o projeto acadêmico. Estão no pacote ZIP entregue na plataforma FIAP. Os artefatos agregados (métricas, figuras, `risco_alunos_atual.csv` com pseudônimos, dashboard) estão publicados.

Para reproduzir o pipeline, coloque `logs_lms.parquet` nesta pasta e rode `python 05_MVP/pipeline/run_all.py`.
