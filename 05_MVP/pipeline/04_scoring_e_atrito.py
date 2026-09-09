# -*- coding: utf-8 -*-
"""
Etapa 04 — Scoring "ao vivo", mapa de atrito de conteúdo e KPIs.

1. Aplica `model/modelo_risco_21d.joblib` à `base_scoring_atual.parquet`
   (corte 23/08/2026) e gera `outputs/risco_alunos_atual.csv` com
   probabilidade, faixa, 3 principais fatores textuais (regras sobre as
   features) e ação sugerida.
2. Mapa de atrito de conteúdo por fase × capítulo → `outputs/atrito_conteudo.csv`
   e recomendações automáticas por regra → `outputs/recomendacoes_conteudo.csv`.
3. KPIs agregados → `outputs/kpis.json`.

Definições do mapa de atrito:
- alunos_alcancaram: nº de alunos cujo capítulo máximo na fase é ≥ c.
- alunos_alcancaram_prox: idem para c+1.
- taxa_queda = 1 − alcançaram(c+1) / alcançaram(c)  (NaN no último capítulo).
- esforço = mediana de eventos por aluno no capítulo c (entre quem o acessou).
- esforço_relativo = esforço ÷ mediana dos esforços da fase (1 = capítulo típico).
- índice_atrito = taxa_queda × esforço_relativo (capítulo caro E onde se perde gente).
- A Fase 5 está em andamento: suas quedas refletem "ainda não chegou", não
  abandono; é sinalizada com `fase_em_andamento = True` e as recomendações
  usam linguagem de monitoramento.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    CAPITULOS_POR_FASE,
    DATA_REFERENCIA,
    DIR_MODEL,
    DIR_OUTPUTS,
    LIMIAR_ALTO,
    LIMIAR_MEDIO,
    NOMES_FASES,
    faixa_risco,
    log,
    salvar_json,
)

ARQ_EVENTOS = DIR_OUTPUTS / "eventos_normalizados.parquet"
ARQ_SCORING = DIR_OUTPUTS / "base_scoring_atual.parquet"
ARQ_MODELO = DIR_MODEL / "modelo_risco_21d.joblib"
ARQ_RISCO = DIR_OUTPUTS / "risco_alunos_atual.csv"
ARQ_ATRITO = DIR_OUTPUTS / "atrito_conteudo.csv"
ARQ_RECOMENDACOES = DIR_OUTPUTS / "recomendacoes_conteudo.csv"
ARQ_KPIS = DIR_OUTPUTS / "kpis.json"

FASE_EM_ANDAMENTO = 5

# Limiares das regras de recomendação de conteúdo. Nas fases concluídas a queda
# capítulo-a-capítulo é pequena (mediana ≈ 1,5 %), então "alta" = ~3× a mediana.
QUEDA_ALTA = 0.04       # ≥ 4 % dos alunos que chegaram ao capítulo não seguem para o próximo
QUEDA_MODERADA = 0.02
ESFORCO_ALTO = 1.4      # ≥ 40 % acima do capítulo típico da fase
ESFORCO_BAIXO = 0.6
PDF_ALTO = 0.20         # ≥ 20 % dos eventos de leitura em PDF
ONBOARDING_ALTO = 0.08  # ≥ 8 % dos alunos da fase nunca abriram o capítulo 1


# ---------------------------------------------------------------------------
# 1. Scoring e fatores textuais
# ---------------------------------------------------------------------------
def fatores_aluno(r: pd.Series) -> list[tuple[int, str]]:
    """Gera (prioridade, texto) para cada sinal de risco detectado nas features.

    Prioridade menor = mais grave. Retorna lista já ordenada.
    """
    f: list[tuple[int, str]] = []
    rec = int(r["recencia_dias"])
    e7, e14, e28 = int(r["eventos_7d"]), int(r["eventos_14d"]), int(r["eventos_28d"])
    fase = int(r["fase_atual"])
    cap = int(r["capitulo_max_fase_atual"])
    total = CAPITULOS_POR_FASE.get(fase, 0)

    if rec >= 60:
        f.append((0, f"{rec} dias sem acesso (inativo há mais de 2 meses)"))
    elif rec >= 28:
        f.append((0, f"{rec} dias sem acesso"))
    elif rec >= 14:
        f.append((1, f"{rec} dias sem acesso"))
    elif rec >= 7:
        f.append((2, f"{rec} dias sem acesso"))

    if e28 == 0:
        f.append((1, "nenhum acesso nos últimos 28 dias"))
    else:
        media_semanal = e28 / 4
        if media_semanal >= 3 and e7 < media_semanal:
            queda = 1 - e7 / media_semanal
            if queda >= 0.5:
                f.append((2, f"queda de {queda:.0%} nos acessos da semana vs. média do mês"))
            elif queda >= 0.3:
                f.append((3, f"queda de {queda:.0%} nos acessos da semana vs. média do mês"))
        if e14 == 0:
            f.append((2, "nenhum acesso nas últimas 2 semanas"))
        if int(r["dias_ativos_28d"]) <= 2:
            f.append((3, f"apenas {int(r['dias_ativos_28d'])} dia(s) ativo(s) no último mês"))

    if total and cap < total:
        if r["pct_capitulos_fase_atual"] < 0.5:
            f.append((2, f"parado no capítulo {cap} de {total} da Fase {fase}"))
        elif r["pct_capitulos_fase_atual"] < 0.8:
            f.append((4, f"no capítulo {cap} de {total} da Fase {fase}"))
    if total and cap == 0:
        f.append((2, f"nenhum capítulo acessado na Fase {fase}"))

    qi, qe = int(r["quiz_iniciados_28d"]), int(r["quiz_entregues_28d"])
    if qi > 0 and qe < qi:
        f.append((4, f"{qi - qe} questionário(s) iniciado(s) sem entrega"))
    if e28 > 0 and qi == 0 and qe == 0:
        f.append((5, "nenhum questionário no último mês"))

    sa = int(r["semanas_ativas_ultimas_8"])
    if sa <= 3:
        f.append((3, f"ativo em apenas {sa} das últimas 8 semanas"))
    elif sa <= 5:
        f.append((5, f"ativo em {sa} das últimas 8 semanas"))

    if int(r["progresso_28d"]) == 0 and e28 > 0:
        f.append((4, "acessou mas não avançou em nenhum conteúdo no mês"))

    f.sort(key=lambda x: x[0])
    return f


def situacao_aluno(rec: int) -> str:
    if rec <= 28:
        return "Ativo (28d)"
    if rec <= 60:
        return "Inativo 29–60d"
    return "Inativo >60d"


def acao_sugerida(faixa: str, fatores: list[str], r: pd.Series) -> str:
    rec = int(r["recencia_dias"])
    parado = next((t for t in fatores if t.startswith("parado no capítulo") or t.startswith("nenhum capítulo")), None)
    if faixa == "Alto":
        if rec > 60:
            return "Contato de resgate pela coordenação (telefone) e oferta de plano de retomada/trancamento assistido"
        if parado:
            return f"Contato do tutor em 48h + monitoria/microaula do capítulo em que parou ({parado})"
        return "Contato ativo do tutor em 48h (telefone/WhatsApp) com plano de retomada de 2 semanas"
    if faixa == "Médio":
        if parado:
            return "Mensagem personalizada de reengajamento com atalho para o capítulo atual e lembrete de prazo"
        if any("queda" in t for t in fatores):
            return "Nudge automático (e-mail/WhatsApp) com resumo do que falta na fase e convite para live de dúvidas"
        return "Mensagem automática de reengajamento + lembrete de prazo da fase"
    if any("questionário" in t for t in fatores):
        return "Acompanhamento padrão; lembrete de conclusão do questionário pendente"
    return "Acompanhamento padrão (sem ação imediata)"


def gerar_scoring() -> pd.DataFrame:
    pacote = joblib.load(ARQ_MODELO)
    modelo, features = pacote["modelo"], pacote["features"]
    base = pd.read_parquet(ARQ_SCORING)
    corte = pd.to_datetime(base["corte"].max())
    log(f"Scoring de {len(base)} alunos no corte {corte.date()} com {pacote['tipo']}")
    prob = modelo.predict_proba(base[features].values)[:, 1]
    base = base.copy()
    base["probabilidade"] = prob.round(4)
    base["faixa"] = [faixa_risco(p) for p in prob]

    fat_cols = {"fator_1": [], "fator_2": [], "fator_3": [], "fatores": [], "acao_sugerida": [], "situacao": []}
    for _, r in base.iterrows():
        fs = [t for _, t in fatores_aluno(r)]
        if not fs:
            fs = ["sem sinais de alerta: acesso regular e progressão em dia"]
        top3 = fs[:3] + [""] * (3 - len(fs[:3]))
        fat_cols["fator_1"].append(top3[0])
        fat_cols["fator_2"].append(top3[1])
        fat_cols["fator_3"].append(top3[2])
        fat_cols["fatores"].append(" | ".join(fs[:3]))
        fat_cols["acao_sugerida"].append(acao_sugerida(r["faixa"], fs, r))
        fat_cols["situacao"].append(situacao_aluno(int(r["recencia_dias"])))
    for k, v in fat_cols.items():
        base[k] = v

    colunas = [
        "aluno_id", "corte", "probabilidade", "faixa", "situacao", "fase_atual", "recencia_dias",
        "eventos_7d", "eventos_14d", "eventos_28d", "dias_ativos_7d", "dias_ativos_28d", "tendencia",
        "capitulo_max_fase_atual", "pct_capitulos_fase_atual", "progresso_28d", "capitulos_distintos_28d",
        "quiz_iniciados_28d", "quiz_entregues_28d", "entregas_28d", "semanas_ativas_ultimas_8",
        "share_noite_28d", "share_fim_semana_28d", "eventos_acumulados", "dias_ativos_acumulados",
        "semanas_desde_primeiro_evento", "primeiro_evento", "ultimo_evento",
        "fator_1", "fator_2", "fator_3", "fatores", "acao_sugerida",
    ]
    saida = base[colunas].sort_values(["probabilidade", "recencia_dias"], ascending=[False, False]).reset_index(drop=True)
    saida["corte"] = pd.to_datetime(saida["corte"]).dt.strftime("%Y-%m-%d")
    for c in ("primeiro_evento", "ultimo_evento"):
        saida[c] = pd.to_datetime(saida[c]).dt.strftime("%Y-%m-%d")
    saida["tendencia"] = saida["tendencia"].round(3)
    saida["pct_capitulos_fase_atual"] = saida["pct_capitulos_fase_atual"].round(3)
    saida[["share_noite_28d", "share_fim_semana_28d"]] = saida[["share_noite_28d", "share_fim_semana_28d"]].round(3)
    saida.to_csv(ARQ_RISCO, index=False, encoding="utf-8-sig")
    log(f"Salvo {ARQ_RISCO}: {saida['faixa'].value_counts().to_dict()}")
    return saida


# ---------------------------------------------------------------------------
# 2. Mapa de atrito de conteúdo
# ---------------------------------------------------------------------------
def gerar_atrito(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ev_cap = ev[ev["capitulo"].notna()].copy()
    ev_cap["capitulo"] = ev_cap["capitulo"].astype(int)
    alunos_fase = ev.groupby("fase_num")["aluno_id"].nunique()
    cap_max = ev_cap.groupby(["fase_num", "aluno_id"])["capitulo"].max().reset_index()
    linhas = []
    for fase, total in CAPITULOS_POR_FASE.items():
        cm_f = cap_max[cap_max["fase_num"] == fase]
        ev_f = ev_cap[ev_cap["fase_num"] == fase]
        n_fase = int(alunos_fase.get(fase, 0))
        for c in range(1, total + 1):
            alcancaram = int((cm_f["capitulo"] >= c).sum())
            alcancaram_prox = int((cm_f["capitulo"] >= c + 1).sum()) if c < total else np.nan
            ev_c = ev_f[ev_f["capitulo"] == c]
            por_aluno = ev_c.groupby("aluno_id").size()
            leitura = ev_c[ev_c["tipo_conteudo"].isin(["HTML", "PDF"])]
            n_leit = len(leitura)
            n_html = int((leitura["tipo_conteudo"] == "HTML").sum())
            titulo = ""
            ctx = ev_c.loc[ev_c["tipo_conteudo"].isin(["HTML", "PDF"]), "contexto"]
            if len(ctx):
                titulo = ctx.value_counts().index[0].split(":", 1)[-1].strip()
                titulo = titulo.replace("&amp;", "&")
            linhas.append({
                "fase": fase,
                "nome_fase": NOMES_FASES[fase],
                "capitulo": c,
                "titulo": titulo,
                "alunos_na_fase": n_fase,
                "alunos_alcancaram": alcancaram,
                "alunos_alcancaram_prox": alcancaram_prox,
                "alunos_perdidos": (alcancaram - alcancaram_prox) if c < total else np.nan,
                "taxa_queda": (1 - alcancaram_prox / alcancaram) if (c < total and alcancaram) else np.nan,
                "alunos_com_eventos": int(por_aluno.shape[0]),
                "eventos_total": int(len(ev_c)),
                "esforco_mediana_eventos": float(por_aluno.median()) if len(por_aluno) else 0.0,
                "quiz_entregues": int(ev_c["is_quiz_entrega"].sum()),
                "pct_html": (n_html / n_leit) if n_leit else np.nan,
                "pct_pdf": (1 - n_html / n_leit) if n_leit else np.nan,
                "fase_em_andamento": fase == FASE_EM_ANDAMENTO,
            })
    at = pd.DataFrame(linhas)
    med_fase = at.groupby("fase")["esforco_mediana_eventos"].transform("median").replace(0, np.nan)
    at["esforco_relativo"] = (at["esforco_mediana_eventos"] / med_fase).fillna(0).clip(upper=4)
    at["indice_atrito"] = (at["taxa_queda"].fillna(0) * at["esforco_relativo"]).round(4)
    at["taxa_queda"] = at["taxa_queda"].round(4)
    at["esforco_relativo"] = at["esforco_relativo"].round(3)
    at[["pct_html", "pct_pdf"]] = at[["pct_html", "pct_pdf"]].round(3)
    at = at.sort_values(["fase", "capitulo"]).reset_index(drop=True)
    at.to_csv(ARQ_ATRITO, index=False, encoding="utf-8-sig")
    log(f"Salvo {ARQ_ATRITO}: {len(at)} capítulos")

    # --- recomendações por regra ------------------------------------------------
    recs = []
    for _, r in at.iterrows():
        q = r["taxa_queda"] if pd.notna(r["taxa_queda"]) else 0.0
        e = r["esforco_relativo"]
        pdf = r["pct_pdf"] if pd.notna(r["pct_pdf"]) else 0.0
        ref = f"Fase {int(r['fase'])} · Cap {int(r['capitulo'])}"
        if r["fase_em_andamento"]:
            if r["capitulo"] <= 2 and r["alunos_alcancaram"] < r["alunos_na_fase"] * 0.9:
                recs.append((r, "Monitorar", 2,
                             f"Fase em andamento: {int(r['alunos_na_fase'] - r['alunos_alcancaram'])} alunos ainda não chegaram ao capítulo {int(r['capitulo'])}. Disparar lembrete de início e destacar o capítulo na home do curso."))
            elif q >= QUEDA_ALTA and e >= ESFORCO_ALTO:
                recs.append((r, "Monitorar", 2,
                             f"Capítulo em andamento com esforço alto ({e:.1f}× o típico) e {q:.0%} dos alunos ainda não avançaram: acompanhar semanalmente e preparar sessão de dúvidas."))
            continue
        # Onboarding da fase: alunos com evento na fase que nunca abriram o capítulo 1.
        if r["capitulo"] == 1 and r["alunos_na_fase"] > 0:
            nunca = int(r["alunos_na_fase"] - r["alunos_alcancaram"])
            if nunca / r["alunos_na_fase"] >= ONBOARDING_ALTO:
                recs.append((r, "Onboarding", 2,
                             f"{nunca} alunos ({nunca / r['alunos_na_fase']:.0%}) entraram na fase mas nunca abriram o capítulo 1: disparar trilha de boas-vindas, vídeo curto de abertura e lembrete no 3º dia sem acesso."))
        if q >= QUEDA_ALTA and e >= ESFORCO_ALTO:
            recs.append((r, "Reestruturar", 1,
                         f"Alto esforço ({e:.1f}× o típico da fase) e alta queda ({q:.1%}): dividir em microaulas de até 10 min, inserir quiz de checagem no meio do capítulo e oferecer exemplo resolvido."))
        elif q >= QUEDA_ALTA and e <= ESFORCO_BAIXO:
            recs.append((r, "Reengajar", 1,
                         f"Queda alta ({q:.1%}) com pouco esforço ({e:.1f}× o típico): alunos desistem antes de se envolver — revisar o gancho inicial, mostrar aplicação prática e disparar nudge para quem parou aqui."))
        elif q >= QUEDA_ALTA:
            recs.append((r, "Reforçar", 1,
                         f"Queda relevante ({q:.1%}, {int(r['alunos_perdidos'])} alunos): adicionar resumo executivo no início, checkpoint de dúvidas com tutor e lembrete automático 3 dias após o acesso."))
        elif q >= QUEDA_MODERADA and e >= ESFORCO_ALTO:
            recs.append((r, "Simplificar", 2,
                         f"Esforço alto ({e:.1f}× o típico) com queda moderada ({q:.1%}): conteúdo denso — publicar resumo/mapa mental e material de apoio em PDF."))
        elif q >= 0.025:
            recs.append((r, "Reforçar", 2,
                         f"Queda moderada ({q:.1%}, {int(r['alunos_perdidos'])} alunos): lembrete automático para quem parou aqui e checkpoint rápido de dúvidas."))
        elif e >= 1.8 and q < QUEDA_MODERADA:
            recs.append((r, "Apoiar", 3,
                         f"Alto esforço ({e:.1f}× o típico) sem queda: alunos persistem, mas gastam muito tempo — oferecer exercícios guiados e FAQ para reduzir retrabalho."))
        if pdf >= PDF_ALTO and r["alunos_com_eventos"] >= 20:
            recs.append((r, "Formato", 3,
                         f"{pdf:.0%} das leituras em PDF: demanda por material offline/impresso — garantir PDF atualizado, versão mobile e áudio-resumo."))
    rec_df = pd.DataFrame([{
        "fase": int(r["fase"]), "capitulo": int(r["capitulo"]), "titulo": r["titulo"],
        "tipo_acao": tipo, "prioridade": prio,
        "taxa_queda": r["taxa_queda"], "esforco_relativo": r["esforco_relativo"], "indice_atrito": r["indice_atrito"],
        "alunos_alcancaram": int(r["alunos_alcancaram"]),
        "alunos_perdidos": int(r["alunos_perdidos"]) if pd.notna(r["alunos_perdidos"]) else None,
        "recomendacao": texto,
    } for r, tipo, prio, texto in recs])
    rec_df = rec_df.sort_values(["prioridade", "indice_atrito"], ascending=[True, False]).reset_index(drop=True)
    rec_df.to_csv(ARQ_RECOMENDACOES, index=False, encoding="utf-8-sig")
    log(f"Salvo {ARQ_RECOMENDACOES}: {len(rec_df)} recomendações")
    return at, rec_df


# ---------------------------------------------------------------------------
# 3. KPIs
# ---------------------------------------------------------------------------
def gerar_kpis(ev_todos: pd.DataFrame, ev: pd.DataFrame, risco: pd.DataFrame, at: pd.DataFrame) -> dict:
    ref = DATA_REFERENCIA
    ultimo = ev.groupby("aluno_id")["data"].max()
    rec = (ref - ultimo).dt.days
    n_ativ = int(len(ultimo))

    ativos_por_fase = ev.groupby("fase_num")["aluno_id"].nunique()
    alunos_f1 = set(ev.loc[ev["fase_num"] == 1, "aluno_id"])
    funil = []
    for k in range(1, 6):
        alunos_k = set(ev.loc[ev["fase_num"] == k, "aluno_id"])
        funil.append({
            "fase": k,
            "nome": NOMES_FASES[k],
            "alunos_ativos": int(len(alunos_k)),
            "pct_dos_ingressantes_f1": round(len(alunos_k & alunos_f1) / max(len(alunos_f1), 1), 4),
            "em_andamento": k == FASE_EM_ANDAMENTO,
        })

    # Conclusão por fase: alcançou o último capítulo.
    concl = []
    for k, total in CAPITULOS_POR_FASE.items():
        linha = at[(at["fase"] == k) & (at["capitulo"] == total)].iloc[0]
        concl.append({
            "fase": k,
            "alunos_ativos": int(linha["alunos_na_fase"]),
            "alunos_ultimo_capitulo": int(linha["alunos_alcancaram"]),
            "taxa_conclusao": round(linha["alunos_alcancaram"] / max(linha["alunos_na_fase"], 1), 4),
            "em_andamento": k == FASE_EM_ANDAMENTO,
        })

    # Curva semanal de alunos ativos (semanas terminando no domingo).
    sem = ev.set_index("timestamp").resample("W-SUN")["aluno_id"].nunique()
    ev_sem = ev.set_index("timestamp").resample("W-SUN").size()
    curva = [{"semana_fim": d.strftime("%Y-%m-%d"), "alunos_ativos": int(v), "eventos": int(ev_sem.get(d, 0))} for d, v in sem.items()]

    fx = risco["faixa"].value_counts()
    n_score = len(risco)
    kpis = {
        "instituicao": "IES Demo",
        "data_referencia": ref.strftime("%Y-%m-%d"),
        "corte_scoring": str(risco["corte"].iloc[0]),
        "periodo_dados": [ev_todos["data"].min().strftime("%Y-%m-%d"), ev_todos["data"].max().strftime("%Y-%m-%d")],
        "eventos_total": int(len(ev_todos)),
        "eventos_atividade": int(len(ev)),
        "alunos_matriculados": int(ev_todos["aluno_id"].nunique()),
        "alunos_com_atividade": n_ativ,
        "alunos_ativos_7d": int((rec <= 7).sum()),
        "alunos_ativos_28d": int((rec <= 28).sum()),
        "alunos_inativos_14d": int((rec > 14).sum()),
        "alunos_inativos_30d": int((rec > 30).sum()),
        "alunos_inativos_60d": int((rec > 60).sum()),
        "pct_inativos_14d": round((rec > 14).mean(), 4),
        "recencia_mediana_dias": float(rec.median()),
        "risco": {
            "alunos_avaliados": int(n_score),
            "alto": int(fx.get("Alto", 0)),
            "medio": int(fx.get("Médio", 0)),
            "baixo": int(fx.get("Baixo", 0)),
            "pct_alto_risco": round(fx.get("Alto", 0) / n_score, 4),
            "pct_medio_risco": round(fx.get("Médio", 0) / n_score, 4),
            "alto_risco_ainda_ativos_28d": int(((risco["faixa"] == "Alto") & (risco["recencia_dias"] <= 28)).sum()),
            "probabilidade_media": round(float(risco["probabilidade"].mean()), 4),
            "limiares": {"alto": LIMIAR_ALTO, "medio": LIMIAR_MEDIO},
        },
        "funil_fases": funil,
        "conclusao_por_fase": concl,
        "curva_semanal_ativos": curva,
        "distribuicao_recencia": {
            "0-7": int((rec <= 7).sum()),
            "8-14": int(((rec > 7) & (rec <= 14)).sum()),
            "15-30": int(((rec > 14) & (rec <= 30)).sum()),
            "31-60": int(((rec > 30) & (rec <= 60)).sum()),
            ">60": int((rec > 60).sum()),
        },
        "atrito": {
            "capitulos_avaliados": int(len(at)),
            "top5_indice_atrito": (
                at[~at["fase_em_andamento"]].sort_values("indice_atrito", ascending=False).head(5)
                .assign(alunos_perdidos=lambda d: d["alunos_perdidos"].fillna(0).astype(int))[
                    ["fase", "capitulo", "titulo", "taxa_queda", "esforco_relativo", "indice_atrito", "alunos_perdidos"]
                ].to_dict(orient="records")
            ),
        },
    }
    salvar_json(kpis, ARQ_KPIS)
    log(f"Salvo {ARQ_KPIS}")
    return kpis


def main() -> None:
    risco = gerar_scoring()
    log(f"Lendo {ARQ_EVENTOS}")
    ev_todos = pd.read_parquet(ARQ_EVENTOS)
    ev = ev_todos[ev_todos["is_atividade_aluno"]].copy()
    at, _ = gerar_atrito(ev)
    kpis = gerar_kpis(ev_todos, ev, risco, at)
    log(f"KPIs: ativos 28d={kpis['alunos_ativos_28d']}, inativos >14d={kpis['alunos_inativos_14d']}, alto risco={kpis['risco']['alto']} ({kpis['risco']['pct_alto_risco']:.1%})")


if __name__ == "__main__":
    main()
