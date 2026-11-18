-- =============================================================================
-- 08_mvp_contato_resultado.sql - MVP final: fecha o ciclo "fila -> contato -> resultado -> receita"
-- DENTRO do Oracle AI Database (26ai Free local; mesmo SQL no Autonomous AI Database).
--
--   PARAMETRO_IES        : parametros de negocio da IES (ticket mensal, horizonte em meses), editaveis pelo painel
--   CONTATO_RESULTADO    : cada contato registrado pela coordenacao/tutoria (historico imutavel, append-only)
--   PRC_REGISTRAR_CONTATO: valida o aluno, grava o contato com o risco do momento e atualiza o status da fila
--                          (RISCO_ALUNO_SNAPSHOT.STATUS_ATENDIMENTO) na MESMA transacao
--   VW_FILA_COORDENACAO  : fila de segunda-feira (snapshot do scoring OML + ultimo contato)
--   VW_DIRETORIA_RESUMO  : numeros da diretoria recalculados a partir do banco (risco e receita preservada)
--   VW_RESULTADO_CONTATOS: taxa de resultado por faixa de risco (insumo do retreino com o resultado real)
--
-- Idempotente: pode ser executado varias vezes. Nao apaga contatos ja registrados.
-- Pre-requisito: 05_scoring_views.sql (RISCO_ALUNO_SNAPSHOT + JOB_RETENA_SCORING_SEMANAL).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1) Parametros de negocio da IES (o ticket muda o R$ da diretoria sem tocar em codigo)
-- ---------------------------------------------------------------------------
DECLARE
  n NUMBER;
BEGIN
  SELECT COUNT(*) INTO n FROM user_tables WHERE table_name = 'PARAMETRO_IES';
  IF n = 0 THEN
    EXECUTE IMMEDIATE q'[
      CREATE TABLE PARAMETRO_IES (
        CHAVE          VARCHAR2(40 CHAR)  PRIMARY KEY,
        VALOR          NUMBER             NOT NULL,
        DESCRICAO      VARCHAR2(200 CHAR),
        DT_ATUALIZACAO TIMESTAMP          DEFAULT SYSTIMESTAMP NOT NULL
      )]';
  END IF;
END;
/

MERGE INTO PARAMETRO_IES d
USING (SELECT 'TICKET_MENSAL' CHAVE, 350 VALOR,
              'Mensalidade media EAD em R$ (estimativa R$ 250-450 do brief; a IES informa o seu)' DESCRICAO FROM dual
       UNION ALL
       SELECT 'MESES_HORIZONTE', 12, 'Meses de receita considerados por aluno retido/em risco' FROM dual
       UNION ALL
       SELECT 'META_REATIVACAO_PCT', 30, 'Meta do piloto: % dos alunos de alto risco reengajados em 30 dias' FROM dual) s
ON (d.CHAVE = s.CHAVE)
WHEN NOT MATCHED THEN INSERT (CHAVE, VALOR, DESCRICAO) VALUES (s.CHAVE, s.VALOR, s.DESCRICAO);
COMMIT;

-- ---------------------------------------------------------------------------
-- 2) Historico de contatos (append-only). Sem FK para o snapshot de proposito: o snapshot e
--    recriado quando o pipeline e reexecutado; o historico de contatos nunca pode se perder.
-- ---------------------------------------------------------------------------
DECLARE
  n NUMBER;
BEGIN
  SELECT COUNT(*) INTO n FROM user_tables WHERE table_name = 'CONTATO_RESULTADO';
  IF n = 0 THEN
    EXECUTE IMMEDIATE q'[
      CREATE TABLE CONTATO_RESULTADO (
        ID_CONTATO        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        NOME              VARCHAR2(30 CHAR)  NOT NULL,
        DT_CONTATO        TIMESTAMP          DEFAULT SYSTIMESTAMP NOT NULL,
        RESULTADO         VARCHAR2(20 CHAR)  NOT NULL,
        CANAL             VARCHAR2(20 CHAR)  DEFAULT 'WHATSAPP' NOT NULL,
        RESPONSAVEL       VARCHAR2(60 CHAR),
        OBSERVACAO        VARCHAR2(400 CHAR),
        PROB_NO_CONTATO   NUMBER(6,4),
        FAIXA_NO_CONTATO  VARCHAR2(10 CHAR),
        DT_SCORING_REF    TIMESTAMP,
        ORIGEM            VARCHAR2(20 CHAR)  DEFAULT 'PAINEL' NOT NULL,
        CONSTRAINT CK_CONTATO_RESULTADO CHECK (RESULTADO IN ('REATIVADO', 'PLANO_COMBINADO', 'SEM_RESPOSTA', 'VAI_CANCELAR')),
        CONSTRAINT CK_CONTATO_CANAL     CHECK (CANAL IN ('WHATSAPP', 'TELEFONE', 'EMAIL', 'LMS', 'PRESENCIAL'))
      )]';
    EXECUTE IMMEDIATE 'CREATE INDEX IX_CONTATO_ALUNO_DT ON CONTATO_RESULTADO (NOME, DT_CONTATO)';
  END IF;
