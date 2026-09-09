# 06_Oracle — Retena: previsão de evasão com Oracle Machine Learning *in-database*

Prova técnica de que o produto Retena (risco de evasão de alunos EAD a partir de logs do LMS) roda **inteiro dentro do Oracle**: ingestão, feature engineering, treino, scoring, JSON para API e consultas de dashboard — sem pipeline externo de ML. Tudo abaixo foi executado de verdade em um **Oracle AI Database 26ai Free (Release 23.26.3.0.0)** em Docker, e cada número citado tem um arquivo correspondente em `evidencias/` gerado por consulta ao banco no momento da coleta.

---

## 1. Por que Oracle (decisão estratégica)

| Motivo | O que muda para a Retena |
|---|---|
| **ML onde o dado já está** (OML: `DBMS_DATA_MINING`, `PREDICTION_*`) | Nenhum dado de aluno sai do banco da IES. Treino, scoring e explicação (`PREDICTION_DETAILS`) são SQL — auditáveis pelo DPO da instituição. |
| **Um só motor para tudo** (SQL Macro, JSON Duality View, `DBMS_SCHEDULER`, APEX, ORDS) | A mesma SQL Macro (`FN_FEATURES_SEMANAIS`) gera features de treino e de produção — zero *training/serving skew*. Reduz stack: sem Airflow, sem feature store, sem serviço de modelo. |
| **Caminho direto para o cliente EAD** | IES brasileiras de grande porte já rodam Oracle (acadêmico/financeiro). Retena entra como *schema* + APEX no ambiente que o cliente já opera — venda técnica mais curta. |
| **Custo zero para começar, escala pagando pelo uso** | Free 26ai local para desenvolver; Autonomous Database *Always Free* para o piloto; *pay-as-you-go* por OCPU/ECPU quando houver contrato. Mesmo código SQL/PLSQL nos três. |
| **Explicabilidade nativa** | Coeficientes do GLM (`DM$VD*`), importância de atributos do Random Forest (`DM$VA*`) e top-3 fatores por aluno via `PREDICTION_DETAILS` — o tutor vê *por que* o aluno está em risco. |

---

## 2. O que foi provado localmente (números reais das evidências)

Fonte: `evidencias/01_versao_banco.txt`, `02_contagens.txt`, `03_modelos_oml.txt`, `04_metricas.txt`, `05_scoring_amostra.csv`, `06_json_api_amostra.json`, `07_apex_consultas.txt`, `docker_ps.txt`, `docker_logs_trecho.txt`, `evidencias.html` e `evidencia_01..08.png`.

**Ambiente**
- `Oracle AI Database 26ai Free Release 23.26.3.0.0`, instância `FREE`, PDB `FREEPDB1`, container `oracle-free` (`gvenzl/oracle-free:slim-faststart`), porta 1521, opção *Advanced Analytics = TRUE*.
- Usuário de aplicação `STARTUP` com `DB_DEVELOPER_ROLE` (inclui `CREATE MINING MODEL`). Acesso por `python-oracledb` em modo *thin* (sem Instant Client).

**Dados** (`01_ddl.sql`, `carregar_eventos.py`)
- **684.723 eventos** do LMS carregados em `EVENTOS_LMS` (679.892 de alunos, **203 alunos distintos**, 15/01/2026 a 26/08/2026), 5 fases (10/12/10/11/8 capítulos). Colunas virtuais `NUM_FASE`, `CAPITULO`, `FLG_ALUNO` calculadas no banco.

**Feature engineering in-database** (`02_features_transicao.sql`, `03_features_semanais.sql`)
- `FEATURES_TRANSICAO_FASE`: 855 linhas (aluno × fase); rótulo *evadiu na próxima fase* = 10 / 6 / 16 / 13 evasões nas fases 1–4 (5,7 % / 3,4 % / 8,9 % / 7,8 %).
- `BASE_RISCO_SEMANAL`: **4.337 casos rotulados** (aluno × corte semanal, 27 domingos) via **SQL Macro de tabela** `FN_FEATURES_SEMANAIS`; alvo `INATIVO_21D`. Treino = 18 cortes < 01/06/2026 (2.682 casos, 11,6 % positivos); teste = 9 cortes ≥ 01/06 (1.655 casos, 23,4 % positivos) — **validação temporal**, não aleatória.

**Modelos OML** (`04_oml_modelos.sql` — `DBMS_DATA_MINING.CREATE_MODEL2`, `PREP_AUTO = ON`, treino em ~1 s cada)

