-- =============================================================================
-- 04_oml_modelos.sql - Treino IN-DATABASE com Oracle Machine Learning (DBMS_DATA_MINING.CREATE_MODEL2)
-- Modelos (todos com PREP_AUTO = ON: normalizacao, binning e tratamento de nulos ficam DENTRO do modelo):
--   RETENA_TRANSICAO_GLM : classificacao, GLM logistico  - evasao na proxima fase (alvo EVADIU_PROXIMA_FASE)
--                          treino = transicoes das fases 1->2, 2->3, 3->4 (CONJUNTO='TREINO', mediana < 2026-06-01)
--                          teste  = transicao 4->5 (CONJUNTO='TESTE')  -> validacao temporal, nao aleatoria
--   RETENA_INATIVO21_RF  : classificacao, Random Forest  - inatividade nos 21 dias seguintes ao corte semanal
--                          treino = cortes < 2026-06-01 (2.682 casos) | teste = cortes >= 2026-06-01 (1.655 casos)
--   RETENA_INATIVO21_GLM : classificacao, GLM logistico  - baseline linear para o mesmo alvo (comparado no 06)
-- Nenhum dado sai do banco: as views de treino sao lidas diretamente pelo motor OML.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) Limpeza: modelos anteriores + artefatos do teste de conectividade OML (OML_TEST*)
-- ---------------------------------------------------------------------------
BEGIN
  FOR m IN (SELECT model_name FROM user_mining_models
             WHERE model_name IN ('RETENA_TRANSICAO_GLM', 'RETENA_INATIVO21_RF', 'RETENA_INATIVO21_GLM',
                                  'MDL_TRANSICAO_FASE', 'MDL_INATIVIDADE_21D', 'MDL_INATIVIDADE_GLM', 'OML_TEST_MODEL')) LOOP
    DBMS_DATA_MINING.DROP_MODEL(m.model_name);
    DBMS_OUTPUT.PUT_LINE('Modelo removido: ' || m.model_name);
  END LOOP;
  FOR t IN (SELECT table_name FROM user_tables WHERE table_name = 'OML_TEST') LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' PURGE';
    DBMS_OUTPUT.PUT_LINE('Tabela de teste removida: ' || t.table_name);
  END LOOP;
END;
/

-- ---------------------------------------------------------------------------
-- 2) Views de treino/teste: apenas ID do caso + features + alvo (nenhuma coluna "vazante":
--    CONJUNTO, DT_MEDIANA_FASE, EVENTOS_FUTURO_21D etc. ficam fora)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_TREINO_TRANSICAO AS
SELECT ID_CASO,
       TOTAL_EVENTOS, DIAS_ATIVOS, SPAN_DIAS, EVENTOS_PROGRESSO, CAPITULO_MAX, PCT_CAPITULOS,
       QUIZ_INICIADOS, QUIZ_ENTREGUES, ENTREGAS_TAREFA, RECENCIA_FIM_FASE, TENDENCIA,
       SHARE_NOITE, SHARE_FIM_SEMANA,
       EVADIU_PROXIMA_FASE
  FROM FEATURES_TRANSICAO_FASE
 WHERE CONJUNTO = 'TREINO';

CREATE OR REPLACE VIEW VW_TESTE_TRANSICAO AS
SELECT ID_CASO,
       TOTAL_EVENTOS, DIAS_ATIVOS, SPAN_DIAS, EVENTOS_PROGRESSO, CAPITULO_MAX, PCT_CAPITULOS,
       QUIZ_INICIADOS, QUIZ_ENTREGUES, ENTREGAS_TAREFA, RECENCIA_FIM_FASE, TENDENCIA,
       SHARE_NOITE, SHARE_FIM_SEMANA,
       EVADIU_PROXIMA_FASE
  FROM FEATURES_TRANSICAO_FASE
 WHERE CONJUNTO = 'TESTE';

CREATE OR REPLACE VIEW VW_TREINO_INATIVIDADE AS
SELECT ID_CASO,
       EVENTOS_7D, EVENTOS_14D, EVENTOS_28D, DIAS_ATIVOS_28D, RECENCIA_DIAS, PROGRESSO_28D,
       CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA,
       INATIVO_21D
  FROM BASE_RISCO_SEMANAL
 WHERE CONJUNTO = 'TREINO';