END;
/

COMMENT ON TABLE CONTATO_RESULTADO IS 'Retena MVP: resultado de cada contato da coordenacao/tutoria com aluno da fila (pseudonimizado)';

-- ---------------------------------------------------------------------------
-- 3) Status da fila aceita o desfecho "vai cancelar" (encaminhado a retencao financeira)
-- ---------------------------------------------------------------------------
BEGIN
  EXECUTE IMMEDIATE 'ALTER TABLE RISCO_ALUNO_SNAPSHOT DROP CONSTRAINT CK_RISCO_STATUS';
EXCEPTION WHEN OTHERS THEN
  IF SQLCODE != -2443 THEN RAISE; END IF;   -- ORA-02443: constraint inexistente
END;
/
ALTER TABLE RISCO_ALUNO_SNAPSHOT ADD CONSTRAINT CK_RISCO_STATUS
  CHECK (STATUS_ATENDIMENTO IN ('PENDENTE', 'CONTATADO', 'REATIVADO', 'SEM_RETORNO', 'CANCELAMENTO', 'IGNORAR'));

-- ---------------------------------------------------------------------------
-- 4) Regra de negocio no banco: registrar contato + atualizar a fila na mesma transacao
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE PRC_REGISTRAR_CONTATO (
  p_nome        IN  VARCHAR2,
  p_resultado   IN  VARCHAR2,
  p_canal       IN  VARCHAR2 DEFAULT 'WHATSAPP',
  p_responsavel IN  VARCHAR2 DEFAULT NULL,
  p_observacao  IN  VARCHAR2 DEFAULT NULL,
  p_id_contato  OUT NUMBER,
  p_novo_status OUT VARCHAR2
) IS
  v_prob   RISCO_ALUNO_SNAPSHOT.PROB_INATIVO_21D%TYPE;
  v_faixa  RISCO_ALUNO_SNAPSHOT.FAIXA_RISCO%TYPE;
  v_dtsc   RISCO_ALUNO_SNAPSHOT.DT_SCORING%TYPE;
BEGIN
  BEGIN
    SELECT PROB_INATIVO_21D, FAIXA_RISCO, DT_SCORING INTO v_prob, v_faixa, v_dtsc
      FROM RISCO_ALUNO_SNAPSHOT WHERE NOME = p_nome FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20001, 'Aluno nao encontrado no snapshot de risco: ' || p_nome);
  END;

  p_novo_status := CASE UPPER(p_resultado)
                     WHEN 'REATIVADO'       THEN 'REATIVADO'
                     WHEN 'PLANO_COMBINADO' THEN 'CONTATADO'
                     WHEN 'SEM_RESPOSTA'    THEN 'SEM_RETORNO'
                     WHEN 'VAI_CANCELAR'    THEN 'CANCELAMENTO'
                   END;
  IF p_novo_status IS NULL THEN
    RAISE_APPLICATION_ERROR(-20002, 'Resultado invalido: ' || p_resultado);
  END IF;

  INSERT INTO CONTATO_RESULTADO (NOME, RESULTADO, CANAL, RESPONSAVEL, OBSERVACAO,
                                 PROB_NO_CONTATO, FAIXA_NO_CONTATO, DT_SCORING_REF)
  VALUES (p_nome, UPPER(p_resultado), UPPER(NVL(p_canal, 'WHATSAPP')), SUBSTR(p_responsavel, 1, 60),
          SUBSTR(p_observacao, 1, 400), v_prob, v_faixa, v_dtsc)
  RETURNING ID_CONTATO INTO p_id_contato;

  UPDATE RISCO_ALUNO_SNAPSHOT
     SET STATUS_ATENDIMENTO = p_novo_status,
         OBSERVACAO         = SUBSTR(TO_CHAR(SYSTIMESTAMP, 'DD/MM HH24:MI') || ' ' || UPPER(p_resultado) ||
                                     NVL2(p_observacao, ' - ' || p_observacao, ''), 1, 400)
   WHERE NOME = p_nome;
  COMMIT;
