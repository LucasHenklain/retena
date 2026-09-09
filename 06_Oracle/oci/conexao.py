# -*- coding: utf-8 -*-
"""
conexao.py - resolve a conexao Oracle do Retena por variaveis de ambiente (.env),
SEM alterar os scripts existentes em ../scripts (que continuam com seus proprios padroes).

Modos (ORACLE_MODO = local | autonomous | auto; padrao = auto):
  local       Oracle Free 26ai em Docker. Mesmos valores atuais do pacote:
              ORACLE_USER=STARTUP  ORACLE_PASSWORD=Startup2026  ORACLE_DSN=localhost:1521/FREEPDB1
  autonomous  Autonomous AI Database (Serverless), duas formas:
              (a) mTLS com wallet : ORACLE_DSN=<alias>_high (do tnsnames.ora) + ORACLE_WALLET_DIR
                                    [+ ORACLE_WALLET_PASSWORD se a wallet nao tiver ewallet.pem]
              (b) TLS sem wallet  : ORACLE_DSN="(description=...(protocol=tcps)(port=1522)...)"
  auto        autonomous se ORACLE_WALLET_DIR estiver preenchido ou o DSN contiver "tcps"; senao local.

Ordem de precedencia: variaveis ja exportadas no ambiente > arquivo .env (nunca sobrescreve o ambiente).
Procura do .env: --env | ORACLE_ENV_FILE | <esta pasta>/.env | ../.env (06_Oracle/.env).

Adaptado do EduRetain (equipe Retena): db.py (_connect_kwargs / get_connection) e config.py,
com a diferenca de manter o modo local como padrao e de tornar a wallet_password opcional
(python-oracledb thin le cwallet.sso/ewallet.pem sem senha nas wallets recentes do Autonomous).

Uso:
  python conexao.py --teste            # conecta e imprime o banner + contagens
  python conexao.py --teste --env C:\\caminho\\.env
  from conexao import get_connection; conn = get_connection()
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import oracledb

AQUI = Path(__file__).resolve().parent

PADRAO_LOCAL = {
    "ORACLE_USER": "STARTUP",
    "ORACLE_PASSWORD": "Startup2026",
    "ORACLE_DSN": "localhost:1521/FREEPDB1",
}


# --------------------------------------------------------------------------- .env
def _carregar_env_simples(caminho: Path) -> int:
    """Fallback sem python-dotenv: KEY=VALUE por linha, ignora comentarios, nao sobrescreve o ambiente."""
    qtd = 0
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        s = linha.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        if k and k not in os.environ:
            os.environ[k] = v
            qtd += 1
    return qtd


def carregar_env(caminho: str | os.PathLike | None = None) -> Path | None:
    """Carrega o primeiro .env encontrado (sem sobrescrever variaveis ja definidas). Retorna o caminho usado."""
    candidatos = []
    if caminho:
        candidatos.append(Path(caminho))
    if os.environ.get("ORACLE_ENV_FILE"):
        candidatos.append(Path(os.environ["ORACLE_ENV_FILE"]))
    candidatos += [AQUI / ".env", AQUI.parent / ".env"]
    for p in candidatos:
        if p.is_file():
            try:
                from dotenv import load_dotenv  # type: ignore

                load_dotenv(p, override=False)
            except ImportError:
                _carregar_env_simples(p)
            return p
    return None


# --------------------------------------------------------------------------- resolucao
def _env(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome, padrao).strip()


def resolver_modo() -> str:
    modo = _env("ORACLE_MODO", "auto").lower()
    if modo in ("local", "autonomous"):
        return modo
    dsn = _env("ORACLE_DSN")
    if _env("ORACLE_WALLET_DIR") or "tcps" in dsn.lower():
        return "autonomous"
    return "local"


def connect_kwargs() -> dict:
    """Monta os kwargs de oracledb.connect() conforme o modo (padrao EduRetain _connect_kwargs, adaptado)."""
    modo = resolver_modo()
    if modo == "local":
        kwargs = {
            "user": _env("ORACLE_USER", PADRAO_LOCAL["ORACLE_USER"]),
            "password": _env("ORACLE_PASSWORD", PADRAO_LOCAL["ORACLE_PASSWORD"]),
            "dsn": _env("ORACLE_DSN", PADRAO_LOCAL["ORACLE_DSN"]),
        }
        return kwargs

    # autonomous
    user, pwd, dsn = _env("ORACLE_USER"), _env("ORACLE_PASSWORD"), _env("ORACLE_DSN")
    faltando = [n for n, v in (("ORACLE_USER", user), ("ORACLE_PASSWORD", pwd), ("ORACLE_DSN", dsn)) if not v]
    if faltando:
        raise SystemExit(f"Modo autonomous exige {', '.join(faltando)} no ambiente/.env")
    kwargs = {"user": user, "password": pwd, "dsn": dsn}
    wallet = _env("ORACLE_WALLET_DIR")
    if wallet:
        wdir = Path(wallet)
        if not (wdir / "tnsnames.ora").is_file():
            raise SystemExit(f"ORACLE_WALLET_DIR={wdir} nao contem tnsnames.ora (descompacte o zip da wallet nessa pasta)")
        kwargs.update(config_dir=str(wdir), wallet_location=str(wdir))
        if _env("ORACLE_WALLET_PASSWORD"):
            kwargs["wallet_password"] = _env("ORACLE_WALLET_PASSWORD")
    # TLS sem wallet: o proprio connect descriptor (protocol=tcps) basta no modo thin
    return kwargs


def get_connection(**extras) -> oracledb.Connection:
    """Conexao python-oracledb (modo thin). `extras` sobrescreve/adiciona kwargs (ex.: tag, events)."""
    kwargs = connect_kwargs()
    kwargs.update(extras)
    return oracledb.connect(**kwargs)


def descrever(mascarar: bool = True) -> str:
    kw = dict(connect_kwargs())
    if mascarar:
        for k in ("password", "wallet_password"):
            if k in kw:
                kw[k] = "***"
    return f"modo={resolver_modo()} " + " ".join(f"{k}={v}" for k, v in kw.items())


# --------------------------------------------------------------------------- teste
def testar() -> int:
    print(f"[conexao] {descrever()}")
    t0 = time.time()
    conn = get_connection()
    print(f"[conexao] conectado em {time.time() - t0:.2f}s | oracledb {oracledb.__version__} (thin={conn.thin})")
    cur = conn.cursor()
    cur.execute("SELECT banner_full FROM v$version")
    print("[banner] " + cur.fetchone()[0].replace("\n", " | "))
    cur.execute(
        """SELECT SYS_CONTEXT('USERENV','SESSION_USER'), SYS_CONTEXT('USERENV','CON_NAME'),
                  SYS_CONTEXT('USERENV','SERVICE_NAME'), SYS_CONTEXT('USERENV','SERVER_HOST'),
                  TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS TZH:TZM'), DBTIMEZONE
             FROM dual"""
    )
    u, con, svc, host, ts, tz = cur.fetchone()
    print(f"[sessao] usuario={u} container={con} service={svc} host={host} systimestamp={ts} dbtimezone={tz}")
    cur.execute("SELECT granted_role FROM user_role_privs ORDER BY 1")
    print("[roles]  " + ", ".join(r[0] for r in cur))
    for tab in ("EVENTOS_LMS", "RISCO_ALUNO_SNAPSHOT"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tab}")
            print(f"[tabela] {tab}: {cur.fetchone()[0]:,} linhas".replace(",", "."))
        except oracledb.DatabaseError as e:
            print(f"[tabela] {tab}: indisponivel ({str(e).splitlines()[0]})")
    cur.execute("SELECT model_name, algorithm, mining_function FROM user_mining_models ORDER BY 1")
    modelos = cur.fetchall()
    print(f"[oml]    {len(modelos)} modelo(s): " + "; ".join(f"{m} ({a}, {f})" for m, a, f in modelos))
    conn.close()
    print("[conexao] OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolucao de conexao Oracle (local Free / Autonomous) via .env")
    ap.add_argument("--teste", action="store_true", help="conecta e imprime banner/contagens")
    ap.add_argument("--env", help="caminho de um .env especifico")
    ap.add_argument("--mostrar", action="store_true", help="so imprime a configuracao resolvida (senha mascarada)")
    args = ap.parse_args()
    usado = carregar_env(args.env)
    print(f"[conexao] .env: {usado if usado else 'nenhum encontrado (usando ambiente/padroes locais)'}")
    if args.mostrar:
        print(descrever())
        return 0
    if args.teste:
        return testar()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
