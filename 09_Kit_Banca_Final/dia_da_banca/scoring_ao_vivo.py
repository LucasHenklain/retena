# -*- coding: utf-8 -*-
"""
Scoring ao vivo para a banca: executa o job semanal de scoring dentro do Oracle (DBMS_SCHEDULER.RUN_JOB) e mostra
o resultado em linguagem clara — carimbo de hoje, faixas de risco, top 5, histórico do job e modelos OML.
Os dados do LMS vão até 26/08/2026 (export da IES parceira); o que roda hoje é o scoring in-database.

Uso: 2_Scoring_ao_vivo.cmd            roda o job (~25 s) e mostra
     python scoring_ao_vivo.py --sem-rodar   só mostra o estado atual
     --sem-pausa                       não espera Enter no fim (usado pelo preparar.ps1)
"""
import argparse, os, sys, time, io

ap = argparse.ArgumentParser()
ap.add_argument("--sem-rodar", action="store_true"); ap.add_argument("--sem-pausa", action="store_true")
args = ap.parse_args()
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = io.StringIO()

def out(s=""):
    print(s); SAIDA.write(s + "\n")
def linha(c="─"): out(c * 100)
def pausa():
    if not args.sem_pausa:
        try: input("\nEnter para fechar.")
        except EOFError: pass

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import oracledb
    c = oracledb.connect(user="STARTUP", password="Startup2026", dsn="localhost:1521/FREEPDB1")
except Exception as e:
    out(f"Não foi possível conectar ao Oracle local (localhost:1521/FREEPDB1): {e}")
    out("Plano B: 06_Oracle/evidencias (evidencias.html) e o último resultado em ultimo_scoring.txt.")
    pausa(); sys.exit(1)
cur = c.cursor()

linha("═")
out("  RETENA · scoring de risco de evasão IN-DATABASE · Oracle AI Database 26ai Free · Oracle Machine Learning")
linha("═")
try:
    cur.execute("select banner_full from v$version")
    out("  " + cur.fetchone()[0])
except Exception:
    try:
        cur.execute("select version_full from product_component_version where product like 'Oracle%'"); out("  Oracle Database " + cur.fetchone()[0])
    except Exception:
        pass
cur.execute("select to_char(systimestamp at time zone 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI:SS'), sessiontimezone from dual")
agora, tz = cur.fetchone(); out(f"  Agora (America/Sao_Paulo): {agora}   · relógio do banco em UTC")
out()

if not args.sem_rodar:
    out("▶ Executando o job semanal de scoring: DBMS_SCHEDULER.RUN_JOB('JOB_RETENA_SCORING_SEMANAL') → PRC_ATUALIZAR_RISCO")
    out("  (recalcula as features em SQL e re-pontua os 203 alunos com PREDICTION_PROBABILITY dos modelos OML; MERGE idempotente)")
    t0 = time.time()
    try:
        cur.execute("BEGIN DBMS_SCHEDULER.RUN_JOB('JOB_RETENA_SCORING_SEMANAL', use_current_session => TRUE); END;"); c.commit()
        out(f"  ✔ concluído em {time.time() - t0:.0f} s")
    except Exception as e:
        out(f"  ✖ falhou: {e}")
    out()

cur.execute("""select count(*), to_char(max(dt_corte), 'DD/MM/YYYY'),
                      to_char(from_tz(cast(max(dt_scoring) as timestamp), 'UTC') at time zone 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI:SS')
                 from risco_aluno_snapshot""")
n, corte, scoring = cur.fetchone()
out(f"  Alunos pontuados: {n}    · eventos do LMS até: {corte} (export da IES parceira)    · último scoring: {scoring}")
out()
out("  Faixas de risco (probabilidade de 21 dias sem acesso):")
cur.execute("""select faixa_risco, count(*), round(avg(prob_inativo_21d), 3)
                 from risco_aluno_snapshot group by faixa_risco
                order by case faixa_risco when 'Alto' then 1 when 'Médio' then 2 when 'Medio' then 2 else 3 end""")
for f, q, p in cur.fetchall():
    barra = "█" * int(q / 3)
    out(f"    {f:<6} {q:>4} alunos  prob. média {p:<6} {barra}")
out()
out("  Quem chamar primeiro (top 5 por probabilidade):")
cur.execute("""select nome, faixa_risco, round(prob_inativo_21d, 3), recencia_dias, nome_fase, substr(fatores_top3, 1, 70), substr(acao_sugerida, 1, 60)
                 from risco_aluno_snapshot order by prob_inativo_21d desc, recencia_dias desc fetch first 5 rows only""")
out(f"    {'Aluno':<12}{'Faixa':<7}{'Prob.':<7}{'Recência':<10}{'Fase':<14}Fatores")
for nome, faixa, prob, rec, fase, fat, acao in cur.fetchall():
    out(f"    {nome:<12}{faixa:<7}{prob:<7}{str(rec) + ' d':<10}{(fase or '')[:13]:<14}{fat or ''}")
out()
out("  Modelos treinados dentro do banco (DBMS_DATA_MINING):")
cur.execute("select model_name, algorithm, mining_function, to_char(creation_date, 'DD/MM/YYYY HH24:MI') from user_mining_models order by 1")
for m in cur.fetchall(): out(f"    {m[0]:<26}{m[1]:<26}{m[2]:<16}criado em {m[3]}")
out()
out("  Histórico do job (DBMS_SCHEDULER):")
cur.execute("""select status, to_char(from_tz(cast(actual_start_date as timestamp), 'UTC') at time zone 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI:SS'),
                      to_char(run_duration)
                 from user_scheduler_job_run_details where job_name = 'JOB_RETENA_SCORING_SEMANAL'
                order by actual_start_date desc fetch first 3 rows only""")
for st, ini, dur in cur.fetchall(): out(f"    {st:<10} início {ini}   duração {dur}")
cur.execute("select repeat_interval, enabled, state from user_scheduler_jobs where job_name = 'JOB_RETENA_SCORING_SEMANAL'")
r = cur.fetchone()
if r: out(f"    agendamento: {r[0]}  · habilitado: {r[1]}  · estado: {r[2]}")
linha("═")
out("  O dado do aluno não saiu do banco: features em SQL, treino e scoring com Oracle Machine Learning, exposição por SQL/JSON.")
linha("═")

with open(os.path.join(AQUI, "ultimo_scoring.txt"), "w", encoding="utf-8") as f:
    f.write(SAIDA.getvalue())
pausa()