END PRC_REGISTRAR_CONTATO;
/

-- ---------------------------------------------------------------------------
-- 5) Re-sincroniza a fila com o historico (necessario se o pipeline 05 recriou o snapshot)
-- ---------------------------------------------------------------------------
MERGE INTO RISCO_ALUNO_SNAPSHOT d
USING (SELECT NOME,
              CASE RESULTADO WHEN 'REATIVADO' THEN 'REATIVADO' WHEN 'PLANO_COMBINADO' THEN 'CONTATADO'
                             WHEN 'SEM_RESPOSTA' THEN 'SEM_RETORNO' WHEN 'VAI_CANCELAR' THEN 'CANCELAMENTO' END STATUS
         FROM (SELECT c.*, ROW_NUMBER() OVER (PARTITION BY NOME ORDER BY DT_CONTATO DESC, ID_CONTATO DESC) rn
                 FROM CONTATO_RESULTADO c)
        WHERE rn = 1) s
ON (d.NOME = s.NOME)
WHEN MATCHED THEN UPDATE SET d.STATUS_ATENDIMENTO = s.STATUS WHERE d.STATUS_ATENDIMENTO = 'PENDENTE';
COMMIT;

-- ---------------------------------------------------------------------------
-- 6) Fila da coordenacao: snapshot OML + ultimo contato + tentativas
--    Prioridade = risco x chance de recuperacao ("quem esta a duas semanas de sumir" vem primeiro):
--      1 Agir agora : risco alto e ultimo acesso ha ate 30 dias (ainda recuperavel)
--      2 Atencao    : risco medio
--      3 Resgate    : risco alto e mais de 30 dias em silencio (reativacao, menor chance)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_FILA_COORDENACAO AS
WITH ult AS (
  SELECT NOME, RESULTADO ULTIMO_RESULTADO, DT_CONTATO DT_ULTIMO_CONTATO, CANAL ULTIMO_CANAL, TENTATIVAS
    FROM (SELECT c.NOME, c.RESULTADO, c.DT_CONTATO, c.CANAL,
                 COUNT(*) OVER (PARTITION BY c.NOME) TENTATIVAS,
                 ROW_NUMBER() OVER (PARTITION BY c.NOME ORDER BY c.DT_CONTATO DESC, c.ID_CONTATO DESC) rn
            FROM CONTATO_RESULTADO c)
   WHERE rn = 1
)
SELECT ROW_NUMBER() OVER (ORDER BY CASE WHEN r.FAIXA_RISCO IN ('Alto', 'Médio')
                                             AND r.STATUS_ATENDIMENTO IN ('PENDENTE', 'SEM_RETORNO') THEN 0 ELSE 1 END,
                                   CASE WHEN r.FAIXA_RISCO = 'Alto' AND r.RECENCIA_DIAS <= 30 THEN 1
                                        WHEN r.FAIXA_RISCO = 'Médio' THEN 2
                                        WHEN r.FAIXA_RISCO = 'Alto' THEN 3 ELSE 4 END,
                                   r.PROB_INATIVO_21D DESC, r.RECENCIA_DIAS ASC, r.NOME) AS POSICAO,
       CASE WHEN r.FAIXA_RISCO = 'Alto' AND r.RECENCIA_DIAS <= 30 THEN 'Agir agora'
            WHEN r.FAIXA_RISCO = 'Médio' THEN 'Atenção'
            WHEN r.FAIXA_RISCO = 'Alto' THEN 'Resgate'
            ELSE 'Monitorar' END AS GRUPO_FILA,
       r.NOME, r.NUM_FASE_ATUAL, r.NOME_FASE, r.CAPITULO_MAX_FASE, r.PCT_CAPITULOS_FASE,
       r.RECENCIA_DIAS, r.EVENTOS_7D, r.EVENTOS_28D, r.DIAS_ATIVOS_28D, r.TENDENCIA,
       r.PROB_INATIVO_21D, r.PROB_INATIVO_21D_GLM, r.PROB_EVASAO_FASE, r.FAIXA_RISCO,
       r.FATORES_TOP3, r.FATORES_JSON, r.ACAO_SUGERIDA, r.STATUS_ATENDIMENTO, r.OBSERVACAO,
       r.DT_CORTE, r.DT_SCORING,
       u.ULTIMO_RESULTADO, u.DT_ULTIMO_CONTATO, u.ULTIMO_CANAL, NVL(u.TENTATIVAS, 0) AS TENTATIVAS,
       CASE WHEN r.FAIXA_RISCO IN ('Alto', 'Médio') AND r.STATUS_ATENDIMENTO IN ('PENDENTE', 'SEM_RETORNO')
            THEN 1 ELSE 0 END AS NA_FILA
  FROM RISCO_ALUNO_SNAPSHOT r
  LEFT JOIN ult u ON u.NOME = r.NOME;

