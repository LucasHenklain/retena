-- =============================================================================
-- 05_scoring_views.sql - Scoring IN-DATABASE e exposicao para API / APEX
--   VW_RISCO_ALUNO_ATUAL : view "viva" - recalcula as features do ultimo corte (VW_FEATURES_ATUAIS,
--                          = ultimo dia com eventos) e pontua com PREDICTION_PROBABILITY / PREDICTION_DETAILS.
--                          Custo: varre os ~685 mil eventos (~20-30 s) -> por isso existe o snapshot abaixo.
--   RISCO_ALUNO_SNAPSHOT : tabela persistida (1 linha por aluno) alimentada por PRC_ATUALIZAR_RISCO (MERGE, preserva
--                          o status de atendimento do coordenador). Agendada semanalmente via DBMS_SCHEDULER.
--   VW_RISCO_JSON        : payload unico (JSON_OBJECT + JSON_ARRAYAGG) pronto para a API/ORDS.
--   RISCO_ALUNO_DV       : JSON Relational Duality View (documento por aluno, leitura E escrita) - 23ai/26ai.
-- Faixas: Alto >= 0,60 | Medio 0,30-0,60 | Baixo < 0,30 (probabilidade de inatividade nos proximos 21 dias)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) View viva de risco (modelo principal: RETENA_INATIVO21_RF; GLM como segunda opiniao;
--    RETENA_TRANSICAO_GLM aplicado as features da fase corrente do aluno)
-- ---------------------------------------------------------------------------
-- Nota: ORA-64630 - view baseada em SQL Macro (VW_FEATURES_ATUAIS) nao pode entrar em clausula WITH;
--       por isso as duas fontes sao inline views no FROM (registrado no log 05_scoring_views.log).
CREATE OR REPLACE VIEW VW_RISCO_ALUNO_ATUAL AS
SELECT s.NOME,
       s.DT_CORTE,
       s.NUM_FASE_ATUAL,
       df.NOME_FASE,
       s.RECENCIA_DIAS,
       s.EVENTOS_7D, s.EVENTOS_14D, s.EVENTOS_28D, s.DIAS_ATIVOS_28D, s.PROGRESSO_28D,
       s.CAPITULOS_DISTINTOS_28D, s.QUIZ_28D, s.ENTREGAS_28D, s.TENDENCIA, s.EVENTOS_ACUMULADOS,
       ROUND(s.PROB_INATIVO_21D, 4)                                  AS PROB_INATIVO_21D,
       ROUND(s.PROB_INATIVO_21D_GLM, 4)                              AS PROB_INATIVO_21D_GLM,
       CASE WHEN s.PROB_INATIVO_21D >= 0.60 THEN 'Alto'
            WHEN s.PROB_INATIVO_21D >= 0.30 THEN 'Médio'
            ELSE 'Baixo' END                                         AS FAIXA_RISCO,
       (SELECT LISTAGG(x.NOME_ATTR || '=' || x.VALOR || ' (peso ' || TO_CHAR(ROUND(x.PESO, 2), 'FM990.00') || ')', '; ')
                 WITHIN GROUP (ORDER BY x.RNK)
          FROM XMLTABLE('/Details/Attribute' PASSING s.DET_XML
                 COLUMNS NOME_ATTR VARCHAR2(60) PATH '@name',
                         VALOR     VARCHAR2(60) PATH '@actualValue',
                         PESO      NUMBER       PATH '@weight',
                         RNK       NUMBER       PATH '@rank') x)     AS FATORES_TOP3,
       (SELECT JSON_ARRAYAGG(JSON_OBJECT('atributo' VALUE x.NOME_ATTR, 'valor' VALUE x.VALOR,
                                         'peso' VALUE ROUND(x.PESO, 3), 'rank' VALUE x.RNK)
                             ORDER BY x.RNK RETURNING VARCHAR2(1000))
          FROM XMLTABLE('/Details/Attribute' PASSING s.DET_XML
                 COLUMNS NOME_ATTR VARCHAR2(60) PATH '@name',
                         VALOR     VARCHAR2(60) PATH '@actualValue',
                         PESO      NUMBER       PATH '@weight',
                         RNK       NUMBER       PATH '@rank') x)     AS FATORES_JSON,
       CASE WHEN s.PROB_INATIVO_21D >= 0.60 AND s.RECENCIA_DIAS > 14 THEN 'Contato ativo do tutor (telefone/WhatsApp) em 48h'
            WHEN s.PROB_INATIVO_21D >= 0.60                          THEN 'Mensagem pessoal do tutor + revisar capítulo atual'
            WHEN s.PROB_INATIVO_21D >= 0.30                          THEN 'Nudge automático (e-mail/push) e reavaliar na próxima semana'
            ELSE 'Sem ação (monitorar)' END                          AS ACAO_SUGERIDA
  FROM (SELECT f.NOME, f.DT_CORTE, f.NUM_FASE_ATUAL, f.RECENCIA_DIAS,
               f.EVENTOS_7D, f.EVENTOS_14D, f.EVENTOS_28D, f.DIAS_ATIVOS_28D, f.PROGRESSO_28D,
               f.CAPITULOS_DISTINTOS_28D, f.QUIZ_28D, f.ENTREGAS_28D, f.TENDENCIA, f.EVENTOS_ACUMULADOS,
               PREDICTION_PROBABILITY(RETENA_INATIVO21_RF,  1 USING *) AS PROB_INATIVO_21D,
               PREDICTION_PROBABILITY(RETENA_INATIVO21_GLM, 1 USING *) AS PROB_INATIVO_21D_GLM,
               PREDICTION_DETAILS(RETENA_INATIVO21_RF, 1, 3 USING *)   AS DET_XML
          FROM VW_FEATURES_ATUAIS f) s
  LEFT JOIN DIM_FASE df ON df.NUM_FASE = s.NUM_FASE_ATUAL;

