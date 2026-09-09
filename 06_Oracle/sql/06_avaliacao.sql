-- =============================================================================
-- 06_avaliacao.sql - Avaliacao dos modelos OML no conjunto de TESTE (validacao temporal)
--   RETENA_INATIVO21_RF / RETENA_INATIVO21_GLM : cortes >= 2026-06-01 (1.655 casos, 387 positivos)
--   RETENA_TRANSICAO_GLM                       : transicao Fase 4 -> Fase 5 (166 casos, 13 positivos)
-- Metricas: AUC (DBMS_DATA_MINING.COMPUTE_ROC e, como contraprova, AUC por SQL com funcoes de janela -
--           estatistica de Mann-Whitney), matriz de confusao no limiar 0,5, taxa observada por faixa,
--           lift por decil (COMPUTE_LIFT) e atributos importantes (views DM$V* geradas pelo OML).
-- Tudo fica registrado na tabela AVALIACAO_MODELOS (lida por scripts/gerar_evidencias.py).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) Scores do conjunto de teste (uma passada por modelo, materializada)
-- ---------------------------------------------------------------------------
BEGIN
  FOR t IN (SELECT table_name FROM user_tables
             WHERE table_name IN ('SCORES_TESTE', 'AVALIACAO_MODELOS', 'ALVO_TESTE_INATIVO21', 'ALVO_TESTE_TRANSICAO')
                OR table_name LIKE 'APPLY\_%' ESCAPE '\' OR table_name LIKE 'ROC\_%' ESCAPE '\' OR table_name LIKE 'LIFT\_%' ESCAPE '\') LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' PURGE';
  END LOOP;
END;
/

CREATE TABLE SCORES_TESTE AS
SELECT 'RETENA_INATIVO21_RF' AS MODELO, ID_CASO, INATIVO_21D AS ALVO,
       PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING *) AS PROB
  FROM VW_TESTE_INATIVIDADE
UNION ALL
SELECT 'RETENA_INATIVO21_GLM', ID_CASO, INATIVO_21D,
       PREDICTION_PROBABILITY(RETENA_INATIVO21_GLM, 1 USING *)
  FROM VW_TESTE_INATIVIDADE
UNION ALL
SELECT 'RETENA_TRANSICAO_GLM', ID_CASO, EVADIU_PROXIMA_FASE,
       PREDICTION_PROBABILITY(RETENA_TRANSICAO_GLM, 1 USING *)
  FROM VW_TESTE_TRANSICAO;

CREATE TABLE AVALIACAO_MODELOS (
  MODELO       VARCHAR2(40)  NOT NULL,
  METRICA      VARCHAR2(60)  NOT NULL,
  VALOR        NUMBER,
  DETALHE      VARCHAR2(400),
  DT_AVALIACAO TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT PK_AVALIACAO_MODELOS PRIMARY KEY (MODELO, METRICA)
);

INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
SELECT MODELO, 'N_TESTE', COUNT(*), 'casos no conjunto de teste (cortes >= 2026-06-01 / fase 4)' FROM SCORES_TESTE GROUP BY MODELO;
INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
SELECT MODELO, 'POSITIVOS_TESTE', SUM(ALVO), 'casos com alvo = 1 no teste' FROM SCORES_TESTE GROUP BY MODELO;
INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
SELECT MODELO, 'PREVALENCIA_TESTE', ROUND(AVG(ALVO), 4), 'taxa base de positivos no teste' FROM SCORES_TESTE GROUP BY MODELO;

-- ---------------------------------------------------------------------------
-- 2) AUC por SQL (Mann-Whitney com rank medio para empates): AUC = (soma_rank_pos - n_pos(n_pos+1)/2) / (n_pos*n_neg)
-- ---------------------------------------------------------------------------
INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
WITH r AS (
  SELECT MODELO, ALVO, PROB,
         RANK() OVER (PARTITION BY MODELO ORDER BY PROB) + (COUNT(*) OVER (PARTITION BY MODELO, PROB) - 1) / 2 AS RANK_MEDIO
    FROM SCORES_TESTE
)
SELECT MODELO, 'AUC_SQL',
       ROUND((SUM(CASE WHEN ALVO = 1 THEN RANK_MEDIO END) - SUM(ALVO) * (SUM(ALVO) + 1) / 2)
             / (SUM(ALVO) * (COUNT(*) - SUM(ALVO))), 4),
       'AUC-ROC calculada em SQL puro (funcoes analiticas, estatistica U de Mann-Whitney)'
  FROM r GROUP BY MODELO;

