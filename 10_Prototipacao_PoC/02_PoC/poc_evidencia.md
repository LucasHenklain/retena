# Prova de conceito — evidência (Parte 2)

## 1. Funcionalidade crítica implementada

**Cálculo do risco de evasão de cada aluno dentro do banco Oracle, a partir dos logs do LMS, com atualização semanal automática.** É a funcionalidade sem a qual não existe produto: a fila de segunda-feira, o painel da diretoria e a medição em R$ derivam dela.

O que roda, de ponta a ponta, no Oracle AI Database 26ai Free (Docker, imagem `gvenzl/oracle-free:slim-faststart`):

| Etapa | Script | O que faz | Medido |
|---|---|---|---|
| 1 | `06_Oracle/scripts/carregar_eventos.py` | lê o export do LMS (684.723 eventos, 203 alunos) e carrega `EVENTOS_LMS` via python-oracledb | 72 s (08/09) · 146 s (22/09) |
| 2 | `06_Oracle/sql/02_features_transicao.sql` | features por fase (quem inicia a fase seguinte) | 16 s |
| 3 | `06_Oracle/sql/03_features_semanais.sql` | base aluno-semana: recência, dias ativos, eventos em 7/14/28 dias, progresso, tendência | 89 s |
| 4 | `06_Oracle/sql/04_oml_modelos.sql` | `DBMS_DATA_MINING.CREATE_MODEL2`: Random Forest e GLM (inatividade 21 dias), GLM (transição) | 7 s · AUC 0,949 / 0,945 / 0,972 |
| 5 | `06_Oracle/sql/05_scoring_views.sql` | `PREDICTION_PROBABILITY` e `PREDICTION_DETAILS`; `RISCO_ALUNO_SNAPSHOT`; `PRC_ATUALIZAR_RISCO` (MERGE idempotente); views JSON e Duality View; `JOB_RETENA_SCORING_SEMANAL` (segunda 06:00) | 67 s · job em 23–24 s |
| 6 | `06_Oracle/sql/06_avaliacao.sql` | métricas no teste temporal (≥ jun/2026) | 4 s |
| 7 | `06_Oracle/sql/07_apex_ready.sql` | consultas prontas para o painel APEX | 6 s |

Resultado atual do snapshot (reexecutado em 23/09/2026 às 18:00, horário de Brasília):

```
Alunos pontuados: 203 · eventos até 26/08/2026 · Alto 59 · Médio 15 · Baixo 129
JOB_RETENA_SCORING_SEMANAL: SUCCEEDED em 23 s · agendamento FREQ=WEEKLY; BYDAY=MON; BYHOUR=6
Modelos: RETENA_INATIVO21_RF (RANDOM_FOREST), RETENA_INATIVO21_GLM, RETENA_TRANSICAO_GLM
```

Saída completa em `../../09_Kit_Banca_Final/dia_da_banca/ultimo_scoring.txt`.

## 2. Integração com banco de dados e API

- **Banco:** Oracle AI Database 26ai Free, usuário de aplicação `STARTUP`, PDB `FREEPDB1`; conexão `python-oracledb` em modo thin (sem Instant Client).
- **Exposição:** views `VW_RISCO_JSON` e Duality View (`RISCO_ALUNO_DV`) entregam o risco por aluno em JSON para APEX, ORDS e para o painel; consultas do `07_apex_ready.sql`.
- **Caminho para a nuvem (executado localmente, runbook para OCI):** `06_Oracle/oci/conexao.py` (conexão dual Free local / Autonomous com wallet), `exportar_para_object_storage.py` (CSV gzip, dry-run), `09_merge_risco_snapshot.sql` (executado 2 vezes sem duplicar), `08_dbms_cloud_ingestao.sql` (Object Storage + `DBMS_CLOUD.COPY_DATA`, aguarda conta OCI).

## 3. Como reproduzir em 10 minutos

```bash
cd entrega/06_Oracle
docker compose up -d                      # Oracle Free; aguardar "healthy" (~1 min)
python scripts/carregar_eventos.py        # carga (precisa do export em 08_Dados; ver LEIA-ME_DADOS.md)
python scripts/executar_sql.py sql/02_features_transicao.sql
python scripts/executar_sql.py sql/03_features_semanais.sql
python scripts/executar_sql.py sql/04_oml_modelos.sql
python scripts/executar_sql.py sql/05_scoring_views.sql
python scripts/executar_sql.py sql/06_avaliacao.sql
python scripts/executar_sql.py sql/07_apex_ready.sql
```

Scoring ao vivo depois disso: `09_Kit_Banca_Final/dia_da_banca/2_Scoring_ao_vivo.cmd` (25 s).

## 4. Evidências

| Arquivo | Conteúdo |
|---|---|
| `06_Oracle/evidencias/evidencias.html` e `evidencia_01..08.png` | prints com timestamps da execução original |
| `06_Oracle/evidencias/logs_reexecucao_2026-09-22/` | logs da reexecução completa do zero (0 erros) |
| `09_Kit_Banca_Final/dia_da_banca/ultimo_scoring.txt` | scoring ao vivo de 23/09/2026 |
| `05_MVP/outputs/RESULTADOS.md` | modelo de referência em Python (validação temporal) |
| `05_MVP/portabilidade_oulad/RESULTADOS_OULAD.md` | mesmo método no dataset público OULAD |

## 5. O que foi simulado (mock) e por quê

- **Registro do resultado do contato:** no protótipo fica no navegador (localStorage), para validar o fluxo com usuários antes de criar a tabela e a API. Vai para o banco na Fase 7.
- **Painel APEX:** ainda não publicado por falta de conta OCI; o dashboard HTML cumpre o papel na demonstração e as consultas do APEX já estão prontas no banco.
- **Entrevistas:** as 8 entrevistas da Fase 6 foram simuladas com personas sintéticas e estão rotuladas assim; os testes de usabilidade desta fase são reais (Parte 5).