| Modelo | Algoritmo | Alvo | Treino |
|---|---|---|---|
| `RETENA_INATIVO21_RF` (principal) | `ALGO_RANDOM_FOREST` (200 árvores, seed 42) | `INATIVO_21D` | `VW_TREINO_INATIVIDADE` |
| `RETENA_INATIVO21_GLM` (baseline) | `ALGO_GENERALIZED_LINEAR_MODEL` (logit, ridge, classes balanceadas) | `INATIVO_21D` | `VW_TREINO_INATIVIDADE` |
| `RETENA_TRANSICAO_GLM` | `ALGO_GENERALIZED_LINEAR_MODEL` | `EVADIU_PROXIMA_FASE` | transições 1→2, 2→3, 3→4 |

**Avaliação no conjunto de teste** (`06_avaliacao.sql` — `DBMS_DATA_MINING.COMPUTE_ROC`/`COMPUTE_LIFT` + contraprova em SQL puro)

| Modelo | AUC (COMPUTE_ROC) | AUC (SQL, Mann-Whitney) | Precisão @0,5 | Recall @0,5 | F1 | **Precisão top-20 %** | Matriz (TP/FP/FN/TN) |
|---|---|---|---|---|---|---|---|
| `RETENA_INATIVO21_RF` | **0,949** | 0,949 | 0,839 | 0,806 | 0,822 | **0,876** (290 de 331) | 312 / 60 / 75 / 1208 |
| `RETENA_INATIVO21_GLM` | 0,945 | 0,945 | 0,643 | 0,904 | 0,752 | 0,885 | 350 / 194 / 37 / 1074 |
| `RETENA_TRANSICAO_GLM` | 0,972 | 0,972 | 0,588 | 0,769 | 0,667 | 0,364 (12 de 13 capturados) | 10 / 7 / 3 / 146 |

- Faixas calibradas no teste (RF): **Alto ≥ 0,60 → 85,3 %** de inatividade observada (347 casos); Médio → 50,9 %; Baixo → 5,1 %.
- Lift do RF: decil 1 captura 42 % dos positivos (lift 4,2); decis 1–2 capturam 75 % (lift 3,7).
- Importância de atributos (RF, `DM$VA`): `DIAS_ATIVOS_28D` (29 %), `RECENCIA_DIAS` (18 %), `EVENTOS_28D` (13 %).

