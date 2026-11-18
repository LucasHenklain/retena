# -*- coding: utf-8 -*-
"""
Retena MVP - API REST sobre o Oracle AI Database (26ai Free local / Autonomous AI Database).

O fluxo principal roda de ponta a ponta no banco:
  fila (RISCO_ALUNO_SNAPSHOT, pontuado por OML via DBMS_SCHEDULER)
  -> aluno (features + fatores PREDICTION_DETAILS + predicao ao vivo PREDICTION_PROBABILITY)
  -> registro do contato (PRC_REGISTRAR_CONTATO grava CONTATO_RESULTADO e atualiza a fila na mesma transacao)
  -> diretoria (VW_DIRETORIA_RESUMO recalcula receita em risco e preservada a partir do banco)

Execucao:  python -m uvicorn app:app --app-dir api --port 8080      (ver iniciar.ps1)
Conexao:   ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN  (padrao STARTUP / Startup2026 / localhost:1521/FREEPDB1)
"""
from __future__ import annotations

import datetime as dt
import decimal
import os
import time
from pathlib import Path
from typing import Literal, Optional

import oracledb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

AQUI = Path(__file__).resolve().parent
RAIZ_MVP = AQUI.parent                                   # 11_Entrega_Final/01_MVP_Oracle
WEB = RAIZ_MVP / "web"
DASH_OFFLINE = (RAIZ_MVP / ".." / ".." / "05_MVP" / "dashboard").resolve()

ORACLE_USER = os.environ.get("ORACLE_USER", "STARTUP")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "Startup2026")
ORACLE_DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")

app = FastAPI(title="Retena MVP API", version="1.0",
              description="Fila de permanência, registro de contato e visão da diretoria sobre Oracle AI Database + OML.")
_pool: Optional[oracledb.ConnectionPool] = None


def pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN,
                                     min=1, max=4, increment=1, getmode=oracledb.POOL_GETMODE_WAIT,
                                     wait_timeout=10000)
    return _pool


def _conv(v):
    if isinstance(v, decimal.Decimal):
        return float(v) if v % 1 else int(v)
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    if isinstance(v, oracledb.LOB):
        return v.read()
    return v


def consultar(sql: str, binds: dict | None = None, conn=None) -> list[dict]:
    def _run(c):
        cur = c.cursor()
        cur.execute(sql, binds or {})
        cols = [d[0].lower() for d in cur.description]
        return [{k: _conv(v) for k, v in zip(cols, row)} for row in cur.fetchall()]
    if conn is not None:
        return _run(conn)
    with pool().acquire() as c:
        return _run(c)


@app.exception_handler(oracledb.Error)
async def erro_oracle(_, exc: oracledb.Error):
    msg = str(exc).splitlines()[0]
    status = 503 if any(k in msg for k in ("DPY-6005", "DPY-4011", "DPY-6000", "ORA-12541", "ORA-12514", "DPY-4005")) else 400
    return JSONResponse(status_code=status, content={"erro": msg, "oracle": True})


# ----------------------------------------------------------------------------- traducao dos fatores do modelo
ROTULO_FATOR = {
    "RECENCIA_DIAS": "{v} dias sem acessar o LMS",
    "DIAS_ATIVOS_28D": "{v} dias com acesso nas últimas 4 semanas",
    "EVENTOS_28D": "{v} ações no LMS em 28 dias",
    "EVENTOS_14D": "{v} ações no LMS em 14 dias",
    "EVENTOS_7D": "{v} ações no LMS na última semana",
    "TENDENCIA": "tendência de uso {v} (últimas 2 semanas vs. anteriores)",
    "PROGRESSO_28D": "{v} registros de progresso em 28 dias",
    "CAPITULOS_DISTINTOS_28D": "{v} capítulos diferentes em 28 dias",
    "QUIZ_28D": "{v} questionários em 28 dias",
    "ENTREGAS_28D": "{v} entregas em 28 dias",
}
FEATURES = ["RECENCIA_DIAS", "EVENTOS_7D", "EVENTOS_14D", "EVENTOS_28D", "DIAS_ATIVOS_28D", "PROGRESSO_28D",
            "CAPITULOS_DISTINTOS_28D", "QUIZ_28D", "ENTREGAS_28D", "TENDENCIA", "NUM_FASE_ATUAL", "EVENTOS_ACUMULADOS"]


