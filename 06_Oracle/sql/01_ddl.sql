-- =============================================================================
-- 01_ddl.sql - Modelo fisico da camada de eventos do LMS (Oracle AI Database 26ai Free)
-- Projeto: Startup One / Enterprise Challenge Oracle - previsao de evasao a partir de logs de LMS
-- Convencao: statements SQL terminam com ";"  |  blocos PL/SQL terminam com "/" em linha propria
-- Idempotente: pode ser executado varias vezes (drop condicional).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0) Limpeza condicional (ordem: dependentes primeiro)
-- ---------------------------------------------------------------------------
DECLARE
  PROCEDURE drop_se_existe(p_tipo VARCHAR2, p_nome VARCHAR2) IS
    v_qtd NUMBER;
  BEGIN
    SELECT COUNT(*) INTO v_qtd FROM user_objects
     WHERE object_name = UPPER(p_nome) AND object_type = UPPER(p_tipo);
    IF v_qtd > 0 THEN
      EXECUTE IMMEDIATE 'DROP ' || p_tipo || ' ' || p_nome ||
                        CASE WHEN UPPER(p_tipo) = 'TABLE' THEN ' CASCADE CONSTRAINTS PURGE' END;
      DBMS_OUTPUT.PUT_LINE('Removido: ' || p_tipo || ' ' || p_nome);
    END IF;
  END;
BEGIN
  drop_se_existe('TABLE', 'EVENTOS_LMS');
  drop_se_existe('TABLE', 'DIM_FASE');
  drop_se_existe('TABLE', 'DIM_TIPO_EVENTO');
END;
/

-- ---------------------------------------------------------------------------
-- 1) DIM_FASE - cursos sequenciais (Fase 1..5) com total de capitulos de cada um
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_FASE (
  NUM_FASE         NUMBER(1)          NOT NULL,
  NOME_FASE        VARCHAR2(20 CHAR)  NOT NULL,
  TOTAL_CAPITULOS  NUMBER(3)          NOT NULL,
  CONSTRAINT PK_DIM_FASE PRIMARY KEY (NUM_FASE),
  CONSTRAINT UK_DIM_FASE_NOME UNIQUE (NOME_FASE)
);

INSERT INTO DIM_FASE (NUM_FASE, NOME_FASE, TOTAL_CAPITULOS)
SELECT 1, 'Fase 1', 10 FROM dual UNION ALL
SELECT 2, 'Fase 2', 12 FROM dual UNION ALL
SELECT 3, 'Fase 3', 10 FROM dual UNION ALL
SELECT 4, 'Fase 4', 11 FROM dual UNION ALL
SELECT 5, 'Fase 5',  8 FROM dual;

-- ---------------------------------------------------------------------------
-- 2) DIM_TIPO_EVENTO - taxonomia de eventos do LMS usada pelo feature engineering
--    (dimensao configuravel: novos nomes de evento do LMS entram aqui, sem alterar as views)
--    Classes: PROGRESSO | VISUALIZACAO | QUIZ_INICIO | QUIZ_ENTREGA | ENTREGA | NOTA | OUTRO
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_TIPO_EVENTO (
  EVENTO         VARCHAR2(120 CHAR) NOT NULL,
  CLASSE_EVENTO  VARCHAR2(20 CHAR)  NOT NULL,
  OBSERVACAO     VARCHAR2(200 CHAR),
  CONSTRAINT PK_DIM_TIPO_EVENTO PRIMARY KEY (EVENTO),
  CONSTRAINT CK_DIM_TIPO_EVENTO_CLASSE CHECK (CLASSE_EVENTO IN
    ('PROGRESSO','VISUALIZACAO','QUIZ_INICIO','QUIZ_ENTREGA','ENTREGA','NOTA','OUTRO'))
);

