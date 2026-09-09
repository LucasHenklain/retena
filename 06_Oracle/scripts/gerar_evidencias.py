# -*- coding: utf-8 -*-
"""
gerar_evidencias.py - coleta EVIDENCIAS REAIS do Oracle (consultas executadas no momento da geracao)
e produz:
  evidencias/01_versao_banco.txt      versao, instancia, host, data/hora do banco
  evidencias/02_contagens.txt         contagens de EVENTOS_LMS, alunos, tabelas de features e snapshot
  evidencias/03_modelos_oml.txt       USER_MINING_MODELS / _SETTINGS / _ATTRIBUTES / views DM$V*
  evidencias/04_metricas.txt          AUC, matriz de confusao, faixas, lift e atributos importantes
  evidencias/05_scoring_amostra.csv   20 alunos de maior risco com fatores (PREDICTION_DETAILS)
  evidencias/06_json_api_amostra.json payload da VW_RISCO_JSON (amostra de 20 alunos)
  evidencias/07_docker.txt            docker ps + trecho de docker logs do container oracle-free
  evidencias/evidencias.html          relatorio tecnico (marca Retena) + evidencia_01.png..0N.png (Edge headless)

Uso: python gerar_evidencias.py [--sem-png]
Conexao: ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN (padrao STARTUP / Startup2026 / localhost:1521/FREEPDB1)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from executar_sql import ORACLE_DSN, ORACLE_USER, conectar, dividir_statements, formatar_tabela  # noqa: E402

RAIZ = os.path.dirname(AQUI)
EVID = os.path.join(RAIZ, "evidencias")
SQL_APEX = os.path.join(RAIZ, "sql", "07_apex_ready.sql")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CONTAINER = "oracle-free"


# ----------------------------------------------------------------------------- utilitarios
def agora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ler_lob(v):
    return v.read() if hasattr(v, "read") else v


def consultar(cur, sql, max_linhas=None):
    """Executa e devolve (colunas, linhas) com LOBs materializados."""
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    linhas = cur.fetchall() if max_linhas is None else cur.fetchmany(max_linhas)
    linhas = [tuple(ler_lob(v) for v in l) for l in linhas]
    return cols, linhas


def bloco(titulo, cols, linhas, max_larg=70):
    return f"== {titulo} ==\n{formatar_tabela(cols, linhas, max_larg=max_larg)}\n{len(linhas)} linha(s)\n"


def cabecalho(titulo):
    return (f"{titulo}\n{'=' * len(titulo)}\n"
            f"Gerado em (maquina local): {agora()}\n"
            f"Conexao: {ORACLE_USER}@{ORACLE_DSN} (python-oracledb thin)\n"
            f"Script: {os.path.abspath(__file__)}\n\n")


def gravar(nome, conteudo):
    caminho = os.path.join(EVID, nome)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo)
    print(f"  gravado {caminho} ({len(conteudo):,} chars)".replace(",", "."))
    return caminho


# ----------------------------------------------------------------------------- coletas
def col_versao(cur):
    secoes = []
    secoes.append(bloco("v$version", *consultar(cur, "SELECT banner_full FROM v$version"), max_larg=110))
    secoes.append(bloco("Instancia / host / container", *consultar(cur, """
        SELECT SYS_CONTEXT('USERENV','INSTANCE_NAME') instance_name,
               SYS_CONTEXT('USERENV','SERVER_HOST')   host_name,
               SYS_CONTEXT('USERENV','DB_NAME')       db_name,
               SYS_CONTEXT('USERENV','CON_NAME')      pdb,
               SYS_CONTEXT('USERENV','SERVICE_NAME')  service_name,
               SYS_CONTEXT('USERENV','CURRENT_USER')  usuario
          FROM dual""")))
    secoes.append(bloco("Data/hora do banco (fuso do container = UTC) x sessao", *consultar(cur, """
        SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') sysdate_,
               TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS.FF3 TZH:TZM') systimestamp_,
               TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS TZR') current_timestamp_sessao,
               DBTIMEZONE dbtimezone, SESSIONTIMEZONE sessiontimezone
          FROM dual""")))
    secoes.append(bloco("Parametros relevantes", *consultar(cur, """
        SELECT name, value FROM v$parameter
         WHERE name IN ('compatible','cpu_count','pga_aggregate_target','sga_target','memory_target','max_string_size')
         ORDER BY name""")))
    secoes.append(bloco("Opcoes habilitadas (v$option) usadas pelo projeto", *consultar(cur, """
        SELECT parameter, value FROM v$option
         WHERE parameter IN ('Advanced Analytics','Partitioning','Oracle Database Vault','Real Application Testing','Advanced Compression')
         ORDER BY parameter""")))
    secoes.append(bloco("Charset", *consultar(cur, """
        SELECT parameter, value FROM nls_database_parameters
         WHERE parameter IN ('NLS_CHARACTERSET','NLS_NCHAR_CHARACTERSET','NLS_RDBMS_VERSION') ORDER BY parameter""")))
    secoes.append(bloco("Privilegios do usuario de aplicacao (role DB_DEVELOPER_ROLE)", *consultar(cur, """
        SELECT granted_role FROM user_role_privs
        UNION ALL
        SELECT 'SYS PRIV: ' || privilege FROM role_sys_privs WHERE privilege IN ('CREATE MINING MODEL','CREATE JOB','CREATE VIEW','CREATE PROCEDURE','CREATE TABLE')
        ORDER BY 1""")))
    return cabecalho("01 - Versao do banco de dados") + "\n".join(secoes)


def col_contagens(cur):
    s = []
    s.append(bloco("EVENTOS_LMS - totais", *consultar(cur, """
        SELECT COUNT(*) total_eventos, SUM(FLG_ALUNO) eventos_de_alunos,
               COUNT(DISTINCT CASE WHEN FLG_ALUNO = 1 THEN NOME END) alunos_distintos,
               TO_CHAR(MIN(TS_EVENTO), 'YYYY-MM-DD HH24:MI') primeiro_evento,
               TO_CHAR(MAX(TS_EVENTO), 'YYYY-MM-DD HH24:MI') ultimo_evento
          FROM EVENTOS_LMS""")))
    s.append(bloco("EVENTOS_LMS - por fase", *consultar(cur, """
        SELECT e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS, COUNT(*) eventos,
               COUNT(DISTINCT CASE WHEN e.FLG_ALUNO = 1 THEN e.NOME END) alunos,
               MAX(e.CAPITULO) capitulo_max_observado,
               SUM(CASE WHEN e.CAPITULO IS NOT NULL THEN 1 ELSE 0 END) eventos_com_capitulo,
               TO_CHAR(MIN(e.TS_EVENTO), 'YYYY-MM-DD') primeiro, TO_CHAR(MAX(e.TS_EVENTO), 'YYYY-MM-DD') ultimo
          FROM EVENTOS_LMS e JOIN DIM_FASE f ON f.NUM_FASE = e.NUM_FASE
         GROUP BY e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS ORDER BY 1""")))
    s.append(bloco("EVENTOS_LMS - eventos de alunos por classe (DIM_TIPO_EVENTO)", *consultar(cur, """
        SELECT NVL(t.CLASSE_EVENTO, 'OUTRO') classe_evento, COUNT(*) eventos, COUNT(DISTINCT e.NOME) alunos
          FROM EVENTOS_LMS e LEFT JOIN DIM_TIPO_EVENTO t ON t.EVENTO = e.EVENTO
         WHERE e.FLG_ALUNO = 1 GROUP BY NVL(t.CLASSE_EVENTO, 'OUTRO') ORDER BY 2 DESC""")))
    s.append(bloco("FEATURES_TRANSICAO_FASE - rotulos por fase (evadiu_proxima_fase)", *consultar(cur, """
        SELECT NUM_FASE, NOME_FASE, CONJUNTO, COUNT(*) alunos, SUM(EVADIU_PROXIMA_FASE) evadiram,
               ROUND(AVG(EVADIU_PROXIMA_FASE), 4) taxa_evasao
          FROM FEATURES_TRANSICAO_FASE GROUP BY NUM_FASE, NOME_FASE, CONJUNTO ORDER BY NUM_FASE""")))
    s.append(bloco("BASE_RISCO_SEMANAL - cortes semanais rotulados (inativo_21d)", *consultar(cur, """
        SELECT CONJUNTO, COUNT(DISTINCT DT_CORTE) cortes, COUNT(*) linhas, SUM(INATIVO_21D) positivos,
               ROUND(AVG(INATIVO_21D), 4) taxa_inatividade,
               TO_CHAR(MIN(DT_CORTE), 'YYYY-MM-DD') primeiro_corte, TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') ultimo_corte
          FROM BASE_RISCO_SEMANAL GROUP BY CONJUNTO ORDER BY 1 DESC""")))
    s.append(bloco("RISCO_ALUNO_SNAPSHOT - scoring do corte atual por faixa", *consultar(cur, """
        SELECT TO_CHAR(MAX(DT_CORTE), 'YYYY-MM-DD') dt_corte, FAIXA_RISCO, COUNT(*) alunos,
               ROUND(AVG(PROB_INATIVO_21D), 4) prob_media, ROUND(AVG(RECENCIA_DIAS), 1) recencia_media,
               TO_CHAR(MAX(DT_SCORING), 'YYYY-MM-DD HH24:MI:SS') dt_scoring
          FROM RISCO_ALUNO_SNAPSHOT GROUP BY FAIXA_RISCO ORDER BY prob_media DESC""")))
    s.append(bloco("Catalogo - tabelas do projeto (USER_TABLES, num_rows das estatisticas)", *consultar(cur, """
        SELECT t.table_name, t.num_rows, TO_CHAR(t.last_analyzed, 'YYYY-MM-DD HH24:MI') last_analyzed,
               (SELECT COUNT(*) FROM user_tab_columns c WHERE c.table_name = t.table_name) colunas
          FROM user_tables t WHERE t.table_name NOT LIKE 'DM$%' ORDER BY 1""")))
    s.append(bloco("Catalogo - views, funcoes e procedimentos do projeto", *consultar(cur, """
        SELECT object_type, object_name, status, TO_CHAR(last_ddl_time, 'YYYY-MM-DD HH24:MI') last_ddl
          FROM user_objects WHERE object_type IN ('VIEW','FUNCTION','PROCEDURE','JOB') AND object_name NOT LIKE 'DM$%'
         ORDER BY object_type, object_name""")))
    return cabecalho("02 - Contagens dos dados carregados e derivados") + "\n".join(s)


def col_modelos(cur):
    s = []
    s.append(bloco("USER_MINING_MODELS", *consultar(cur, """
        SELECT model_name, mining_function, algorithm, TO_CHAR(creation_date, 'YYYY-MM-DD HH24:MI:SS') creation_date_utc,
               build_duration seg_treino, model_size bytes, comments
          FROM user_mining_models ORDER BY model_name""")))
    s.append(bloco("USER_MINING_MODEL_SETTINGS (todas as configuracoes, incluindo defaults)", *consultar(cur, """
        SELECT model_name, setting_name, setting_value, setting_type
          FROM user_mining_model_settings WHERE model_name LIKE 'RETENA%' ORDER BY model_name, setting_type, setting_name""")))
    s.append(bloco("USER_MINING_MODEL_ATTRIBUTES", *consultar(cur, """
        SELECT model_name, attribute_name, attribute_type, data_type, usage_type, target
          FROM user_mining_model_attributes WHERE model_name LIKE 'RETENA%' ORDER BY model_name, target DESC, attribute_name""")))
    s.append(bloco("USER_MINING_MODEL_VIEWS (detalhes gerados pelo OML)", *consultar(cur, """
        SELECT model_name, view_name, view_type FROM user_mining_model_views WHERE model_name LIKE 'RETENA%' ORDER BY 1, 2""")))
    s.append(bloco("Diagnosticos globais de treino (DM$VG*)", *consultar(cur, """
        SELECT 'RETENA_TRANSICAO_GLM' modelo, name, numeric_value, string_value FROM DM$VGRETENA_TRANSICAO_GLM
        UNION ALL SELECT 'RETENA_INATIVO21_GLM', name, numeric_value, string_value FROM DM$VGRETENA_INATIVO21_GLM
        UNION ALL SELECT 'RETENA_INATIVO21_RF', name, numeric_value, string_value FROM DM$VGRETENA_INATIVO21_RF
        ORDER BY 1, 2""")))
    s.append(bloco("Views de treino/teste usadas no CREATE_MODEL2", *consultar(cur, """
        SELECT 'VW_TREINO_TRANSICAO' view_treino, COUNT(*) linhas, SUM(EVADIU_PROXIMA_FASE) positivos FROM VW_TREINO_TRANSICAO
        UNION ALL SELECT 'VW_TESTE_TRANSICAO', COUNT(*), SUM(EVADIU_PROXIMA_FASE) FROM VW_TESTE_TRANSICAO
        UNION ALL SELECT 'VW_TREINO_INATIVIDADE', COUNT(*), SUM(INATIVO_21D) FROM VW_TREINO_INATIVIDADE
        UNION ALL SELECT 'VW_TESTE_INATIVIDADE', COUNT(*), SUM(INATIVO_21D) FROM VW_TESTE_INATIVIDADE""")))
    return cabecalho("03 - Modelos Oracle Machine Learning (in-database)") + "\n".join(s)


def col_metricas(cur):
    s = []
    s.append(bloco("AVALIACAO_MODELOS - metricas no conjunto de TESTE (validacao temporal)", *consultar(cur, """
        SELECT MODELO, METRICA, VALOR, DETALHE, TO_CHAR(DT_AVALIACAO, 'YYYY-MM-DD HH24:MI:SS') dt_avaliacao
          FROM AVALIACAO_MODELOS
         ORDER BY MODELO, DECODE(METRICA, 'N_TESTE',1,'POSITIVOS_TESTE',2,'PREVALENCIA_TESTE',3,'AUC_COMPUTE_ROC',4,'AUC_SQL',5,
                  'ACURACIA_0.5',6,'ACUR_BALANC_0.5',7,'PRECISAO_0.5',8,'RECALL_0.5',9,'ESPECIFIC_0.5',10,'F1_0.5',11,
                  'TP_0.5',12,'FP_0.5',13,'FN_0.5',14,'TN_0.5',15, 16), METRICA"""), max_larg=90))
    s.append(bloco("Resumo comparativo (AUC e F1 por modelo)", *consultar(cur, """
        SELECT MODELO,
               MAX(CASE WHEN METRICA = 'N_TESTE' THEN VALOR END) n_teste,
               MAX(CASE WHEN METRICA = 'PREVALENCIA_TESTE' THEN VALOR END) prevalencia,
               MAX(CASE WHEN METRICA = 'AUC_COMPUTE_ROC' THEN VALOR END) auc_compute_roc,
               MAX(CASE WHEN METRICA = 'AUC_SQL' THEN VALOR END) auc_sql,
               MAX(CASE WHEN METRICA = 'ACUR_BALANC_0.5' THEN VALOR END) acur_balanceada,
               MAX(CASE WHEN METRICA = 'PRECISAO_0.5' THEN VALOR END) precisao,
               MAX(CASE WHEN METRICA = 'RECALL_0.5' THEN VALOR END) recall,
               MAX(CASE WHEN METRICA = 'F1_0.5' THEN VALOR END) f1
          FROM AVALIACAO_MODELOS GROUP BY MODELO ORDER BY MODELO""")))
    s.append(bloco("Matriz de confusao (limiar 0,5)", *consultar(cur, """
        SELECT MODELO,
               MAX(CASE WHEN METRICA = 'TP_0.5' THEN VALOR END) tp,
               MAX(CASE WHEN METRICA = 'FP_0.5' THEN VALOR END) fp,
               MAX(CASE WHEN METRICA = 'FN_0.5' THEN VALOR END) fn,
               MAX(CASE WHEN METRICA = 'TN_0.5' THEN VALOR END) tn
          FROM AVALIACAO_MODELOS GROUP BY MODELO ORDER BY MODELO""")))
    s.append(bloco("Taxa observada por faixa (Alto >= 0,60 | Medio 0,30-0,60 | Baixo)", *consultar(cur, """
        SELECT * FROM VW_AVALIACAO_FAIXAS ORDER BY MODELO, PROB_MEDIA DESC""")))
    s.append(bloco("Precisao / captura / lift no TOP-20% de risco (fila operacional do tutor)", *consultar(cur, """
        SELECT MODELO,
               MAX(CASE WHEN METRICA = 'PRECISAO_TOP20PCT' THEN VALOR END) precisao_top20,
               MAX(CASE WHEN METRICA = 'CAPTURA_TOP20PCT'  THEN VALOR END) captura_top20,
               MAX(CASE WHEN METRICA = 'LIFT_TOP20PCT'     THEN VALOR END) lift_top20,
               MAX(CASE WHEN METRICA = 'PRECISAO_TOP20PCT' THEN DETALHE END) detalhe
          FROM AVALIACAO_MODELOS WHERE METRICA LIKE '%TOP20PCT' GROUP BY MODELO ORDER BY MODELO"""), max_larg=100))
    s.append(bloco("Lift por decil - RETENA_INATIVO21_RF (DBMS_DATA_MINING.COMPUTE_LIFT)", *consultar(cur, """
        SELECT QUANTILE_NUMBER decil, ROUND(PROBABILITY_THRESHOLD, 4) limiar_prob, TARGETS_CUMULATIVE positivos_acum,
               ROUND(LIFT_CUMULATIVE, 3) lift_acum, ROUND(GAIN_CUMULATIVE, 4) captura_acum,
               ROUND(PERCENTAGE_RECORDS_CUMULATIVE, 4) pct_casos_acum
          FROM LIFT_INATIVO21_RF ORDER BY QUANTILE_NUMBER""")))
    s.append(bloco("Importancia de atributos - RETENA_INATIVO21_RF (DM$VA - Random Forest)", *consultar(cur, """
        SELECT ATTRIBUTE_NAME, ROUND(ATTRIBUTE_IMPORTANCE, 4) importancia, ROUND(RATIO_TO_REPORT(ATTRIBUTE_IMPORTANCE) OVER (), 4) participacao
          FROM DM$VARETENA_INATIVO21_RF ORDER BY ATTRIBUTE_IMPORTANCE DESC""")))
    s.append(bloco("Coeficientes - RETENA_INATIVO21_GLM (DM$VD, escala transformada pelo PREP_AUTO)", *consultar(cur, """
        SELECT NVL(ATTRIBUTE_NAME, '(intercepto)') atributo, ROUND(COEFFICIENT, 4) coeficiente, ROUND(STD_ERROR, 4) erro_padrao,
               ROUND(P_VALUE, 4) p_valor, ROUND(EXP(COEFFICIENT), 4) odds_ratio
          FROM DM$VDRETENA_INATIVO21_GLM ORDER BY ABS(COEFFICIENT) DESC""")))
    s.append(bloco("Coeficientes - RETENA_TRANSICAO_GLM (DM$VD)", *consultar(cur, """
        SELECT NVL(ATTRIBUTE_NAME, '(intercepto)') atributo, ROUND(COEFFICIENT, 4) coeficiente, ROUND(STD_ERROR, 4) erro_padrao,
               ROUND(P_VALUE, 4) p_valor, ROUND(EXP(COEFFICIENT), 4) odds_ratio
          FROM DM$VDRETENA_TRANSICAO_GLM ORDER BY ABS(COEFFICIENT) DESC""")))
    return cabecalho("04 - Metricas dos modelos (conjunto de teste: cortes >= 2026-06-01 / transicao F4->F5)") + "\n".join(s)


def col_scoring(cur):
    cols, linhas = consultar(cur, """
        SELECT NOME, TO_CHAR(DT_CORTE, 'YYYY-MM-DD') DT_CORTE, NUM_FASE_ATUAL, NOME_FASE, RECENCIA_DIAS, EVENTOS_7D, EVENTOS_14D,
               EVENTOS_28D, DIAS_ATIVOS_28D, PROGRESSO_28D, CAPITULOS_DISTINTOS_28D, QUIZ_28D, ENTREGAS_28D, TENDENCIA,
               PROB_INATIVO_21D, PROB_INATIVO_21D_GLM, FAIXA_RISCO, CAPITULO_MAX_FASE, PCT_CAPITULOS_FASE, PROB_EVASAO_FASE,
               FATORES_TOP3, ACAO_SUGERIDA, STATUS_ATENDIMENTO, TO_CHAR(DT_SCORING, 'YYYY-MM-DD HH24:MI:SS') DT_SCORING
          FROM RISCO_ALUNO_SNAPSHOT ORDER BY PROB_INATIVO_21D DESC, RECENCIA_DIAS DESC, NOME FETCH FIRST 20 ROWS ONLY""")
    import csv
    caminho = os.path.join(EVID, "05_scoring_amostra.csv")
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for l in linhas:
            w.writerow(["" if v is None else v for v in l])
    print(f"  gravado {caminho} ({len(linhas)} linhas)")
    return cols, linhas


def col_json(cur):
    cols, linhas = consultar(cur, "SELECT PAYLOAD FROM VW_RISCO_JSON")
    payload = json.loads(linhas[0][0])
    total = len(payload["alunos"])
    payload["alunos"] = payload["alunos"][:20]
    payload["_amostra"] = {"alunos_exibidos": len(payload["alunos"]), "alunos_no_payload_completo": total,
                           "origem": "SELECT PAYLOAD FROM VW_RISCO_JSON (JSON_OBJECT + JSON_ARRAYAGG, Oracle 26ai)",
                           "extraido_em": agora()}
    # documento da duality view (leitura) para a mesma amostra
    cols2, doc = consultar(cur, """
        SELECT JSON_SERIALIZE(dv.DATA) FROM RISCO_ALUNO_DV dv
         ORDER BY dv.DATA.probInativo21d.number() DESC, dv.DATA."_id".string() FETCH FIRST 2 ROWS ONLY""")
    payload["_duality_view_amostra"] = [json.loads(d[0]) for d in doc]
    texto = json.dumps(payload, ensure_ascii=False, indent=2)
    gravar("06_json_api_amostra.json", texto)
    return payload, texto


def col_docker():
    """Devolve (texto_consolidado, saida_docker_ps, saida_docker_logs) - tudo executado agora."""
    partes = [f"07 - Container Docker ({CONTAINER})\n{'=' * 40}\nColetado em: {agora()}\n"]
    isolados = {}
    for titulo, cmd in [
        ("docker ps --filter name=" + CONTAINER, ["docker", "ps", "--filter", f"name={CONTAINER}", "--format",
                                                 "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}"]),
        ("docker inspect (imagem, criacao, saude)", ["docker", "inspect", "--format",
                                                     "Image={{.Config.Image}} | Created={{.Created}} | Status={{.State.Status}} | Health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}} | StartedAt={{.State.StartedAt}}",
                                                     CONTAINER]),
        ("docker logs --tail 40 " + CONTAINER, ["docker", "logs", "--tail", "40", CONTAINER]),
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
            saida = (r.stdout or "") + (r.stderr or "")
        except Exception as e:  # docker ausente
            saida = f"ERRO ao executar: {e}"
        partes.append(f"\n$ {' '.join(cmd) if len(' '.join(cmd)) < 120 else titulo}\n{saida.rstrip()}\n")
        isolados[cmd[1]] = f"$ {' '.join(cmd)}\n# executado em {agora()}\n{saida.rstrip()}\n"
    return "\n".join(partes), isolados.get("ps", ""), isolados.get("logs", "")


def texto_apex(apex):
    """07_apex_consultas.txt - resultados resumidos (ate 15 linhas por consulta) das consultas APEX."""
    partes = [cabecalho("07 - Consultas prontas para APEX (sql/07_apex_ready.sql) - resultados reais")]
    for titulo, cols, linhas, seg in apex:
        partes.append(f"== {titulo} ==\n{len(linhas)} linha(s) retornada(s) em {seg:.2f} s (exibindo ate 15)\n"
                      f"{formatar_tabela(cols, linhas[:15], max_larg=60)}\n")
    return "\n".join(partes)


def col_apex(cur):
    """Executa as 5 consultas do 07_apex_ready.sql e devolve [(titulo, cols, linhas, segundos)]."""
    with open(SQL_APEX, encoding="utf-8") as f:
        texto = f.read()
    titulos = re.findall(r"^-- (\d\) [A-ZÇÃÉÍÕÚ][^\n]*)", texto, flags=re.M)
    stmts = [s for s, p in dividir_statements(texto) if not p]
    out = []
    for k, stmt in enumerate(stmts):
        t0 = time.time()
        cols, linhas = consultar(cur, stmt, max_linhas=60)
        titulo = titulos[k] if k < len(titulos) else f"Consulta {k + 1}"
        out.append((titulo, cols, linhas, time.time() - t0))
    return out


# ----------------------------------------------------------------------------- HTML
CSS = """
@font-face { font-family: 'Sora'; src: url('../../03_Marca/fontes/Sora-Variable.ttf') format('truetype'); font-weight: 100 900; }
:root { --bg:#F6F7F9; --navy:#0B2545; --teal:#2EC4B6; --ink:#1F2937; --muted:#5B6B7F; --term:#0E1726; --line:#E3E7EE; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:'Sora', 'Segoe UI', system-ui, sans-serif; }
.pagina { width:1600px; margin:0 auto; padding:36px 56px 48px; }
header { display:flex; align-items:center; justify-content:space-between; border-bottom:3px solid var(--teal); padding-bottom:18px; margin-bottom:28px; }
header img { height:54px; }
header .meta { text-align:right; color:var(--muted); font-size:14px; line-height:1.5; }
header .meta b { color:var(--navy); }
h1 { color:var(--navy); font-size:30px; margin:0 0 6px; font-weight:700; letter-spacing:-0.01em; }
h2 { color:var(--navy); font-size:24px; margin:0 0 14px; font-weight:700; }
h2 .num { display:inline-block; background:var(--teal); color:#fff; border-radius:8px; padding:2px 12px; margin-right:12px; font-size:18px; vertical-align:middle; }
h3 { color:var(--navy); font-size:16px; margin:22px 0 8px; font-weight:600; }
p, li { font-size:15px; line-height:1.55; }
.sub { color:var(--muted); font-size:15px; margin:0 0 22px; }
section { background:#fff; border:1px solid var(--line); border-radius:14px; padding:26px 30px; margin-bottom:26px; box-shadow:0 1px 2px rgba(11,37,69,.04); }
pre.term { background:var(--term); color:#D8E3F0; border-radius:10px; padding:16px 18px; font:12.5px/1.45 Consolas, 'Cascadia Mono', monospace; overflow:hidden; white-space:pre; margin:8px 0 0; border-left:5px solid var(--teal); }
pre.term .cmd { color:var(--teal); }
table.dados { border-collapse:collapse; width:100%; font-size:13px; margin-top:8px; }
table.dados th { background:var(--navy); color:#fff; text-align:left; padding:8px 10px; font-weight:600; white-space:nowrap; }
table.dados td { padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
table.dados tr:nth-child(even) td { background:#F9FAFC; }
.kpis { display:flex; gap:16px; margin:6px 0 10px; flex-wrap:wrap; }
.kpi { flex:1 1 160px; background:#F0FAF9; border:1px solid #CBEFEA; border-radius:12px; padding:14px 16px; }
.kpi .v { color:var(--navy); font-size:26px; font-weight:700; }
.kpi .l { color:var(--muted); font-size:13px; margin-top:2px; }
.faixa-Alto { color:#B42318; font-weight:700; } .faixa-Médio { color:#B54708; font-weight:700; } .faixa-Baixo { color:#067647; font-weight:700; }
footer { color:var(--muted); font-size:13px; margin-top:8px; text-align:right; }
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def tabela_html(cols, linhas, max_larg=90):
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            s = f"{v:.4f}".rstrip("0").rstrip(".")
            return s if s else "0"
        s = str(v)
        return s if len(s) <= max_larg else s[: max_larg - 3] + "..."

    th = "".join(f"<th>{esc(c)}</th>" for c in cols)
    trs = []
    for l in linhas:
        tds = []
        for c, v in zip(cols, l):
            cls = f' class="faixa-{esc(v)}"' if str(c).upper() in ("FAIXA_RISCO", "FAIXA") and v else ""
            tds.append(f"<td{cls}>{esc(fmt(v))}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table class="dados"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


def term(txt, cmd=None):
    c = f'<span class="cmd">$ {esc(cmd)}</span>\n' if cmd else ""
    return f'<pre class="term">{c}{esc(txt)}</pre>'


def montar_secoes(cur, textos, scoring, payload_json, apex):
    """Devolve lista de (titulo, html_interno)."""
    S = []
    # 1 - ambiente
    cols, l = consultar(cur, "SELECT banner_full FROM v$version")
    cols2, l2 = consultar(cur, """SELECT SYS_CONTEXT('USERENV','INSTANCE_NAME') instancia, SYS_CONTEXT('USERENV','SERVER_HOST') host,
        SYS_CONTEXT('USERENV','CON_NAME') pdb, TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS TZH:TZM') systimestamp FROM dual""")
    docker_txt = textos["07"]
    S.append(("Ambiente: Oracle AI Database 26ai Free em Docker", f"""
      <p class="sub">Banco real rodando localmente no container <b>oracle-free</b> (imagem gvenzl/oracle-free:slim-faststart), acessado por python-oracledb (modo thin) como usuario de aplicacao STARTUP.</p>
      {term(l[0][0], "SELECT banner_full FROM v$version")}
      {tabela_html(cols2, l2)}
      <h3>Container</h3>
      {term(docker_txt[docker_txt.find("$ docker ps"):docker_txt.find("$ docker logs")].strip())}
      {term(docker_txt[docker_txt.find("$ docker logs"):].strip()[:2600])}
    """))
    # 2 - dados
    c1, l1 = consultar(cur, """SELECT COUNT(*) eventos, SUM(FLG_ALUNO) eventos_alunos, COUNT(DISTINCT CASE WHEN FLG_ALUNO=1 THEN NOME END) alunos,
        TO_CHAR(MIN(TS_EVENTO),'YYYY-MM-DD') primeiro, TO_CHAR(MAX(TS_EVENTO),'YYYY-MM-DD') ultimo FROM EVENTOS_LMS""")
    kp = l1[0]
    c2, l2 = consultar(cur, """SELECT e.NUM_FASE fase, f.NOME_FASE, f.TOTAL_CAPITULOS capitulos, COUNT(*) eventos,
        COUNT(DISTINCT CASE WHEN e.FLG_ALUNO=1 THEN e.NOME END) alunos, MAX(e.CAPITULO) cap_max_observado,
        TO_CHAR(MIN(e.TS_EVENTO),'YYYY-MM-DD') primeiro, TO_CHAR(MAX(e.TS_EVENTO),'YYYY-MM-DD') ultimo
        FROM EVENTOS_LMS e JOIN DIM_FASE f ON f.NUM_FASE=e.NUM_FASE GROUP BY e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS ORDER BY 1""")
    c3, l3 = consultar(cur, """SELECT table_name, num_rows, TO_CHAR(last_analyzed,'YYYY-MM-DD HH24:MI') last_analyzed FROM user_tables
        WHERE table_name IN ('EVENTOS_LMS','DIM_FASE','DIM_TIPO_EVENTO','FEATURES_TRANSICAO_FASE','BASE_RISCO_SEMANAL','RISCO_ALUNO_SNAPSHOT','SCORES_TESTE','AVALIACAO_MODELOS') ORDER BY 1""")
    S.append(("Dados carregados: logs do LMS em EVENTOS_LMS", f"""
      <div class="kpis">
        <div class="kpi"><div class="v">{kp[0]:,}</div><div class="l">eventos do LMS carregados</div></div>
        <div class="kpi"><div class="v">{kp[1]:,}</div><div class="l">eventos de alunos (FLG_ALUNO = 1)</div></div>
        <div class="kpi"><div class="v">{kp[2]}</div><div class="l">alunos distintos</div></div>
        <div class="kpi"><div class="v">{kp[3]} a {kp[4]}</div><div class="l">periodo observado</div></div>
      </div>
      <h3>Eventos por fase (colunas virtuais NUM_FASE / CAPITULO / FLG_ALUNO calculadas no banco)</h3>
      {tabela_html(c2, l2)}
      <h3>Tabelas do projeto (USER_TABLES)</h3>
      {tabela_html(c3, l3)}
    """.replace(",", ".")))
    # 3 - features
    c1, l1 = consultar(cur, """SELECT NUM_FASE fase, NOME_FASE, CONJUNTO, COUNT(*) alunos, SUM(EVADIU_PROXIMA_FASE) evadiram,
        ROUND(AVG(EVADIU_PROXIMA_FASE),4) taxa_evasao FROM FEATURES_TRANSICAO_FASE GROUP BY NUM_FASE, NOME_FASE, CONJUNTO ORDER BY 1""")
    c2, l2 = consultar(cur, """SELECT CONJUNTO, COUNT(DISTINCT DT_CORTE) cortes, COUNT(*) casos, SUM(INATIVO_21D) positivos,
        ROUND(AVG(INATIVO_21D),4) taxa, TO_CHAR(MIN(DT_CORTE),'YYYY-MM-DD') primeiro_corte, TO_CHAR(MAX(DT_CORTE),'YYYY-MM-DD') ultimo_corte
        FROM BASE_RISCO_SEMANAL GROUP BY CONJUNTO ORDER BY 1 DESC""")
    c3, l3 = consultar(cur, """SELECT TO_CHAR(DT_CORTE,'YYYY-MM-DD') corte, CONJUNTO, COUNT(*) alunos, SUM(INATIVO_21D) inativos_21d,
        ROUND(AVG(INATIVO_21D),3) taxa, ROUND(AVG(EVENTOS_28D),1) media_ev_28d, ROUND(AVG(RECENCIA_DIAS),1) media_recencia
        FROM BASE_RISCO_SEMANAL GROUP BY DT_CORTE, CONJUNTO ORDER BY DT_CORTE""")
    S.append(("Feature engineering in-database (views + SQL Macro)", f"""
      <p class="sub">Duas unidades de analise. <b>Transicao de fase</b> (aluno x fase k: evadiu = 0 eventos na fase k+1) e <b>risco semanal</b> (aluno x corte t, domingos de 2026-02-01 a 2026-08-02: inativo_21d = 0 eventos em (t, t+21d]). Features usam apenas eventos &le; t; a mesma SQL Macro FN_FEATURES_SEMANAIS serve treino e scoring (sem training/serving skew).</p>
      <h3>FEATURES_TRANSICAO_FASE - rotulos por fase</h3>{tabela_html(c1, l1)}
      <h3>BASE_RISCO_SEMANAL - treino (cortes &lt; 2026-06-01) e teste (&ge; 2026-06-01)</h3>{tabela_html(c2, l2)}
      <h3>Cortes semanais</h3>{tabela_html(c3, l3)}
    """))
    # 4 - modelos
    c1, l1 = consultar(cur, """SELECT model_name, mining_function, algorithm, TO_CHAR(creation_date,'YYYY-MM-DD HH24:MI:SS') criado_em_utc,
        build_duration seg_treino, model_size bytes FROM user_mining_models ORDER BY 1""")
    c2, l2 = consultar(cur, """SELECT model_name, setting_name, setting_value, setting_type FROM user_mining_model_settings
        WHERE model_name LIKE 'RETENA%' AND (setting_type='INPUT' OR setting_name IN ('ODMS_MISSING_VALUE_TREATMENT','PREP_AUTO')) ORDER BY 1,2""")
    c3, l3 = consultar(cur, """SELECT model_name, LISTAGG(attribute_name, ', ') WITHIN GROUP (ORDER BY attribute_name) atributos
        FROM user_mining_model_attributes WHERE model_name LIKE 'RETENA%' AND target='NO' GROUP BY model_name ORDER BY 1""")
    S.append(("Modelos Oracle Machine Learning treinados no banco", f"""
      <p class="sub">DBMS_DATA_MINING.CREATE_MODEL2 com PREP_AUTO = ON: o modelo carrega a preparacao (normalizacao, tratamento de nulos). Nenhum dado saiu do banco; o treino le as views VW_TREINO_*.</p>
      <h3>USER_MINING_MODELS</h3>{tabela_html(c1, l1)}
      <h3>USER_MINING_MODEL_SETTINGS (configuracoes informadas)</h3>{tabela_html(c2, l2)}
      <h3>Atributos (USER_MINING_MODEL_ATTRIBUTES)</h3>{tabela_html(c3, l3, max_larg=400)}
    """))
    # 5 - avaliacao
    c1, l1 = consultar(cur, """SELECT MODELO, MAX(CASE WHEN METRICA='N_TESTE' THEN VALOR END) n_teste,
        MAX(CASE WHEN METRICA='PREVALENCIA_TESTE' THEN VALOR END) prevalencia,
        MAX(CASE WHEN METRICA='AUC_COMPUTE_ROC' THEN VALOR END) auc_compute_roc, MAX(CASE WHEN METRICA='AUC_SQL' THEN VALOR END) auc_sql,
        MAX(CASE WHEN METRICA='ACUR_BALANC_0.5' THEN VALOR END) acur_balanceada, MAX(CASE WHEN METRICA='PRECISAO_0.5' THEN VALOR END) precisao,
        MAX(CASE WHEN METRICA='RECALL_0.5' THEN VALOR END) recall, MAX(CASE WHEN METRICA='F1_0.5' THEN VALOR END) f1,
        MAX(CASE WHEN METRICA='TP_0.5' THEN VALOR END) tp, MAX(CASE WHEN METRICA='FP_0.5' THEN VALOR END) fp,
        MAX(CASE WHEN METRICA='FN_0.5' THEN VALOR END) fn, MAX(CASE WHEN METRICA='TN_0.5' THEN VALOR END) tn
        FROM AVALIACAO_MODELOS GROUP BY MODELO ORDER BY 1""")
    c2, l2 = consultar(cur, "SELECT * FROM VW_AVALIACAO_FAIXAS ORDER BY MODELO, PROB_MEDIA DESC")
    c3, l3 = consultar(cur, """SELECT QUANTILE_NUMBER decil, ROUND(PROBABILITY_THRESHOLD,4) limiar_prob, TARGETS_CUMULATIVE positivos_acum,
        ROUND(LIFT_CUMULATIVE,3) lift_acum, ROUND(GAIN_CUMULATIVE,4) captura_acum, ROUND(PERCENTAGE_RECORDS_CUMULATIVE,4) pct_casos_acum
        FROM LIFT_INATIVO21_RF ORDER BY 1""")
    c4, l4 = consultar(cur, """SELECT ATTRIBUTE_NAME atributo, ROUND(ATTRIBUTE_IMPORTANCE,4) importancia, ROUND(RATIO_TO_REPORT(ATTRIBUTE_IMPORTANCE) OVER (),4) participacao
        FROM DM$VARETENA_INATIVO21_RF ORDER BY 2 DESC""")
    c5, l5 = consultar(cur, """SELECT NVL(ATTRIBUTE_NAME,'(intercepto)') atributo, ROUND(COEFFICIENT,4) coeficiente, ROUND(P_VALUE,4) p_valor, ROUND(EXP(COEFFICIENT),4) odds_ratio
        FROM DM$VDRETENA_TRANSICAO_GLM ORDER BY ABS(COEFFICIENT) DESC""")
    c6, l6 = consultar(cur, """SELECT MODELO, MAX(CASE WHEN METRICA='PRECISAO_TOP20PCT' THEN VALOR END) precisao_top20,
        MAX(CASE WHEN METRICA='CAPTURA_TOP20PCT' THEN VALOR END) captura_top20, MAX(CASE WHEN METRICA='LIFT_TOP20PCT' THEN VALOR END) lift_top20,
        MAX(CASE WHEN METRICA='PRECISAO_TOP20PCT' THEN DETALHE END) detalhe
        FROM AVALIACAO_MODELOS WHERE METRICA LIKE '%TOP20PCT' GROUP BY MODELO ORDER BY 1""")
    rf = next((x for x in l1 if x[0] == "RETENA_INATIVO21_RF"), None)
    rf20 = next((x for x in l6 if x[0] == "RETENA_INATIVO21_RF"), None)
    kpis = ""
    if rf:
        kpis = f"""<div class="kpis">
          <div class="kpi"><div class="v">{rf[3]}</div><div class="l">AUC - RETENA_INATIVO21_RF (COMPUTE_ROC)</div></div>
          <div class="kpi"><div class="v">{rf[7]}</div><div class="l">recall no limiar 0,5</div></div>
          <div class="kpi"><div class="v">{rf[6]}</div><div class="l">precisao no limiar 0,5</div></div>
          <div class="kpi"><div class="v">{rf20[1] if rf20 else '-'}</div><div class="l">precisao no top-20% de risco</div></div>
          <div class="kpi"><div class="v">{int(rf[1])}</div><div class="l">casos de teste (cortes &ge; 2026-06-01)</div></div>
        </div>"""
    S.append(("Avaliacao no conjunto de teste (validacao temporal)", f"""
      {kpis}
      <h3>Metricas por modelo (AUC via DBMS_DATA_MINING.COMPUTE_ROC e contraprova em SQL; limiar 0,5)</h3>{tabela_html(c1, l1)}
      <h3>Precisao, captura e lift no top-20% de risco (fila operacional: contatar 1 em cada 5 alunos)</h3>{tabela_html(c6, l6, max_larg=110)}
      <h3>Taxa observada por faixa de risco</h3>{tabela_html(c2, l2)}
      <h3>Lift por decil - RETENA_INATIVO21_RF (COMPUTE_LIFT)</h3>{tabela_html(c3, l3)}
      <h3>Importancia de atributos (Random Forest, DM$VA)</h3>{tabela_html(c4, l4)}
      <h3>Coeficientes do GLM de transicao (DM$VD)</h3>{tabela_html(c5, l5)}
    """))
    # 6 - scoring
    cols, linhas = scoring
    idx = {c: i for i, c in enumerate(cols)}
    sel = ["NOME", "NUM_FASE_ATUAL", "RECENCIA_DIAS", "EVENTOS_28D", "DIAS_ATIVOS_28D", "PROB_INATIVO_21D", "PROB_INATIVO_21D_GLM",
           "FAIXA_RISCO", "PROB_EVASAO_FASE", "FATORES_TOP3", "ACAO_SUGERIDA"]
    linhas_sel = [tuple(l[idx[c]] for c in sel) for l in linhas]
    c2, l2 = consultar(cur, """SELECT FAIXA_RISCO, COUNT(*) alunos, ROUND(AVG(PROB_INATIVO_21D),4) prob_media, ROUND(AVG(RECENCIA_DIAS),1) recencia_media,
        ROUND(AVG(EVENTOS_28D),1) eventos_28d_media FROM RISCO_ALUNO_SNAPSHOT GROUP BY FAIXA_RISCO ORDER BY 3 DESC""")
    c3, l3 = consultar(cur, """SELECT job_name, job_action, repeat_interval, enabled, state, TO_CHAR(next_run_date,'YYYY-MM-DD HH24:MI TZR') proxima_execucao
        FROM user_scheduler_jobs WHERE job_name='JOB_RETENA_SCORING_SEMANAL'""")
    S.append(("Scoring por SQL: PREDICTION_PROBABILITY + PREDICTION_DETAILS", f"""
      <p class="sub">VW_RISCO_ALUNO_ATUAL pontua o ultimo corte (ultimo dia com eventos) com os modelos OML; PRC_ATUALIZAR_RISCO persiste em RISCO_ALUNO_SNAPSHOT (agendado por DBMS_SCHEDULER). Faixas: Alto &ge; 0,60 | Medio 0,30-0,60 | Baixo.</p>
      <h3>Distribuicao por faixa</h3>{tabela_html(c2, l2)}
      <h3>20 alunos de maior risco (fatores = PREDICTION_DETAILS top 3, XML convertido em texto)</h3>{tabela_html(sel, linhas_sel, max_larg=95)}
      <h3>Agendamento (USER_SCHEDULER_JOBS)</h3>{tabela_html(c3, l3)}
    """))
    # 7 - json
    resumo = {k: v for k, v in payload_json.items() if k not in ("alunos", "_duality_view_amostra", "_amostra")}
    resumo["alunos"] = payload_json["alunos"][:3] + ["... (%d alunos no payload completo)" % payload_json["_amostra"]["alunos_no_payload_completo"]]
    dv = payload_json.get("_duality_view_amostra", [])[:1]
    S.append(("JSON pronto para API e JSON Relational Duality View", f"""
      <p class="sub">VW_RISCO_JSON monta o payload completo com JSON_OBJECT / JSON_ARRAYAGG (pronto para ORDS ou API Gateway). RISCO_ALUNO_DV e uma <b>JSON Relational Duality View</b> (26ai): documento por aluno com leitura e escrita - o coordenador atualiza o status pelo app e a tabela relacional continua a fonte unica.</p>
      {term(json.dumps(resumo, ensure_ascii=False, indent=2), "SELECT PAYLOAD FROM VW_RISCO_JSON")}
      {term(json.dumps(dv, ensure_ascii=False, indent=2), "SELECT JSON_SERIALIZE(dv.DATA) FROM RISCO_ALUNO_DV dv ORDER BY dv.DATA.probInativo21d.number() DESC FETCH FIRST 1 ROWS ONLY")}
    """))
    # 8 - apex
    partes = []
    for titulo, cols, linhas, seg in apex:
        partes.append(f"<h3>{esc(titulo)} <span style='color:#5B6B7F;font-weight:400'>- {len(linhas)} linha(s) em {seg:.2f} s</span></h3>{tabela_html(cols, linhas, max_larg=80)}")
    S.append(("Consultas prontas para APEX (07_apex_ready.sql) - resultados reais", f"""
      <p class="sub">As cinco consultas abaixo foram executadas neste momento contra o banco. No APEX, os literais da CTE "parametros" viram itens de pagina (:P1_TICKET_MENSAL etc.).</p>
      {''.join(partes)}
    """))
    return S


def html_pagina(secoes, meta, apenas=None):
    """Monta a pagina; 'apenas' = indice de uma unica secao (para o PNG)."""
    corpo = []
    for i, (titulo, interno) in enumerate(secoes, 1):
        if apenas is not None and i != apenas:
            continue
        corpo.append(f'<section id="s{i}"><h2><span class="num">{i:02d}</span>{esc(titulo)}</h2>{interno}</section>')
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Retena - Evidencias Oracle</title><style>{CSS}</style></head>
<body><div class="pagina">
<header>
  <img src="../../03_Marca/logo/retena_horizontal_escuro_sobre_claro.svg" alt="Retena">
  <div class="meta"><b>Evidencias tecnicas - integracao Oracle</b><br>{esc(meta['banner'])}<br>Gerado em {esc(meta['gerado_em'])} (local) | {esc(meta['db_ts'])} (banco, UTC)</div>
</header>
{'<h1>Previsao de evasao com Oracle Machine Learning in-database</h1><p class="sub">Relatorio gerado automaticamente por scripts/gerar_evidencias.py a partir de consultas reais ao banco. Cada secao corresponde a uma imagem evidencia_NN.png.</p>' if apenas is None else ''}
{''.join(corpo)}
<footer>Retena - Startup One / Enterprise Challenge Oracle - {esc(meta['gerado_em'])}</footer>
</div></body></html>"""


def estimar_altura(html_secao):
    linhas_pre = sum(t.count("\n") + 1 for t in re.findall(r"<pre class=\"term\">(.*?)</pre>", html_secao, flags=re.S))
    linhas_tab = html_secao.count("<tr>")
    h3 = html_secao.count("<h3>")
    kpis = 1 if "kpis" in html_secao else 0
    # estimativa generosa (melhor sobrar margem em branco do que cortar a ultima tabela)
    h = 420 + linhas_pre * 19.5 + linhas_tab * 34 + h3 * 56 + kpis * 120 + html_secao.count('class="sub"') * 70
    return int(min(max(h, 800), 9500))


def render_png(html_path, png_path, altura):
    user_dir = os.path.join(tempfile.gettempdir(), "edge_oracle")
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
           f"--user-data-dir={user_dir}", f"--window-size=1600,{altura}", f"--screenshot={png_path}",
           "file:///" + html_path.replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, timeout=120)
    return os.path.exists(png_path)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-png", action="store_true")
    args = ap.parse_args()
    os.makedirs(EVID, exist_ok=True)
    t0 = time.time()
    print(f"[{agora()}] gerar_evidencias.py - conectando em {ORACLE_USER}@{ORACLE_DSN}")
    conn = conectar()
    cur = conn.cursor()

    textos = {}
    textos["01"] = col_versao(cur); gravar("01_versao_banco.txt", textos["01"])
    textos["02"] = col_contagens(cur); gravar("02_contagens.txt", textos["02"])
    textos["03"] = col_modelos(cur); gravar("03_modelos_oml.txt", textos["03"])
    textos["04"] = col_metricas(cur); gravar("04_metricas.txt", textos["04"])
    scoring = col_scoring(cur)
    payload, _ = col_json(cur)
    textos["07"], docker_ps, docker_logs = col_docker()
    gravar("docker_ps.txt", docker_ps)
    gravar("docker_logs_trecho.txt", docker_logs)
    apex = col_apex(cur)
    gravar("07_apex_consultas.txt", texto_apex(apex))
    print(f"  consultas APEX executadas: {[(t[:14], len(l), round(s, 2)) for t, c, l, s in apex]}")

    cols, l = consultar(cur, "SELECT banner_full FROM v$version")
    _, ts = consultar(cur, "SELECT TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS TZH:TZM') FROM dual")
    meta = {"banner": l[0][0].split("\n")[0], "gerado_em": agora(), "db_ts": ts[0][0]}
    secoes = montar_secoes(cur, textos, scoring, payload, apex)
    html_full = html_pagina(secoes, meta)
    caminho_html = gravar("evidencias.html", html_full)
    conn.close()

    if not args.sem_png:
        if not os.path.exists(EDGE):
            print(f"  Edge nao encontrado em {EDGE} - PNGs nao gerados")
        else:
            for i, (titulo, interno) in enumerate(secoes, 1):
                tmp_html = os.path.join(EVID, f"_secao_{i:02d}.html")
                with open(tmp_html, "w", encoding="utf-8") as f:
                    f.write(html_pagina(secoes, meta, apenas=i))
                png = os.path.join(EVID, f"evidencia_{i:02d}.png")
                alt = estimar_altura(interno)
                ok = render_png(tmp_html, png, alt)
                print(f"  {'ok  ' if ok else 'FALHA'} {png} ({alt}px) - {titulo}")
                try:
                    os.remove(tmp_html)
                except OSError:
                    pass
    print(f"[{agora()}] concluido em {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
