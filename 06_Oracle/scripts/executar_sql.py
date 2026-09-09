# -*- coding: utf-8 -*-
"""
executar_sql.py - executa um script .sql contra o Oracle (python-oracledb, modo thin).

Regras de separacao de statements:
  * statements SQL terminam com ";"  (fora de aspas/comentarios)
  * blocos PL/SQL (DECLARE / BEGIN / CREATE [OR REPLACE] PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE)
    terminam com "/" sozinho em uma linha
  * "/" sozinho em linha tambem encerra um statement SQL pendente (compatibilidade SQL*Plus)

Uso:
  python executar_sql.py <arquivo.sql> [--log <arquivo.log>] [--parar-no-erro] [--max-linhas 50]

Conexao: variaveis ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN (padrao STARTUP / Startup2026 / localhost:1521/FREEPDB1)
"""
import argparse
import datetime as dt
import os
import re
import sys
import time

import oracledb

ORACLE_USER = os.environ.get("ORACLE_USER", "STARTUP")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "Startup2026")
ORACLE_DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")

RE_PLSQL = re.compile(
    r"^\s*(DECLARE|BEGIN|CREATE\s+(OR\s+REPLACE\s+)?(EDITIONABLE\s+|NONEDITIONABLE\s+)?"
    r"(PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE)\b)",
    re.IGNORECASE,
)


def conectar():
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)


class Logger:
    """Escreve no console e, opcionalmente, em arquivo (evidencia)."""

    def __init__(self, caminho=None):
        self.arq = None
        if caminho:
            os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
            self.arq = open(caminho, "w", encoding="utf-8")

    def __call__(self, msg=""):
        print(msg)
        if self.arq:
            self.arq.write(msg + "\n")
            self.arq.flush()

    def close(self):
        if self.arq:
            self.arq.close()


def dividir_statements(texto):
    """Divide o texto em [(statement, eh_plsql)] usando um automato de caracteres
    que ignora ';' dentro de aspas e comentarios."""
    stmts = []
    buf = []
    i, n = 0, len(texto)
    em_plsql = None  # None = inicio de statement ainda nao decidido
    inicio_linha = True

    def fechar(plsql):
        s = "".join(buf).strip()
        # remove comentarios que sobraram apenas com espacos (statement vazio)
        if s and not re.fullmatch(r"(\s|--[^\n]*\n?)*", s + "\n"):
            stmts.append((s, plsql))
        buf.clear()

    while i < n:
        ch = texto[i]
        # inicio de statement: decide o tipo quando aparece o primeiro token util
        if em_plsql is None:
            if ch.isspace():
                buf.append(ch)
                i += 1
                inicio_linha = ch == "\n"
                continue
            if texto.startswith("--", i):
                fim = texto.find("\n", i)
                fim = n if fim < 0 else fim
                i = fim
                buf.clear()  # comentario entre statements nao faz parte do proximo
                continue
            if texto.startswith("/*", i):
                fim = texto.find("*/", i + 2)
                i = n if fim < 0 else fim + 2
                buf.clear()
                continue
            if ch == "/" and inicio_linha and (i + 1 >= n or texto[i + 1] in "\r\n"):
                # "/" solto sem statement pendente - ignora
                i += 1
                continue
            resto = texto[i : i + 200]
            em_plsql = bool(RE_PLSQL.match(resto))
            buf.clear()

        # "/" sozinho na linha encerra o statement (SQL ou PL/SQL)
        if ch == "/" and inicio_linha:
            j = i + 1
            while j < n and texto[j] in " \t":
                j += 1
            if j >= n or texto[j] in "\r\n":
                fechar(em_plsql)
                em_plsql = None
                i = j
                continue

        if texto.startswith("--", i):
            fim = texto.find("\n", i)
            fim = n if fim < 0 else fim
            buf.append(texto[i:fim])
            i = fim
            continue
        if texto.startswith("/*", i):
            fim = texto.find("*/", i + 2)
            fim = n if fim < 0 else fim + 2
            buf.append(texto[i:fim])
            i = fim
            continue
        if ch == "'":
            j = i + 1
            while j < n:
                if texto[j] == "'":
                    if j + 1 < n and texto[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            buf.append(texto[i : j + 1])
            i = j + 1
            inicio_linha = False
            continue
        if ch == '"':
            j = texto.find('"', i + 1)
            j = n - 1 if j < 0 else j
            buf.append(texto[i : j + 1])
            i = j + 1
            inicio_linha = False
            continue
        if ch == ";" and not em_plsql:
            fechar(False)
            em_plsql = None
            i += 1
            inicio_linha = False
            continue

        buf.append(ch)
        inicio_linha = ch == "\n"
        i += 1

    if "".join(buf).strip():
        fechar(bool(em_plsql))
    return stmts


def resumo(stmt, tam=90):
    linha = " ".join(stmt.split())
    return linha if len(linha) <= tam else linha[: tam - 3] + "..."


def formatar_tabela(colunas, linhas, max_larg=40):
    def fmt(v):
        if v is None:
            return "NULL"
        if isinstance(v, float):
            return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.2f}"
        if isinstance(v, (dt.datetime, dt.date)):
            return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, dt.datetime) else v.isoformat()
        if hasattr(v, "read"):
            v = v.read()
        s = str(v).replace("\n", " ")
        return s if len(s) <= max_larg else s[: max_larg - 3] + "..."

    dados = [[fmt(v) for v in l] for l in linhas]
    largs = [len(c) for c in colunas]
    for l in dados:
        for k, v in enumerate(l):
            largs[k] = max(largs[k], len(v))
    sep = "+".join("-" * (w + 2) for w in largs)
    out = [sep, "|".join(f" {c:<{largs[k]}} " for k, c in enumerate(colunas)), sep]
    for l in dados:
        out.append("|".join(f" {v:<{largs[k]}} " for k, v in enumerate(l)))
    out.append(sep)
    return "\n".join(out)


