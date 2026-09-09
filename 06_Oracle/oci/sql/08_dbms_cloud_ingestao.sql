-- =============================================================================
-- 08_dbms_cloud_ingestao.sql - Ingestao de EVENTOS_LMS a partir do OCI Object Storage (DBMS_CLOUD)
-- Projeto Retena | adaptado do EduRetain (equipe Retena): la a carga era Python (oci_storage.py -> pandas ->
--   executemany); aqui o PROPRIO BANCO puxa o CSV do bucket (nenhum dado passa pela maquina do operador).
--
-- *** EXECUTA APENAS NO AUTONOMOUS AI DATABASE ***
--   DBMS_CLOUD nao existe no Oracle Free local (verificado em 2026-09-09 no container oracle-free:
--   SELECT owner FROM all_objects WHERE object_name = 'DBMS_CLOUD' -> 0 linhas). Este script NAO foi executado
--   nesta maquina (sem tenancy/credenciais OCI) - e runbook, com a sintaxe conferida na documentacao do DBMS_CLOUD.
--
-- Pre-requisitos:
--   1. sql/01_ddl.sql executado no Autonomous (EVENTOS_LMS com IDENTITY + colunas virtuais);
--   2. arquivo(s) eventos_lms_*.csv.gz no bucket (gerados por oci/exportar_para_object_storage.py):
--      UTF-8, cabecalho, delimitador ",", aspas duplas, TS_EVENTO 'YYYY-MM-DD HH24:MI:SS', gzip;
--   3. usuario RETENA com EXECUTE ON DBMS_CLOUD (README passo 3) e um Auth Token OCI (ou Resource Principal).
-- Substitua: <REGIAO> (ex.: sa-saopaulo-1), <NAMESPACE>, <BUCKET> (ex.: retena-lms), <usuario_oci>, <auth_token>.
-- Convencao do runner (scripts/executar_sql.py): SQL termina com ";", PL/SQL com "/" em linha propria.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0) Credencial de acesso ao Object Storage
--    Opcao A - Auth Token do usuario OCI (Console > icone do usuario > My Profile > Auth tokens > Generate token).
--    O usuario precisa de policy IAM de leitura no bucket, ex.:
--      Allow group RetenaDB to read objects in compartment <comp> where target.bucket.name='<BUCKET>'
-- ---------------------------------------------------------------------------
BEGIN
  BEGIN
    DBMS_CLOUD.DROP_CREDENTIAL(credential_name => 'RETENA_OBJ_STORE_CRED');
  EXCEPTION WHEN OTHERS THEN NULL;   -- nao existia
  END;
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'RETENA_OBJ_STORE_CRED',
    username        => '<usuario_oci>',    -- ex.: nome@dominio.com ou oracleidentitycloudservice/nome@dominio.com
    password        => '<auth_token>');    -- Auth Token (NAO e a senha do console; 32 caracteres)
  DBMS_OUTPUT.PUT_LINE('Credencial RETENA_OBJ_STORE_CRED criada');
END;
/

--    Opcao B - Resource Principal (sem segredo no SQL). Como ADMIN, uma unica vez:
--      BEGIN DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL(username => 'RETENA'); END;
--    + no IAM: dynamic group com a regra  resource.id = '<OCID do Autonomous>'  e policy
--      Allow dynamic-group RetenaADB to read objects in compartment <comp>
--    Depois use credential_name => 'OCI$RESOURCE_PRINCIPAL' nas chamadas abaixo.

SELECT credential_name, username, enabled FROM user_credentials WHERE credential_name = 'RETENA_OBJ_STORE_CRED';

-- ---------------------------------------------------------------------------
-- 1) Teste de acesso: lista os objetos do prefixo (falha aqui = credencial/policy/URI errados)
-- ---------------------------------------------------------------------------
SELECT object_name, bytes, last_modified
  FROM DBMS_CLOUD.LIST_OBJECTS('RETENA_OBJ_STORE_CRED',
         'https://objectstorage.<REGIAO>.oraclecloud.com/n/<NAMESPACE>/b/<BUCKET>/o/eventos_lms/')
 ORDER BY last_modified DESC;