-- ---------------------------------------------------------------------------
-- 7) Visao da diretoria recalculada a partir do banco (ticket e horizonte vem de PARAMETRO_IES)
--    Receita anual em risco  = alunos de alto risco x ticket x horizonte (mesma regra do painel offline)
--    Perda esperada          = soma(prob. de inatividade) x ticket x horizonte (alto + medio)
--    Receita preservada      = alunos cujo ULTIMO contato e REATIVADO x ticket x horizonte (estimativa:
--                              em producao a reativacao e confirmada quando o LMS registra novo acesso em 7 dias)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_DIRETORIA_RESUMO AS
WITH p AS (
  SELECT MAX(CASE WHEN CHAVE = 'TICKET_MENSAL'       THEN VALOR END) TICKET,
         MAX(CASE WHEN CHAVE = 'MESES_HORIZONTE'     THEN VALOR END) MESES,
         MAX(CASE WHEN CHAVE = 'META_REATIVACAO_PCT' THEN VALOR END) META_PCT
    FROM PARAMETRO_IES
),
ult AS (
  SELECT NOME, RESULTADO, FAIXA_NO_CONTATO
    FROM (SELECT c.*, ROW_NUMBER() OVER (PARTITION BY NOME ORDER BY DT_CONTATO DESC, ID_CONTATO DESC) rn
            FROM CONTATO_RESULTADO c)
   WHERE rn = 1
),
r AS (
  SELECT COUNT(*)                                                             TOTAL_ALUNOS,
         SUM(CASE WHEN FAIXA_RISCO = 'Alto'  THEN 1 ELSE 0 END)               ALUNOS_ALTO,
         SUM(CASE WHEN FAIXA_RISCO = 'Médio' THEN 1 ELSE 0 END)               ALUNOS_MEDIO,
         SUM(CASE WHEN FAIXA_RISCO = 'Baixo' THEN 1 ELSE 0 END)               ALUNOS_BAIXO,
         SUM(CASE WHEN FAIXA_RISCO IN ('Alto', 'Médio')
                   AND STATUS_ATENDIMENTO IN ('PENDENTE', 'SEM_RETORNO') THEN 1 ELSE 0 END) NA_FILA,
         SUM(CASE WHEN FAIXA_RISCO = 'Alto' AND EVENTOS_28D > 0 THEN 1 ELSE 0 END) ALTO_AINDA_ATIVOS,
         SUM(CASE WHEN RECENCIA_DIAS > 14 THEN 1 ELSE 0 END)                  SILENCIOSOS_14D,
         SUM(CASE WHEN RECENCIA_DIAS > 30 THEN 1 ELSE 0 END)                  SILENCIOSOS_30D,
         SUM(CASE WHEN FAIXA_RISCO IN ('Alto', 'Médio') THEN PROB_INATIVO_21D ELSE 0 END) SOMA_PROB,
         MAX(DT_CORTE)                                                        DT_CORTE,
         MAX(DT_SCORING)                                                      DT_SCORING
    FROM RISCO_ALUNO_SNAPSHOT
),
c AS (
  SELECT COUNT(*)                                                             ALUNOS_CONTATADOS,
         SUM(CASE WHEN RESULTADO = 'REATIVADO'       THEN 1 ELSE 0 END)       REATIVADOS,
         SUM(CASE WHEN RESULTADO = 'REATIVADO' AND FAIXA_NO_CONTATO = 'Alto' THEN 1 ELSE 0 END) REATIVADOS_ALTO,
         SUM(CASE WHEN RESULTADO = 'PLANO_COMBINADO' THEN 1 ELSE 0 END)       PLANOS,
         SUM(CASE WHEN RESULTADO = 'SEM_RESPOSTA'    THEN 1 ELSE 0 END)       SEM_RESPOSTA,
         SUM(CASE WHEN RESULTADO = 'VAI_CANCELAR'    THEN 1 ELSE 0 END)       VAI_CANCELAR
    FROM ult
)
SELECT r.TOTAL_ALUNOS, r.ALUNOS_ALTO, r.ALUNOS_MEDIO, r.ALUNOS_BAIXO, r.NA_FILA, r.ALTO_AINDA_ATIVOS,
       r.SILENCIOSOS_14D, r.SILENCIOSOS_30D, r.DT_CORTE, r.DT_SCORING,
       p.TICKET, p.MESES, p.META_PCT,
       r.ALUNOS_ALTO * p.TICKET * p.MESES                          AS RECEITA_ANUAL_EM_RISCO,
       ROUND(r.SOMA_PROB * p.TICKET * p.MESES, 2)                  AS PERDA_ESPERADA_ANUAL,
       (SELECT COUNT(*) FROM CONTATO_RESULTADO)                   AS CONTATOS_REGISTRADOS, c.ALUNOS_CONTATADOS, NVL(c.REATIVADOS, 0) REATIVADOS, NVL(c.REATIVADOS_ALTO, 0) REATIVADOS_ALTO,
       NVL(c.PLANOS, 0) PLANOS, NVL(c.SEM_RESPOSTA, 0) SEM_RESPOSTA, NVL(c.VAI_CANCELAR, 0) VAI_CANCELAR,
       NVL(c.REATIVADOS, 0) * p.TICKET * p.MESES                   AS RECEITA_PRESERVADA_ESTIMADA,
       CEIL(r.ALUNOS_ALTO * p.META_PCT / 100)                      AS META_REATIVACOES,
       ROUND(100 * NVL(c.REATIVADOS_ALTO, 0) / NULLIF(r.ALUNOS_ALTO, 0), 1) AS PCT_META_ATINGIDA_BASE
  FROM r CROSS JOIN p CROSS JOIN c;