def ler_dbms_output(cur, log):
    linhas = cur.var(str, arraysize=1000)
    qtd = cur.var(int)
    qtd.setvalue(0, 1000)
    try:
        cur.callproc("dbms_output.get_lines", (linhas, qtd))
    except oracledb.Error:
        return
    for l in (linhas.getvalue() or [])[: qtd.getvalue()]:
        log(f"      | {l}")


def executar_script(caminho, conn=None, log=None, parar_no_erro=False, max_linhas=50):
    """Executa o script. Retorna (qtd_ok, qtd_erros)."""
    log = log or Logger()
    fechar_conn = conn is None
    conn = conn or conectar()
    cur = conn.cursor()
    cur.callproc("dbms_output.enable", [None])
    with open(caminho, "r", encoding="utf-8") as f:
        texto = f.read()
    stmts = dividir_statements(texto)
    log(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Script: {os.path.abspath(caminho)}")
    log(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Conexao: {ORACLE_USER}@{ORACLE_DSN} | {len(stmts)} statement(s)")
    ok = erros = 0
    t0_total = time.time()
    for k, (stmt, plsql) in enumerate(stmts, 1):
        tipo = "PLSQL" if plsql else stmt.split(None, 1)[0].upper()
        log(f"[{dt.datetime.now():%H:%M:%S}] #{k:02d} {tipo:<7} {resumo(stmt)}")
        t0 = time.time()
        try:
            cur.execute(stmt)
            dur = time.time() - t0
            if cur.description:
                linhas = cur.fetchmany(max_linhas)
                cols = [d[0] for d in cur.description]
                tab = formatar_tabela(cols, linhas)
                for l in tab.splitlines():
                    log("      " + l)
                extra = cur.fetchmany(1)
                log(f"      {len(linhas)} linha(s) exibida(s){' (ha mais)' if extra else ''} em {dur:.2f}s")
            else:
                if tipo in ("INSERT", "UPDATE", "DELETE", "MERGE"):
                    log(f"      OK - {cur.rowcount} linha(s) afetada(s) em {dur:.2f}s")
                else:
                    log(f"      OK em {dur:.2f}s")
            if plsql:
                ler_dbms_output(cur, log)
            ok += 1
        except oracledb.Error as e:
            dur = time.time() - t0
            (err,) = e.args
            log(f"      ERRO em {dur:.2f}s: {str(err.message).strip()}")
            if plsql:
                ler_dbms_output(cur, log)
            erros += 1
            if parar_no_erro:
                break
    conn.commit()
    log(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] Fim: {ok} ok, {erros} erro(s), {time.time() - t0_total:.1f}s")
    if fechar_conn:
        conn.close()
    return ok, erros


def main():
    ap = argparse.ArgumentParser(description="Executa script SQL/PLSQL no Oracle")
    ap.add_argument("arquivo")
    ap.add_argument("--log", help="arquivo de log (tee)")
    ap.add_argument("--parar-no-erro", action="store_true")
    ap.add_argument("--max-linhas", type=int, default=50)
    args = ap.parse_args()
    log = Logger(args.log)
    try:
        ok, erros = executar_script(args.arquivo, log=log, parar_no_erro=args.parar_no_erro, max_linhas=args.max_linhas)
    finally:
        log.close()
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