**Scoring, JSON e Duality View** (`05_scoring_views.sql`)
- `VW_RISCO_ALUNO_ATUAL`: `PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING *)` + `PREDICTION_DETAILS(..., 1, 3 USING *)` sobre o último corte; faixa Alto/Médio/Baixo; ação sugerida.
- `RISCO_ALUNO_SNAPSHOT` (203 alunos no corte 26/08/2026: **59 Alto, 15 Médio, 129 Baixo**) atualizado por `PRC_ATUALIZAR_RISCO`, agendado em `JOB_RETENA_SCORING_SEMANAL` (`DBMS_SCHEDULER`, segundas 06:00).
- `VW_RISCO_JSON`: payload único (`JSON_OBJECT` + `JSON_ARRAYAGG`, 89.871 bytes) pronto para ORDS/API Gateway.
- `RISCO_ALUNO_DV`: **JSON Relational Duality View funcionou na Free 26ai** — leitura de documento por aluno e **escrita** (`UPDATE ... JSON_TRANSFORM`) refletida na tabela relacional (log `05_scoring_views.log`, statements #12–#16).

**Consultas APEX** (`07_apex_ready.sql`, 5 consultas, todas executadas — `07_apex_consultas.txt`)
1. Fila de segunda-feira (25 alunos, com *por quê* e *o que fazer*);
2. Funil por fase (175 → 165 → 168 → 163 → 153 avançaram);
3. Mapa de atrito fase × capítulo (43 células);
4. **Receita em risco**: ticket parametrizado R$ 350/mês → R$ 22.347,82/mês (31,5 % da receita bruta de R$ 71.050) e R$ 134.086,89 no ciclo;
5. Reativações (9–10 % dos inativos voltam em 21 dias).

---

## 3. Estrutura

```
06_Oracle/
├── docker-compose.yml, .env.example      # Oracle Free 26ai (gvenzl) com healthcheck
├── sql/
│   ├── 01_ddl.sql                        # EVENTOS_LMS (colunas virtuais), DIM_FASE, DIM_TIPO_EVENTO
│   ├── 02_features_transicao.sql         # VW_/FEATURES_TRANSICAO_FASE (aluno x fase)
│   ├── 03_features_semanais.sql          # SQL Macro FN_FEATURES_SEMANAIS + BASE_RISCO_SEMANAL
│   ├── 04_oml_modelos.sql                # CREATE_MODEL2: RF + 2 GLM (views de treino/teste)
│   ├── 05_scoring_views.sql              # VW_RISCO_ALUNO_ATUAL, snapshot, job, VW_RISCO_JSON, RISCO_ALUNO_DV
│   ├── 06_avaliacao.sql                  # COMPUTE_ROC/LIFT, confusao, faixas, top-20 %, DM$V*
│   └── 07_apex_ready.sql                 # 5 consultas para o dashboard
├── scripts/
│   ├── executar_sql.py                   # runner .sql (SQL ';' / PL-SQL '/') com log
│   ├── carregar_eventos.py               # DDL + carga do parquet (executemany, 10k/lote)
│   ├── gerar_evidencias.py               # TXT/CSV/JSON + evidencias.html + evidencia_NN.png (Edge headless)
│   └── run_all.ps1                       # pipeline completo (0..8)
└── evidencias/                           # saidas reais + logs/ de cada execucao (inclusive tentativas com erro)
```

---

## 4. Como reproduzir em 5 comandos

Pré-requisitos: Docker Desktop, Python 3.13 (`pip install oracledb pandas pyarrow`), Microsoft Edge (só para os PNG), `08_Dados/logs_lms.parquet`.

```powershell
cd entrega\06_Oracle
docker compose up -d                                   # 1) sobe o Oracle Free 26ai (aguarde "healthy": docker compose ps)
python scripts\carregar_eventos.py --log evidencias\logs\carga_eventos.log         # 2) DDL + 684.723 eventos
2..7 | % { $f = Get-Item "sql\0$_*.sql"; python scripts\executar_sql.py $f --log "evidencias\logs\$($f.BaseName).log" }   # 3) features, modelos, scoring, avaliacao, APEX
python scripts\gerar_evidencias.py                     # 4) TXT/CSV/JSON + evidencias.html + PNG
start evidencias\evidencias.html                       # 5) conferir
```

Ou tudo de uma vez: `.\scripts\run_all.ps1` (`-SemCarga` pula a ingestão; `-SemPng` dispensa o Edge).

---

## 5. Caminho de produção (OCI)

1. **Autonomous AI Database Serverless — Always Free → pago.** Mesmo schema, mesmos scripts (OML já incluso). Always Free (2 ECPU/20 GB) cobre piloto com 1 IES; a partir do contrato, *auto scaling* por ECPU-hora. Backups, patches e TDE automáticos — argumento decisivo para o DPO da IES.
2. **OML Notebooks + AutoML UI**: re-treino comparativo (RF × GLM × SVM × XGBoost via `ALGO_XGBOOST`) e *drift* mensal sem sair do banco; o modelo campeão continua sendo consumido por `PREDICTION_PROBABILITY`.
3. **Select AI**: coordenador pergunta em linguagem natural ("quais alunos da Fase 3 ficaram sem acessar 10 dias?") sobre `RISCO_ALUNO_SNAPSHOT` / `EVENTOS_LMS`.
4. **APEX** (incluso no Autonomous): as 5 consultas do `07_apex_ready.sql` viram páginas (Interactive Report / Cards / Chart) com itens `:P1_TICKET_MENSAL`, `:P1_FAIXA_MINIMA`; `RISCO_ALUNO_DV` recebe o *status de atendimento* pelo app.
5. **OCI Object Storage + `DBMS_CLOUD.COPY_DATA`**: o LMS exporta logs (parquet/CSV) para um *bucket*; carga incremental substitui `carregar_eventos.py`; `DBMS_SCHEDULER` já agendado dispara o re-scoring.
6. **OCI Functions + API Gateway** (ou ORDS nativo): expõe `VW_RISCO_JSON` e a Duality View como REST autenticado (OAuth) para o LMS/CRM da IES.

### Local (Free 26ai) → Produção (Autonomous)

| Componente | Local (este pacote) | Produção (OCI Autonomous AI Database) |
|---|---|---|
| Banco | `gvenzl/oracle-free:slim-faststart`, 2 CPU, PDB `FREEPDB1` | Autonomous Serverless (Always Free → ECPU pago), *auto scaling*, TDE, backup automático |
| Ingestão | `carregar_eventos.py` (parquet → `executemany`) | `DBMS_CLOUD.COPY_DATA` / External Tables sobre Object Storage; carga incremental agendada |
| Features | Views + SQL Macro `FN_FEATURES_SEMANAIS` | Idênticas (mesmo SQL); opcional *materialized view* com refresh |
| Treino | `DBMS_DATA_MINING.CREATE_MODEL2` (RF, GLM) | Idêntico + OML AutoML / Notebooks para seleção e monitoramento de drift |
| Scoring | `PREDICTION_PROBABILITY` / `PREDICTION_DETAILS` em view + `DBMS_SCHEDULER` | Idêntico; job no Autonomous; *Data Guard* opcional |
| API/JSON | `VW_RISCO_JSON`, `RISCO_ALUNO_DV` (Duality View) | ORDS (incluso) ou OCI Functions + API Gateway com OAuth |
| Dashboard | Consultas prontas (`07_apex_ready.sql`) | APEX incluso no Autonomous; Select AI para perguntas em linguagem natural |
| Segurança | Usuário `STARTUP` com `DB_DEVELOPER_ROLE` | IAM/OCI Vault, Database Vault, *Data Safe* (mascaramento de PII) |
| Custo | R$ 0 | Always Free (piloto) → ~US$ 0,34/ECPU-h (pay-as-you-go) |

---

## 6. Limitações e observações honestas

- **Nomes dos modelos** diferem do plano inicial (`RETENA_RISCO_21D` / `RETENA_TRANSICAO_FASE`): o pacote usa `RETENA_INATIVO21_RF`, `RETENA_INATIVO21_GLM` e `RETENA_TRANSICAO_GLM` para deixar explícito algoritmo e alvo; a comparação RF × GLM está no `06_avaliacao.sql`.
- **Probabilidades do RF saturam em 0,9237** para alunos sem nenhum evento nos 28 dias (top-20 do `05_scoring_amostra.csv`): efeito esperado do voto de 200 árvores em casos "óbvios"; o desempate da fila usa `RECENCIA_DIAS` e o GLM como segunda opinião.
- **Shift de prevalência** entre treino (11,6 %) e teste (23,4 %) — o fim do ciclo concentra inatividade. AUC se mantém, mas a precisão por faixa deve ser recalibrada a cada re-treino (a view `VW_AVALIACAO_FAIXAS` já faz isso).
- **Modelo de transição tem poucos positivos** (32 no treino, 13 no teste): AUC 0,972 é promissora mas com intervalo largo; coeficientes não são estatisticamente significativos (`p > 0,05`). Em produção, acumular mais coortes antes de usar isoladamente.
- **Recursos testados na Free**: `COMPUTE_ROC`/`COMPUTE_LIFT`, SQL Macro de tabela, JSON Duality View, `DBMS_SCHEDULER` e `PREDICTION_DETAILS` funcionaram. Tropeços registrados em `evidencias/logs/*tentativa*`: `ORA-64630` (SQL Macro dentro de `WITH` não é suportada — reescrita), `MERGE` lento com `PREDICTION_DETAILS` inline (sessão encerrada aos 769 s — refeito com tabela intermediária), `ORA-00984` (`SQLERRM` direto em `INSERT`) e `ORA-00923` (alias `SHARE` é palavra reservada).
- O container das evidências foi iniciado sem o healthcheck do `docker-compose.yml` (por isso `Health=n/a` em `docker_ps.txt`); o compose fornecido já inclui o healthcheck. Fuso do banco é UTC (`SYSTIMESTAMP +00:00`); os TXT mostram também o horário local (-03:00).
- Dados: 203 alunos de uma única turma/ano (base sintética do desafio). Os números provam a **arquitetura e o fluxo**, não a generalização do modelo para outras IES.

---

## 7. Caminho OCI (v2)

Pacote "OCI-ready" em [`oci/`](oci/) — adaptado do EduRetain (equipe Retena); nenhum arquivo acima foi alterado:
1. [`oci/README.md`](oci/README.md) — runbook "Do Oracle Free local ao Autonomous AI Database em 60 minutos": Always Free, wallet mTLS × TLS, usuário `RETENA`, bucket + `DBMS_CLOUD.COPY_DATA`, scripts 01→08→02..07→09, `DBMS_SCHEDULER`, APEX, Select AI, e a tabela "executado nesta máquina × runbook".
2. [`oci/conexao.py`](oci/conexao.py) + [`oci/.env.example`](oci/.env.example) — conexão por variáveis de ambiente (Free local por padrão; Autonomous por wallet ou TLS); `python oci\conexao.py --teste` executado contra o Free local.
3. [`oci/exportar_para_object_storage.py`](oci/exportar_para_object_storage.py) — `EVENTOS_LMS` (ou o parquet) → CSV gzip → bucket via SDK `oci`; `--dry-run` executado: 684.723 linhas, 3,54 MiB, mesmo SHA-256 nas duas fontes.
4. [`oci/sql/08_dbms_cloud_ingestao.sql`](oci/sql/08_dbms_cloud_ingestao.sql) (só Autonomous — **não executado** aqui) e [`oci/sql/09_merge_risco_snapshot.sql`](oci/sql/09_merge_risco_snapshot.sql) (MERGE idempotente, executado 2× no Free local: 203 → 203 linhas, 0 duplicatas — [`oci/evidencia_merge.txt`](oci/evidencia_merge.txt)).
5. [`oci/executar_sql_oci.py`](oci/executar_sql_oci.py) — roda os `.sql` existentes com o runner original e a conexão do `conexao.py` (necessário para wallet mTLS), sem tocar em `scripts/executar_sql.py`.