CREATE OR REPLACE VIEW VW_TESTE_INATIVIDADE AS
SELECT ID_CASO,
       EVENTOS_7D, EVENTOS_14D, EVENTOS_28D, DIAS_ATIVOS_28D, RECENCIA_DIAS, PROGRESSO_28D,
       CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA,
       INATIVO_21D
  FROM BASE_RISCO_SEMANAL
 WHERE CONJUNTO = 'TESTE';

SELECT 'VW_TREINO_TRANSICAO' origem, COUNT(*) linhas, SUM(EVADIU_PROXIMA_FASE) positivos, ROUND(AVG(EVADIU_PROXIMA_FASE), 4) taxa FROM VW_TREINO_TRANSICAO
UNION ALL
SELECT 'VW_TESTE_TRANSICAO', COUNT(*), SUM(EVADIU_PROXIMA_FASE), ROUND(AVG(EVADIU_PROXIMA_FASE), 4) FROM VW_TESTE_TRANSICAO
UNION ALL
SELECT 'VW_TREINO_INATIVIDADE', COUNT(*), SUM(INATIVO_21D), ROUND(AVG(INATIVO_21D), 4) FROM VW_TREINO_INATIVIDADE
UNION ALL
SELECT 'VW_TESTE_INATIVIDADE', COUNT(*), SUM(INATIVO_21D), ROUND(AVG(INATIVO_21D), 4) FROM VW_TESTE_INATIVIDADE;

-- ---------------------------------------------------------------------------
-- 3) RETENA_TRANSICAO_GLM - GLM logistico (interpretavel: coeficiente por feature)
-- ---------------------------------------------------------------------------
DECLARE
  v_set DBMS_DATA_MINING.SETTING_LIST;
  v_t0  TIMESTAMP := SYSTIMESTAMP;
BEGIN
  v_set('ALGO_NAME')             := 'ALGO_GENERALIZED_LINEAR_MODEL';
  v_set('PREP_AUTO')             := 'ON';
  v_set('GLMS_RIDGE_REGRESSION') := 'GLMS_RIDGE_REG_ENABLE';   -- estabiliza com ~530 linhas e 32 positivos
  v_set('CLAS_WEIGHTS_BALANCED') := 'ON';                      -- classes desbalanceadas (~6% positivos)
  v_set('ODMS_DETAILS')          := 'ODMS_ENABLE';
  DBMS_DATA_MINING.CREATE_MODEL2(
    model_name          => 'RETENA_TRANSICAO_GLM',
    mining_function     => 'CLASSIFICATION',
    data_query          => 'SELECT * FROM VW_TREINO_TRANSICAO',
    set_list            => v_set,
    case_id_column_name => 'ID_CASO',
    target_column_name  => 'EVADIU_PROXIMA_FASE');
  DBMS_OUTPUT.PUT_LINE('RETENA_TRANSICAO_GLM treinado em ' ||
    TO_CHAR(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_t0)) + 60 * EXTRACT(MINUTE FROM (SYSTIMESTAMP - v_t0)), 'FM9990.00') ||
    ' s (' || TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') || ')');
END;
/

-- ---------------------------------------------------------------------------
-- 4) RETENA_INATIVO21_RF - Random Forest (nao linear, importancia de atributos nativa)
-- ---------------------------------------------------------------------------
DECLARE
  v_set DBMS_DATA_MINING.SETTING_LIST;
  v_t0  TIMESTAMP := SYSTIMESTAMP;
BEGIN
  v_set('ALGO_NAME')           := 'ALGO_RANDOM_FOREST';
  v_set('PREP_AUTO')           := 'ON';
  v_set('RFOR_NUM_TREES')      := '200';
  v_set('RFOR_SAMPLING_RATIO') := '0.6';
  v_set('ODMS_RANDOM_SEED')    := '42';                         -- reprodutibilidade
  v_set('ODMS_DETAILS')        := 'ODMS_ENABLE';
  DBMS_DATA_MINING.CREATE_MODEL2(
    model_name          => 'RETENA_INATIVO21_RF',
    mining_function     => 'CLASSIFICATION',
    data_query          => 'SELECT * FROM VW_TREINO_INATIVIDADE',
    set_list            => v_set,
    case_id_column_name => 'ID_CASO',
    target_column_name  => 'INATIVO_21D');
  DBMS_OUTPUT.PUT_LINE('RETENA_INATIVO21_RF treinado em ' ||
    TO_CHAR(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_t0)) + 60 * EXTRACT(MINUTE FROM (SYSTIMESTAMP - v_t0)), 'FM9990.00') ||
    ' s (' || TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') || ')');