-- ---------------------------------------------------------------------------
-- 3) AUC oficial via DBMS_DATA_MINING.COMPUTE_ROC + lift por decil via COMPUTE_LIFT
--    (formato "apply result": uma linha por caso x classe com PREDICTION e PROBABILITY)
-- ---------------------------------------------------------------------------
CREATE TABLE ALVO_TESTE_INATIVO21 AS SELECT ID_CASO, INATIVO_21D         AS ALVO FROM VW_TESTE_INATIVIDADE;
CREATE TABLE ALVO_TESTE_TRANSICAO AS SELECT ID_CASO, EVADIU_PROXIMA_FASE AS ALVO FROM VW_TESTE_TRANSICAO;

CREATE TABLE APPLY_INATIVO21_RF AS
SELECT ID_CASO, 1 AS PREDICTION, PROB AS PROBABILITY FROM SCORES_TESTE WHERE MODELO = 'RETENA_INATIVO21_RF'
UNION ALL
SELECT ID_CASO, 0, 1 - PROB FROM SCORES_TESTE WHERE MODELO = 'RETENA_INATIVO21_RF';

CREATE TABLE APPLY_INATIVO21_GLM AS
SELECT ID_CASO, 1 AS PREDICTION, PROB AS PROBABILITY FROM SCORES_TESTE WHERE MODELO = 'RETENA_INATIVO21_GLM'
UNION ALL
SELECT ID_CASO, 0, 1 - PROB FROM SCORES_TESTE WHERE MODELO = 'RETENA_INATIVO21_GLM';

CREATE TABLE APPLY_TRANSICAO_GLM AS
SELECT ID_CASO, 1 AS PREDICTION, PROB AS PROBABILITY FROM SCORES_TESTE WHERE MODELO = 'RETENA_TRANSICAO_GLM'
UNION ALL
SELECT ID_CASO, 0, 1 - PROB FROM SCORES_TESTE WHERE MODELO = 'RETENA_TRANSICAO_GLM';

DECLARE
  v_auc NUMBER;
  PROCEDURE avaliar(p_modelo VARCHAR2, p_apply VARCHAR2, p_alvo VARCHAR2, p_sufixo VARCHAR2) IS
    v_t0  TIMESTAMP := SYSTIMESTAMP;
    v_err VARCHAR2(400);
  BEGIN
    DBMS_DATA_MINING.COMPUTE_ROC(
      roc_area_under_curve        => v_auc,
      apply_result_table_name     => p_apply,
      target_table_name           => p_alvo,
      case_id_column_name         => 'ID_CASO',
      target_column_name          => 'ALVO',
      score_column_name           => 'PREDICTION',
      score_criterion_column_name => 'PROBABILITY',
      roc_table_name              => 'ROC_' || p_sufixo,
      positive_target_value       => '1');
    INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
    VALUES (p_modelo, 'AUC_COMPUTE_ROC', ROUND(v_auc, 4), 'DBMS_DATA_MINING.COMPUTE_ROC (tabela ROC_' || p_sufixo || ')');
    DBMS_DATA_MINING.COMPUTE_LIFT(
      apply_result_table_name     => p_apply,
      target_table_name           => p_alvo,
      case_id_column_name         => 'ID_CASO',
      target_column_name          => 'ALVO',
      lift_table_name             => 'LIFT_' || p_sufixo,
      positive_target_value       => '1',
      score_column_name           => 'PREDICTION',
      score_criterion_column_name => 'PROBABILITY',
      num_quantiles               => 10);
    DBMS_OUTPUT.PUT_LINE(p_modelo || ': AUC (COMPUTE_ROC) = ' || TO_CHAR(ROUND(v_auc, 4), 'FM0.0000') ||
      ' | ROC_' || p_sufixo || ' e LIFT_' || p_sufixo || ' gerados em ' ||
      TO_CHAR(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_t0)), 'FM9990.00') || ' s');
  EXCEPTION WHEN OTHERS THEN
    -- SQLERRM nao pode ser referenciado diretamente dentro de um INSERT (ORA-00984): copia para variavel
    v_err := 'ERRO: ' || SUBSTR(SQLERRM, 1, 380);
    INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
    VALUES (p_modelo, 'AUC_COMPUTE_ROC', NULL, v_err);
    DBMS_OUTPUT.PUT_LINE(p_modelo || ': COMPUTE_ROC/COMPUTE_LIFT falhou -> ' || v_err);
  END;
