# -*- coding: utf-8 -*-
"""
Etapa 02 — Engenharia de features.

Produz três bases a partir de `outputs/eventos_normalizados.parquet`:

1. `base_treino_semanal.parquet` — grão aluno-semana. Para cada corte semanal t
   (domingos, 2026-02-01 → 2026-08-23) e cada aluno com ≥ 1 evento de atividade
   até t, calcula features usando SOMENTE eventos com data ≤ t e o rótulo
   `inativo_21d` = 1 se não há nenhum evento de atividade em (t, t+21 dias].
   Cortes cujo horizonte ultrapassa a última data da base (26/08/2026) não têm
   rótulo conhecido e são descartados da base de treino.
2. `base_scoring_atual.parquet` — o corte mais recente sem rótulo (23/08/2026),
   usado para o scoring "ao vivo".
3. `base_transicao_fases.parquet` — grão aluno-fase (fases 1..4) com features
   agregadas da fase k e rótulo `evadiu_proxima_fase` = 1 se o aluno não tem
   nenhum evento de atividade na fase k+1.

Também gera `outputs/dicionario_features.md`.

Decisões:
- "Evento" aqui significa evento de atividade do aluno (`is_atividade_aluno`),
  ou seja, ação do próprio aluno no LMS. Eventos administrativos (nota lançada
  pelo tutor, matrícula, cron) não contam como engajamento nem como "sinal de
  vida" no rótulo — caso contrário um aluno que nunca acessou apareceria ativo.
- `fase_atual` = fase mais avançada em que o aluno já teve evento até t.
- O corte t inclui o próprio domingo (eventos com data ≤ t).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    CAPITULOS_POR_FASE,
    DATA_REFERENCIA,
    DIR_OUTPUTS,
    HORIZONTE_ROTULO_DIAS,
    PRIMEIRO_CORTE,
    ULTIMO_CORTE,
    log,
)

ARQ_EVENTOS = DIR_OUTPUTS / "eventos_normalizados.parquet"
ARQ_TREINO = DIR_OUTPUTS / "base_treino_semanal.parquet"
ARQ_SCORING = DIR_OUTPUTS / "base_scoring_atual.parquet"
ARQ_TRANSICAO = DIR_OUTPUTS / "base_transicao_fases.parquet"
ARQ_DICIONARIO = DIR_OUTPUTS / "dicionario_features.md"

FEATURES_SEMANAIS = [
    "eventos_7d", "eventos_14d", "eventos_28d",
    "dias_ativos_7d", "dias_ativos_14d", "dias_ativos_28d",
    "recencia_dias", "progresso_28d", "capitulos_distintos_28d",
    "capitulo_max_fase_atual", "pct_capitulos_fase_atual",
    "quiz_iniciados_28d", "quiz_entregues_28d", "entregas_28d",
    "tendencia", "share_noite_28d", "share_fim_semana_28d",
    "semanas_ativas_ultimas_8", "eventos_acumulados", "dias_ativos_acumulados",
    "fase_atual", "semanas_desde_primeiro_evento",
]


# ---------------------------------------------------------------------------
# Base semanal
# ---------------------------------------------------------------------------
def _janela(ev: pd.DataFrame, t: pd.Timestamp, dias: int) -> pd.DataFrame:
    """Eventos com data em (t - dias, t]."""
    return ev[ev["data"] > t - pd.Timedelta(days=dias)]


def features_no_corte(ev_ate_t: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    """Calcula as features de todos os alunos para um corte t.

    `ev_ate_t` deve conter apenas eventos de atividade com data ≤ t.
    """
    g_all = ev_ate_t.groupby("aluno_id")
    base = pd.DataFrame({
        "eventos_acumulados": g_all.size(),
        "dias_ativos_acumulados": g_all["data"].nunique(),
        "primeiro_evento": g_all["data"].min(),
        "ultimo_evento": g_all["data"].max(),
        "fase_atual": g_all["fase_num"].max(),
    })
    base["recencia_dias"] = (t - base["ultimo_evento"]).dt.days
    base["semanas_desde_primeiro_evento"] = ((t - base["primeiro_evento"]).dt.days // 7)

    for dias in (7, 14, 28):
        j = _janela(ev_ate_t, t, dias)
        g = j.groupby("aluno_id")
        base[f"eventos_{dias}d"] = g.size()
        base[f"dias_ativos_{dias}d"] = g["data"].nunique()

    j28 = _janela(ev_ate_t, t, 28)
    g28 = j28.groupby("aluno_id")
    base["progresso_28d"] = g28["is_progresso"].sum()
    base["quiz_iniciados_28d"] = g28["is_quiz_inicio"].sum()
    base["quiz_entregues_28d"] = g28["is_quiz_entrega"].sum()
    base["entregas_28d"] = g28["is_entrega_tarefa"].sum()
    base["share_noite_28d"] = g28["noite"].mean()
    base["share_fim_semana_28d"] = g28["fim_de_semana"].mean()
    com_cap = j28[j28["capitulo"].notna()]
    base["capitulos_distintos_28d"] = (
        com_cap.groupby("aluno_id")[["fase_num", "capitulo"]]
        .apply(lambda d: d.drop_duplicates().shape[0])
        if len(com_cap) else pd.Series(dtype="float")
    )

    # Semanas ativas nas últimas 8 semanas (janelas de 7 dias terminando em t).
    j56 = _janela(ev_ate_t, t, 56).copy()
    j56["idx_semana"] = ((t - j56["data"]).dt.days // 7)
    base["semanas_ativas_ultimas_8"] = j56.groupby("aluno_id")["idx_semana"].nunique()

    # Capítulo máximo na fase atual (fase mais avançada até t).
    ev_cap = ev_ate_t[ev_ate_t["capitulo"].notna()]
    cap_max_fase = ev_cap.groupby(["aluno_id", "fase_num"])["capitulo"].max()
    idx = pd.MultiIndex.from_arrays([base.index, base["fase_atual"].values])
    base["capitulo_max_fase_atual"] = cap_max_fase.reindex(idx).values
    base["capitulo_max_fase_atual"] = base["capitulo_max_fase_atual"].astype("float").fillna(0)
    total_caps = base["fase_atual"].map(CAPITULOS_POR_FASE)
    base["pct_capitulos_fase_atual"] = base["capitulo_max_fase_atual"] / total_caps

    colunas_contagem = [c for c in base.columns if c.startswith(("eventos_", "dias_ativos_", "progresso_", "quiz_", "entregas_", "capitulos_distintos", "semanas_ativas"))]
    base[colunas_contagem] = base[colunas_contagem].fillna(0)
    base[["share_noite_28d", "share_fim_semana_28d"]] = base[["share_noite_28d", "share_fim_semana_28d"]].fillna(0)
    base["tendencia"] = base["eventos_7d"] / (base["eventos_28d"] / 4 + 1)
    base["recencia_dias"] = base["recencia_dias"].fillna(999)

    base = base.reset_index().rename(columns={"index": "aluno_id"})
    base.insert(0, "corte", t)
    return base


def gerar_base_semanal(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cortes = pd.date_range(PRIMEIRO_CORTE, ULTIMO_CORTE, freq="7D")
    assert all(c.dayofweek == 6 for c in cortes), "cortes devem ser domingos"
    ultimo_dia = ev["data"].max()
    log(f"{len(cortes)} cortes semanais de {cortes[0].date()} a {cortes[-1].date()}; último evento {ultimo_dia.date()}")

    partes_rotuladas, partes_scoring = [], []
    for t in cortes:
        ev_ate_t = ev[ev["data"] <= t]
        if ev_ate_t.empty:
            continue
        feats = features_no_corte(ev_ate_t, t)
        fim_janela = t + pd.Timedelta(days=HORIZONTE_ROTULO_DIAS)
        if fim_janela <= ultimo_dia:
            ativos_futuro = set(ev.loc[(ev["data"] > t) & (ev["data"] <= fim_janela), "aluno_id"])
            feats["inativo_21d"] = (~feats["aluno_id"].isin(ativos_futuro)).astype("int8")
            partes_rotuladas.append(feats)
        else:
            feats["inativo_21d"] = np.nan
            partes_scoring.append(feats)
        log(f"  corte {t.date()}: {len(feats):>4} alunos"
            + (f", positivos={feats['inativo_21d'].sum():.0f} ({feats['inativo_21d'].mean():.1%})" if fim_janela <= ultimo_dia else ", sem rótulo (scoring)"))

    treino = pd.concat(partes_rotuladas, ignore_index=True)
    scoring_todos = pd.concat(partes_scoring, ignore_index=True)
    scoring = scoring_todos[scoring_todos["corte"] == scoring_todos["corte"].max()].copy()
    return treino, scoring


# ---------------------------------------------------------------------------
# Base de transição de fases
# ---------------------------------------------------------------------------
def calendario_fases(ev: pd.DataFrame) -> dict[int, tuple[pd.Timestamp, pd.Timestamp]]:
    """Início/fim de cada fase estimados pela atividade dos alunos.

    Início = percentil 5 das datas de evento da fase (robusto a acessos
    antecipados); fim = início da fase seguinte (fases são sequenciais); para a
    última fase, fim = data de referência.
    """
    inicio = ev.groupby("fase_num")["data"].quantile(0.05).dt.normalize()
    cal = {}
    fases = sorted(inicio.index)
    for i, k in enumerate(fases):
        fim = inicio[fases[i + 1]] if i + 1 < len(fases) else DATA_REFERENCIA
        cal[int(k)] = (inicio[k], fim)
    return cal


def gerar_base_transicao(ev: pd.DataFrame) -> pd.DataFrame:
    cal = calendario_fases(ev)
    for k, (ini, fim) in cal.items():
        log(f"  Fase {k}: início≈{ini.date()} fim≈{fim.date()}")

    alunos_por_fase = {k: set(ev.loc[ev["fase_num"] == k, "aluno_id"]) for k in cal}
    linhas = []
    for k in range(1, 5):
        ini, fim = cal[k]
        # Features apenas com o que era conhecido até o fim da fase k.
        evk = ev[(ev["fase_num"] == k) & (ev["data"] <= fim)]
        if evk.empty:
            continue
        g = evk.groupby("aluno_id")
        f = pd.DataFrame({
            "eventos_fase": g.size(),
            "dias_ativos_fase": g["data"].nunique(),
            "primeiro_evento": g["data"].min(),
            "ultimo_evento": g["data"].max(),
            "capitulo_max": g["capitulo"].max().astype("float").fillna(0),
            "quiz_iniciados": g["is_quiz_inicio"].sum(),
            "quiz_entregues": g["is_quiz_entrega"].sum(),
            "entregas": g["is_entrega_tarefa"].sum(),
            "progresso": g["is_progresso"].sum(),
            "share_noite": g["noite"].mean(),
            "share_fim_semana": g["fim_de_semana"].mean(),
        })
        f["span_dias"] = (f["ultimo_evento"] - f["primeiro_evento"]).dt.days + 1
        f["pct_capitulos"] = f["capitulo_max"] / CAPITULOS_POR_FASE[k]
        f["recencia_fim_fase"] = (fim - f["ultimo_evento"]).dt.days
        f["atraso_inicio_dias"] = (f["primeiro_evento"] - ini).dt.days.clip(lower=0)
        # Tendência: eventos nas últimas 2 semanas da fase vs. média quinzenal anterior.
        ult2 = evk[evk["data"] > fim - pd.Timedelta(days=14)].groupby("aluno_id").size()
        ant = evk[evk["data"] <= fim - pd.Timedelta(days=14)].groupby("aluno_id").size()
        n_quinzenas_ant = max(((fim - ini).days - 14) / 14, 1)
        f["eventos_ultimas_2sem"] = ult2.reindex(f.index).fillna(0)
        f["tendencia_fase"] = f["eventos_ultimas_2sem"] / (ant.reindex(f.index).fillna(0) / n_quinzenas_ant + 1)
        f["fase"] = k
        f["evadiu_proxima_fase"] = (~f.index.isin(alunos_por_fase.get(k + 1, set()))).astype("int8")
        f = f.reset_index()
        linhas.append(f)
        log(f"  transição F{k}→F{k+1}: {len(f)} alunos, evadiram={f['evadiu_proxima_fase'].sum()} ({f['evadiu_proxima_fase'].mean():.1%})")
    base = pd.concat(linhas, ignore_index=True)
    cols = ["aluno_id", "fase", "eventos_fase", "dias_ativos_fase", "span_dias", "capitulo_max", "pct_capitulos",
            "quiz_iniciados", "quiz_entregues", "entregas", "progresso", "share_noite", "share_fim_semana",
            "recencia_fim_fase", "atraso_inicio_dias", "eventos_ultimas_2sem", "tendencia_fase",
            "primeiro_evento", "ultimo_evento", "evadiu_proxima_fase"]
    return base[cols]


# ---------------------------------------------------------------------------
# Dicionário de features
# ---------------------------------------------------------------------------
def escrever_dicionario(treino: pd.DataFrame, scoring: pd.DataFrame, transicao: pd.DataFrame) -> None:
    desc = {
        "corte": "Data do corte semanal t (domingo). Features usam apenas eventos com data ≤ t.",
        "aluno_id": "Identificador anonimizado do aluno (\"Aluno NNNN\").",
        "eventos_7d": "Nº de eventos de atividade do aluno em (t−7d, t].",
        "eventos_14d": "Nº de eventos de atividade em (t−14d, t].",
        "eventos_28d": "Nº de eventos de atividade em (t−28d, t].",
        "dias_ativos_7d": "Nº de dias distintos com atividade em (t−7d, t].",
        "dias_ativos_14d": "Nº de dias distintos com atividade em (t−14d, t].",
        "dias_ativos_28d": "Nº de dias distintos com atividade em (t−28d, t].",
        "recencia_dias": "Dias entre o último evento de atividade (≤ t) e t. 999 se nunca houve evento.",
        "progresso_28d": "Nº de eventos \"Progresso de conteúdo atualizado\" em 28 dias.",
        "capitulos_distintos_28d": "Nº de pares (fase, capítulo) distintos acessados em 28 dias.",
        "capitulo_max_fase_atual": "Maior capítulo acessado na fase atual (0 se nenhum evento com capítulo).",
        "pct_capitulos_fase_atual": "capitulo_max_fase_atual ÷ total de capítulos da fase (F1=10, F2=12, F3=10, F4=11, F5=8).",
        "quiz_iniciados_28d": "Nº de tentativas de questionário iniciadas em 28 dias.",
        "quiz_entregues_28d": "Nº de tentativas de questionário entregues em 28 dias.",
        "entregas_28d": "Nº de entregas de tarefa/atividade em 28 dias.",
        "tendencia": "eventos_7d ÷ (eventos_28d/4 + 1). ≈1 = ritmo estável; <0,5 = queda forte; >1 = aceleração.",
        "share_noite_28d": "Fração dos eventos de 28 dias ocorridos entre 19h e 23h.",
        "share_fim_semana_28d": "Fração dos eventos de 28 dias ocorridos em sábado/domingo.",
        "semanas_ativas_ultimas_8": "Nº de janelas semanais (entre as 8 anteriores a t) com ≥ 1 evento.",
        "eventos_acumulados": "Total de eventos de atividade do aluno até t.",
        "dias_ativos_acumulados": "Total de dias distintos com atividade até t.",
        "fase_atual": "Fase mais avançada (1–5) em que o aluno já teve evento até t.",
        "semanas_desde_primeiro_evento": "Semanas completas entre o primeiro evento do aluno e t.",
        "primeiro_evento": "Data do primeiro evento de atividade do aluno (auxiliar, não usada no modelo).",
        "ultimo_evento": "Data do último evento de atividade até t (auxiliar, não usada no modelo).",
        "inativo_21d": "RÓTULO: 1 se o aluno não tem nenhum evento de atividade em (t, t+21d]; NaN na base de scoring.",
    }
    desc_trans = {
        "aluno_id": "Identificador do aluno.",
        "fase": "Fase k (1–4) de origem da transição k → k+1.",
        "eventos_fase": "Nº de eventos de atividade na fase k até o fim estimado da fase.",
        "dias_ativos_fase": "Dias distintos com atividade na fase k.",
        "span_dias": "Dias entre primeiro e último evento na fase k (+1).",
        "capitulo_max": "Maior capítulo acessado na fase k.",
        "pct_capitulos": "capitulo_max ÷ total de capítulos da fase k.",
        "quiz_iniciados": "Tentativas de questionário iniciadas na fase k.",
        "quiz_entregues": "Tentativas de questionário entregues na fase k.",
        "entregas": "Entregas de tarefa na fase k.",
        "progresso": "Eventos de progresso de conteúdo na fase k.",
        "share_noite": "Fração de eventos entre 19h e 23h na fase k.",
        "share_fim_semana": "Fração de eventos em fim de semana na fase k.",
        "recencia_fim_fase": "Dias entre o último evento do aluno na fase k e o fim estimado da fase.",
        "atraso_inicio_dias": "Dias entre o início estimado da fase e o primeiro evento do aluno na fase.",
        "eventos_ultimas_2sem": "Eventos nas 2 últimas semanas da fase k.",
        "tendencia_fase": "eventos_ultimas_2sem ÷ (média quinzenal anterior + 1).",
        "primeiro_evento": "Data do primeiro evento na fase (auxiliar).",
        "ultimo_evento": "Data do último evento na fase (auxiliar).",
        "evadiu_proxima_fase": "RÓTULO: 1 se o aluno não tem nenhum evento de atividade na fase k+1.",
    }
    linhas = [
        "# Dicionário de features — MVP de risco de evasão",
        "",
        "Gerado automaticamente por `pipeline/02_features_semanais.py`.",
        "",
        "## Definições gerais",
        "",
        "- **Evento de atividade**: ação do próprio aluno no LMS (origem `web`, evento não administrativo). "
        "Eventos gerados por tutor/coordenação/rotinas (lançamento de nota, matrícula, cron) são excluídos "
        "de contagens de engajamento e do rótulo.",
        f"- **Cortes**: domingos de {PRIMEIRO_CORTE.date()} a {ULTIMO_CORTE.date()} (t inclui o domingo).",
        f"- **Horizonte do rótulo**: {HORIZONTE_ROTULO_DIAS} dias após o corte.",
        "- Apenas alunos com ≥ 1 evento de atividade até t entram no corte t.",
        "",
        "## Base aluno-semana (`base_treino_semanal.parquet` e `base_scoring_atual.parquet`)",
        "",
        f"- Treino rotulado: {len(treino):,} linhas, {treino['aluno_id'].nunique()} alunos, "
        f"{treino['corte'].nunique()} cortes ({treino['corte'].min().date()} → {treino['corte'].max().date()}), "
        f"taxa de positivos {treino['inativo_21d'].mean():.1%}.",
        f"- Scoring atual: {len(scoring):,} alunos no corte {scoring['corte'].max().date()} (sem rótulo).",
        "",
        "| Coluna | Descrição |",
        "|---|---|",
    ]
    for c in treino.columns:
        linhas.append(f"| `{c}` | {desc.get(c, '')} |")
    linhas += [
        "",
        "## Base de transição de fases (`base_transicao_fases.parquet`)",
        "",
        f"- {len(transicao):,} linhas aluno-fase; taxa de evasão entre fases {transicao['evadiu_proxima_fase'].mean():.1%}.",
        "- Início de cada fase estimado pelo percentil 5 das datas de evento; fim = início da fase seguinte.",
        "",
        "| Coluna | Descrição |",
        "|---|---|",
    ]
    for c in transicao.columns:
        linhas.append(f"| `{c}` | {desc_trans.get(c, '')} |")
    ARQ_DICIONARIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    log(f"Salvo {ARQ_DICIONARIO}")


def main() -> None:
    log(f"Lendo {ARQ_EVENTOS}")
    ev_todos = pd.read_parquet(ARQ_EVENTOS)
    ev = ev_todos[ev_todos["is_atividade_aluno"]].copy()
    log(f"Eventos de atividade do aluno: {len(ev):,} de {len(ev_todos):,} ({ev['aluno_id'].nunique()} alunos)")

    log("Gerando base aluno-semana...")
    treino, scoring = gerar_base_semanal(ev)
    colunas_ordem = ["corte", "aluno_id"] + FEATURES_SEMANAIS + ["primeiro_evento", "ultimo_evento", "inativo_21d"]
    treino = treino[colunas_ordem]
    scoring = scoring[colunas_ordem]
    treino.to_parquet(ARQ_TREINO, index=False)
    scoring.to_parquet(ARQ_SCORING, index=False)
    log(f"Salvo {ARQ_TREINO}: {len(treino):,} linhas, positivos={treino['inativo_21d'].mean():.1%}")
    log(f"Salvo {ARQ_SCORING}: {len(scoring):,} alunos no corte {scoring['corte'].max().date()}")

    log("Gerando base de transição de fases...")
    transicao = gerar_base_transicao(ev)
    transicao.to_parquet(ARQ_TRANSICAO, index=False)
    log(f"Salvo {ARQ_TRANSICAO}: {len(transicao):,} linhas")

    escrever_dicionario(treino, scoring, transicao)


if __name__ == "__main__":
    main()
