# Retena no OCI — do Oracle Free local ao Autonomous AI Database em 60 minutos

Runbook para levar o pacote `06_Oracle` (que roda inteiro no **Oracle AI Database 26ai Free** em Docker) para o **Oracle Autonomous AI Database Serverless (Always Free)** na OCI, sem alterar nenhum script já entregue: os mesmos `sql/01..07` rodam nos dois ambientes; muda só a conexão, a ingestão (bucket + `DBMS_CLOUD`) e o que o Autonomous oferece de graça por cima (APEX, ORDS, Select AI, OML Notebooks).

Os passos de provisionamento, wallet, `~/.oci/config` e troubleshooting foram **adaptados do EduRetain (equipe Retena)** — `docs/provisionamento_oracle.md`, `db.py`, `oci_storage.py`, `scoring.py`, `.env.example` — para os nomes reais do Retena (`EVENTOS_LMS`, `VW_RISCO_ALUNO_ATUAL`, `RISCO_ALUNO_SNAPSHOT`, modelos `RETENA_*`).

> **Honestidade sobre o que foi executado.** Esta máquina não tem tenancy nem credenciais OCI (`~/.oci/config` ausente). Tudo o que depende da OCI está aqui como runbook e está marcado como **não executado**. O que pôde ser executado contra o Free local **foi executado** e a saída está colada neste arquivo (seções 3, 5, 7) e em [`evidencia_merge.txt`](evidencia_merge.txt). Resumo na [seção 11](#11-o-que-foi-executado-nesta-máquina--o-que-é-runbook).

---

## Arquivos desta pasta

| Arquivo | Para quê | Status |
|---|---|---|
| `README.md` | este runbook | — |
| `conexao.py` | resolve a conexão por `.env`/ambiente: **local** (Free, padrão) ou **autonomous** (wallet mTLS ou TLS); `get_connection()`; `--teste` | executado (local) |
| `.env.example` | variáveis dos dois modos + Object Storage, comentadas | — |
| `executar_sql_oci.py` | roda os `.sql` existentes com o runner original (`scripts/executar_sql.py`) mas com a conexão do `conexao.py` (necessário para wallet) | executado (local, script 09) |
| `exportar_para_object_storage.py` | `EVENTOS_LMS` (ou o parquet) → CSV gzip → bucket via SDK `oci`; `--dry-run` só gera o arquivo | executado (`--dry-run`) |
| `sql/08_dbms_cloud_ingestao.sql` | `DBMS_CLOUD.CREATE_CREDENTIAL` + `COPY_DATA` → `EVENTOS_LMS`; alternativa com tabela externa; job de ingestão | **não executado** (só Autonomous) |
| `sql/09_merge_risco_snapshot.sql` | MERGE idempotente `VW_RISCO_ALUNO_ATUAL` → `RISCO_ALUNO_SNAPSHOT` (+ `RISCO_ALUNO_HISTORICO` aluno + corte) | executado 2× (local) |
| `evidencia_merge.txt` | logs integrais das 2 execuções do 09 + verificação independente | gerado |

---

## 0. Antes de começar (5 min)

- Conta OCI (o *Always Free* não expira nem cobra) — [cloud.oracle.com](https://cloud.oracle.com/).
- Windows + Python 3.13 com `oracledb`, `oci`, `pandas`, `pyarrow` (já usados pelo pacote). Se instalar o `oci` de novo, use um **venv na pasta do projeto**: o pacote tem caminhos internos enormes e estoura o limite de 260 caracteres do Windows quando instalado no Python da Microsoft Store (lição do EduRetain).
- O pacote local funcionando (`docker compose up -d` em `06_Oracle`, `python oci\conexao.py --teste`).

Orçamento de tempo (o "60 minutos" do título):

| # | Etapa | min | # | Etapa | min |
|---|---|---|---|---|---|
| 1 | Provisionar Autonomous Always Free | 10 | 6 | Credencial + `COPY_DATA` (script 08) | 5 |
| 2 | Wallet / TLS + `.env` + `conexao.py --teste` | 5 | 7 | Scripts 01→08→02..07→09 | 10 |
| 3 | Usuário `RETENA` + privilégios | 5 | 8 | `DBMS_SCHEDULER` (já vem nos scripts) | 2 |
| 4 | Bucket + `~/.oci/config` + upload do CSV | 10 | 9 | APEX | 5 |
| 5 | (dentro do 4) | — | 10 | Select AI | 3 |

---

## 1. Local (Free) → Autonomous: o que muda

| Componente | Local — Oracle Free 26ai (este pacote) | Autonomous AI Database Serverless (Always Free → pago) |
|---|---|---|
| Banco | `gvenzl/oracle-free:slim-faststart`, PDB `FREEPDB1`, porta 1521, UTC | Serverless **23ai** (escolher na criação; 19c não tem Duality View), 1 OCPU (2 ECPU) / 20 GB no Always Free, TDE + backup + patch automáticos |
| Conexão | `STARTUP/Startup2026@localhost:1521/FREEPDB1` (thin) | `RETENA@<db>_high` com wallet mTLS (`ORACLE_WALLET_DIR`) **ou** connect string TLS (`protocol=tcps`, porta 1522) — `conexao.py` resolve os dois |
| Usuário | `STARTUP` + `DB_DEVELOPER_ROLE` | `RETENA` + `DB_DEVELOPER_ROLE`/`DWROLE` + `CREATE MINING MODEL` + `EXECUTE ON DBMS_CLOUD` (+ `DBMS_CLOUD_AI`, `OML_DEVELOPER`) — seção 3 |
| Ingestão | `scripts/carregar_eventos.py` (parquet → `executemany`, 10k/lote) | `exportar_para_object_storage.py` → bucket → **`sql/08`: `DBMS_CLOUD.COPY_DATA`** (ou tabela externa + carga incremental) |
| Features, modelos, avaliação, APEX-ready | `sql/02..04`, `06`, `07` | **idênticos** (OML já incluso no Autonomous) |
| Scoring | `sql/05` (`PRC_ATUALIZAR_RISCO`, MERGE na view) | idêntico + **`sql/09`** (staging + MERGE idempotente + histórico por corte) |
| Agendamento | `DBMS_SCHEDULER` (`JOB_RETENA_SCORING_SEMANAL`, seg 06:00) | mesmo job + `JOB_RETENA_INGESTAO_SEMANAL` (dom 23:00, script 08); fuso do scheduler ajustável |
| API/JSON | `VW_RISCO_JSON`, `RISCO_ALUNO_DV` (Duality View) | mesmas views expostas por **ORDS AutoREST** (incluso) — `GET /ords/retena/vw_risco_json/` |
| Dashboard | consultas prontas (`07_apex_ready.sql`) | **APEX incluso** (workspace `RETENA`, 5 páginas) — seção 9 |
| Linguagem natural | — | **Select AI** (`DBMS_CLOUD_AI`) sobre `RISCO_ALUNO_SNAPSHOT`/`EVENTOS_LMS` — seção 10 |
| Runner dos `.sql` | `scripts/executar_sql.py` | `oci/executar_sql_oci.py` (mesmo runner, conexão com wallet) |
| Segurança / custo | container local, R$ 0 | IAM, Vault, Data Safe; Always Free R$ 0 → pay-as-you-go por ECPU-hora |

---

## 2. Provisionar o Autonomous AI Database Always Free (10 min) — *não executado aqui*

Adaptado do passo 1 do EduRetain, com as armadilhas que a equipe já pagou para descobrir:

1. Console OCI → menu ☰ → **Oracle Database** → **Autonomous AI Database** (a primeira opção; *não* "Dedicated", "Globally Distributed" ou "Cloud@Customer" — essas não têm Always Free).
2. **Create Autonomous Database**:
   - **Compartment**: o do projeto (ou `root` para piloto).
   - **Display/Database name**: `retenadb`.
   - **Workload type**: *Data Warehouse* ou *Transaction Processing* — no Always Free os limites são iguais; **Deployment**: *Serverless*.
   - **Database version**: **23ai** (o `RISCO_ALUNO_DV` do `05_scoring_views.sql` é JSON Relational Duality View, 23ai+).
   - **Always Free**: **marque**. Se esquecer, o banco nasce *Paid* e não converte depois — só terminando e recriando (se seguir pago, ative *Auto start/stop* ou pare em **Actions → Stop**).
   - **Password** do `ADMIN`: guarde em cofre.
   - **Network access**: *Secure access from everywhere* para começar (restrinja por IP/VCN depois). Deixe **mTLS required** ligado — é o padrão e a wallet funciona sempre.
3. **Create** → aguarde *Available* (1–2 min).
4. Always Free: o banco **para sozinho após 7 dias sem uso** e é **terminado após 3 meses parado**. No piloto, o acesso semanal do coordenador ao APEX já conta como uso; em contrato pago isso não se aplica.

---

## 3. Conexão: wallet mTLS × TLS (5 min)

| | **Opção B — mTLS com wallet (recomendada)** | **Opção A — TLS sem wallet** |
|---|---|---|
| Quando funciona | sempre (padrão do Autonomous) | só com *mTLS required* desligado — e o botão só destrava com *Access type* restrito a IPs/VCN |
| O que baixar | **Database Connection → Mutual TLS → Download Wallet** (Instance Wallet, defina a senha) → extrair em `C:\wallets\retenadb` | nada: copie o **Connection String** da aba **TLS** |
| `.env` | `ORACLE_DSN=retenadb_high` + `ORACLE_WALLET_DIR=C:\wallets\retenadb` (+ `ORACLE_WALLET_PASSWORD` só se a wallet não tiver `ewallet.pem`) | `ORACLE_DSN=(description=...(protocol=tcps)(port=1522)...(service_name=..._retenadb_high...))` e `ORACLE_WALLET_DIR` vazio |
| Erro típico | `DPY-6005` → `ORACLE_WALLET_DIR` sem `tnsnames.ora`/`sqlnet.ora`/`cwallet.sso` | `DPY-6005`/`DPY-6000 Listener refused` → o banco ainda exige mTLS (2 bancos do EduRetain falharam assim; a wallet conectou de primeira) |
| Aliases | `_high` para carga/treino (paralelismo), `_medium`/`_low` para APEX/BI | idem, no `service_name` |

Passos: `copy oci\.env.example oci\.env`, comente o bloco *local*, descomente o bloco *autonomous* e preencha; depois:

```powershell
python oci\conexao.py --teste            # modo detectado automaticamente (ORACLE_MODO=auto)
python oci\conexao.py --mostrar          # só imprime a configuração resolvida (senha mascarada)
```

`conexao.py` segue o `db.py`/`config.py` do EduRetain (`_connect_kwargs` só adiciona `config_dir`/`wallet_location`/`wallet_password` quando há wallet), com duas diferenças: o modo **local é o padrão** (valores atuais do pacote, sem `.env`) e a `wallet_password` é opcional (wallets recentes trazem `ewallet.pem`). Variáveis já exportadas no ambiente têm prioridade sobre o `.env`; o `.env` é procurado em `--env`, `ORACLE_ENV_FILE`, `oci/.env`, `06_Oracle/.env`.

**Executado nesta máquina (Free local, 2026-09-09):**

```
> python oci\conexao.py --teste
[conexao] .env: nenhum encontrado (usando ambiente/padroes locais)
[conexao] modo=local user=STARTUP password=*** dsn=localhost:1521/FREEPDB1
[conexao] conectado em 0.06s | oracledb 4.0.2 (thin=True)
[banner] Oracle AI Database 26ai Free Release 23.26.3.0.0 - Develop, Learn, and Run for Free | Version 23.26.3.0.0
[sessao] usuario=STARTUP container=FREEPDB1 service=freepdb1 host=c5e7ee510d1a systimestamp=2026-09-09 13:52:35 +00:00 dbtimezone=+00:00
[roles]  DB_DEVELOPER_ROLE
[tabela] EVENTOS_LMS: 684.723 linhas
[tabela] RISCO_ALUNO_SNAPSHOT: 203 linhas
[oml]    3 modelo(s): RETENA_INATIVO21_GLM (GENERALIZED_LINEAR_MODEL, CLASSIFICATION); RETENA_INATIVO21_RF (RANDOM_FOREST, CLASSIFICATION); RETENA_TRANSICAO_GLM (GENERALIZED_LINEAR_MODEL, CLASSIFICATION)
[conexao] OK
```

O mesmo comando em modo *autonomous* **não foi executado** (sem tenancy).

---

## 4. Criar o usuário `RETENA` (5 min) — *não executado aqui*

Como `ADMIN`, em **Database Actions → SQL** (não use o `ADMIN` no dia a dia — mesma regra do EduRetain):

```sql
CREATE USER RETENA IDENTIFIED BY "TroqueEstaSenha#2026";
GRANT DB_DEVELOPER_ROLE TO RETENA;          -- 23ai: mesmo papel do STARTUP no Free (CREATE SESSION/TABLE/VIEW/PROCEDURE/JOB/...)
-- GRANT DWROLE TO RETENA;                  -- se o banco for 19c (DB_DEVELOPER_ROLE nao existe)
GRANT CREATE MINING MODEL TO RETENA;        -- OML: DBMS_DATA_MINING.CREATE_MODEL2 (04_oml_modelos.sql)
GRANT EXECUTE ON DBMS_CLOUD TO RETENA;      -- 08: CREATE_CREDENTIAL / COPY_DATA / CREATE_EXTERNAL_TABLE
GRANT EXECUTE ON DBMS_CLOUD_AI TO RETENA;   -- Select AI (secao 10)
GRANT OML_DEVELOPER TO RETENA;              -- OML Notebooks / AutoML UI (opcional)
ALTER USER RETENA QUOTA UNLIMITED ON DATA;
-- REST (ORDS) e APEX/OML UI para o schema:
BEGIN
  ORDS_ADMIN.ENABLE_SCHEMA(p_enabled => TRUE, p_schema => 'RETENA',
                           p_url_mapping_type => 'BASE_PATH', p_url_mapping_pattern => 'retena', p_auto_rest_auth => TRUE);
END;
/
```

Depois, em **Database Actions → Database Users → RETENA → Edit**: ligar **Web Access** e **OML** (habilita SQL worksheet, REST e OML Notebooks para o usuário). Atualize `ORACLE_USER=RETENA` / `ORACLE_PASSWORD` no `.env`.

---

## 5. Object Storage: bucket, `~/.oci/config` e upload do CSV (10 min)

### 5.1 Bucket — *não executado aqui*
Menu ☰ → **Storage → Buckets** → confira o *Compartment* → **Create Bucket** `retena-lms` (Standard, privado) → anote o **Object Storage Namespace** no topo da página → `OCI_NAMESPACE`/`OCI_BUCKET_NAME` no `.env`. (Ou deixe o script criar: `--criar-bucket`, usando `OCI_COMPARTMENT_OCID` ou a tenancy.)

### 5.2 `~/.oci/config` (autenticação do SDK) — *não executado aqui*
Igual ao passo 0.2 do EduRetain: `oci setup config` (CLI) **ou** gerar o par de chaves em Python (`cryptography`, já vem com o `oci`) e colar a chave pública em **My Profile → API Keys → Add API Key → Paste Public Key** (com as linhas `BEGIN/END PUBLIC KEY`, senão dá "Invalid public key header or footer"). A OCI mostra o *Configuration File Preview* pronto — salve como `~/.oci/config` (`[DEFAULT]`, `user`, `fingerprint`, `tenancy`, `region=sa-saopaulo-1`, `key_file`). Policy mínima do grupo do usuário: `Allow group RetenaDB to manage objects in compartment <comp> where target.bucket.name='retena-lms'`.

### 5.3 Exportar e subir — `--dry-run` **executado**, upload *não executado*

```powershell
python oci\exportar_para_object_storage.py --dry-run                 # só gera %TEMP%\retena_oci\eventos_lms_<ts>.csv.gz
python oci\exportar_para_object_storage.py --dry-run --fonte parquet # fallback sem banco (08_Dados\logs_lms.parquet)
python oci\exportar_para_object_storage.py --criar-bucket            # gera + envia (exige ~/.oci/config)
python oci\exportar_para_object_storage.py --desde 2026-08-01        # incremental (TS_EVENTO >= data)
python oci\exportar_para_object_storage.py --listar                  # lista o prefixo eventos_lms/ no bucket
```

O CSV sai exatamente no formato que o `08_dbms_cloud_ingestao.sql` espera: UTF-8, cabeçalho, `,`, aspas duplas, `TS_EVENTO` em `YYYY-MM-DD HH24:MI:SS`, gzip (`mtime=0`, então o mesmo conteúdo dá o mesmo SHA-256), só as 9 colunas físicas (`ID_EVENTO` é IDENTITY; `NUM_FASE`/`CAPITULO`/`FLG_ALUNO` são virtuais). O upload usa `oci.object_storage.UploadManager` (multipart automático) e imprime a URI pronta para o `COPY_DATA`. A listagem paginada (`next_start_with`) vem do `oci_storage.py` do EduRetain.

**Executado nesta máquina (2026-09-09):**

```
> python oci\exportar_para_object_storage.py --dry-run
[cfg] .env=nenhum | modo=local user=STARTUP password=*** dsn=localhost:1521/FREEPDB1 | bucket=retena-lms prefixo=eventos_lms/
[fonte] oracle:EVENTOS_LMS
[csv] arquivo : C:\Users\lmhsilva\AppData\Local\Temp\retena_oci\eventos_lms_20260909_112234.csv.gz
[csv] tamanho : 3.707.061 bytes (3.54 MiB, gzip)
[csv] linhas  : 684.723 de dados + 1 cabecalho | releitura: 684.723 (ok=True)
[csv] sha256  : 4b6335b89ce89d8d5bc8acafda8589dc43668f2e7f04633cd0fcd58ae219b664
[csv] colunas : FASE,TS_EVENTO,NOME,USUARIO_AFETADO,CONTEXTO,COMPONENTE,EVENTO,DESCRICAO,ORIGEM | TS_EVENTO='%Y-%m-%d %H:%M:%S' | gerado em 4.6s
[dry-run] nada enviado a OCI. Para enviar: remova --dry-run (exige ~/.oci/config).

> python oci\exportar_para_object_storage.py --dry-run --fonte parquet
[fonte] parquet:C:\Users\lmhsilva\Projetos\StartupOne\entrega\08_Dados\logs_lms.parquet
[csv] tamanho : 3.707.061 bytes (3.54 MiB, gzip)
[csv] linhas  : 684.723 de dados + 1 cabecalho | releitura: 684.723 (ok=True)
[csv] sha256  : 4b6335b89ce89d8d5bc8acafda8589dc43668f2e7f04633cd0fcd58ae219b664
```

As duas fontes geram um arquivo **byte a byte idêntico** (mesmo SHA-256): a carga local do `carregar_eventos.py` é fiel ao parquet, e o mesmo CSV serve para o Autonomous.

---

## 6. `DBMS_CLOUD`: credencial e `COPY_DATA` (5 min) — *não executado aqui*

`DBMS_CLOUD` **não existe no Free local** (verificado: `SELECT owner FROM all_objects WHERE object_name='DBMS_CLOUD'` → 0 linhas), por isso [`sql/08_dbms_cloud_ingestao.sql`](sql/08_dbms_cloud_ingestao.sql) é o único script que **só roda no Autonomous**. O que ele faz, na ordem:

1. `DBMS_CLOUD.CREATE_CREDENTIAL('RETENA_OBJ_STORE_CRED', username, password)` — `password` é um **Auth Token** (My Profile → Auth tokens → Generate), não a senha do console. Alternativa sem segredo no SQL: `DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL(username => 'RETENA')` (ADMIN) + dynamic group/policy e `credential_name => 'OCI$RESOURCE_PRINCIPAL'`.
2. `DBMS_CLOUD.LIST_OBJECTS` no prefixo — teste de acesso (falhou aqui = credencial/policy/URI).
3. `TRUNCATE EVENTOS_LMS` + **`DBMS_CLOUD.COPY_DATA`** com `file_uri_list` `.../o/eventos_lms/eventos_lms_*.csv.gz` (wildcard), `field_list` = 9 colunas físicas, `format` JSON `{"type":"csv","delimiter":",","skipheaders":1,"quote":"\"","dateformat":"YYYY-MM-DD HH24:MI:SS","compression":"gzip","blankasnull":true,"rejectlimit":1000,...}`.
4. Verificação em `USER_LOAD_OPERATIONS` (status, `rows_loaded`, tabelas `COPY$n_LOG`/`_BAD`) e contagem esperada: **684.723 eventos, 204 nomes distintos (203 alunos + `-`), 2026-01-15 → 2026-08-26**; `DBMS_STATS`.
5. **Alternativa**: `DBMS_CLOUD.CREATE_EXTERNAL_TABLE` (`EVENTOS_LMS_EXT` lê o bucket sem copiar) + `VALIDATE_EXTERNAL_TABLE` + `INSERT ... WHERE TS_EVENTO > MAX(TS_EVENTO)` (carga incremental idempotente).
6. `PRC_INGERIR_EVENTOS_OCI` + `JOB_RETENA_INGESTAO_SEMANAL` (domingo 23:00) — ingere o incremento antes do re-scoring de segunda.

Substitua `<REGIAO>`, `<NAMESPACE>`, `<BUCKET>`, `<usuario_oci>`, `<auth_token>` (o `exportar_para_object_storage.py` imprime a URI exata após o upload). O script foi **conferido pelo divisor de statements do runner** (16 statements: 7 blocos PL/SQL, 7 `SELECT`, `TRUNCATE`, `INSERT`, `COMMIT`), mas **não executado**.

---

## 7. Executar os scripts na ordem (10 min)

No Autonomous a ordem muda em um ponto: o **08 substitui o `carregar_eventos.py`** e roda logo depois do DDL. Tudo pelo mesmo runner, com a conexão do `conexao.py`:

```powershell
cd entrega\06_Oracle
python oci\conexao.py --teste                                     # tem que mostrar modo=autonomous, usuario=RETENA
python oci\executar_sql_oci.py `
    sql\01_ddl.sql `                                              # EVENTOS_LMS, DIM_FASE, DIM_TIPO_EVENTO
    oci\sql\08_dbms_cloud_ingestao.sql `                          # bucket -> EVENTOS_LMS (684.723 linhas)
    sql\02_features_transicao.sql sql\03_features_semanais.sql `  # features (SQL Macro FN_FEATURES_SEMANAIS)
    sql\04_oml_modelos.sql `                                      # RETENA_INATIVO21_RF / _GLM / RETENA_TRANSICAO_GLM
    sql\05_scoring_views.sql `                                    # VW_RISCO_ALUNO_ATUAL, RISCO_ALUNO_SNAPSHOT, job, JSON, Duality View
    sql\06_avaliacao.sql sql\07_apex_ready.sql `                  # metricas + 5 consultas do dashboard
    oci\sql\09_merge_risco_snapshot.sql `                         # MERGE idempotente + historico por corte
    --log-dir oci\logs_autonomous --parar-no-erro
```

Esperado (mesmos números das evidências locais, seção 2 do `../README.md`): 684.723 eventos; 4.337 casos rotulados; 3 modelos; AUC 0,949 (RF); snapshot com 203 alunos (59 Alto / 15 Médio / 129 Baixo). *Não executado no Autonomous.*

### 7.1 `sql/09_merge_risco_snapshot.sql` — **executado 2× no Free local**

Padrão do `scoring.py` do EduRetain (stage → `MERGE ... ON (chave natural)` → `dt_processamento`), adaptado depois de inspecionar `USER_TAB_COLS`/`USER_CONSTRAINTS` (a inspeção é reimpressa no início do script como evidência):

- **`RISCO_ALUNO_STG`**: materializa `VW_RISCO_ALUNO_ATUAL` **uma vez** (`PREDICTION_PROBABILITY` + `PREDICTION_DETAILS` sobre 684.723 eventos, ~17 s) — lição do log `05_scoring_views_tentativa2_merge_lento.log`.
- **MERGE 1 → `RISCO_ALUNO_SNAPSHOT` `ON (NOME)`**: a PK real é `NOME` (estado atual, 1 linha por aluno). Preserva `STATUS_ATENDIMENTO`/`OBSERVACAO` do coordenador; `REATIVADO` que volta a `Alto` reabre como `PENDENTE`.
- **MERGE 2 → `RISCO_ALUNO_HISTORICO` `ON (NOME, DT_CORTE)`**: a chave natural **aluno + corte** (equivalente a `id_student + code_module + code_presentation + cutoff_days`), com `MODELO_VERSAO` (`RETENA_INATIVO21_RF@2026-09-08`, de `USER_MINING_MODELS`) e `DT_PROCESSAMENTO`. Tabela nova — o pacote v1 não guardava histórico.
- **MERGE 3** (só `UPDATE`) aplica o modelo de transição de fase.

```
Execução 1  13:58:49 → 13:59:10 UTC   MERGE snapshot 203 | historico 203 | transicao 203   SNAPSHOT 203 linhas/203 chaves   HISTORICO 203/203   duplicatas 0/0
Execução 2  13:59:11 → 13:59:33 UTC   MERGE snapshot 203 | historico 203 | transicao 203   SNAPSHOT 203 linhas/203 chaves   HISTORICO 203/203   duplicatas 0/0
Faixas: Alto 59 (prob. média 0,8444) | Médio 15 (0,4719) | Baixo 129 (0,0539)
```

Logs integrais, timestamps do banco (UTC) e do runner (local) e a verificação independente em [`evidencia_merge.txt`](evidencia_merge.txt).

---

## 8. Agendar com `DBMS_SCHEDULER` (2 min) — *no Autonomous: não executado*

Nada novo a instalar: `05_scoring_views.sql` já cria **`JOB_RETENA_SCORING_SEMANAL`** (`PRC_ATUALIZAR_RISCO`, `FREQ=WEEKLY; BYDAY=MON; BYHOUR=6`) e o `08` cria **`JOB_RETENA_INGESTAO_SEMANAL`** (`PRC_INGERIR_EVENTOS_OCI`, domingo 23:00). Os dois já rodaram/foram criados no Free local (o primeiro está em `user_scheduler_jobs`, estado `SCHEDULED`). No Autonomous, só dois cuidados:

```sql
-- o banco e o scheduler ficam em UTC; para "segunda 06:00" ser horario de Brasilia (ADMIN, uma vez):
BEGIN DBMS_SCHEDULER.SET_SCHEDULER_ATTRIBUTE('default_timezone', 'America/Sao_Paulo'); END;
/
SELECT job_name, state, enabled, TO_CHAR(next_run_date, 'YYYY-MM-DD HH24:MI TZR') proxima, run_count, failure_count
  FROM user_scheduler_jobs WHERE job_name LIKE 'JOB_RETENA%';
SELECT job_name, status, TO_CHAR(actual_start_date, 'YYYY-MM-DD HH24:MI') inicio, run_duration, error#
  FROM user_scheduler_job_run_details WHERE job_name LIKE 'JOB_RETENA%' ORDER BY actual_start_date DESC FETCH FIRST 10 ROWS ONLY;
```

Always Free: o job só roda com o banco *Available* (ver seção 2, item 4). Para re-pontuar sob demanda: `BEGIN PRC_ATUALIZAR_RISCO; END;` ou `python oci\executar_sql_oci.py oci\sql\09_merge_risco_snapshot.sql`.

---

## 9. Publicar no APEX (5 min) — *não executado aqui*

1. Página do banco → **Tool configuration → APEX → Open** (ou Database Actions → APEX) → entre no workspace `INTERNAL` como `ADMIN` → **Create Workspace → Existing schema** `RETENA` → workspace `RETENA`, usuário admin do workspace.
2. Entre no workspace `RETENA` → **App Builder → Create → New Application** "Retena" → adicione as páginas com as consultas de [`../sql/07_apex_ready.sql`](../sql/07_apex_ready.sql):

| Página | Tipo APEX | Consulta do 07 | Itens |
|---|---|---|---|
| Fila de segunda-feira | Interactive Report sobre `RISCO_ALUNO_SNAPSHOT` (ordem `PROB_INATIVO_21D DESC`) | 1 | `:P1_FAIXA_MINIMA` (Alto/Médio) |
| Funil por fase | Chart (bar) | 2 | — |
| Mapa de atrito fase × capítulo | Chart (heat map) ou Classic Report com cor por célula | 3 | — |
| Receita em risco | Cards/KPI | 4 | `:P1_TICKET_MENSAL` (número, padrão 350) |
| Reativações | Classic Report | 5 | — |
| Atendimento do aluno | Form sobre `RISCO_ALUNO_SNAPSHOT` (`STATUS_ATENDIMENTO`, `OBSERVACAO`) — ou via `RISCO_ALUNO_DV` REST | — | — |

3. **Shared Components → Authentication**: APEX Accounts no piloto; OCI IAM/SSO da IES no contrato.
4. REST para o LMS/CRM: **Database Actions → REST → AutoREST** em `VW_RISCO_JSON` e `RISCO_ALUNO_DV` → `GET https://<host>/ords/retena/vw_risco_json/` (OAuth2 client credentials em **REST → Security → OAuth Clients**).

---

## 10. Habilitar Select AI (3 min) — *não executado aqui*

```sql
-- ADMIN, uma vez: permite ao banco assumir identidade propria na OCI (sem chave/API key no SQL)
BEGIN DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL(username => 'RETENA'); END;
/
-- IAM: dynamic group RetenaADB { resource.id = '<OCID do Autonomous>' } e policy
--      Allow dynamic-group RetenaADB to use generative-ai-family in compartment <comp>

-- RETENA: perfil sobre as tabelas do produto (OCI Generative AI, regiao com o servico, ex. sa-saopaulo-1)
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'RETENA_AI',
    attributes   => '{"provider": "oci",
                      "credential_name": "OCI$RESOURCE_PRINCIPAL",
                      "oci_compartment_id": "<OCID do compartment>",
                      "object_list": [{"owner": "RETENA", "name": "RISCO_ALUNO_SNAPSHOT"},
                                      {"owner": "RETENA", "name": "RISCO_ALUNO_HISTORICO"},
                                      {"owner": "RETENA", "name": "EVENTOS_LMS"},
                                      {"owner": "RETENA", "name": "DIM_FASE"}],
                      "comments": true}');
  DBMS_CLOUD_AI.SET_PROFILE('RETENA_AI');
END;
/
-- no SQL worksheet / SQLcl (a sessao precisa do profile setado):
SELECT AI quais alunos da Fase 3 estao em risco Alto e sem acessar ha mais de 10 dias;
SELECT AI showsql quantos alunos por faixa de risco no ultimo corte;
-- via python-oracledb / APEX (sem a sintaxe SELECT AI):
SELECT DBMS_CLOUD_AI.GENERATE(prompt => 'quantos alunos estao em risco Alto', profile_name => 'RETENA_AI', action => 'runsql') FROM dual;
```

Os `COMMENT ON` do `01_ddl.sql` (`EVENTOS_LMS.NOME`, `CAPITULO`, ...) são lidos pelo Select AI (`"comments": true`) e melhoram o SQL gerado. Para OpenAI/Azure/Cohere em vez de OCI GenAI: `DBMS_CLOUD.CREATE_CREDENTIAL` com a API key + `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE` para o host do provedor.

---

## 11. O que foi executado nesta máquina × o que é runbook

| Item | Executado aqui (Free local, 2026-09-09) | Runbook (Autonomous/OCI) — **não executado** |
|---|---|---|
| Conexão | `conexao.py --teste` em modo local: banner 26ai Free 23.26.3.0.0, `SYSTIMESTAMP 2026-09-09 13:52:35 +00:00`, 684.723 eventos, 203 no snapshot, 3 modelos OML | `conexao.py` em modo autonomous (wallet/TLS) |
| Export CSV | `exportar_para_object_storage.py --dry-run` (Oracle **e** parquet): 684.723 linhas, 3.707.061 bytes, SHA-256 `4b6335b8…` idêntico nas duas fontes | upload ao bucket (`~/.oci/config` ausente nesta máquina), `--criar-bucket`, `--listar` |
| Ingestão | inspeção do DDL/colunas de `EVENTOS_LMS`; confirmação de que `DBMS_CLOUD` não existe no Free; parse do `08` pelo runner (16 statements) | `08_dbms_cloud_ingestao.sql`: `CREATE_CREDENTIAL`, `LIST_OBJECTS`, `COPY_DATA`, tabela externa, `PRC_INGERIR_EVENTOS_OCI`, `JOB_RETENA_INGESTAO_SEMANAL` |
| MERGE | `09_merge_risco_snapshot.sql` **2×** via `executar_sql_oci.py`: 19/19 statements ok, 203 → 203 linhas em `RISCO_ALUNO_SNAPSHOT` e `RISCO_ALUNO_HISTORICO`, 0 duplicatas ([`evidencia_merge.txt`](evidencia_merge.txt)) | mesmo script no Autonomous |
| Scripts 01–07 | já executados na v1 (evidências em `../evidencias/`) | reexecução no Autonomous na ordem 01 → 08 → 02..07 → 09 |
| Scheduler | `JOB_RETENA_SCORING_SEMANAL` existente e `SCHEDULED` no Free | fuso `America/Sao_Paulo`; `JOB_RETENA_INGESTAO_SEMANAL` |
| Provisionamento, usuário `RETENA`, bucket, APEX, ORDS, Select AI | — | seções 2, 4, 5.1–5.2, 9, 10 |

Objetos criados no Free local por esta entrega (não alteram nenhum objeto da v1): tabelas `RISCO_ALUNO_STG` e `RISCO_ALUNO_HISTORICO`.

---

## 12. Troubleshooting (herdado do EduRetain, ajustado)

- **`DPY-6005` / `DPY-6000: Listener refused connection` (~`ORA-12506`) com TLS sem wallet** → o banco exige mTLS. Não insista: baixe a wallet (Opção B). Outras causas: banco parado (Always Free hiberna) ou *Network access* restrito.
- **`DPY-6005` com wallet** → `ORACLE_WALLET_DIR` precisa conter `tnsnames.ora`, `sqlnet.ora`, `cwallet.sso`/`ewallet.pem`; `conexao.py` já avisa se falta o `tnsnames.ora`.
- **`ORA-01017`** → usuário/senha; a rede já aceitou a conexão.
- **`ORA-20401: Authorization failed` / `ORA-20404: Object not found` no `COPY_DATA`** → Auth Token errado/expirado, policy IAM sem `read objects`, ou URI com namespace/bucket/prefixo errados (teste primeiro com `DBMS_CLOUD.LIST_OBJECTS`).
- **`COPY_DATA` com `status = FAILED`** → `SELECT * FROM <badfile_table>`; causa comum é `dateformat` diferente do CSV (aqui: `YYYY-MM-DD HH24:MI:SS`) ou `rejectlimit` baixo.
- **`ModuleNotFoundError: No module named 'oci.retry'`** → pacote `oci` instalado pela metade (limite de 260 caracteres do Windows). Reinstale dentro de um venv na pasta do projeto.
- **`ORA-64630` (SQL Macro em `WITH`), `ORA-00984`, `ORA-00923`** → já contornados nos scripts v1 (ver `../README.md`, seção 6); não reaparecem no Autonomous.
- **`RISCO_ALUNO_DV` falha no Autonomous** → banco 19c; Duality View exige 23ai. Todo o resto do pacote funciona em 19c.
