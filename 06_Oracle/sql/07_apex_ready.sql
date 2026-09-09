-- =============================================================================
-- 07_apex_ready.sql - 5 consultas prontas para paginas APEX (Interactive Report / Cards / Chart)
-- Convencao de parametros: a CTE "parametros" simula os itens de pagina. No APEX basta trocar
-- os literais por binds (:P1_TICKET_MENSAL, :P1_MESES_RESTANTES, :P1_FAIXA_MINIMA).
-- Ticket medio EAD: R$ 350/mes (ponto medio da estimativa R$ 250-450 do brief do projeto - parametro da IES).
-- Todas as consultas leem apenas objetos deste pacote (snapshot + features + eventos) - sem pipeline externo.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) FILA DE SEGUNDA-FEIRA - quem contatar, por que e o que fazer (pagina inicial do coordenador)
--    Fonte: RISCO_ALUNO_SNAPSHOT (re-pontuado toda segunda 06:00 por DBMS_SCHEDULER)
-- ---------------------------------------------------------------------------
WITH parametros AS (SELECT 'Médio' AS FAIXA_MINIMA FROM dual)   -- APEX: :P1_FAIXA_MINIMA ('Alto' | 'Médio')
SELECT ROW_NUMBER() OVER (ORDER BY r.PROB_INATIVO_21D DESC, r.RECENCIA_DIAS DESC) AS POSICAO,
       r.NOME                                   AS ALUNO,
       r.NOME_FASE                              AS FASE,
       r.CAPITULO_MAX_FASE                      AS CAP_ATUAL,
       ROUND(100 * r.PCT_CAPITULOS_FASE)        AS PCT_FASE,
       r.RECENCIA_DIAS                          AS DIAS_SEM_ACESSO,
       r.EVENTOS_28D                            AS EVENTOS_28D,
       ROUND(100 * r.PROB_INATIVO_21D, 1)       AS RISCO_PCT,
       r.FAIXA_RISCO                            AS FAIXA,
       r.FATORES_TOP3                           AS POR_QUE,
       r.ACAO_SUGERIDA                          AS O_QUE_FAZER,
       r.STATUS_ATENDIMENTO                     AS STATUS,
       TO_CHAR(r.DT_SCORING, 'DD/MM HH24:MI')   AS PONTUADO_EM
  FROM RISCO_ALUNO_SNAPSHOT r
 CROSS JOIN parametros p
 WHERE r.STATUS_ATENDIMENTO IN ('PENDENTE', 'SEM_RETORNO')
   AND (p.FAIXA_MINIMA = 'Médio' AND r.FAIXA_RISCO IN ('Alto', 'Médio') OR p.FAIXA_MINIMA = 'Alto' AND r.FAIXA_RISCO = 'Alto')
 ORDER BY POSICAO
 FETCH FIRST 25 ROWS ONLY;

-- ---------------------------------------------------------------------------
-- 2) FUNIL POR FASE - quantos iniciaram cada fase, quantos avancaram e onde a coorte se perde
--    Fonte: FEATURES_TRANSICAO_FASE (rotulo evadiu_proxima_fase) + DIM_FASE
-- ---------------------------------------------------------------------------
SELECT f.NUM_FASE,
       f.NOME_FASE,
       f.TOTAL_CAPITULOS,
       COUNT(*)                                                       AS INICIARAM,
       COUNT(*) - NVL(SUM(t.EVADIU_PROXIMA_FASE), 0)                  AS AVANCARAM,
       NVL(SUM(t.EVADIU_PROXIMA_FASE), 0)                             AS EVADIRAM,
       ROUND(100 * NVL(AVG(t.EVADIU_PROXIMA_FASE), 0), 1)             AS TAXA_EVASAO_PCT,
       ROUND(100 * COUNT(*) / FIRST_VALUE(COUNT(*)) OVER (ORDER BY f.NUM_FASE), 1) AS PCT_DA_COORTE_F1,
       ROUND(AVG(t.PCT_CAPITULOS) * 100, 1)                           AS PROGRESSO_MEDIO_PCT,
       ROUND(AVG(t.DIAS_ATIVOS), 1)                                   AS DIAS_ATIVOS_MEDIO,
       CASE WHEN f.NUM_FASE = 5 THEN 'fase em andamento (sem rótulo)' END AS OBS
  FROM FEATURES_TRANSICAO_FASE t
  JOIN DIM_FASE f ON f.NUM_FASE = t.NUM_FASE
 GROUP BY f.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS
 ORDER BY f.NUM_FASE;