INSERT INTO DIM_TIPO_EVENTO (EVENTO, CLASSE_EVENTO, OBSERVACAO)
SELECT 'Progresso de conteúdo atualizado',   'PROGRESSO',    'Componente Flags - avanco no player HTML'          FROM dual UNION ALL
SELECT 'Conteúdo HTML visualizado',          'VISUALIZACAO', 'Player de Conteudo'                                 FROM dual UNION ALL
SELECT 'Conteudo PDF visualizado',           'VISUALIZACAO', 'Player de PDF'                                      FROM dual UNION ALL
SELECT 'Módulo do curso visualizado',        'VISUALIZACAO', 'Tarefa / Questionario'                              FROM dual UNION ALL
SELECT 'Box de resumo da fase visualizada',  'VISUALIZACAO', 'Home'                                               FROM dual UNION ALL
SELECT 'Tentativa do questionário iniciada', 'QUIZ_INICIO',  'Questionario'                                       FROM dual UNION ALL
SELECT 'Tentativa do questionário entregue', 'QUIZ_ENTREGA', 'Questionario'                                       FROM dual UNION ALL
SELECT 'Um envio foi submetido.',            'ENTREGA',      'Tarefa (assign) - entrega do aluno'                  FROM dual UNION ALL
SELECT 'Entregou uma atividade',             'ENTREGA',      'Atividade'                                          FROM dual UNION ALL
SELECT 'Um arquivo foi enviado.',            'ENTREGA',      'Envio de arquivos'                                  FROM dual UNION ALL
SELECT 'Usuário recebeu nota',               'NOTA',         'Sistema'                                            FROM dual UNION ALL
SELECT 'Nota assign enviado',                'NOTA',         'Notas'                                              FROM dual;

-- ---------------------------------------------------------------------------
-- 3) EVENTOS_LMS - fato de eventos (1 linha por evento do log do LMS)
--    Colunas virtuais derivam fase numerica, capitulo (regex "Cap (\d+)") e flag de aluno,
--    mantendo a regra de negocio dentro do banco (mesma definicao para SQL, OML e APEX).
-- ---------------------------------------------------------------------------
CREATE TABLE EVENTOS_LMS (
  ID_EVENTO        NUMBER GENERATED ALWAYS AS IDENTITY,
  FASE             VARCHAR2(10 CHAR)   NOT NULL,
  TS_EVENTO        DATE                NOT NULL,
  NOME             VARCHAR2(30 CHAR)   NOT NULL,
  USUARIO_AFETADO  VARCHAR2(30 CHAR),
  CONTEXTO         VARCHAR2(300 CHAR),
  COMPONENTE       VARCHAR2(60 CHAR),
  EVENTO           VARCHAR2(120 CHAR),
  DESCRICAO        VARCHAR2(1000 CHAR),
  ORIGEM           VARCHAR2(10 CHAR),
  -- derivadas (virtuais, sem custo de armazenamento)
  NUM_FASE         NUMBER(1)  GENERATED ALWAYS AS (TO_NUMBER(REGEXP_SUBSTR(FASE, '\d+'))) VIRTUAL,
  CAPITULO         NUMBER(3)  GENERATED ALWAYS AS (TO_NUMBER(REGEXP_SUBSTR(CONTEXTO, 'Cap (\d+)', 1, 1, NULL, 1))) VIRTUAL,
  FLG_ALUNO        NUMBER(1)  GENERATED ALWAYS AS (CASE WHEN NOME LIKE 'Aluno%' THEN 1 ELSE 0 END) VIRTUAL,
  CONSTRAINT PK_EVENTOS_LMS PRIMARY KEY (ID_EVENTO)
);

COMMENT ON TABLE  EVENTOS_LMS IS 'Eventos brutos do LMS (export FIAP ON / Moodle-like). Fonte: logs_lms.parquet';
COMMENT ON COLUMN EVENTOS_LMS.TS_EVENTO IS 'Data/hora do evento (origem "dd/mm/yyyy HH24:MI")';
COMMENT ON COLUMN EVENTOS_LMS.NOME      IS 'Aluno anonimizado ("Aluno NNNN") ou "-" para eventos de sistema/professor';
COMMENT ON COLUMN EVENTOS_LMS.CAPITULO  IS 'Capitulo extraido do contexto via regex "Cap (\d+)" (NULL quando nao se aplica)';

-- Indices: acesso por aluno/fase/tempo (features) e por tempo (cortes semanais)
CREATE INDEX IX_EVENTOS_ALUNO_FASE_TS ON EVENTOS_LMS (NOME, NUM_FASE, TS_EVENTO);
CREATE INDEX IX_EVENTOS_TS            ON EVENTOS_LMS (TS_EVENTO);
CREATE INDEX IX_EVENTOS_EVENTO        ON EVENTOS_LMS (EVENTO);

COMMIT;
