-- =============================================================================
-- 09_merge_risco_snapshot.sql - MERGE idempotente do risco atual (padrao EduRetain, adaptado)
-- Projeto Retena | adaptado do EduRetain (equipe Retena): scoring.py -> _build_merge_sql()
--   EduRetain : stage (predicao_evasao_aluno_stg) -> MERGE em predicao_evasao_aluno
--               ON (id_student, code_module, code_presentation, cutoff_days) + dt_processamento
--   Retena    : stage (RISCO_ALUNO_STG, materializa VW_RISCO_ALUNO_ATUAL UMA vez)
--               -> MERGE 1 em RISCO_ALUNO_SNAPSHOT  ON (NOME)            [PK real: 1 linha por aluno = estado atual]
--               -> MERGE 2 em RISCO_ALUNO_HISTORICO ON (NOME, DT_CORTE)  [chave natural aluno + corte]
--               -> MERGE 3 (so UPDATE) com VW_RISCO_TRANSICAO_ATUAL     ON (NOME, NUM_FASE_ATUAL)
-- Colunas conferidas em USER_TAB_COLS antes de escrever (secao 0 reimprime a inspecao como evidencia).
-- Roda em QUALQUER Oracle (Free local ou Autonomous) - nao depende de DBMS_CLOUD.
-- Idempotente: executar N vezes nao duplica linhas (verificacoes na secao 5).
-- Convencao do runner (scripts/executar_sql.py): SQL termina com ";", PL/SQL com "/" em linha propria.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0) Inspecao (evidencia): colunas reais da origem e do alvo + PK do alvo
-- ---------------------------------------------------------------------------
SELECT table_name, column_id, column_name, data_type, data_length, nullable
  FROM user_tab_columns
 WHERE table_name IN ('VW_RISCO_ALUNO_ATUAL', 'RISCO_ALUNO_SNAPSHOT')
 ORDER BY table_name, column_id;

SELECT uc.constraint_name, uc.constraint_type, LISTAGG(ucc.column_name, ', ') WITHIN GROUP (ORDER BY ucc.position) colunas
  FROM user_constraints uc JOIN user_cons_columns ucc ON ucc.constraint_name = uc.constraint_name
 WHERE uc.table_name = 'RISCO_ALUNO_SNAPSHOT' AND uc.constraint_type IN ('P', 'U')
 GROUP BY uc.constraint_name, uc.constraint_type;

SELECT TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS.FF3 TZH:TZM') inicio_execucao,
       SYS_CONTEXT('USERENV', 'SESSION_USER') usuario, SYS_CONTEXT('USERENV', 'CON_NAME') container
  FROM dual;