def _fatores_legiveis(fatores_json: str | None) -> list[dict]:
    import json
    try:
        itens = json.loads(fatores_json or "[]")
    except ValueError:
        return []
    out = []
    for f in itens:
        attr, valor = f.get("atributo"), f.get("valor")
        try:
            vnum = float(valor)
            vtxt = f"{vnum:+.0%}".replace(".", ",") if attr == "TENDENCIA" else (f"{vnum:.0f}" if vnum == int(vnum) else f"{vnum:.1f}")
        except (TypeError, ValueError):
            vtxt = str(valor)
        texto = ROTULO_FATOR.get(attr, attr + " = {v}").format(v=vtxt)
        if vtxt == "1":   # singular so na palavra logo apos o numero: "1 dia", "1 ação", "1 capítulo"...
            for pl, sg in (("1 dias", "1 dia"), ("1 ações", "1 ação"), ("1 registros", "1 registro"),
                           ("1 capítulos diferentes", "1 capítulo"), ("1 questionários", "1 questionário"),
                           ("1 entregas", "1 entrega")):
                if texto.startswith(pl):
                    texto = sg + texto[len(pl):]
        out.append({"atributo": attr, "valor": valor, "peso": f.get("peso"), "texto": texto})
    return out


# ----------------------------------------------------------------------------- saude / status
@app.get("/api/saude")
def saude():
    t0 = time.perf_counter()
    with pool().acquire() as c:
        banner = consultar("SELECT BANNER_FULL FROM V$VERSION", conn=c)
        resumo = consultar("""SELECT s.*, (SELECT COUNT(*) FROM CONTATO_RESULTADO) CONTATOS,
                                     (SELECT COUNT(*) FROM EVENTOS_LMS) EVENTOS
                                FROM (SELECT COUNT(*) ALUNOS, MAX(DT_SCORING) DT_SCORING, MAX(DT_CORTE) DT_CORTE
                                        FROM RISCO_ALUNO_SNAPSHOT) s""", conn=c)[0]
        job = consultar("""SELECT JOB_NAME, STATE, ENABLED, REPEAT_INTERVAL,
                                  TO_CHAR(LAST_START_DATE, 'YYYY-MM-DD"T"HH24:MI:SS') LAST_START,
                                  TO_CHAR(NEXT_RUN_DATE, 'YYYY-MM-DD"T"HH24:MI:SS') NEXT_RUN, RUN_COUNT
                             FROM USER_SCHEDULER_JOBS WHERE JOB_NAME = 'JOB_RETENA_SCORING_SEMANAL'""", conn=c)
        modelos = consultar("""SELECT m.MODEL_NAME, m.ALGORITHM, m.MINING_FUNCTION,
                                      TO_CHAR(m.CREATION_DATE, 'YYYY-MM-DD') CRIADO_EM,
                                      (SELECT ROUND(MAX(VALOR), 3) FROM AVALIACAO_MODELOS a
                                        WHERE a.MODELO = m.MODEL_NAME AND a.METRICA = 'AUC_COMPUTE_ROC') AUC,
                                      (SELECT ROUND(MAX(VALOR), 2) FROM AVALIACAO_MODELOS a
                                        WHERE a.MODELO = m.MODEL_NAME AND a.METRICA = 'LIFT_TOP20PCT') LIFT_TOP20
                                 FROM USER_MINING_MODELS m ORDER BY m.MODEL_NAME""", conn=c)
    return {"ok": True, "banco": banner[0]["banner_full"].splitlines()[0], "dsn": ORACLE_DSN, "usuario": ORACLE_USER,
            **resumo, "job": job[0] if job else None, "modelos": modelos,
            "latencia_ms": round(1000 * (time.perf_counter() - t0), 1)}


# ----------------------------------------------------------------------------- fila
@app.get("/api/fila")
def fila(escopo: Literal["fila", "tratados", "todos"] = "fila",
         faixa: Optional[Literal["Alto", "Médio", "Baixo"]] = None, limite: int = Query(100, ge=1, le=300)):
    filtro = {"fila": "NA_FILA = 1",
              "tratados": "STATUS_ATENDIMENTO NOT IN ('PENDENTE')",
              "todos": "1 = 1"}[escopo]
    binds = {"lim": limite}
    if faixa:
        filtro += " AND FAIXA_RISCO = :faixa"
        binds["faixa"] = faixa
    linhas = consultar(f"""SELECT POSICAO, GRUPO_FILA, NOME, NUM_FASE_ATUAL, NOME_FASE, CAPITULO_MAX_FASE, PCT_CAPITULOS_FASE,
                                  RECENCIA_DIAS, EVENTOS_7D, EVENTOS_28D, DIAS_ATIVOS_28D, TENDENCIA,
                                  PROB_INATIVO_21D, PROB_EVASAO_FASE, FAIXA_RISCO, FATORES_JSON, ACAO_SUGERIDA,
                                  STATUS_ATENDIMENTO, ULTIMO_RESULTADO, DT_ULTIMO_CONTATO, TENTATIVAS, NA_FILA
                             FROM VW_FILA_COORDENACAO WHERE {filtro}
                            ORDER BY POSICAO FETCH FIRST :lim ROWS ONLY""", binds)
    for l in linhas:
        l["fatores"] = _fatores_legiveis(l.pop("fatores_json"))
    contagem = consultar("""SELECT SUM(NA_FILA) NA_FILA,
                                   SUM(CASE WHEN STATUS_ATENDIMENTO <> 'PENDENTE' THEN 1 ELSE 0 END) TRATADOS,
                                   COUNT(*) TODOS FROM VW_FILA_COORDENACAO""")[0]
    return {"escopo": escopo, "contagem": contagem, "alunos": linhas}