-- Segundo modelo aplicado a fase corrente de cada aluno (evasao na transicao de fase).
-- Mantido em view separada: na 1a tentativa o join das duas views pesadas (ambas varrem EVENTOS_LMS)
-- entrou em nested loops e a MERGE ficou > 10 min (sessao encerrada; ver log *_tentativa2). Em duas
-- passadas independentes cada view e avaliada uma unica vez.
CREATE OR REPLACE VIEW VW_RISCO_TRANSICAO_ATUAL AS
SELECT t.NOME, t.NUM_FASE, t.NOME_FASE, t.CAPITULO_MAX, t.PCT_CAPITULOS, t.TOTAL_EVENTOS, t.DIAS_ATIVOS,
       ROUND(PREDICTION_PROBABILITY(RETENA_TRANSICAO_GLM, 1 USING t.*), 4) AS PROB_EVASAO_FASE
  FROM VW_FEATURES_TRANSICAO_FASE t;

-- ---------------------------------------------------------------------------
-- 2) Snapshot persistido + procedimento de atualizacao (MERGE preserva atendimento)
-- ---------------------------------------------------------------------------
BEGIN
  EXECUTE IMMEDIATE 'DROP VIEW RISCO_ALUNO_DV';
EXCEPTION WHEN OTHERS THEN
  IF SQLCODE NOT IN (-942, -4043) THEN RAISE; END IF;
END;
/
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE RISCO_ALUNO_SNAPSHOT PURGE';
EXCEPTION WHEN OTHERS THEN
  IF SQLCODE != -942 THEN RAISE; END IF;
END;
/

CREATE TABLE RISCO_ALUNO_SNAPSHOT (
  NOME                     VARCHAR2(30 CHAR)   NOT NULL,
  DT_CORTE                 DATE                NOT NULL,
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
  PROB_INATIVO_21D         NUMBER(6,4)         NOT NULL,
  PROB_INATIVO_21D_GLM     NUMBER(6,4),
  FAIXA_RISCO              VARCHAR2(10 CHAR)   NOT NULL,
  FATORES_TOP3             VARCHAR2(600 CHAR),
  FATORES_JSON             VARCHAR2(1000 CHAR) CHECK (FATORES_JSON IS JSON),
  CAPITULO_MAX_FASE        NUMBER,
  PCT_CAPITULOS_FASE       NUMBER,
  PROB_EVASAO_FASE         NUMBER(6,4),
  ACAO_SUGERIDA            VARCHAR2(120 CHAR),
  STATUS_ATENDIMENTO       VARCHAR2(20 CHAR)   DEFAULT 'PENDENTE' NOT NULL,
  OBSERVACAO               VARCHAR2(400 CHAR),
  DT_SCORING               TIMESTAMP           NOT NULL,
  CONSTRAINT PK_RISCO_ALUNO_SNAPSHOT PRIMARY KEY (NOME),
  CONSTRAINT CK_RISCO_FAIXA  CHECK (FAIXA_RISCO IN ('Alto', 'Médio', 'Baixo')),
  CONSTRAINT CK_RISCO_STATUS CHECK (STATUS_ATENDIMENTO IN ('PENDENTE', 'CONTATADO', 'REATIVADO', 'SEM_RETORNO', 'IGNORAR'))
);