-- ---------------------------------------------------------------------------
-- 1) Staging: materializa a view viva UMA vez (PREDICTION_PROBABILITY + PREDICTION_DETAILS
--    sobre ~685 mil eventos, ~20-30 s). Evita reavaliar a view em cada MERGE
--    (licao do log 05_scoring_views_tentativa2_merge_lento.log).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS RISCO_ALUNO_STG (
  NOME                     VARCHAR2(30 CHAR)    NOT NULL,
  DT_CORTE                 DATE                 NOT NULL,
  NUM_FASE_ATUAL           NUMBER(1),
  NOME_FASE                VARCHAR2(20 CHAR),
  RECENCIA_DIAS            NUMBER,
  EVENTOS_7D               NUMBER,
  EVENTOS_14D              NUMBER,
  EVENTOS_28D              NUMBER,
  DIAS_ATIVOS_28D          NUMBER,
  PROGRESSO_28D            NUMBER,
  CAPITULOS_DISTINTOS_28D  NUMBER,
  QUIZ_28D                 NUMBER,
  ENTREGAS_28D             NUMBER,
  TENDENCIA                NUMBER,
  EVENTOS_ACUMULADOS       NUMBER,
  PROB_INATIVO_21D         NUMBER(6,4)          NOT NULL,
  PROB_INATIVO_21D_GLM     NUMBER(6,4),
  FAIXA_RISCO              VARCHAR2(10 CHAR)    NOT NULL,
  FATORES_TOP3             VARCHAR2(2000 CHAR),
  FATORES_JSON             VARCHAR2(1000 CHAR),
  ACAO_SUGERIDA            VARCHAR2(120 CHAR),
  DT_EXTRACAO              TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

TRUNCATE TABLE RISCO_ALUNO_STG;

INSERT INTO RISCO_ALUNO_STG (
       NOME, DT_CORTE, NUM_FASE_ATUAL, NOME_FASE, RECENCIA_DIAS, EVENTOS_7D, EVENTOS_14D, EVENTOS_28D,
       DIAS_ATIVOS_28D, PROGRESSO_28D, CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA, EVENTOS_ACUMULADOS,
       PROB_INATIVO_21D, PROB_INATIVO_21D_GLM, FAIXA_RISCO, FATORES_TOP3, FATORES_JSON, ACAO_SUGERIDA)
SELECT NOME, DT_CORTE, NUM_FASE_ATUAL, NOME_FASE, RECENCIA_DIAS, EVENTOS_7D, EVENTOS_14D, EVENTOS_28D,
       DIAS_ATIVOS_28D, PROGRESSO_28D, CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA, EVENTOS_ACUMULADOS,
       PROB_INATIVO_21D, PROB_INATIVO_21D_GLM, FAIXA_RISCO, FATORES_TOP3, FATORES_JSON, ACAO_SUGERIDA
  FROM VW_RISCO_ALUNO_ATUAL;

COMMIT;

SELECT COUNT(*) linhas_stg, COUNT(DISTINCT NOME) alunos_distintos, TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') dt_corte
  FROM RISCO_ALUNO_STG;

-- ---------------------------------------------------------------------------
-- 2) Historico por corte (aluno + corte) - equivalente da chave natural do EduRetain
--    (id_student, code_module, code_presentation, cutoff_days). Nao existe no pacote v1;
--    criado aqui porque RISCO_ALUNO_SNAPSHOT tem PK (NOME) e guarda so o estado atual.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS RISCO_ALUNO_HISTORICO (
  NOME                  VARCHAR2(30 CHAR)   NOT NULL,
  DT_CORTE              DATE                NOT NULL,
  NUM_FASE_ATUAL        NUMBER(1),
  RECENCIA_DIAS         NUMBER,
  EVENTOS_28D           NUMBER,
  DIAS_ATIVOS_28D       NUMBER,
  PROB_INATIVO_21D      NUMBER(6,4)         NOT NULL,
  PROB_INATIVO_21D_GLM  NUMBER(6,4),
  FAIXA_RISCO           VARCHAR2(10 CHAR)   NOT NULL,
  FATORES_JSON          VARCHAR2(1000 CHAR) CHECK (FATORES_JSON IS JSON),
  MODELO_VERSAO         VARCHAR2(60 CHAR),
  DT_PROCESSAMENTO      TIMESTAMP           NOT NULL,
  CONSTRAINT PK_RISCO_ALUNO_HISTORICO PRIMARY KEY (NOME, DT_CORTE)
);

-- ---------------------------------------------------------------------------
-- 3) MERGE 1 - estado atual (RISCO_ALUNO_SNAPSHOT), chave = NOME (PK real).
--    Preserva STATUS_ATENDIMENTO / OBSERVACAO do coordenador (mesma regra de PRC_ATUALIZAR_RISCO):
--    aluno REATIVADO que volta a 'Alto' reabre a fila como PENDENTE.
-- ---------------------------------------------------------------------------
MERGE INTO RISCO_ALUNO_SNAPSHOT d
USING RISCO_ALUNO_STG s
   ON (d.NOME = s.NOME)