# ----------------------------------------------------------------------------- aluno
@app.get("/api/alunos/{nome}")
def aluno(nome: str):
    with pool().acquire() as c:
        r = consultar("SELECT * FROM VW_FILA_COORDENACAO WHERE NOME = :n", {"n": nome}, conn=c)
        if not r:
            raise HTTPException(404, f"Aluno não encontrado: {nome}")
        a = r[0]
        a["fatores"] = _fatores_legiveis(a.pop("fatores_json"))
        a["atividade_semanal"] = consultar("""
            WITH sem AS (SELECT TRUNC(:corte, 'IW') - 7 * (LEVEL - 1) INICIO FROM dual CONNECT BY LEVEL <= 12)
            SELECT TO_CHAR(s.INICIO, 'YYYY-MM-DD') SEMANA, COUNT(e.ID_EVENTO) EVENTOS
              FROM sem s LEFT JOIN EVENTOS_LMS e
                ON e.NOME = :n AND e.FLG_ALUNO = 1 AND e.TS_EVENTO >= s.INICIO AND e.TS_EVENTO < s.INICIO + 7
             GROUP BY s.INICIO ORDER BY s.INICIO""",
            {"n": nome, "corte": dt.datetime.fromisoformat(a["dt_corte"])}, conn=c)
        a["contatos"] = consultar("""SELECT ID_CONTATO, DT_CONTATO, RESULTADO, CANAL, RESPONSAVEL, OBSERVACAO,
                                            PROB_NO_CONTATO, FAIXA_NO_CONTATO
                                       FROM CONTATO_RESULTADO WHERE NOME = :n ORDER BY DT_CONTATO DESC, ID_CONTATO DESC""",
                                  {"n": nome}, conn=c)
    return a


class Simulacao(BaseModel):
    recencia_dias: Optional[float] = Field(None, ge=0, le=400)
    eventos_7d: Optional[float] = Field(None, ge=0, le=5000)
    dias_ativos_28d: Optional[float] = Field(None, ge=0, le=28)


@app.post("/api/alunos/{nome}/predicao")
def predicao(nome: str, sim: Simulacao | None = None):
    """Aplica o modelo OML RETENA_INATIVO21_RF AGORA, dentro do banco, sobre as features do aluno.
    Com corpo, faz um 'e se' (ex.: o aluno voltar a acessar esta semana)."""
    sim = sim or Simulacao()
    sel = []
    binds = {"n": nome}
    for f in FEATURES:
        k = f.lower()
        if getattr(sim, k, None) is not None:
            sel.append(f":{k} AS {f}")
            binds[k] = getattr(sim, k)
        else:
            sel.append(f"s.{f} AS {f}")
    sql = f"""SELECT x.NOME,
                     ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING x.*), 4)  PROB_RF,
                     ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_GLM, 1 USING x.*), 4) PROB_GLM
                FROM (SELECT s.NOME, {', '.join(sel)} FROM RISCO_ALUNO_SNAPSHOT s WHERE s.NOME = :n) x"""
    t0 = time.perf_counter()
    r = consultar(sql, binds)
    if not r:
        raise HTTPException(404, f"Aluno não encontrado: {nome}")
    return {**r[0], "simulacao": sim.model_dump(exclude_none=True), "ms": round(1000 * (time.perf_counter() - t0), 1),
            "sql": "PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING <features do aluno>)"}


