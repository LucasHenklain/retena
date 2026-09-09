# -*- coding: utf-8 -*-
"""
executar_sql_oci.py - roda um ou mais scripts .sql com o runner EXISTENTE (../scripts/executar_sql.py),
mas com a conexao resolvida por conexao.py (Free local ou Autonomous com wallet mTLS / TLS).

Motivo: scripts/executar_sql.py conecta com user/password/dsn puros (suficiente no Free e no TLS sem
wallet); para o Autonomous com wallet e preciso config_dir/wallet_location - e isso quem resolve e o
conexao.py, sem tocar no runner original (arquivos do manifesto v1 nao sao alterados).

Uso:
  python executar_sql_oci.py sql\\09_merge_risco_snapshot.sql [--log-dir <pasta>] [--parar-no-erro] [--env <.env>]
  python executar_sql_oci.py ..\\sql\\01_ddl.sql sql\\08_dbms_cloud_ingestao.sql ..\\sql\\02_*.sql ...   (ordem = argumentos)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))  # ../scripts/executar_sql.py
sys.path.insert(0, str(AQUI))

import executar_sql  # noqa: E402  (runner original, inalterado)
from conexao import carregar_env, connect_kwargs, descrever, get_connection  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Executa scripts SQL/PLSQL usando a conexao do conexao.py")
    ap.add_argument("arquivos", nargs="+", help="scripts .sql, executados na ordem informada")
    ap.add_argument("--log-dir", help="pasta para <nome_do_script>.log (padrao: sem arquivo de log)")
    ap.add_argument("--parar-no-erro", action="store_true")
    ap.add_argument("--max-linhas", type=int, default=50)
    ap.add_argument("--env", help="caminho de um .env especifico")
    args = ap.parse_args()

    usado = carregar_env(args.env)
    print(f"[conexao] .env: {usado if usado else 'nenhum (ambiente/padroes locais)'} | {descrever()}")
    kw = connect_kwargs()
    # so para o cabecalho do log do runner refletir a conexao real (o runner usa esses globais apenas no print)
    executar_sql.ORACLE_USER, executar_sql.ORACLE_DSN = kw["user"], kw["dsn"]

    total_erros = 0
    for arquivo in args.arquivos:
        caminho = Path(arquivo)
        if not caminho.is_file():
            print(f"[erro] arquivo nao encontrado: {caminho}")
            return 2
        log = executar_sql.Logger(str(Path(args.log_dir) / f"{caminho.stem}.log") if args.log_dir else None)
        conn = get_connection()
        try:
            ok, erros = executar_sql.executar_script(
                str(caminho), conn=conn, log=log, parar_no_erro=args.parar_no_erro, max_linhas=args.max_linhas
            )
        finally:
            conn.close()
            log.close()
        total_erros += erros
        if erros and args.parar_no_erro:
            break
    return 1 if total_erros else 0


if __name__ == "__main__":
    sys.exit(main())