-- ---------------------------------------------------------------------------
-- 2) Carga FULL: TRUNCATE + DBMS_CLOUD.COPY_DATA (substitui scripts/carregar_eventos.py)
--    field_list = colunas fisicas na ordem do CSV. ID_EVENTO (IDENTITY) e NUM_FASE/CAPITULO/FLG_ALUNO (virtuais)
--    ficam de fora: o banco calcula. Wildcard eventos_lms_*.csv.gz carrega todos os arquivos do prefixo.
--    format (JSON): delimiter, skipheaders, quote, dateformat, compression, rejectlimit -> casa 1:1 com o
--    CSV do exportar_para_object_storage.py.
-- ---------------------------------------------------------------------------
TRUNCATE TABLE EVENTOS_LMS;

BEGIN
  DBMS_CLOUD.COPY_DATA(
    table_name      => 'EVENTOS_LMS',
    credential_name => 'RETENA_OBJ_STORE_CRED',
    file_uri_list   => 'https://objectstorage.<REGIAO>.oraclecloud.com/n/<NAMESPACE>/b/<BUCKET>/o/eventos_lms/eventos_lms_*.csv.gz',
    field_list      => 'FASE, TS_EVENTO, NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM',
    format          => '{"type":"csv",
                         "delimiter":",",
                         "skipheaders":1,
                         "quote":"\"",
                         "dateformat":"YYYY-MM-DD HH24:MI:SS",
                         "compression":"gzip",
                         "characterset":"AL32UTF8",
                         "blankasnull":true,
                         "trimspaces":"lrtrim",
                         "ignoremissingcolumns":true,
                         "rejectlimit":1000,
                         "logretention":7}');
  DBMS_OUTPUT.PUT_LINE('COPY_DATA concluido');
END;
/

-- ---------------------------------------------------------------------------
-- 3) Verificacao da carga (log/bad tables ficam em USER_LOAD_OPERATIONS)
-- ---------------------------------------------------------------------------
SELECT id, type, status, rows_loaded, table_name, logfile_table, badfile_table,
       TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI:SS') inicio, TO_CHAR(update_time, 'YYYY-MM-DD HH24:MI:SS') fim
  FROM user_load_operations
 WHERE type = 'COPY'
 ORDER BY id DESC
 FETCH FIRST 5 ROWS ONLY;
--  se status <> 'COMPLETED':  SELECT * FROM <logfile_table>;   SELECT * FROM <badfile_table>;

-- Esperado com o CSV completo gerado em 2026-09-09 (dry-run, 684.723 linhas de dados):
--   684.723 eventos | 204 NOME distintos (203 alunos + '-') | 2026-01-15 11:14 .. 2026-08-26 09:34 | 679.892 com FLG_ALUNO=1
SELECT COUNT(*) eventos, COUNT(DISTINCT NOME) nomes_distintos, SUM(FLG_ALUNO) eventos_de_aluno,
       TO_CHAR(MIN(TS_EVENTO), 'YYYY-MM-DD HH24:MI') primeiro, TO_CHAR(MAX(TS_EVENTO), 'YYYY-MM-DD HH24:MI') ultimo,
       COUNT(DISTINCT NUM_FASE) fases, MAX(CAPITULO) capitulo_max
  FROM EVENTOS_LMS;

BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(ownname => USER, tabname => 'EVENTOS_LMS');
END;
/

-- ---------------------------------------------------------------------------
-- 4) ALTERNATIVA: tabela externa sobre o bucket (le sem copiar) + carga INCREMENTAL
--    Uso tipico: o LMS exporta um eventos_lms_desde_<data>.csv.gz por semana; so o que e mais novo entra.
-- ---------------------------------------------------------------------------
BEGIN
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE EVENTOS_LMS_EXT';
  EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -942 THEN RAISE; END IF;
  END;
  DBMS_CLOUD.CREATE_EXTERNAL_TABLE(
    table_name      => 'EVENTOS_LMS_EXT',
    credential_name => 'RETENA_OBJ_STORE_CRED',
    file_uri_list   => 'https://objectstorage.<REGIAO>.oraclecloud.com/n/<NAMESPACE>/b/<BUCKET>/o/eventos_lms/eventos_lms_*.csv.gz',
    column_list     => 'FASE            VARCHAR2(10 CHAR),
                        TS_EVENTO       DATE,
                        NOME            VARCHAR2(30 CHAR),
                        USUARIO_AFETADO VARCHAR2(30 CHAR),
                        CONTEXTO        VARCHAR2(300 CHAR),
                        COMPONENTE      VARCHAR2(60 CHAR),
                        EVENTO          VARCHAR2(120 CHAR),
                        DESCRICAO       VARCHAR2(1000 CHAR),
                        ORIGEM          VARCHAR2(10 CHAR)',
    format          => '{"type":"csv","delimiter":",","skipheaders":1,"quote":"\"",
                         "dateformat":"YYYY-MM-DD HH24:MI:SS","compression":"gzip","characterset":"AL32UTF8",
                         "blankasnull":true,"trimspaces":"lrtrim","rejectlimit":1000}');
  DBMS_OUTPUT.PUT_LINE('Tabela externa EVENTOS_LMS_EXT criada');