# ----------------------------------------------------------------------------- contatos
class Contato(BaseModel):
    aluno: str = Field(..., min_length=3, max_length=30)
    resultado: Literal["REATIVADO", "PLANO_COMBINADO", "SEM_RESPOSTA", "VAI_CANCELAR"]
    canal: Literal["WHATSAPP", "TELEFONE", "EMAIL", "LMS", "PRESENCIAL"] = "WHATSAPP"
    responsavel: Optional[str] = Field(None, max_length=60)
    observacao: Optional[str] = Field(None, max_length=400)


@app.post("/api/contatos", status_code=201)
def registrar_contato(c: Contato):
    with pool().acquire() as conn:
        cur = conn.cursor()
        id_out = cur.var(oracledb.NUMBER)
        st_out = cur.var(oracledb.STRING)
        try:
            cur.callproc("PRC_REGISTRAR_CONTATO", [c.aluno, c.resultado, c.canal, c.responsavel, c.observacao,
                                                   id_out, st_out])
        except oracledb.DatabaseError as e:
            msg = str(e).splitlines()[0]
            raise HTTPException(404 if "ORA-20001" in msg else 400, msg)
        novo = consultar("SELECT * FROM CONTATO_RESULTADO WHERE ID_CONTATO = :i", {"i": int(id_out.getvalue())}, conn=conn)[0]
    return {"id_contato": novo["id_contato"], "novo_status": st_out.getvalue(), "registro": novo,
            "sql_verificacao": f"SELECT * FROM CONTATO_RESULTADO WHERE ID_CONTATO = {novo['id_contato']};"}


@app.get("/api/contatos")
def contatos(limite: int = Query(20, ge=1, le=200)):
    return consultar("""SELECT ID_CONTATO, NOME, DT_CONTATO, RESULTADO, CANAL, RESPONSAVEL, OBSERVACAO,
                               PROB_NO_CONTATO, FAIXA_NO_CONTATO
                          FROM CONTATO_RESULTADO ORDER BY ID_CONTATO DESC FETCH FIRST :l ROWS ONLY""", {"l": limite})


# ----------------------------------------------------------------------------- diretoria
@app.get("/api/diretoria")
def diretoria():
    with pool().acquire() as c:
        resumo = consultar("SELECT * FROM VW_DIRETORIA_RESUMO", conn=c)[0]
        por_faixa = consultar("SELECT * FROM VW_RESULTADO_CONTATOS ORDER BY PROB_MEDIA_NO_CONTATO DESC", conn=c)
        por_fase = consultar("""SELECT NUM_FASE_ATUAL FASE, COUNT(*) ALUNOS,
                                       SUM(CASE WHEN FAIXA_RISCO = 'Alto' THEN 1 ELSE 0 END) ALTO,
                                       SUM(CASE WHEN FAIXA_RISCO = 'Médio' THEN 1 ELSE 0 END) MEDIO
                                  FROM RISCO_ALUNO_SNAPSHOT GROUP BY NUM_FASE_ATUAL ORDER BY 1""", conn=c)
    return {"resumo": resumo, "resultado_por_faixa": por_faixa, "risco_por_fase": por_fase}


class Parametros(BaseModel):
    ticket_mensal: float = Field(..., ge=50, le=5000)


@app.put("/api/parametros")
def salvar_parametros(p: Parametros):
    with pool().acquire() as c:
        cur = c.cursor()
        cur.execute("UPDATE PARAMETRO_IES SET VALOR = :v, DT_ATUALIZACAO = SYSTIMESTAMP WHERE CHAVE = 'TICKET_MENSAL'",
                    {"v": p.ticket_mensal})
        c.commit()
    return diretoria()


# ----------------------------------------------------------------------------- scoring (job OML)
@app.post("/api/scoring")
def executar_scoring():
    """Dispara o job semanal JOB_RETENA_SCORING_SEMANAL (DBMS_SCHEDULER) agora e espera terminar (~25-40 s)."""
    t0 = time.perf_counter()
    with pool().acquire() as c:
        c.cursor().execute("BEGIN DBMS_SCHEDULER.RUN_JOB('JOB_RETENA_SCORING_SEMANAL', use_current_session => TRUE); END;")
        r = consultar("""SELECT MAX(DT_SCORING) DT_SCORING, COUNT(*) ALUNOS,
                                SUM(CASE WHEN FAIXA_RISCO = 'Alto' THEN 1 ELSE 0 END) ALTO,
                                SUM(CASE WHEN FAIXA_RISCO = 'Médio' THEN 1 ELSE 0 END) MEDIO
                           FROM RISCO_ALUNO_SNAPSHOT""", conn=c)[0]
    return {**r, "segundos": round(time.perf_counter() - t0, 1)}


