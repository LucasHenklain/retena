-- =============================================================================
-- 02_features_transicao.sql - Feature engineering IN-DATABASE: transicao de fase
-- Unidade de analise: (aluno, fase k). Rotulo EVADIU_PROXIMA_FASE = 1 quando o aluno
-- teve >= 1 evento na fase k e 0 eventos na fase k+1 (k = 1..4). Fase 5 nao tem rotulo.
-- Definicoes alinhadas ao pipeline Python do projeto (ver README).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) Janela temporal observada de cada fase (data-driven)
--    DT_MEDIANA define o "centro" da fase e e usada para o corte temporal treino/teste:
--    fases com mediana < 2026-06-01 (F1, F2, F3) treinam; F4 (mediana 25/06) e o teste.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_JANELA_FASE AS
SELECT e.NUM_FASE,
       f.NOME_FASE,
       f.TOTAL_CAPITULOS,
       MIN(e.TS_EVENTO)              AS DT_PRIMEIRO_EVENTO,
       MEDIAN(e.TS_EVENTO)           AS DT_MEDIANA,
       MAX(e.TS_EVENTO)              AS DT_ULTIMO_EVENTO,
       COUNT(DISTINCT e.NOME)        AS ALUNOS,
       COUNT(*)                      AS EVENTOS
  FROM EVENTOS_LMS e
  JOIN DIM_FASE f ON f.NUM_FASE = e.NUM_FASE
 WHERE e.FLG_ALUNO = 1
 GROUP BY e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS;

-- ---------------------------------------------------------------------------
-- 2) View de features por (aluno, fase) - sempre atualizada a partir de EVENTOS_LMS
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_FEATURES_TRANSICAO_FASE AS
WITH ev AS (
  SELECT e.NOME,
         e.NUM_FASE,
         e.TS_EVENTO,
         e.CAPITULO,
         NVL(t.CLASSE_EVENTO, 'OUTRO') AS CLASSE_EVENTO,
         j.DT_ULTIMO_EVENTO            AS DT_FIM_FASE,   -- ultimo evento de qualquer aluno na fase
         j.DT_MEDIANA                  AS DT_MEDIANA_FASE
    FROM EVENTOS_LMS e
    LEFT JOIN DIM_TIPO_EVENTO t ON t.EVENTO = e.EVENTO
    JOIN VW_JANELA_FASE j ON j.NUM_FASE = e.NUM_FASE
   WHERE e.FLG_ALUNO = 1
),
agg AS (
  SELECT NOME,
         NUM_FASE,
         COUNT(*)                                                         AS TOTAL_EVENTOS,
         COUNT(DISTINCT TRUNC(TS_EVENTO))                                 AS DIAS_ATIVOS,
         ROUND(MAX(TS_EVENTO) - MIN(TS_EVENTO), 2)                        AS SPAN_DIAS,
         SUM(CASE WHEN CLASSE_EVENTO = 'PROGRESSO'    THEN 1 ELSE 0 END)  AS EVENTOS_PROGRESSO,
         NVL(MAX(CAPITULO), 0)                                            AS CAPITULO_MAX,
         SUM(CASE WHEN CLASSE_EVENTO = 'QUIZ_INICIO'  THEN 1 ELSE 0 END)  AS QUIZ_INICIADOS,
         SUM(CASE WHEN CLASSE_EVENTO = 'QUIZ_ENTREGA' THEN 1 ELSE 0 END)  AS QUIZ_ENTREGUES,
         SUM(CASE WHEN CLASSE_EVENTO = 'ENTREGA'      THEN 1 ELSE 0 END)  AS ENTREGAS_TAREFA,
         ROUND(MAX(DT_FIM_FASE) - MAX(TS_EVENTO), 2)                      AS RECENCIA_FIM_FASE,
         -- tendencia: eventos nas ultimas 2 semanas da fase vs. 2 semanas anteriores
         SUM(CASE WHEN TS_EVENTO >  DT_FIM_FASE - 14 THEN 1 ELSE 0 END)   AS EVENTOS_ULT_2SEM,
         SUM(CASE WHEN TS_EVENTO <= DT_FIM_FASE - 14
                   AND TS_EVENTO >  DT_FIM_FASE - 28 THEN 1 ELSE 0 END)   AS EVENTOS_2SEM_ANT,
         -- perfil de horario: noite (19h-23h) e fim de semana (sab/dom, independente de NLS)
         SUM(CASE WHEN TO_NUMBER(TO_CHAR(TS_EVENTO, 'HH24')) BETWEEN 19 AND 23 THEN 1 ELSE 0 END) AS EVENTOS_NOITE,
         SUM(CASE WHEN TRUNC(TS_EVENTO) - TRUNC(TS_EVENTO, 'IW') >= 5 THEN 1 ELSE 0 END)          AS EVENTOS_FIM_SEMANA,
         MAX(DT_MEDIANA_FASE)                                             AS DT_MEDIANA_FASE
    FROM ev
   GROUP BY NOME, NUM_FASE
),
presenca AS (
  SELECT DISTINCT NOME, NUM_FASE FROM ev
)
SELECT a.NOME || '_F' || a.NUM_FASE                                   AS ID_CASO,
       a.NOME,
       a.NUM_FASE,
       f.NOME_FASE,
       a.TOTAL_EVENTOS,
       a.DIAS_ATIVOS,
       a.SPAN_DIAS,
       a.EVENTOS_PROGRESSO,
       a.CAPITULO_MAX,
       ROUND(a.CAPITULO_MAX / f.TOTAL_CAPITULOS, 4)                    AS PCT_CAPITULOS,
       a.QUIZ_INICIADOS,
       a.QUIZ_ENTREGUES,
       a.ENTREGAS_TAREFA,
       a.RECENCIA_FIM_FASE,
       ROUND(a.EVENTOS_ULT_2SEM / NULLIF(a.EVENTOS_2SEM_ANT, 0), 4)    AS TENDENCIA,
       ROUND(a.EVENTOS_NOITE / a.TOTAL_EVENTOS, 4)                     AS SHARE_NOITE,
       ROUND(a.EVENTOS_FIM_SEMANA / a.TOTAL_EVENTOS, 4)                AS SHARE_FIM_SEMANA,
       CASE WHEN a.NUM_FASE >= 5 THEN NULL            -- ultima fase: nao ha "proxima"
            WHEN p.NOME IS NULL THEN 1 ELSE 0 END                       AS EVADIU_PROXIMA_FASE,
       a.DT_MEDIANA_FASE,
       CASE WHEN a.NUM_FASE >= 5 THEN 'SEM_ROTULO'
            WHEN a.DT_MEDIANA_FASE < DATE '2026-06-01' THEN 'TREINO'
            ELSE 'TESTE' END                                            AS CONJUNTO
  FROM agg a
  JOIN DIM_FASE f ON f.NUM_FASE = a.NUM_FASE
  LEFT JOIN presenca p ON p.NOME = a.NOME AND p.NUM_FASE = a.NUM_FASE + 1;

