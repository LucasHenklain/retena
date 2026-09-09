-- =============================================================================
-- 03_features_semanais.sql - Feature engineering IN-DATABASE: risco de inatividade 21 dias
-- Cortes semanais t (domingos) de 2026-02-01 a 2026-08-02 (27 cortes) + 1 corte "ATUAL"
-- (= ultimo dia com eventos, para scoring do dashboard). Para cada corte t e cada aluno com
-- >= 1 evento ate t: features calculadas so com eventos <= t (dia do corte incluso) e rotulo
-- INATIVO_21D = 1 quando o aluno nao tem eventos em (t, t+21d].
--
-- Decisoes de engenharia:
--  * pre-agregacao em grao aluno x dia (VW_ATIVIDADE_DIARIA, ~20 mil linhas) antes de cruzar
--    com os cortes -> evita join de 680 mil eventos x 28 cortes;
--  * UMA definicao de features (SQL Macro de tabela FN_FEATURES_SEMANAIS) reutilizada pelo
--    treino (cortes HIST) e pelo scoring (corte ATUAL) -> zero "training/serving skew".
--
-- Licao aprendida (registrada no log 03_features_semanais.log da 1a tentativa):
--    em SQL Macro de tabela, o parametro escalar so e substituido quando referenciado no
--    bloco SELECT principal do texto retornado; dentro de uma CTE (WITH ...) o Oracle 23ai/26ai
--    devolve ORA-00904 "P_TIPO_CORTE": invalid identifier. Por isso o filtro de tipo de corte
--    fica no WHERE final (o otimizador o empurra ate VW_CORTES_SEMANAIS via predicate pushdown).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) Calendario de cortes
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_CORTES_SEMANAIS AS
SELECT DATE '2026-02-01' + 7 * (LEVEL - 1) AS DT_CORTE, 'HIST' AS TIPO_CORTE
  FROM dual
CONNECT BY LEVEL <= (DATE '2026-08-02' - DATE '2026-02-01') / 7 + 1
UNION ALL
SELECT TRUNC(MAX(TS_EVENTO)), 'ATUAL' FROM EVENTOS_LMS WHERE FLG_ALUNO = 1;

-- ---------------------------------------------------------------------------
-- 2) Grao diario por aluno (view reutilizavel)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_ATIVIDADE_DIARIA AS
SELECT e.NOME,
       TRUNC(e.TS_EVENTO)                                                        AS DIA,
       COUNT(*)                                                                  AS EVENTOS,
       SUM(CASE WHEN t.CLASSE_EVENTO = 'PROGRESSO' THEN 1 ELSE 0 END)            AS PROGRESSO,
       SUM(CASE WHEN t.CLASSE_EVENTO IN ('QUIZ_INICIO','QUIZ_ENTREGA') THEN 1 ELSE 0 END) AS QUIZ,
       SUM(CASE WHEN t.CLASSE_EVENTO = 'ENTREGA' THEN 1 ELSE 0 END)              AS ENTREGAS,
       MAX(e.NUM_FASE)                                                           AS FASE_MAX_DIA
  FROM EVENTOS_LMS e
  LEFT JOIN DIM_TIPO_EVENTO t ON t.EVENTO = e.EVENTO
 WHERE e.FLG_ALUNO = 1
 GROUP BY e.NOME, TRUNC(e.TS_EVENTO);

-- Capitulos distintos tocados por aluno x dia (fase*100+capitulo evita colisao entre fases)
CREATE OR REPLACE VIEW VW_CAPITULOS_DIARIOS AS
SELECT DISTINCT e.NOME, TRUNC(e.TS_EVENTO) AS DIA, e.NUM_FASE * 100 + e.CAPITULO AS COD_CAPITULO
  FROM EVENTOS_LMS e
 WHERE e.FLG_ALUNO = 1 AND e.CAPITULO IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 3) SQL Macro de tabela: features por (aluno, corte). p_tipo_corte = 'HIST' | 'ATUAL' | 'TODOS'
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION FN_FEATURES_SEMANAIS(p_tipo_corte IN VARCHAR2 DEFAULT 'TODOS')
RETURN CLOB SQL_MACRO(TABLE) IS
BEGIN
  RETURN q'[