END;
/

-- valida o parse dos arquivos sem carregar (gera tabelas VALIDATE$n_LOG / _BAD em USER_LOAD_OPERATIONS)
BEGIN
  DBMS_CLOUD.VALIDATE_EXTERNAL_TABLE(table_name => 'EVENTOS_LMS_EXT', rowcount => 1000);
END;
/

SELECT COUNT(*) linhas_no_bucket, TO_CHAR(MAX(TS_EVENTO), 'YYYY-MM-DD HH24:MI') ultimo_evento_no_bucket FROM EVENTOS_LMS_EXT;

-- carga incremental idempotente: so eventos posteriores ao ultimo ja carregado
INSERT /*+ APPEND */ INTO EVENTOS_LMS (FASE, TS_EVENTO, NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM)
SELECT e.FASE, e.TS_EVENTO, e.NOME, e.USUARIO_AFETADO, e.CONTEXTO, e.COMPONENTE, e.EVENTO, e.DESCRICAO, e.ORIGEM
  FROM EVENTOS_LMS_EXT e
 WHERE e.TS_EVENTO > (SELECT NVL(MAX(TS_EVENTO), DATE '1900-01-01') FROM EVENTOS_LMS);

COMMIT;

-- ---------------------------------------------------------------------------
-- 5) Agendamento da ingestao incremental (DBMS_SCHEDULER) - roda domingo 23:00, antes do
--    JOB_RETENA_SCORING_SEMANAL (segunda 06:00, criado em 05_scoring_views.sql) re-pontuar os alunos.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE PRC_INGERIR_EVENTOS_OCI IS
  v_antes NUMBER;
  v_qtd   NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_antes FROM EVENTOS_LMS;
  INSERT /*+ APPEND */ INTO EVENTOS_LMS (FASE, TS_EVENTO, NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM)
  SELECT e.FASE, e.TS_EVENTO, e.NOME, e.USUARIO_AFETADO, e.CONTEXTO, e.COMPONENTE, e.EVENTO, e.DESCRICAO, e.ORIGEM
    FROM EVENTOS_LMS_EXT e
   WHERE e.TS_EVENTO > (SELECT NVL(MAX(TS_EVENTO), DATE '1900-01-01') FROM EVENTOS_LMS);
  v_qtd := SQL%ROWCOUNT;
  COMMIT;
  IF v_qtd > 0 THEN
    DBMS_STATS.GATHER_TABLE_STATS(ownname => USER, tabname => 'EVENTOS_LMS');
  END IF;
  DBMS_OUTPUT.PUT_LINE('PRC_INGERIR_EVENTOS_OCI: ' || v_qtd || ' evento(s) novo(s) (' || v_antes || ' -> ' || (v_antes + v_qtd) || ') em ' ||
                       TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'));
END PRC_INGERIR_EVENTOS_OCI;
/

BEGIN
  BEGIN
    DBMS_SCHEDULER.DROP_JOB('JOB_RETENA_INGESTAO_SEMANAL', force => TRUE);
  EXCEPTION WHEN OTHERS THEN NULL;
  END;
  DBMS_SCHEDULER.CREATE_JOB(
    job_name        => 'JOB_RETENA_INGESTAO_SEMANAL',
    job_type        => 'STORED_PROCEDURE',
    job_action      => 'PRC_INGERIR_EVENTOS_OCI',
    start_date      => SYSTIMESTAMP,
    repeat_interval => 'FREQ=WEEKLY; BYDAY=SUN; BYHOUR=23; BYMINUTE=0',
    enabled         => TRUE,
    comments        => 'Retena - ingere do Object Storage os eventos novos do LMS toda semana, antes do re-scoring de segunda 06:00');
END;
/

SELECT job_name, repeat_interval, enabled, state, TO_CHAR(next_run_date, 'YYYY-MM-DD HH24:MI TZR') proxima_execucao
  FROM user_scheduler_jobs
 WHERE job_name IN ('JOB_RETENA_INGESTAO_SEMANAL', 'JOB_RETENA_SCORING_SEMANAL')
 ORDER BY 1;