WHEN MATCHED THEN UPDATE SET
     d.DT_CORTE = s.DT_CORTE, d.NUM_FASE_ATUAL = s.NUM_FASE_ATUAL, d.NOME_FASE = s.NOME_FASE,
     d.RECENCIA_DIAS = s.RECENCIA_DIAS, d.EVENTOS_7D = s.EVENTOS_7D, d.EVENTOS_14D = s.EVENTOS_14D,
     d.EVENTOS_28D = s.EVENTOS_28D, d.DIAS_ATIVOS_28D = s.DIAS_ATIVOS_28D, d.PROGRESSO_28D = s.PROGRESSO_28D,
     d.CAPITULOS_DISTINTOS_28D = s.CAPITULOS_DISTINTOS_28D, d.QUIZ_28D = s.QUIZ_28D, d.ENTREGAS_28D = s.ENTREGAS_28D,
     d.TENDENCIA = s.TENDENCIA, d.EVENTOS_ACUMULADOS = s.EVENTOS_ACUMULADOS,
     d.PROB_INATIVO_21D = s.PROB_INATIVO_21D, d.PROB_INATIVO_21D_GLM = s.PROB_INATIVO_21D_GLM,
     d.FAIXA_RISCO = s.FAIXA_RISCO, d.FATORES_TOP3 = s.FATORES_TOP3, d.FATORES_JSON = s.FATORES_JSON,
     d.ACAO_SUGERIDA = s.ACAO_SUGERIDA,
     d.STATUS_ATENDIMENTO = CASE WHEN d.STATUS_ATENDIMENTO = 'REATIVADO' AND s.FAIXA_RISCO = 'Alto'
                                 THEN 'PENDENTE' ELSE d.STATUS_ATENDIMENTO END,
     d.DT_SCORING = SYSTIMESTAMP
WHEN NOT MATCHED THEN INSERT (
     NOME, DT_CORTE, NUM_FASE_ATUAL, NOME_FASE, RECENCIA_DIAS, EVENTOS_7D, EVENTOS_14D, EVENTOS_28D,
     DIAS_ATIVOS_28D, PROGRESSO_28D, CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA, EVENTOS_ACUMULADOS,
     PROB_INATIVO_21D, PROB_INATIVO_21D_GLM, FAIXA_RISCO, FATORES_TOP3, FATORES_JSON,
     ACAO_SUGERIDA, STATUS_ATENDIMENTO, DT_SCORING)
VALUES (
     s.NOME, s.DT_CORTE, s.NUM_FASE_ATUAL, s.NOME_FASE, s.RECENCIA_DIAS, s.EVENTOS_7D, s.EVENTOS_14D, s.EVENTOS_28D,
     s.DIAS_ATIVOS_28D, s.PROGRESSO_28D, s.CAPITULOS_DISTINTOS_28D, s.QUIZ_28D, s.ENTREGAS_28D, s.TENDENCIA, s.EVENTOS_ACUMULADOS,
     s.PROB_INATIVO_21D, s.PROB_INATIVO_21D_GLM, s.FAIXA_RISCO, s.FATORES_TOP3, s.FATORES_JSON,
     s.ACAO_SUGERIDA, 'PENDENTE', SYSTIMESTAMP);

-- ---------------------------------------------------------------------------
-- 4) MERGE 2 - historico (RISCO_ALUNO_HISTORICO), chave natural = (NOME, DT_CORTE).
--    Reprocessar o mesmo corte atualiza a linha; um corte novo insere. MODELO_VERSAO = nome + data de
--    criacao do modelo em USER_MINING_MODELS (equivale a modelo_versao do EduRetain).
-- ---------------------------------------------------------------------------
MERGE INTO RISCO_ALUNO_HISTORICO h
USING (SELECT s.NOME, s.DT_CORTE, s.NUM_FASE_ATUAL, s.RECENCIA_DIAS, s.EVENTOS_28D, s.DIAS_ATIVOS_28D,
              s.PROB_INATIVO_21D, s.PROB_INATIVO_21D_GLM, s.FAIXA_RISCO, s.FATORES_JSON,
              (SELECT m.model_name || '@' || TO_CHAR(m.creation_date, 'YYYY-MM-DD')
                 FROM user_mining_models m WHERE m.model_name = 'RETENA_INATIVO21_RF') AS MODELO_VERSAO
         FROM RISCO_ALUNO_STG s) s
   ON (h.NOME = s.NOME AND h.DT_CORTE = s.DT_CORTE)
WHEN MATCHED THEN UPDATE SET
     h.NUM_FASE_ATUAL = s.NUM_FASE_ATUAL, h.RECENCIA_DIAS = s.RECENCIA_DIAS, h.EVENTOS_28D = s.EVENTOS_28D,
     h.DIAS_ATIVOS_28D = s.DIAS_ATIVOS_28D, h.PROB_INATIVO_21D = s.PROB_INATIVO_21D,
     h.PROB_INATIVO_21D_GLM = s.PROB_INATIVO_21D_GLM, h.FAIXA_RISCO = s.FAIXA_RISCO, h.FATORES_JSON = s.FATORES_JSON,
     h.MODELO_VERSAO = s.MODELO_VERSAO, h.DT_PROCESSAMENTO = SYSTIMESTAMP