END;
/

-- ---------------------------------------------------------------------------
-- 5) RETENA_INATIVO21_GLM - baseline linear para o mesmo alvo (comparacao de AUC no 06)
-- ---------------------------------------------------------------------------
DECLARE
  v_set DBMS_DATA_MINING.SETTING_LIST;
  v_t0  TIMESTAMP := SYSTIMESTAMP;
BEGIN
  v_set('ALGO_NAME')             := 'ALGO_GENERALIZED_LINEAR_MODEL';
  v_set('PREP_AUTO')             := 'ON';
  v_set('GLMS_RIDGE_REGRESSION') := 'GLMS_RIDGE_REG_ENABLE';
  v_set('CLAS_WEIGHTS_BALANCED') := 'ON';
  v_set('ODMS_DETAILS')          := 'ODMS_ENABLE';
  DBMS_DATA_MINING.CREATE_MODEL2(
    model_name          => 'RETENA_INATIVO21_GLM',
    mining_function     => 'CLASSIFICATION',
    data_query          => 'SELECT * FROM VW_TREINO_INATIVIDADE',
    set_list            => v_set,
    case_id_column_name => 'ID_CASO',
    target_column_name  => 'INATIVO_21D');
  DBMS_OUTPUT.PUT_LINE('RETENA_INATIVO21_GLM treinado em ' ||
    TO_CHAR(EXTRACT(SECOND FROM (SYSTIMESTAMP - v_t0)) + 60 * EXTRACT(MINUTE FROM (SYSTIMESTAMP - v_t0)), 'FM9990.00') ||
    ' s (' || TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') || ')');
END;
/

-- ---------------------------------------------------------------------------
-- 6) Catalogo: modelos, settings e atributos usados
-- ---------------------------------------------------------------------------
SELECT model_name, mining_function, algorithm, TO_CHAR(creation_date, 'YYYY-MM-DD HH24:MI:SS') criado_em,
       build_duration seg_treino, model_size bytes
  FROM user_mining_models ORDER BY model_name;

SELECT model_name, setting_name, setting_value, setting_type
  FROM user_mining_model_settings
 WHERE model_name LIKE 'RETENA%'
   AND setting_name IN ('ALGO_NAME','PREP_AUTO','CLAS_WEIGHTS_BALANCED','GLMS_RIDGE_REGRESSION',
                        'RFOR_NUM_TREES','RFOR_SAMPLING_RATIO','ODMS_RANDOM_SEED','ODMS_MISSING_VALUE_TREATMENT')
 ORDER BY model_name, setting_name;

SELECT model_name, attribute_name, attribute_type, data_type, target
  FROM user_mining_model_attributes
 WHERE model_name LIKE 'RETENA%'
 ORDER BY model_name, target DESC, attribute_name;

-- Views de detalhes geradas automaticamente pelo OML (DM$V*): base do 06_avaliacao.sql
SELECT view_name, view_type FROM user_mining_model_views WHERE model_name LIKE 'RETENA%' ORDER BY model_name, view_name;

-- Scoring imediato por SQL (prova de que o modelo "roda onde os dados estao")
SELECT ID_CASO,
       EVADIU_PROXIMA_FASE                                                AS real,
       PREDICTION(RETENA_TRANSICAO_GLM USING *)                           AS previsto,
       ROUND(PREDICTION_PROBABILITY(RETENA_TRANSICAO_GLM, 1 USING *), 4)  AS prob_evasao
  FROM VW_TESTE_TRANSICAO
 ORDER BY prob_evasao DESC
 FETCH FIRST 10 ROWS ONLY;

SELECT ID_CASO,
       INATIVO_21D                                                        AS real,
       ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING *), 4)   AS prob_rf,
       ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_GLM, 1 USING *), 4)  AS prob_glm
  FROM VW_TESTE_INATIVIDADE
 ORDER BY prob_rf DESC
 FETCH FIRST 10 ROWS ONLY;