BEGIN
  avaliar('RETENA_INATIVO21_RF',  'APPLY_INATIVO21_RF',  'ALVO_TESTE_INATIVO21', 'INATIVO21_RF');
  avaliar('RETENA_INATIVO21_GLM', 'APPLY_INATIVO21_GLM', 'ALVO_TESTE_INATIVO21', 'INATIVO21_GLM');
  avaliar('RETENA_TRANSICAO_GLM', 'APPLY_TRANSICAO_GLM', 'ALVO_TESTE_TRANSICAO', 'TRANSICAO_GLM');
END;
/

-- ---------------------------------------------------------------------------
-- 4) Matriz de confusao no limiar 0,5 + metricas derivadas
-- ---------------------------------------------------------------------------
INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
WITH m AS (
  SELECT MODELO,
         SUM(CASE WHEN PROB >= 0.5 AND ALVO = 1 THEN 1 ELSE 0 END) TP,
         SUM(CASE WHEN PROB >= 0.5 AND ALVO = 0 THEN 1 ELSE 0 END) FP,
         SUM(CASE WHEN PROB <  0.5 AND ALVO = 1 THEN 1 ELSE 0 END) FN,
         SUM(CASE WHEN PROB <  0.5 AND ALVO = 0 THEN 1 ELSE 0 END) TN
    FROM SCORES_TESTE GROUP BY MODELO
)
SELECT MODELO, METRICA, VALOR, DETALHE FROM m
UNPIVOT (VALOR FOR METRICA IN (TP AS 'TP_0.5', FP AS 'FP_0.5', FN AS 'FN_0.5', TN AS 'TN_0.5'))
CROSS JOIN (SELECT 'matriz de confusao, limiar 0,5' DETALHE FROM dual);

INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
WITH m AS (
  SELECT MODELO,
         SUM(CASE WHEN PROB >= 0.5 AND ALVO = 1 THEN 1 ELSE 0 END) TP,
         SUM(CASE WHEN PROB >= 0.5 AND ALVO = 0 THEN 1 ELSE 0 END) FP,
         SUM(CASE WHEN PROB <  0.5 AND ALVO = 1 THEN 1 ELSE 0 END) FN,
         SUM(CASE WHEN PROB <  0.5 AND ALVO = 0 THEN 1 ELSE 0 END) TN
    FROM SCORES_TESTE GROUP BY MODELO
)
SELECT MODELO, 'ACURACIA_0.5',  ROUND((TP + TN) / (TP + FP + FN + TN), 4), 'limiar 0,5' FROM m UNION ALL
SELECT MODELO, 'PRECISAO_0.5',  ROUND(TP / NULLIF(TP + FP, 0), 4), 'limiar 0,5' FROM m UNION ALL
SELECT MODELO, 'RECALL_0.5',    ROUND(TP / NULLIF(TP + FN, 0), 4), 'limiar 0,5 (sensibilidade)' FROM m UNION ALL
SELECT MODELO, 'ESPECIFIC_0.5', ROUND(TN / NULLIF(TN + FP, 0), 4), 'limiar 0,5' FROM m UNION ALL
SELECT MODELO, 'F1_0.5',        ROUND(2 * TP / NULLIF(2 * TP + FP + FN, 0), 4), 'limiar 0,5' FROM m UNION ALL
SELECT MODELO, 'ACUR_BALANC_0.5', ROUND((TP / NULLIF(TP + FN, 0) + TN / NULLIF(TN + FP, 0)) / 2, 4), 'media de recall e especificidade' FROM m;