-- ---------------------------------------------------------------------------
-- 3) Materializacao para treino/avaliacao (snapshot reproduzivel)
-- ---------------------------------------------------------------------------
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE FEATURES_TRANSICAO_FASE PURGE';
EXCEPTION WHEN OTHERS THEN
  IF SQLCODE != -942 THEN RAISE; END IF;
END;
/

CREATE TABLE FEATURES_TRANSICAO_FASE AS
SELECT * FROM VW_FEATURES_TRANSICAO_FASE;

ALTER TABLE FEATURES_TRANSICAO_FASE ADD CONSTRAINT PK_FEATURES_TRANSICAO PRIMARY KEY (ID_CASO);

BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(USER, 'FEATURES_TRANSICAO_FASE');
END;
/

-- ---------------------------------------------------------------------------
-- 4) Verificacoes
-- ---------------------------------------------------------------------------
SELECT NUM_FASE, NOME_FASE, TOTAL_CAPITULOS, ALUNOS, EVENTOS,
       TO_CHAR(DT_PRIMEIRO_EVENTO, 'YYYY-MM-DD') DT_PRIMEIRO,
       TO_CHAR(DT_MEDIANA, 'YYYY-MM-DD')         DT_MEDIANA,
       TO_CHAR(DT_ULTIMO_EVENTO, 'YYYY-MM-DD')   DT_ULTIMO
  FROM VW_JANELA_FASE ORDER BY NUM_FASE;

SELECT NUM_FASE, CONJUNTO, COUNT(*) ALUNOS,
       SUM(EVADIU_PROXIMA_FASE) EVADIRAM,
       ROUND(AVG(EVADIU_PROXIMA_FASE), 4) TAXA_EVASAO,
       ROUND(AVG(TOTAL_EVENTOS), 1) MEDIA_EVENTOS,
       ROUND(AVG(PCT_CAPITULOS), 3) MEDIA_PCT_CAP,
       ROUND(AVG(RECENCIA_FIM_FASE), 1) MEDIA_RECENCIA
  FROM FEATURES_TRANSICAO_FASE
 GROUP BY NUM_FASE, CONJUNTO ORDER BY NUM_FASE;

SELECT * FROM FEATURES_TRANSICAO_FASE WHERE CONJUNTO = 'TREINO' ORDER BY EVADIU_PROXIMA_FASE DESC, NOME FETCH FIRST 8 ROWS ONLY;