-- ---------------------------------------------------------------------------
-- 3) MAPA DE ATRITO POR CAPITULO - em qual capitulo os alunos "travam" antes de evadir
--    Chegaram = alunos cujo capitulo maximo na fase >= cap; Pararam = evadiram com capitulo maximo = cap
--    Esforco = eventos por aluno no capitulo (capitulos com muito esforco e muito atrito pedem revisao pedagogica)
-- ---------------------------------------------------------------------------
WITH caps AS (
  SELECT f.NUM_FASE, f.NOME_FASE, c.COLUMN_VALUE AS CAPITULO
    FROM DIM_FASE f,
         TABLE(CAST(MULTISET(SELECT LEVEL FROM dual CONNECT BY LEVEL <= f.TOTAL_CAPITULOS) AS SYS.ODCINUMBERLIST)) c
   WHERE f.NUM_FASE <= 4                                              -- fases com rotulo de transicao
),
esforco AS (
  SELECT NUM_FASE, CAPITULO, COUNT(*) EVENTOS, COUNT(DISTINCT NOME) ALUNOS_COM_EVENTO
    FROM EVENTOS_LMS WHERE FLG_ALUNO = 1 AND CAPITULO IS NOT NULL GROUP BY NUM_FASE, CAPITULO
)
SELECT c.NOME_FASE                                                   AS FASE,
       c.CAPITULO                                                    AS CAP,
       COUNT(t.NOME)                                                 AS CHEGARAM,
       SUM(CASE WHEN t.CAPITULO_MAX = c.CAPITULO AND t.EVADIU_PROXIMA_FASE = 1 THEN 1 ELSE 0 END) AS PARARAM_E_EVADIRAM,
       ROUND(100 * SUM(CASE WHEN t.CAPITULO_MAX = c.CAPITULO AND t.EVADIU_PROXIMA_FASE = 1 THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(t.NOME), 0), 1)                      AS ATRITO_PCT,
       ROUND(e.EVENTOS / NULLIF(e.ALUNOS_COM_EVENTO, 0), 1)          AS EVENTOS_POR_ALUNO,
       CASE WHEN SUM(CASE WHEN t.CAPITULO_MAX = c.CAPITULO AND t.EVADIU_PROXIMA_FASE = 1 THEN 1 ELSE 0 END) >= 3
            THEN 'revisar capítulo (dividir / vídeo curto / checkpoint)' END AS RECOMENDACAO
  FROM caps c
  LEFT JOIN FEATURES_TRANSICAO_FASE t ON t.NUM_FASE = c.NUM_FASE AND t.CAPITULO_MAX >= c.CAPITULO
  LEFT JOIN esforco e ON e.NUM_FASE = c.NUM_FASE AND e.CAPITULO = c.CAPITULO
 GROUP BY c.NUM_FASE, c.NOME_FASE, c.CAPITULO, e.EVENTOS, e.ALUNOS_COM_EVENTO
 ORDER BY c.NUM_FASE, c.CAPITULO;

-- ---------------------------------------------------------------------------
-- 4) RECEITA EM RISCO - por faixa e total, parametrizada pelo ticket medio da IES
--    Receita mensal em risco = soma(prob x ticket); horizonte = meses restantes do ciclo
-- ---------------------------------------------------------------------------
WITH parametros AS (SELECT 350 AS TICKET_MENSAL, 6 AS MESES_RESTANTES FROM dual)  -- APEX: :P1_TICKET_MENSAL, :P1_MESES_RESTANTES
SELECT NVL(r.FAIXA_RISCO, 'TOTAL')                                  AS FAIXA,
       COUNT(*)                                                     AS ALUNOS,
       ROUND(AVG(r.PROB_INATIVO_21D), 3)                            AS PROB_MEDIA,
       p.TICKET_MENSAL                                              AS TICKET,
       ROUND(COUNT(*) * p.TICKET_MENSAL, 2)                         AS RECEITA_MENSAL_BRUTA,
       ROUND(SUM(r.PROB_INATIVO_21D) * p.TICKET_MENSAL, 2)          AS RECEITA_MENSAL_EM_RISCO,
       ROUND(SUM(r.PROB_INATIVO_21D) * p.TICKET_MENSAL * p.MESES_RESTANTES, 2) AS RECEITA_CICLO_EM_RISCO,
       ROUND(100 * SUM(r.PROB_INATIVO_21D) / COUNT(*), 1)           AS PCT_RECEITA_EM_RISCO
  FROM RISCO_ALUNO_SNAPSHOT r
 CROSS JOIN parametros p
 GROUP BY ROLLUP(r.FAIXA_RISCO), p.TICKET_MENSAL, p.MESES_RESTANTES
 ORDER BY GROUPING(r.FAIXA_RISCO), PROB_MEDIA DESC;

-- ---------------------------------------------------------------------------
-- 5) REATIVACOES - alunos ja inativos (> 21 dias sem acesso no corte) que voltaram nos 21 dias seguintes
--    Base: BASE_RISCO_SEMANAL (cortes semanais historicos). Mede o "resgate" que a IES ja consegue
--    sem a Retena (baseline) e vira o KPI "receita preservada por reativacao" quando o contato e registrado.
-- ---------------------------------------------------------------------------
WITH parametros AS (SELECT 350 AS TICKET_MENSAL FROM dual)  -- APEX: :P1_TICKET_MENSAL
SELECT TO_CHAR(b.DT_CORTE, 'YYYY-MM')                                   AS MES_CORTE,
       COUNT(DISTINCT b.DT_CORTE)                                       AS CORTES,
       COUNT(*)                                                         AS CASOS_INATIVOS_21D,
       SUM(CASE WHEN b.EVENTOS_FUTURO_21D > 0 THEN 1 ELSE 0 END)        AS REATIVADOS_21D,
       ROUND(100 * AVG(CASE WHEN b.EVENTOS_FUTURO_21D > 0 THEN 1 ELSE 0 END), 1) AS TAXA_REATIVACAO_PCT,
       ROUND(AVG(CASE WHEN b.EVENTOS_FUTURO_21D > 0 THEN b.RECENCIA_DIAS END), 1) AS DIAS_INATIVO_MEDIO_REATIVADOS,
       COUNT(DISTINCT CASE WHEN b.EVENTOS_FUTURO_21D > 0 THEN b.NOME END) AS ALUNOS_DISTINTOS_REATIVADOS,
       COUNT(DISTINCT CASE WHEN b.EVENTOS_FUTURO_21D > 0 THEN b.NOME END) * p.TICKET_MENSAL AS RECEITA_MENSAL_PRESERVADA
  FROM BASE_RISCO_SEMANAL b
 CROSS JOIN parametros p
 WHERE b.RECENCIA_DIAS > 21
 GROUP BY TO_CHAR(b.DT_CORTE, 'YYYY-MM'), p.TICKET_MENSAL
 ORDER BY MES_CORTE;