-- ---------------------------------------------------------------------------
-- 5) Taxa observada por faixa (calibracao das faixas Alto/Medio/Baixo no teste)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_AVALIACAO_FAIXAS AS
SELECT MODELO,
       CASE WHEN PROB >= 0.60 THEN 'Alto' WHEN PROB >= 0.30 THEN 'Médio' ELSE 'Baixo' END AS FAIXA,
       COUNT(*) CASOS, SUM(ALVO) POSITIVOS, ROUND(AVG(ALVO), 4) TAXA_OBSERVADA, ROUND(AVG(PROB), 4) PROB_MEDIA,
       ROUND(SUM(ALVO) / SUM(SUM(ALVO)) OVER (PARTITION BY MODELO), 4) CAPTURA_DOS_POSITIVOS
  FROM SCORES_TESTE
 GROUP BY MODELO, CASE WHEN PROB >= 0.60 THEN 'Alto' WHEN PROB >= 0.30 THEN 'Médio' ELSE 'Baixo' END;

INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
SELECT MODELO, 'TAXA_OBS_' || UPPER(FAIXA), TAXA_OBSERVADA,
       CASOS || ' casos, ' || POSITIVOS || ' positivos, captura ' || ROUND(100 * CAPTURA_DOS_POSITIVOS, 1) || '% dos positivos'
  FROM VW_AVALIACAO_FAIXAS;

-- ---------------------------------------------------------------------------
-- 5b) Precisao e captura no TOP-20% de risco (capacidade operacional do tutor: contatar 1 em cada 5)
--     PERCENT_RANK ordena por probabilidade decrescente; os 20% primeiros formam a "fila"
-- ---------------------------------------------------------------------------
INSERT INTO AVALIACAO_MODELOS (MODELO, METRICA, VALOR, DETALHE)
WITH r AS (
  SELECT MODELO, ALVO, PROB,
         PERCENT_RANK() OVER (PARTITION BY MODELO ORDER BY PROB DESC, ID_CASO) AS PR
    FROM SCORES_TESTE
), top AS (
  SELECT MODELO, COUNT(*) N_TOP, SUM(ALVO) POS_TOP FROM r WHERE PR < 0.20 GROUP BY MODELO
), tot AS (
  SELECT MODELO, COUNT(*) N_TOT, SUM(ALVO) POS_TOT, ROUND(AVG(ALVO), 4) PREV FROM SCORES_TESTE GROUP BY MODELO
)
SELECT t.MODELO, m.METRICA,
       CASE m.METRICA WHEN 'PRECISAO_TOP20PCT' THEN ROUND(t.POS_TOP / t.N_TOP, 4)
                      WHEN 'CAPTURA_TOP20PCT'  THEN ROUND(t.POS_TOP / o.POS_TOT, 4)
                      WHEN 'LIFT_TOP20PCT'     THEN ROUND((t.POS_TOP / t.N_TOP) / o.PREV, 3) END,
       t.N_TOP || ' casos no top-20% (' || t.POS_TOP || ' positivos de ' || o.POS_TOT || '); prevalencia ' || o.PREV
  FROM top t JOIN tot o ON o.MODELO = t.MODELO
 CROSS JOIN (SELECT 'PRECISAO_TOP20PCT' METRICA FROM dual UNION ALL SELECT 'CAPTURA_TOP20PCT' FROM dual
             UNION ALL SELECT 'LIFT_TOP20PCT' FROM dual) m;

COMMIT;

-- ---------------------------------------------------------------------------
-- 6) Relatorios
-- ---------------------------------------------------------------------------
SELECT MODELO, METRICA, VALOR, DETALHE FROM AVALIACAO_MODELOS
 WHERE METRICA LIKE '%TOP20PCT' ORDER BY MODELO, METRICA;

-- ---------------------------------------------------------------------------
SELECT MODELO, METRICA, VALOR, DETALHE
  FROM AVALIACAO_MODELOS
 WHERE METRICA IN ('N_TESTE','POSITIVOS_TESTE','PREVALENCIA_TESTE','AUC_COMPUTE_ROC','AUC_SQL',
                   'ACURACIA_0.5','PRECISAO_0.5','RECALL_0.5','ESPECIFIC_0.5','F1_0.5','ACUR_BALANC_0.5')
 ORDER BY MODELO, DECODE(METRICA, 'N_TESTE',1,'POSITIVOS_TESTE',2,'PREVALENCIA_TESTE',3,'AUC_COMPUTE_ROC',4,'AUC_SQL',5,
                                  'ACURACIA_0.5',6,'ACUR_BALANC_0.5',7,'PRECISAO_0.5',8,'RECALL_0.5',9,'ESPECIFIC_0.5',10,'F1_0.5',11);