CREATE INDEX IX_RISCO_SNAPSHOT_FAIXA ON RISCO_ALUNO_SNAPSHOT (FAIXA_RISCO, PROB_INATIVO_21D);

CREATE OR REPLACE PROCEDURE PRC_ATUALIZAR_RISCO IS
  v_t0   TIMESTAMP := SYSTIMESTAMP;
  v_qtd  NUMBER;
BEGIN
  MERGE INTO RISCO_ALUNO_SNAPSHOT d
  USING VW_RISCO_ALUNO_ATUAL v ON (d.NOME = v.NOME)
  WHEN MATCHED THEN UPDATE SET
       d.DT_CORTE = v.DT_CORTE, d.NUM_FASE_ATUAL = v.NUM_FASE_ATUAL, d.NOME_FASE = v.NOME_FASE,
       d.RECENCIA_DIAS = v.RECENCIA_DIAS, d.EVENTOS_7D = v.EVENTOS_7D, d.EVENTOS_14D = v.EVENTOS_14D,
       d.EVENTOS_28D = v.EVENTOS_28D, d.DIAS_ATIVOS_28D = v.DIAS_ATIVOS_28D, d.PROGRESSO_28D = v.PROGRESSO_28D,
       d.CAPITULOS_DISTINTOS_28D = v.CAPITULOS_DISTINTOS_28D, d.QUIZ_28D = v.QUIZ_28D, d.ENTREGAS_28D = v.ENTREGAS_28D,
       d.TENDENCIA = v.TENDENCIA, d.EVENTOS_ACUMULADOS = v.EVENTOS_ACUMULADOS,
       d.PROB_INATIVO_21D = v.PROB_INATIVO_21D, d.PROB_INATIVO_21D_GLM = v.PROB_INATIVO_21D_GLM,
       d.FAIXA_RISCO = v.FAIXA_RISCO, d.FATORES_TOP3 = v.FATORES_TOP3, d.FATORES_JSON = v.FATORES_JSON,
       d.ACAO_SUGERIDA = v.ACAO_SUGERIDA,
       -- aluno que voltou a ficar em risco depois de tratado reabre a fila
       d.STATUS_ATENDIMENTO = CASE WHEN d.STATUS_ATENDIMENTO = 'REATIVADO' AND v.FAIXA_RISCO = 'Alto'
                                   THEN 'PENDENTE' ELSE d.STATUS_ATENDIMENTO END,
       d.DT_SCORING = SYSTIMESTAMP
  WHEN NOT MATCHED THEN INSERT (
       NOME, DT_CORTE, NUM_FASE_ATUAL, NOME_FASE, RECENCIA_DIAS, EVENTOS_7D, EVENTOS_14D, EVENTOS_28D,
       DIAS_ATIVOS_28D, PROGRESSO_28D, CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA, EVENTOS_ACUMULADOS,
       PROB_INATIVO_21D, PROB_INATIVO_21D_GLM, FAIXA_RISCO, FATORES_TOP3, FATORES_JSON,
       ACAO_SUGERIDA, STATUS_ATENDIMENTO, DT_SCORING)
  VALUES (
       v.NOME, v.DT_CORTE, v.NUM_FASE_ATUAL, v.NOME_FASE, v.RECENCIA_DIAS, v.EVENTOS_7D, v.EVENTOS_14D, v.EVENTOS_28D,
       v.DIAS_ATIVOS_28D, v.PROGRESSO_28D, v.CAPITULOS_DISTINTOS_28D, v.QUIZ_28D, v.ENTREGAS_28D, v.TENDENCIA, v.EVENTOS_ACUMULADOS,
       v.PROB_INATIVO_21D, v.PROB_INATIVO_21D_GLM, v.FAIXA_RISCO, v.FATORES_TOP3, v.FATORES_JSON,
       v.ACAO_SUGERIDA, 'PENDENTE', SYSTIMESTAMP);
  v_qtd := SQL%ROWCOUNT;
  -- 2a passada: modelo de transicao de fase aplicado a fase corrente do aluno (view avaliada uma unica vez)
  MERGE INTO RISCO_ALUNO_SNAPSHOT d
  USING VW_RISCO_TRANSICAO_ATUAL t ON (d.NOME = t.NOME AND d.NUM_FASE_ATUAL = t.NUM_FASE)
  WHEN MATCHED THEN UPDATE SET
       d.CAPITULO_MAX_FASE = t.CAPITULO_MAX, d.PCT_CAPITULOS_FASE = t.PCT_CAPITULOS, d.PROB_EVASAO_FASE = t.PROB_EVASAO_FASE;
  COMMIT;
  DBMS_OUTPUT.PUT_LINE('PRC_ATUALIZAR_RISCO: ' || v_qtd || ' aluno(s) pontuado(s) em ' ||
    TO_CHAR(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_t0)) + 60 * EXTRACT(MINUTE FROM (SYSTIMESTAMP - v_t0)), 'FM9990.00') ||
    ' s (' || TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') || ')');