-- ---------------------------------------------------------------------------
-- 8) Resultado real dos contatos por faixa de risco (o que alimenta o retreino com rotulo de intervencao)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW VW_RESULTADO_CONTATOS AS
SELECT FAIXA_NO_CONTATO                                                  AS FAIXA,
       COUNT(*)                                                          AS CONTATOS,
       SUM(CASE WHEN RESULTADO = 'REATIVADO' THEN 1 ELSE 0 END)          AS REATIVADOS,
       ROUND(100 * AVG(CASE WHEN RESULTADO = 'REATIVADO' THEN 1 ELSE 0 END), 1) AS TAXA_REATIVACAO_PCT,
       ROUND(AVG(PROB_NO_CONTATO), 3)                                    AS PROB_MEDIA_NO_CONTATO
  FROM CONTATO_RESULTADO
 GROUP BY FAIXA_NO_CONTATO;

-- ---------------------------------------------------------------------------
-- 9) Verificacoes
-- ---------------------------------------------------------------------------
SELECT CHAVE, VALOR FROM PARAMETRO_IES ORDER BY CHAVE;
SELECT COUNT(*) contatos_registrados FROM CONTATO_RESULTADO;
SELECT NA_FILA, COUNT(*) alunos FROM VW_FILA_COORDENACAO GROUP BY NA_FILA;
SELECT TOTAL_ALUNOS, ALUNOS_ALTO, ALUNOS_MEDIO, NA_FILA, TICKET, RECEITA_ANUAL_EM_RISCO, PERDA_ESPERADA_ANUAL,
       REATIVADOS, RECEITA_PRESERVADA_ESTIMADA FROM VW_DIRETORIA_RESUMO;