SELECT MODELO, METRICA, VALOR FROM AVALIACAO_MODELOS WHERE METRICA LIKE 'T%\_0.5' ESCAPE '\' OR METRICA LIKE 'F%\_0.5' ESCAPE '\'
 ORDER BY MODELO, METRICA;

SELECT * FROM VW_AVALIACAO_FAIXAS ORDER BY MODELO, PROB_MEDIA DESC;

-- lift por decil do modelo principal (10% mais arriscados: quantos positivos capturam?)
SELECT QUANTILE_NUMBER decil, PROBABILITY_THRESHOLD limiar_prob, TARGETS_CUMULATIVE positivos_acum,
       ROUND(LIFT_CUMULATIVE, 3) lift_acum, ROUND(GAIN_CUMULATIVE, 4) captura_acum, ROUND(PERCENTAGE_RECORDS_CUMULATIVE, 4) pct_casos_acum
  FROM LIFT_INATIVO21_RF ORDER BY QUANTILE_NUMBER;

-- ROC (pontos amostrados) do modelo principal
SELECT PROBABILITY, TRUE_POSITIVES, FALSE_NEGATIVES, FALSE_POSITIVES, TRUE_NEGATIVES,
       ROUND(TRUE_POSITIVE_FRACTION, 4) tpr, ROUND(FALSE_POSITIVE_FRACTION, 4) fpr
  FROM ROC_INATIVO21_RF WHERE MOD(ROWNUM, 40) = 1 OR PROBABILITY IN (SELECT MIN(PROBABILITY) FROM ROC_INATIVO21_RF)
 ORDER BY PROBABILITY DESC FETCH FIRST 15 ROWS ONLY;

-- atributos importantes: Random Forest (importancia nativa) e GLM (coeficientes na escala transformada pelo PREP_AUTO)
-- (alias PARTICIPACAO: "SHARE" e palavra reservada do Oracle e gera ORA-00923)
SELECT ATTRIBUTE_NAME, ROUND(ATTRIBUTE_IMPORTANCE, 4) IMPORTANCIA,
       ROUND(RATIO_TO_REPORT(ATTRIBUTE_IMPORTANCE) OVER (), 4) PARTICIPACAO
  FROM DM$VARETENA_INATIVO21_RF ORDER BY ATTRIBUTE_IMPORTANCE DESC;

SELECT NVL(ATTRIBUTE_NAME, '(intercepto)') ATRIBUTO, ROUND(COEFFICIENT, 4) COEFICIENTE, ROUND(STD_ERROR, 4) ERRO_PADRAO,
       ROUND(P_VALUE, 4) P_VALOR, ROUND(EXP(COEFFICIENT), 4) ODDS_RATIO
  FROM DM$VDRETENA_INATIVO21_GLM ORDER BY ABS(COEFFICIENT) DESC;

SELECT NVL(ATTRIBUTE_NAME, '(intercepto)') ATRIBUTO, ROUND(COEFFICIENT, 4) COEFICIENTE, ROUND(STD_ERROR, 4) ERRO_PADRAO,
       ROUND(P_VALUE, 4) P_VALOR, ROUND(EXP(COEFFICIENT), 4) ODDS_RATIO
  FROM DM$VDRETENA_TRANSICAO_GLM ORDER BY ABS(COEFFICIENT) DESC;

-- diagnosticos globais do treino (convergencia, numero de linhas, etc.)
SELECT 'RETENA_TRANSICAO_GLM' MODELO, NAME, NUMERIC_VALUE, STRING_VALUE FROM DM$VGRETENA_TRANSICAO_GLM
UNION ALL
SELECT 'RETENA_INATIVO21_GLM', NAME, NUMERIC_VALUE, STRING_VALUE FROM DM$VGRETENA_INATIVO21_GLM
UNION ALL
SELECT 'RETENA_INATIVO21_RF', NAME, NUMERIC_VALUE, STRING_VALUE FROM DM$VGRETENA_INATIVO21_RF
ORDER BY 1, 2;