END PRC_ATUALIZAR_RISCO;
/

-- primeira carga do snapshot (scoring real dos 3 modelos sobre o corte atual)
BEGIN
  PRC_ATUALIZAR_RISCO;
END;
/

-- Agendamento semanal (segunda 06:00) - DBMS_SCHEDULER, mesmo mecanismo do Autonomous Database
BEGIN
  BEGIN
    DBMS_SCHEDULER.DROP_JOB('JOB_RETENA_SCORING_SEMANAL', force => TRUE);
  EXCEPTION WHEN OTHERS THEN NULL;
  END;
  DBMS_SCHEDULER.CREATE_JOB(
    job_name        => 'JOB_RETENA_SCORING_SEMANAL',
    job_type        => 'STORED_PROCEDURE',
    job_action      => 'PRC_ATUALIZAR_RISCO',
    start_date      => SYSTIMESTAMP,
    repeat_interval => 'FREQ=WEEKLY; BYDAY=MON; BYHOUR=6; BYMINUTE=0',
    enabled         => TRUE,
    comments        => 'Retena - re-pontua o risco de inatividade 21d de todos os alunos toda segunda 06:00');
  DBMS_OUTPUT.PUT_LINE('JOB_RETENA_SCORING_SEMANAL criado');
END;
/

SELECT job_name, job_type, job_action, repeat_interval, enabled, state,
       TO_CHAR(next_run_date, 'YYYY-MM-DD HH24:MI TZR') proxima_execucao
  FROM user_scheduler_jobs WHERE job_name = 'JOB_RETENA_SCORING_SEMANAL';

-- ---------------------------------------------------------------------------
-- 3) JSON pronto para API (um documento com resumo + lista ordenada por risco)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_RISCO_JSON AS
SELECT JSON_OBJECT(
         'produto'        VALUE 'Retena',
         'gerado_em'      VALUE TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD"T"HH24:MI:SS.FF3TZH:TZM'),
         'dt_corte'       VALUE TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD'),
         'dt_scoring'     VALUE TO_CHAR(MAX(DT_SCORING), 'YYYY-MM-DD"T"HH24:MI:SS'),
         'modelo'         VALUE 'RETENA_INATIVO21_RF (Oracle Machine Learning, Random Forest, in-database)',
         'horizonte_dias' VALUE 21,
         'total_alunos'   VALUE COUNT(*),
         'resumo'         VALUE JSON_OBJECT(
                              'alto'  VALUE SUM(CASE WHEN FAIXA_RISCO = 'Alto'  THEN 1 ELSE 0 END),
                              'medio' VALUE SUM(CASE WHEN FAIXA_RISCO = 'Médio' THEN 1 ELSE 0 END),
                              'baixo' VALUE SUM(CASE WHEN FAIXA_RISCO = 'Baixo' THEN 1 ELSE 0 END),
                              'prob_media' VALUE ROUND(AVG(PROB_INATIVO_21D), 4)),
         'alunos'         VALUE JSON_ARRAYAGG(
                              JSON_OBJECT(
                                'aluno'             VALUE NOME,
                                'fase'              VALUE NUM_FASE_ATUAL,
                                'prob_inativo_21d'  VALUE PROB_INATIVO_21D,
                                'faixa'             VALUE FAIXA_RISCO,
                                'recencia_dias'     VALUE RECENCIA_DIAS,
                                'eventos_28d'       VALUE EVENTOS_28D,
                                'progresso_fase'    VALUE PCT_CAPITULOS_FASE,
                                'prob_evasao_fase'  VALUE PROB_EVASAO_FASE,
                                'fatores'           VALUE JSON_QUERY(FATORES_JSON, '$'),
                                'acao_sugerida'     VALUE ACAO_SUGERIDA,
                                'status_atendimento' VALUE STATUS_ATENDIMENTO)
                              ORDER BY PROB_INATIVO_21D DESC, NOME
                              RETURNING CLOB)
         RETURNING CLOB) AS PAYLOAD
  FROM RISCO_ALUNO_SNAPSHOT;