WHEN NOT MATCHED THEN INSERT (
     NOME, DT_CORTE, NUM_FASE_ATUAL, RECENCIA_DIAS, EVENTOS_28D, DIAS_ATIVOS_28D, PROB_INATIVO_21D,
     PROB_INATIVO_21D_GLM, FAIXA_RISCO, FATORES_JSON, MODELO_VERSAO, DT_PROCESSAMENTO)
VALUES (
     s.NOME, s.DT_CORTE, s.NUM_FASE_ATUAL, s.RECENCIA_DIAS, s.EVENTOS_28D, s.DIAS_ATIVOS_28D, s.PROB_INATIVO_21D,
     s.PROB_INATIVO_21D_GLM, s.FAIXA_RISCO, s.FATORES_JSON, s.MODELO_VERSAO, SYSTIMESTAMP);

-- ---------------------------------------------------------------------------
-- 4b) MERGE 3 - 2a passada (modelo de transicao de fase), so UPDATE: nunca insere, logo nunca duplica.
-- ---------------------------------------------------------------------------
MERGE INTO RISCO_ALUNO_SNAPSHOT d
USING VW_RISCO_TRANSICAO_ATUAL t
   ON (d.NOME = t.NOME AND d.NUM_FASE_ATUAL = t.NUM_FASE)
WHEN MATCHED THEN UPDATE SET
     d.CAPITULO_MAX_FASE = t.CAPITULO_MAX, d.PCT_CAPITULOS_FASE = t.PCT_CAPITULOS, d.PROB_EVASAO_FASE = t.PROB_EVASAO_FASE;

COMMIT;

-- ---------------------------------------------------------------------------
-- 5) Verificacoes de idempotencia (rodar o script 2x: contagens iguais, 0 duplicatas)
-- ---------------------------------------------------------------------------
SELECT 'RISCO_ALUNO_SNAPSHOT' tabela, COUNT(*) linhas, COUNT(DISTINCT NOME) chaves_distintas,
       TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') dt_corte, TO_CHAR(MAX(DT_SCORING), 'YYYY-MM-DD HH24:MI:SS.FF3') ultimo_processamento
  FROM RISCO_ALUNO_SNAPSHOT
UNION ALL
SELECT 'RISCO_ALUNO_HISTORICO', COUNT(*), COUNT(DISTINCT NOME || '|' || TO_CHAR(DT_CORTE, 'YYYYMMDD')),
       TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD'), TO_CHAR(MAX(DT_PROCESSAMENTO), 'YYYY-MM-DD HH24:MI:SS.FF3')
  FROM RISCO_ALUNO_HISTORICO;

-- duplicatas: as duas consultas DEVEM retornar 0 linha(s)
SELECT NOME, COUNT(*) qtd FROM RISCO_ALUNO_SNAPSHOT GROUP BY NOME HAVING COUNT(*) > 1;

SELECT NOME, DT_CORTE, COUNT(*) qtd FROM RISCO_ALUNO_HISTORICO GROUP BY NOME, DT_CORTE HAVING COUNT(*) > 1;

SELECT FAIXA_RISCO, COUNT(*) alunos, ROUND(AVG(PROB_INATIVO_21D), 4) prob_media,
       SUM(CASE WHEN STATUS_ATENDIMENTO = 'PENDENTE' THEN 1 ELSE 0 END) pendentes
  FROM RISCO_ALUNO_SNAPSHOT GROUP BY FAIXA_RISCO ORDER BY prob_media DESC;

SELECT MODELO_VERSAO, TO_CHAR(DT_CORTE, 'YYYY-MM-DD') dt_corte, COUNT(*) alunos
  FROM RISCO_ALUNO_HISTORICO GROUP BY MODELO_VERSAO, DT_CORTE ORDER BY 2;

SELECT TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS.FF3 TZH:TZM') fim_execucao FROM dual;