@app.get("/api/scoring/execucoes")
def execucoes():
    return consultar("""SELECT LOG_ID, TO_CHAR(ACTUAL_START_DATE, 'YYYY-MM-DD"T"HH24:MI:SS') INICIO,
                               EXTRACT(MINUTE FROM RUN_DURATION) * 60 + EXTRACT(SECOND FROM RUN_DURATION) SEGUNDOS, STATUS
                          FROM USER_SCHEDULER_JOB_RUN_DETAILS WHERE JOB_NAME = 'JOB_RETENA_SCORING_SEMANAL'
                         ORDER BY LOG_ID DESC FETCH FIRST 6 ROWS ONLY""")


# ----------------------------------------------------------------------------- prova SQL (consultas fixas)
PROVAS = {
    "ultimos_contatos": ("Últimos contatos gravados no Oracle",
        """SELECT ID_CONTATO, NOME, TO_CHAR(DT_CONTATO, 'DD/MM HH24:MI:SS') DT_CONTATO, RESULTADO, CANAL,
       RESPONSAVEL, PROB_NO_CONTATO, FAIXA_NO_CONTATO
  FROM CONTATO_RESULTADO
 ORDER BY ID_CONTATO DESC
 FETCH FIRST 5 ROWS ONLY"""),
    "status_fila": ("Status da fila no snapshot (atualizado pela procedure)",
        """SELECT STATUS_ATENDIMENTO, FAIXA_RISCO, COUNT(*) ALUNOS
  FROM RISCO_ALUNO_SNAPSHOT
 GROUP BY STATUS_ATENDIMENTO, FAIXA_RISCO
 ORDER BY 1, 2"""),
    "diretoria": ("Visão da diretoria recalculada no banco",
        """SELECT ALUNOS_ALTO, NA_FILA, TICKET, RECEITA_ANUAL_EM_RISCO,
       CONTATOS_REGISTRADOS, REATIVADOS, RECEITA_PRESERVADA_ESTIMADA
  FROM VW_DIRETORIA_RESUMO"""),
    "scoring_in_database": ("Scoring OML in-database (5 maiores riscos)",
        """SELECT NOME, RECENCIA_DIAS,
       ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, 1 USING s.*), 4) PROB_RF_AGORA,
       PROB_INATIVO_21D PROB_NO_SNAPSHOT, FAIXA_RISCO
  FROM RISCO_ALUNO_SNAPSHOT s
 ORDER BY PROB_INATIVO_21D DESC, NOME
 FETCH FIRST 5 ROWS ONLY"""),
    "job_scheduler": ("Job semanal de scoring (DBMS_SCHEDULER)",
        """SELECT JOB_NAME, STATE, REPEAT_INTERVAL,
       TO_CHAR(LAST_START_DATE, 'DD/MM/YYYY HH24:MI:SS') ULTIMA_EXECUCAO,
       TO_CHAR(NEXT_RUN_DATE, 'DD/MM/YYYY HH24:MI') PROXIMA, RUN_COUNT
  FROM USER_SCHEDULER_JOBS"""),
    "duality_view": ("Documento JSON do aluno pela Duality View",
        """SELECT JSON_SERIALIZE(dv.DATA RETURNING VARCHAR2(4000)) DOCUMENTO
  FROM RISCO_ALUNO_DV dv
 WHERE dv.DATA.atendimento.status.string() <> 'PENDENTE'
 FETCH FIRST 2 ROWS ONLY"""),
}


@app.get("/api/sql")
def lista_provas():
    return [{"id": k, "titulo": v[0], "sql": v[1]} for k, v in PROVAS.items()]


@app.get("/api/sql/{prova}")
def executar_prova(prova: str):
    if prova not in PROVAS:
        raise HTTPException(404, "consulta desconhecida")
    titulo, sql = PROVAS[prova]
    t0 = time.perf_counter()
    linhas = consultar(sql)
    return {"id": prova, "titulo": titulo, "sql": sql, "linhas": linhas, "ms": round(1000 * (time.perf_counter() - t0), 1)}


# ----------------------------------------------------------------------------- front-end
if DASH_OFFLINE.exists():
    app.mount("/offline", StaticFiles(directory=str(DASH_OFFLINE), html=True), name="offline")
    _marca = DASH_OFFLINE.parent.parent / "03_Marca"          # o painel offline referencia ../../03_Marca/logo
    if _marca.exists():
        app.mount("/03_Marca", StaticFiles(directory=str(_marca)), name="marca")


@app.get("/")
def raiz():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=str(WEB)), name="web")