-- ---------------------------------------------------------------------------
-- 4) JSON Relational Duality View (23ai/26ai): documento por aluno com leitura e escrita
--    (o coordenador atualiza o status pelo app via JSON; a tabela relacional continua a fonte unica)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW RISCO_ALUNO_DV AS
SELECT JSON {
         '_id'              : NOME,
         'dtCorte'          : DT_CORTE,
         'fase'             : NUM_FASE_ATUAL,
         'nomeFase'         : NOME_FASE,
         'probInativo21d'   : PROB_INATIVO_21D,
         'faixa'            : FAIXA_RISCO,
         'recenciaDias'     : RECENCIA_DIAS,
         'eventos28d'       : EVENTOS_28D,
         'fatoresTop3'      : FATORES_TOP3,
         'acaoSugerida'     : ACAO_SUGERIDA,
         'atendimento'      : { 'status' : STATUS_ATENDIMENTO, 'observacao' : OBSERVACAO },
         'dtScoring'        : DT_SCORING
       }
  FROM RISCO_ALUNO_SNAPSHOT WITH UPDATE;

-- leitura pela duality view
SELECT JSON_SERIALIZE(dv.DATA PRETTY) documento
  FROM RISCO_ALUNO_DV dv
 WHERE dv.DATA.faixa.string() = 'Alto'
 ORDER BY dv.DATA.probInativo21d.number() DESC
 FETCH FIRST 1 ROWS ONLY;

-- escrita pela duality view (fluxo do coordenador no app) -> reflete na tabela relacional
UPDATE RISCO_ALUNO_DV dv
   SET dv.DATA = JSON_TRANSFORM(dv.DATA, SET '$.atendimento.status' = 'CONTATADO',
                                          SET '$.atendimento.observacao' = 'Teste de escrita via duality view (05_scoring_views.sql)')
 WHERE dv.DATA."_id".string() = (SELECT NOME FROM RISCO_ALUNO_SNAPSHOT ORDER BY PROB_INATIVO_21D DESC, NOME FETCH FIRST 1 ROWS ONLY);

SELECT NOME, FAIXA_RISCO, STATUS_ATENDIMENTO, OBSERVACAO
  FROM RISCO_ALUNO_SNAPSHOT WHERE STATUS_ATENDIMENTO <> 'PENDENTE';

-- desfaz o teste para nao poluir a fila real
UPDATE RISCO_ALUNO_SNAPSHOT SET STATUS_ATENDIMENTO = 'PENDENTE', OBSERVACAO = NULL WHERE STATUS_ATENDIMENTO = 'CONTATADO';
COMMIT;

-- ---------------------------------------------------------------------------
-- 5) Verificacoes
-- ---------------------------------------------------------------------------
SELECT FAIXA_RISCO, COUNT(*) alunos, ROUND(AVG(PROB_INATIVO_21D), 4) prob_media,
       ROUND(AVG(RECENCIA_DIAS), 1) recencia_media, ROUND(AVG(EVENTOS_28D), 1) eventos_28d_media
  FROM RISCO_ALUNO_SNAPSHOT GROUP BY FAIXA_RISCO ORDER BY prob_media DESC;

SELECT NOME, NUM_FASE_ATUAL fase, RECENCIA_DIAS recencia, EVENTOS_28D ev_28d, PROB_INATIVO_21D prob_rf,
       PROB_INATIVO_21D_GLM prob_glm, FAIXA_RISCO faixa, PROB_EVASAO_FASE prob_fase, FATORES_TOP3
  FROM RISCO_ALUNO_SNAPSHOT ORDER BY PROB_INATIVO_21D DESC, NOME FETCH FIRST 10 ROWS ONLY;

SELECT DBMS_LOB.GETLENGTH(PAYLOAD) bytes_payload, JSON_VALUE(PAYLOAD, '$.total_alunos') total,
       JSON_VALUE(PAYLOAD, '$.resumo.alto') alto, JSON_VALUE(PAYLOAD, '$.resumo.medio') medio,
       JSON_VALUE(PAYLOAD, '$.resumo.baixo') baixo, JSON_VALUE(PAYLOAD, '$.alunos[0].aluno') primeiro_da_fila
  FROM VW_RISCO_JSON;
