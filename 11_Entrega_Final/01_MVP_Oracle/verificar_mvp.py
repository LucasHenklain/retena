# -*- coding: utf-8 -*-
"""
verificar_mvp.py - teste ponta a ponta do MVP Retena (API + Oracle).

Executa o fluxo principal como a coordenadora faria e confere cada passo DIRETO no banco (SQL), sem confiar na API:
  1. /api/saude          -> banco, modelos OML, job
  2. /api/fila           -> fila lida do RISCO_ALUNO_SNAPSHOT
  3. /api/alunos/{n}     -> detalhe + fatores + atividade semanal
  4. /api/alunos/{n}/predicao -> PREDICTION_PROBABILITY ao vivo (e "e se")
  5. POST /api/contatos  -> PRC_REGISTRAR_CONTATO; confere a linha em CONTATO_RESULTADO e o status no snapshot via SQL
  6. /api/diretoria      -> receita preservada recalculada no banco (+ ticket x 12 por reativado)
  7. limpeza: apaga os contatos de teste e devolve o status original (a menos que --manter)

Uso:  python verificar_mvp.py [--url http://127.0.0.1:8080] [--manter]
Sai com codigo 0 se tudo passar. Grava o relatorio em logs/verificacao_mvp.txt.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

import oracledb

AQUI = Path(__file__).resolve().parent
RESP_TESTE = "teste-automatico (verificar_mvp.py)"
linhas_log = []


def log(msg=""):
    print(msg)
    linhas_log.append(msg)


def http(url, metodo="GET", corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.loads(r.read().decode())


def checar(cond, msg):
    log(("  [OK]   " if cond else "  [FALHA] ") + msg)
    if not cond:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("RETENA_URL", "http://127.0.0.1:8080"))
    ap.add_argument("--manter", action="store_true", help="nao apaga o contato de teste no final")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    conn = oracledb.connect(user=os.environ.get("ORACLE_USER", "STARTUP"), password=os.environ.get("ORACLE_PASSWORD", "Startup2026"),
                            dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))
    cur = conn.cursor()
    log(f"Verificacao do MVP Retena - {dt.datetime.now():%Y-%m-%d %H:%M:%S} - API {base}")

    log("\n1) Saude do banco")
    _, s = http(base + "/api/saude")
    log(f"  banco: {s['banco']}")
    checar(s["alunos"] > 0, f"{s['alunos']} alunos no RISCO_ALUNO_SNAPSHOT; {s['eventos']} eventos em EVENTOS_LMS")
    checar(len(s["modelos"]) >= 1, "modelos OML: " + ", ".join(f"{m['model_name']} ({m['algorithm']}, AUC {m['auc']})" for m in s["modelos"]))
    checar(s["job"] is not None, f"job {s['job']['job_name']} estado {s['job']['state']}, proxima execucao {s['job']['next_run']}")

    log("\n2) Fila de segunda")
    _, f = http(base + "/api/fila?escopo=fila")
    checar(len(f["alunos"]) > 0, f"{f['contagem']['na_fila']} alunos na fila; primeiro: {f['alunos'][0]['nome']} ({f['alunos'][0]['grupo_fila']}, risco {f['alunos'][0]['prob_inativo_21d']:.1%})")
    cur.execute("SELECT COUNT(*) FROM VW_FILA_COORDENACAO WHERE NA_FILA = 1")
    checar(cur.fetchone()[0] == f["contagem"]["na_fila"], "contagem da API = contagem em SQL (VW_FILA_COORDENACAO)")
    aluno = f["alunos"][0]["nome"]

    log(f"\n3) Painel do aluno {aluno}")
    _, d = http(base + "/api/alunos/" + urllib.request.quote(aluno))
    checar(len(d["fatores"]) > 0, "motivos: " + "; ".join(x["texto"] for x in d["fatores"]))
    checar(len(d["atividade_semanal"]) == 12, "atividade das ultimas 12 semanas lida de EVENTOS_LMS: " + str([w["eventos"] for w in d["atividade_semanal"]]))
    status_original = d["status_atendimento"]

    log("\n4) Predicao ao vivo no Oracle (PREDICTION_PROBABILITY)")
    _, p = http(base + f"/api/alunos/{urllib.request.quote(aluno)}/predicao", "POST", {})
    checar(abs(p["prob_rf"] - d["prob_inativo_21d"]) < 0.0001, f"agora {p['prob_rf']:.1%} = snapshot {d['prob_inativo_21d']:.1%} ({p['ms']} ms)")
    _, p2 = http(base + f"/api/alunos/{urllib.request.quote(aluno)}/predicao", "POST", {"recencia_dias": 1, "eventos_7d": 30, "dias_ativos_28d": 5})
    checar(p2["prob_rf"] < p["prob_rf"], f"'e se voltar esta semana': {p2['prob_rf']:.1%} (< {p['prob_rf']:.1%})")

    log("\n5) Registro do contato (grava no Oracle)")
    _, dir0 = http(base + "/api/diretoria")
    r0 = dir0["resumo"]
    st, r = http(base + "/api/contatos", "POST", {"aluno": aluno, "resultado": "REATIVADO", "canal": "WHATSAPP",
                                                   "responsavel": RESP_TESTE, "observacao": "contato de teste automatico"})
    checar(st == 201, f"HTTP 201, ID_CONTATO {r['id_contato']}, novo status {r['novo_status']}")
    cur.execute("SELECT NOME, RESULTADO, CANAL, FAIXA_NO_CONTATO, PROB_NO_CONTATO FROM CONTATO_RESULTADO WHERE ID_CONTATO = :i", i=r["id_contato"])
    row = cur.fetchone()
    checar(row is not None and row[0] == aluno and row[1] == "REATIVADO", f"SQL: SELECT ... FROM CONTATO_RESULTADO WHERE ID_CONTATO = {r['id_contato']} -> {row}")
    cur.execute("SELECT STATUS_ATENDIMENTO FROM RISCO_ALUNO_SNAPSHOT WHERE NOME = :n", n=aluno)
    checar(cur.fetchone()[0] == "REATIVADO", "SQL: RISCO_ALUNO_SNAPSHOT.STATUS_ATENDIMENTO = 'REATIVADO' (mesma transacao)")
    _, f2 = http(base + "/api/fila?escopo=fila")
    checar(aluno not in [x["nome"] for x in f2["alunos"]], f"aluno saiu da fila ({f['contagem']['na_fila']} -> {f2['contagem']['na_fila']})")

    log("\n6) Diretoria recalculada no banco")
    _, dir1 = http(base + "/api/diretoria")
    r1 = dir1["resumo"]
    delta = r1["receita_preservada_estimada"] - r0["receita_preservada_estimada"]
    esperado = r1["ticket"] * r1["meses"] if status_original != "REATIVADO" else 0
    checar(abs(delta - esperado) < 0.01, f"receita preservada {r0['receita_preservada_estimada']} -> {r1['receita_preservada_estimada']} (+{delta:.0f} = ticket {r1['ticket']} x {r1['meses']})")
    checar(r1["contatos_registrados"] == r0["contatos_registrados"] + 1, f"contatos registrados {r0['contatos_registrados']} -> {r1['contatos_registrados']}")

    if not a.manter:
        log("\n7) Limpeza do teste")
        cur.execute("DELETE FROM CONTATO_RESULTADO WHERE RESPONSAVEL = :r", r=RESP_TESTE)
        apagados = cur.rowcount
        cur.execute("""UPDATE RISCO_ALUNO_SNAPSHOT s SET STATUS_ATENDIMENTO = :st, OBSERVACAO = NULL
                        WHERE NOME = :n AND NOT EXISTS (SELECT 1 FROM CONTATO_RESULTADO c WHERE c.NOME = s.NOME)""", st=status_original, n=aluno)
        conn.commit()
        log(f"  {apagados} contato(s) de teste apagado(s); status de {aluno} devolvido para {status_original}")

    log("\nRESULTADO: TODOS OS PASSOS PASSARAM")
    (AQUI / "logs").mkdir(exist_ok=True)
    (AQUI / "logs" / "verificacao_mvp.txt").write_text("\n".join(linhas_log), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"API indisponivel ({e}). Suba o MVP com iniciar.ps1 antes de verificar.")
        sys.exit(2)