WITH cortes AS (
  SELECT DT_CORTE, TIPO_CORTE
    FROM VW_CORTES_SEMANAIS
),
base AS (      -- alunos elegiveis no corte: primeiro evento <= t
  SELECT c.DT_CORTE, c.TIPO_CORTE, a.NOME
    FROM cortes c
    JOIN (SELECT NOME, MIN(DIA) AS PRIMEIRO_DIA FROM VW_ATIVIDADE_DIARIA GROUP BY NOME) a
      ON a.PRIMEIRO_DIA <= c.DT_CORTE
),
agg AS (       -- uma passada: janelas 7/14/28d, historico ate t e futuro (t, t+21]
  SELECT b.DT_CORTE, b.TIPO_CORTE, b.NOME,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 7  AND d.DIA <= b.DT_CORTE THEN d.EVENTOS   ELSE 0 END) AS EVENTOS_7D,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 14 AND d.DIA <= b.DT_CORTE THEN d.EVENTOS   ELSE 0 END) AS EVENTOS_14D,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 28 AND d.DIA <= b.DT_CORTE THEN d.EVENTOS   ELSE 0 END) AS EVENTOS_28D,
         COUNT(CASE WHEN d.DIA > b.DT_CORTE - 28 AND d.DIA <= b.DT_CORTE THEN d.DIA           END) AS DIAS_ATIVOS_28D,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 28 AND d.DIA <= b.DT_CORTE THEN d.PROGRESSO ELSE 0 END) AS PROGRESSO_28D,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 28 AND d.DIA <= b.DT_CORTE THEN d.QUIZ      ELSE 0 END) AS QUIZ_28D,
         SUM(CASE WHEN d.DIA > b.DT_CORTE - 28 AND d.DIA <= b.DT_CORTE THEN d.ENTREGAS  ELSE 0 END) AS ENTREGAS_28D,
         MAX(CASE WHEN d.DIA <= b.DT_CORTE THEN d.DIA          END)                                 AS ULTIMO_DIA,
         MAX(CASE WHEN d.DIA <= b.DT_CORTE THEN d.FASE_MAX_DIA END)                                 AS NUM_FASE_ATUAL,
         SUM(CASE WHEN d.DIA <= b.DT_CORTE THEN d.EVENTOS ELSE 0 END)                               AS EVENTOS_ACUMULADOS,
         SUM(CASE WHEN d.DIA > b.DT_CORTE AND d.DIA <= b.DT_CORTE + 21 THEN d.EVENTOS ELSE 0 END)   AS EVENTOS_FUTURO_21D
    FROM base b
    JOIN VW_ATIVIDADE_DIARIA d ON d.NOME = b.NOME AND d.DIA <= b.DT_CORTE + 21
   GROUP BY b.DT_CORTE, b.TIPO_CORTE, b.NOME
),
caps AS (
  SELECT b.DT_CORTE, b.NOME, COUNT(DISTINCT dc.COD_CAPITULO) AS CAPITULOS_DISTINTOS_28D
    FROM base b
    JOIN VW_CAPITULOS_DIARIOS dc ON dc.NOME = b.NOME AND dc.DIA > b.DT_CORTE - 28 AND dc.DIA <= b.DT_CORTE
   GROUP BY b.DT_CORTE, b.NOME
)
SELECT a.NOME || '_' || TO_CHAR(a.DT_CORTE, 'YYYYMMDD')            AS ID_CASO,
       a.DT_CORTE,
       a.TIPO_CORTE,
       a.NOME,
       a.EVENTOS_7D,
       a.EVENTOS_14D,
       a.EVENTOS_28D,
       a.DIAS_ATIVOS_28D,
       a.DT_CORTE - a.ULTIMO_DIA                                    AS RECENCIA_DIAS,
       a.PROGRESSO_28D,
       NVL(c.CAPITULOS_DISTINTOS_28D, 0)                            AS CAPITULOS_DISTINTOS_28D,
       a.QUIZ_28D,
       a.ENTREGAS_28D,
       ROUND(a.EVENTOS_7D / (a.EVENTOS_28D / 4 + 1), 4)             AS TENDENCIA,
       a.NUM_FASE_ATUAL,
       a.EVENTOS_ACUMULADOS,
       a.EVENTOS_FUTURO_21D,
       CASE WHEN a.TIPO_CORTE = 'ATUAL' THEN NULL
            WHEN a.EVENTOS_FUTURO_21D = 0 THEN 1 ELSE 0 END         AS INATIVO_21D,
       CASE WHEN a.TIPO_CORTE = 'ATUAL' THEN 'ATUAL'
            WHEN a.DT_CORTE < DATE '2026-06-01' THEN 'TREINO'
            ELSE 'TESTE' END                                        AS CONJUNTO
  FROM agg a
  LEFT JOIN caps c ON c.DT_CORTE = a.DT_CORTE AND c.NOME = a.NOME
 WHERE (p_tipo_corte = 'TODOS' OR a.TIPO_CORTE = p_tipo_corte)
]';
END FN_FEATURES_SEMANAIS;
/

