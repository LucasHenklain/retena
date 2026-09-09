# -*- coding: utf-8 -*-
"""
carregar_eventos.py - ingestao dos logs do LMS (parquet) na tabela EVENTOS_LMS do Oracle.

Passos:
  1. executa sql/01_ddl.sql (recria EVENTOS_LMS, DIM_FASE, DIM_TIPO_EVENTO)
  2. le logs_lms.parquet com pandas, converte "dd/mm/yyyy HH:MM" -> datetime
  3. insere em lotes de 10.000 linhas com cursor.executemany (bind arrays)
  4. coleta estatisticas (DBMS_STATS) e imprime contagens de verificacao

Uso: python carregar_eventos.py [--parquet <caminho>] [--lote 10000] [--sem-ddl] [--log <arquivo>]
"""
import argparse
import datetime as dt
import os
import sys
import time

import oracledb
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from executar_sql import Logger, conectar, executar_script, formatar_tabela  # noqa: E402

RAIZ = os.path.dirname(AQUI)
PARQUET_PADRAO = os.path.normpath(os.path.join(RAIZ, "..", "08_Dados", "logs_lms.parquet"))
DDL = os.path.join(RAIZ, "sql", "01_ddl.sql")

SQL_INSERT = """
INSERT INTO EVENTOS_LMS (FASE, TS_EVENTO, NOME, USUARIO_AFETADO, CONTEXTO, COMPONENTE, EVENTO, DESCRICAO, ORIGEM)
VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
"""


def consulta(cur, sql, log, titulo):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    log(f"\n== {titulo} ==")
    for l in formatar_tabela(cols, cur.fetchall()).splitlines():
        log(l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=PARQUET_PADRAO)
    ap.add_argument("--lote", type=int, default=10_000)
    ap.add_argument("--sem-ddl", action="store_true", help="nao recria as tabelas (apenas TRUNCATE + carga)")
    ap.add_argument("--log")
    args = ap.parse_args()
    log = Logger(args.log)

    t_ini = time.time()
    log(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Inicio da carga | parquet: {args.parquet}")
    conn = conectar()
    cur = conn.cursor()

    if args.sem_ddl:
        cur.execute("TRUNCATE TABLE EVENTOS_LMS")
        log("TRUNCATE TABLE EVENTOS_LMS - ok")
    else:
        ok, erros = executar_script(DDL, conn=conn, log=log)
        if erros:
            log("DDL com erros - abortando.")
            sys.exit(1)

    # ---- leitura e preparo ---------------------------------------------------
    df = pd.read_parquet(args.parquet)
    log(f"\nParquet lido: {len(df):,} linhas x {df.shape[1]} colunas".replace(",", "."))
    df["ts"] = pd.to_datetime(df["hora"], format="%d/%m/%Y %H:%M")
    cols = ["fase", "ts", "nome", "usuario_afetado", "contexto", "componente", "evento", "descricao", "origem"]
    for c in cols:
        if c != "ts":
            df[c] = df[c].astype("string").str.slice(0, 1000)
    registros = [
        (r.fase, r.ts.to_pydatetime(), r.nome, r.usuario_afetado, r.contexto, r.componente, r.evento, r.descricao, r.origem)
        for r in df[cols].itertuples(index=False)
    ]

    # tamanhos de bind fixos evitam re-alocacao entre lotes
    cur.setinputsizes(10, oracledb.DB_TYPE_DATE, 30, 30, 300, 60, 120, 1000, 10)
    total = len(registros)
    inseridos = 0
    t0 = time.time()
    for ini in range(0, total, args.lote):
        lote = registros[ini : ini + args.lote]
        cur.executemany(SQL_INSERT, lote)
        inseridos += len(lote)
        if (ini // args.lote) % 10 == 0 or inseridos == total:
            log(f"[{dt.datetime.now():%H:%M:%S}] lote {ini // args.lote + 1:>3}: {inseridos:>8,} / {total:,} linhas ({inseridos / total:6.1%}) - {time.time() - t0:6.1f}s".replace(",", "."))
    conn.commit()
    log(f"COMMIT - {inseridos:,} linhas inseridas em {time.time() - t0:.1f}s".replace(",", "."))

    # ---- estatisticas e verificacao -------------------------------------------
    cur.callproc("DBMS_STATS.GATHER_TABLE_STATS", [conn.username, "EVENTOS_LMS"])
    log("DBMS_STATS.GATHER_TABLE_STATS(EVENTOS_LMS) - ok")

    consulta(cur, """
        SELECT COUNT(*) total_eventos,
               SUM(FLG_ALUNO) eventos_de_alunos,
               COUNT(DISTINCT CASE WHEN FLG_ALUNO = 1 THEN NOME END) alunos_distintos,
               TO_CHAR(MIN(TS_EVENTO), 'YYYY-MM-DD HH24:MI') primeiro_evento,
               TO_CHAR(MAX(TS_EVENTO), 'YYYY-MM-DD HH24:MI') ultimo_evento
          FROM EVENTOS_LMS""", log, "EVENTOS_LMS - totais")
    consulta(cur, """
        SELECT e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS,
               COUNT(*) eventos,
               COUNT(DISTINCT CASE WHEN e.FLG_ALUNO = 1 THEN e.NOME END) alunos,
               MAX(e.CAPITULO) capitulo_max_observado,
               SUM(CASE WHEN e.CAPITULO IS NOT NULL THEN 1 ELSE 0 END) eventos_com_capitulo
          FROM EVENTOS_LMS e JOIN DIM_FASE f ON f.NUM_FASE = e.NUM_FASE
         GROUP BY e.NUM_FASE, f.NOME_FASE, f.TOTAL_CAPITULOS ORDER BY 1""", log, "Eventos por fase")
    consulta(cur, """
        SELECT NVL(t.CLASSE_EVENTO, 'OUTRO') classe_evento, COUNT(*) eventos
          FROM EVENTOS_LMS e LEFT JOIN DIM_TIPO_EVENTO t ON t.EVENTO = e.EVENTO
         WHERE e.FLG_ALUNO = 1
         GROUP BY NVL(t.CLASSE_EVENTO, 'OUTRO') ORDER BY 2 DESC""", log, "Eventos de alunos por classe (DIM_TIPO_EVENTO)")
    consulta(cur, """
        SELECT index_name, uniqueness, status FROM user_indexes WHERE table_name = 'EVENTOS_LMS' ORDER BY 1""", log, "Indices")

    log(f"\n[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Carga concluida em {time.time() - t_ini:.1f}s")
    conn.close()
    log.close()


if __name__ == "__main__":
    main()