-- Views de conveniencia sobre a macro
CREATE OR REPLACE VIEW VW_FEATURES_SEMANAIS AS
SELECT * FROM FN_FEATURES_SEMANAIS('HIST');

CREATE OR REPLACE VIEW VW_FEATURES_ATUAIS AS
SELECT * FROM FN_FEATURES_SEMANAIS('ATUAL');

-- ---------------------------------------------------------------------------
-- 4) Materializacao da base historica rotulada
-- ---------------------------------------------------------------------------
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE BASE_RISCO_SEMANAL PURGE';
EXCEPTION WHEN OTHERS THEN
  IF SQLCODE != -942 THEN RAISE; END IF;
END;
/

CREATE TABLE BASE_RISCO_SEMANAL AS
SELECT * FROM VW_FEATURES_SEMANAIS;

ALTER TABLE BASE_RISCO_SEMANAL ADD CONSTRAINT PK_BASE_RISCO_SEMANAL PRIMARY KEY (ID_CASO);
CREATE INDEX IX_BASE_RISCO_CORTE ON BASE_RISCO_SEMANAL (DT_CORTE, NOME);

BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(USER, 'BASE_RISCO_SEMANAL');
END;
/

-- ---------------------------------------------------------------------------
-- 5) Verificacoes
-- ---------------------------------------------------------------------------
SELECT CONJUNTO, COUNT(DISTINCT DT_CORTE) CORTES, COUNT(*) LINHAS,
       SUM(INATIVO_21D) POSITIVOS, ROUND(AVG(INATIVO_21D), 4) TAXA_INATIVIDADE,
       TO_CHAR(MIN(DT_CORTE), 'YYYY-MM-DD') PRIMEIRO_CORTE, TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') ULTIMO_CORTE
  FROM BASE_RISCO_SEMANAL GROUP BY CONJUNTO ORDER BY 1 DESC;

SELECT TO_CHAR(DT_CORTE, 'YYYY-MM-DD') CORTE, CONJUNTO, COUNT(*) ALUNOS, SUM(INATIVO_21D) INATIVOS_21D,
       ROUND(AVG(INATIVO_21D), 3) TAXA, ROUND(AVG(EVENTOS_28D), 1) MEDIA_EV_28D, ROUND(AVG(RECENCIA_DIAS), 1) MEDIA_RECENCIA
  FROM BASE_RISCO_SEMANAL GROUP BY DT_CORTE, CONJUNTO ORDER BY DT_CORTE;

-- corte ATUAL (scoring): recalcula o grao diario a partir dos ~685 mil eventos (tempo medido no log)
SELECT COUNT(*) ALUNOS_CORTE_ATUAL, TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') DT_CORTE_ATUAL,
       SUM(CASE WHEN RECENCIA_DIAS > 21 THEN 1 ELSE 0 END) JA_INATIVOS_21D,
       SUM(CASE WHEN RECENCIA_DIAS <= 7 THEN 1 ELSE 0 END) ATIVOS_ULT_7D
  FROM VW_FEATURES_ATUAIS;
