# -*- coding: utf-8 -*-
"""
Etapa 03 — Treinamento e avaliação dos modelos.

Modelo principal (risco de inatividade em 21 dias, grão aluno-semana):
- HistGradientBoostingClassifier (principal) e LogisticRegression com
  StandardScaler (baseline).
- Split TEMPORAL: treino = cortes < 2026-06-01; teste = cortes ≥ 2026-06-01.
  Para evitar que a janela de rótulo de linhas de treino invada o período de
  teste (sobreposição de 21 dias), os dois últimos cortes de treino
  (24/05 e 31/05) são descartados — "embargo".
- Hiperparâmetros do HGB escolhidos em validação temporal interna ao treino
  (últimos 4 cortes de treino como validação).
- Métricas no teste: AUC-ROC, AUC-PR, precisão/recall/F1 no limiar 0,5,
  precisão@top-20 %, matriz de confusão, curva de calibração (10 bins),
  Brier score, e o mesmo conjunto no subconjunto "acionável" (alunos com
  atividade nos últimos 28 dias).
- Importância por permutação (top 12) no teste.
- Faixas de risco: Alto ≥ 0,60; Médio 0,30–0,60; Baixo < 0,30.
- Retreino no conjunto completo rotulado → `model/modelo_risco_21d.joblib`.

Modelo secundário (transição de fases): LogisticRegression, validação
leave-one-phase-out (treina em 3 transições, testa na 4ª); AUC médio.

Saídas: `model/*.joblib`, `model/metadados.json`, `outputs/metricas.json`,
`outputs/RESULTADOS.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    DATA_SPLIT_TESTE,
    DIR_MODEL,
    DIR_OUTPUTS,
    HORIZONTE_ROTULO_DIAS,
    LIMIAR_ALTO,
    LIMIAR_MEDIO,
    faixa_risco,
    log,
    salvar_json,
)

ARQ_TREINO = DIR_OUTPUTS / "base_treino_semanal.parquet"
ARQ_TRANSICAO = DIR_OUTPUTS / "base_transicao_fases.parquet"
ARQ_MODELO = DIR_MODEL / "modelo_risco_21d.joblib"
ARQ_MODELO_TRANSICAO = DIR_MODEL / "modelo_transicao_fases.joblib"
ARQ_METADADOS = DIR_MODEL / "metadados.json"
ARQ_METRICAS = DIR_OUTPUTS / "metricas.json"
ARQ_RESULTADOS = DIR_OUTPUTS / "RESULTADOS.md"

SEED = 42

FEATURES = [
    "eventos_7d", "eventos_14d", "eventos_28d",
    "dias_ativos_7d", "dias_ativos_14d", "dias_ativos_28d",
    "recencia_dias", "progresso_28d", "capitulos_distintos_28d",
    "capitulo_max_fase_atual", "pct_capitulos_fase_atual",
    "quiz_iniciados_28d", "quiz_entregues_28d", "entregas_28d",
    "tendencia", "share_noite_28d", "share_fim_semana_28d",
    "semanas_ativas_ultimas_8", "eventos_acumulados", "dias_ativos_acumulados",
    "fase_atual", "semanas_desde_primeiro_evento",
]
ROTULO = "inativo_21d"

FEATURES_TRANSICAO = [
    "eventos_fase", "dias_ativos_fase", "span_dias", "capitulo_max", "pct_capitulos",
    "quiz_iniciados", "quiz_entregues", "entregas", "progresso", "share_noite",
    "share_fim_semana", "recencia_fim_fase", "atraso_inicio_dias", "eventos_ultimas_2sem",
    "tendencia_fase",
]
ROTULO_TRANSICAO = "evadiu_proxima_fase"

# Grade pequena de hiperparâmetros do HGB (dados pequenos → modelos rasos e regularizados).
GRADE_HGB = [
    dict(learning_rate=0.05, max_iter=200, max_leaf_nodes=15, min_samples_leaf=25, l2_regularization=1.0),
    dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=8, min_samples_leaf=40, l2_regularization=2.0),
    dict(learning_rate=0.03, max_iter=400, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=0.5),
    dict(learning_rate=0.1, max_iter=150, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1.0),
]


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def precisao_top_k(y: np.ndarray, p: np.ndarray, frac: float = 0.20) -> dict:
    n = len(y)
    k = max(int(np.ceil(n * frac)), 1)
    ordem = np.argsort(-p)
    top = ordem[:k]
    return {
        "frac": frac,
        "k": int(k),
        "precisao": float(y[top].mean()),
        "recall_capturado": float(y[top].sum() / max(y.sum(), 1)),
        "lift": float(y[top].mean() / max(y.mean(), 1e-9)),
    }


def avaliar(y: np.ndarray, p: np.ndarray, limiar: float = 0.5, n_bins: int = 10) -> dict:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    yhat = (p >= limiar).astype(int)
    cm = confusion_matrix(y, yhat, labels=[0, 1])
    fpr, tpr, _ = roc_curve(y, p)
    prec_c, rec_c, _ = precision_recall_curve(y, p)
    # Calibração: bins uniformes; guardamos também contagem por bin.
    frac_pos, media_pred = calibration_curve(y, p, n_bins=n_bins, strategy="uniform")
    bins = np.linspace(0, 1, n_bins + 1)
    idx_bin = np.clip(np.digitize(p, bins[1:-1]), 0, n_bins - 1)
    contagem_bins = np.bincount(idx_bin, minlength=n_bins)
    calib = []
    for b in range(n_bins):
        m = idx_bin == b
        if m.sum() == 0:
            continue
        calib.append({
            "bin": f"{bins[b]:.1f}–{bins[b + 1]:.1f}",
            "n": int(m.sum()),
            "prob_media_prevista": float(p[m].mean()),
            "taxa_observada": float(y[m].mean()),
        })

    def _amostrar(a, b, n=60):
        if len(a) <= n:
            return [list(map(float, a)), list(map(float, b))]
        ix = np.linspace(0, len(a) - 1, n).round().astype(int)
        return [list(map(float, np.asarray(a)[ix])), list(map(float, np.asarray(b)[ix]))]

    faixas = pd.Series([faixa_risco(v) for v in p])
    por_faixa = {}
    for f in ["Alto", "Médio", "Baixo"]:
        m = (faixas == f).values
        por_faixa[f] = {
            "n": int(m.sum()),
            "share": float(m.mean()),
            "taxa_observada": float(y[m].mean()) if m.sum() else None,
        }
    return {
        "n": int(len(y)),
        "positivos": int(y.sum()),
        "taxa_positivos": float(y.mean()),
        "auc_roc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
        "auc_pr": float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else None,
        "brier": float(brier_score_loss(y, p)),
        "limiar": limiar,
        "precisao": float(precision_score(y, yhat, zero_division=0)),
        "recall": float(recall_score(y, yhat, zero_division=0)),
        "f1": float(f1_score(y, yhat, zero_division=0)),
        "matriz_confusao": {"vn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "vp": int(cm[1, 1])},
        "top20": precisao_top_k(y, p, 0.20),
        "calibracao": calib,
        "curva_roc": dict(zip(["fpr", "tpr"], _amostrar(fpr, tpr))),
        "curva_pr": dict(zip(["recall", "precisao"], _amostrar(rec_c, prec_c))),
        "por_faixa": por_faixa,
    }


def novo_hgb(params: dict) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(random_state=SEED, early_stopping=False, **params)


def novo_lr() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=5000, C=1.0, random_state=SEED)),
    ])


# ---------------------------------------------------------------------------
# Modelo principal
# ---------------------------------------------------------------------------
def treinar_modelo_principal(base: pd.DataFrame) -> dict:
    base = base.copy()
    base["corte"] = pd.to_datetime(base["corte"])
    cortes = sorted(base["corte"].unique())
    cortes_teste = [c for c in cortes if c >= DATA_SPLIT_TESTE]
    primeiro_teste = min(cortes_teste)
    limite_embargo = primeiro_teste - pd.Timedelta(days=HORIZONTE_ROTULO_DIAS)
    cortes_treino = [c for c in cortes if c < DATA_SPLIT_TESTE and c <= limite_embargo]
    cortes_embargo = [c for c in cortes if c < DATA_SPLIT_TESTE and c > limite_embargo]

    tr = base[base["corte"].isin(cortes_treino)]
    te = base[base["corte"].isin(cortes_teste)]
    Xtr, ytr = tr[FEATURES].values, tr[ROTULO].astype(int).values
    Xte, yte = te[FEATURES].values, te[ROTULO].astype(int).values
    log(f"Treino: {len(tr):,} linhas / {len(cortes_treino)} cortes ({pd.Timestamp(cortes_treino[0]).date()} → {pd.Timestamp(cortes_treino[-1]).date()}), positivos {ytr.mean():.1%}")
    log(f"Embargo (descartados): {[pd.Timestamp(c).strftime('%Y-%m-%d') for c in cortes_embargo]}")
    log(f"Teste : {len(te):,} linhas / {len(cortes_teste)} cortes ({pd.Timestamp(cortes_teste[0]).date()} → {pd.Timestamp(cortes_teste[-1]).date()}), positivos {yte.mean():.1%}")

    # --- seleção de hiperparâmetros em validação temporal interna --------------
    cortes_val = cortes_treino[-4:]
    tr_in = tr[~tr["corte"].isin(cortes_val)]
    va_in = tr[tr["corte"].isin(cortes_val)]
    resultados_grade = []
    for params in GRADE_HGB:
        m = novo_hgb(params).fit(tr_in[FEATURES].values, tr_in[ROTULO].astype(int).values)
        pv = m.predict_proba(va_in[FEATURES].values)[:, 1]
        yv = va_in[ROTULO].astype(int).values
        resultados_grade.append({
            "params": params,
            "auc_pr_val": float(average_precision_score(yv, pv)),
            "auc_roc_val": float(roc_auc_score(yv, pv)),
        })
        log(f"  HGB {params}: AUC-PR val={resultados_grade[-1]['auc_pr_val']:.3f} AUC-ROC val={resultados_grade[-1]['auc_roc_val']:.3f}")
    melhor = max(resultados_grade, key=lambda r: r["auc_pr_val"])
    params_hgb = melhor["params"]
    log(f"Hiperparâmetros escolhidos: {params_hgb}")

    # --- treino no período de treino e avaliação no teste ----------------------
    hgb = novo_hgb(params_hgb).fit(Xtr, ytr)
    lr = novo_lr().fit(Xtr, ytr)
    p_hgb = hgb.predict_proba(Xte)[:, 1]
    p_lr = lr.predict_proba(Xte)[:, 1]

    met_hgb = avaliar(yte, p_hgb)
    met_lr = avaliar(yte, p_lr)
    log(f"HGB  teste: AUC-ROC={met_hgb['auc_roc']:.3f} AUC-PR={met_hgb['auc_pr']:.3f} F1@0.5={met_hgb['f1']:.3f} P@top20={met_hgb['top20']['precisao']:.3f}")
    log(f"LR   teste: AUC-ROC={met_lr['auc_roc']:.3f} AUC-PR={met_lr['auc_pr']:.3f} F1@0.5={met_lr['f1']:.3f} P@top20={met_lr['top20']['precisao']:.3f}")

    # Subconjunto acionável: alunos que ainda tinham atividade no último mês.
    m_acion = (te["eventos_28d"] > 0).values
    met_hgb_acion = avaliar(yte[m_acion], p_hgb[m_acion])
    met_lr_acion = avaliar(yte[m_acion], p_lr[m_acion])
    log(f"HGB  teste (acionável, n={m_acion.sum()}): AUC-ROC={met_hgb_acion['auc_roc']:.3f} AUC-PR={met_hgb_acion['auc_pr']:.3f} P@top20={met_hgb_acion['top20']['precisao']:.3f}")
    log(f"LR   teste (acionável): AUC-ROC={met_lr_acion['auc_roc']:.3f} AUC-PR={met_lr_acion['auc_pr']:.3f}")

    # Métricas por corte de teste (estabilidade temporal).
    por_corte = []
    for c in cortes_teste:
        m = (te["corte"] == c).values
        if len(np.unique(yte[m])) < 2:
            continue
        por_corte.append({
            "corte": pd.Timestamp(c).strftime("%Y-%m-%d"),
            "n": int(m.sum()),
            "taxa_positivos": float(yte[m].mean()),
            "auc_roc_hgb": float(roc_auc_score(yte[m], p_hgb[m])),
            "auc_pr_hgb": float(average_precision_score(yte[m], p_hgb[m])),
            "auc_roc_lr": float(roc_auc_score(yte[m], p_lr[m])),
        })

    # --- importância por permutação (teste) --------------------------------------
    log("Calculando importância por permutação...")
    pi = permutation_importance(hgb, Xte, yte, scoring="roc_auc", n_repeats=15, random_state=SEED, n_jobs=1)
    imp = (
        pd.DataFrame({"feature": FEATURES, "importancia_media": pi.importances_mean, "importancia_dp": pi.importances_std})
        .sort_values("importancia_media", ascending=False)
        .reset_index(drop=True)
    )
    top12 = imp.head(12).to_dict(orient="records")
    for r in top12:
        log(f"  {r['feature']:<32} {r['importancia_media']:.4f} ± {r['importancia_dp']:.4f}")

    # Coeficientes padronizados da regressão (interpretação do baseline).
    coefs = pd.DataFrame({"feature": FEATURES, "coef_padronizado": lr.named_steps["lr"].coef_[0]}).sort_values("coef_padronizado", key=np.abs, ascending=False)

    # --- retreino no conjunto completo rotulado ------------------------------------
    X_all, y_all = base[FEATURES].values, base[ROTULO].astype(int).values
    hgb_final = novo_hgb(params_hgb).fit(X_all, y_all)
    lr_final = novo_lr().fit(X_all, y_all)
    joblib.dump({"modelo": hgb_final, "features": FEATURES, "tipo": "HistGradientBoostingClassifier", "baseline": lr_final}, ARQ_MODELO)
    log(f"Salvo {ARQ_MODELO} (retreinado em {len(base):,} linhas)")

    return {
        "features": FEATURES,
        "rotulo": ROTULO,
        "horizonte_dias": HORIZONTE_ROTULO_DIAS,
        "split": {
            "criterio": f"treino: cortes < {DATA_SPLIT_TESTE.date()} (com embargo de {HORIZONTE_ROTULO_DIAS} dias); teste: cortes ≥ {DATA_SPLIT_TESTE.date()}",
            "cortes_treino": [pd.Timestamp(c).strftime("%Y-%m-%d") for c in cortes_treino],
            "cortes_embargo": [pd.Timestamp(c).strftime("%Y-%m-%d") for c in cortes_embargo],
            "cortes_teste": [pd.Timestamp(c).strftime("%Y-%m-%d") for c in cortes_teste],
            "n_treino": int(len(tr)), "n_teste": int(len(te)),
            "alunos_treino": int(tr["aluno_id"].nunique()), "alunos_teste": int(te["aluno_id"].nunique()),
            "taxa_positivos_treino": float(ytr.mean()), "taxa_positivos_teste": float(yte.mean()),
            "n_total_rotulado": int(len(base)), "taxa_positivos_total": float(y_all.mean()),
            "alunos_total": int(base["aluno_id"].nunique()),
        },
        "hiperparametros_hgb": params_hgb,
        "grade_hgb": resultados_grade,
        "hgb": met_hgb,
        "logistica": met_lr,
        "hgb_acionavel": met_hgb_acion,
        "logistica_acionavel": met_lr_acion,
        "por_corte_teste": por_corte,
        "importancia_permutacao_top12": top12,
        "importancia_permutacao_completa": imp.to_dict(orient="records"),
        "coeficientes_logistica": coefs.to_dict(orient="records"),
        "faixas": {"alto_min": LIMIAR_ALTO, "medio_min": LIMIAR_MEDIO},
    }


# ---------------------------------------------------------------------------
# Modelo secundário — transição de fases
# ---------------------------------------------------------------------------
def treinar_modelo_transicao(base: pd.DataFrame) -> dict:
    fases = sorted(base["fase"].unique())
    folds = []
    for f_teste in fases:
        tr = base[base["fase"] != f_teste]
        te = base[base["fase"] == f_teste]
        if te[ROTULO_TRANSICAO].nunique() < 2:
            continue
        m = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression(max_iter=5000, C=0.5, class_weight="balanced", random_state=SEED))])
        m.fit(tr[FEATURES_TRANSICAO].values, tr[ROTULO_TRANSICAO].astype(int).values)
        p = m.predict_proba(te[FEATURES_TRANSICAO].values)[:, 1]
        y = te[ROTULO_TRANSICAO].astype(int).values
        folds.append({
            "fase_teste": int(f_teste),
            "transicao": f"F{int(f_teste)}→F{int(f_teste) + 1}",
            "n": int(len(te)),
            "positivos": int(y.sum()),
            "auc_roc": float(roc_auc_score(y, p)),
            "auc_pr": float(average_precision_score(y, p)),
            "top20": precisao_top_k(y, p, 0.20),
        })
        log(f"  LOPO teste F{f_teste}→F{f_teste + 1}: n={len(te)} pos={y.sum()} AUC-ROC={folds[-1]['auc_roc']:.3f} AUC-PR={folds[-1]['auc_pr']:.3f}")
    auc_medio = float(np.mean([f["auc_roc"] for f in folds]))
    auc_pr_medio = float(np.mean([f["auc_pr"] for f in folds]))
    log(f"Transição de fases — AUC-ROC médio={auc_medio:.3f}, AUC-PR médio={auc_pr_medio:.3f}")

    final = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression(max_iter=5000, C=0.5, class_weight="balanced", random_state=SEED))])
    final.fit(base[FEATURES_TRANSICAO].values, base[ROTULO_TRANSICAO].astype(int).values)
    coefs = pd.DataFrame({"feature": FEATURES_TRANSICAO, "coef_padronizado": final.named_steps["lr"].coef_[0]}).sort_values("coef_padronizado", key=np.abs, ascending=False)
    joblib.dump({"modelo": final, "features": FEATURES_TRANSICAO, "tipo": "LogisticRegression"}, ARQ_MODELO_TRANSICAO)
    log(f"Salvo {ARQ_MODELO_TRANSICAO}")
    return {
        "features": FEATURES_TRANSICAO,
        "rotulo": ROTULO_TRANSICAO,
        "n": int(len(base)),
        "alunos": int(base["aluno_id"].nunique()),
        "taxa_positivos": float(base[ROTULO_TRANSICAO].mean()),
        "por_fase": base.groupby("fase")[ROTULO_TRANSICAO].agg(n="size", positivos="sum", taxa="mean").reset_index().to_dict(orient="records"),
        "validacao": "leave-one-phase-out (treina em 3 transições, testa na 4ª)",
        "folds": folds,
        "auc_roc_medio": auc_medio,
        "auc_pr_medio": auc_pr_medio,
        "coeficientes": coefs.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def _pct(x) -> str:
    return "n/d" if x is None else f"{100 * x:.1f}%"


def _f(x, nd=3) -> str:
    return "n/d" if x is None else f"{x:.{nd}f}"


def escrever_resultados(m: dict, t: dict) -> None:
    s = m["split"]
    h, l, ha, la = m["hgb"], m["logistica"], m["hgb_acionavel"], m["logistica_acionavel"]
    cm = h["matriz_confusao"]
    L = []
    L += [
        "# Resultados do MVP — risco de evasão (IES Demo)",
        "",
        "Gerado automaticamente por `pipeline/03_treinar_modelo.py`. Todos os números vêm do pipeline; nada foi ajustado à mão.",
        "",
        "## 1. Problema e dados",
        "",
        "- **Objetivo principal**: prever, a cada domingo (corte t), se o aluno ficará **21 dias sem nenhuma ação no LMS** (`inativo_21d`).",
        "- **Fonte**: logs do LMS de um único curso em 5 fases sequenciais (15/01/2026 → 26/08/2026), 684.723 eventos brutos, 203 alunos matriculados, "
        "196 com alguma ação própria na plataforma (7 só têm eventos administrativos — matrícula/nota — e nunca acessaram).",
        "- **Evento de atividade**: ação do próprio aluno (origem `web`, evento não administrativo). Lançamentos de nota, matrículas e rotinas automáticas não contam como engajamento nem como \"sinal de vida\" para o rótulo.",
        f"- **Base aluno-semana rotulada**: {s['n_total_rotulado']:,} linhas, {s['alunos_total']} alunos, taxa global de positivos {_pct(s['taxa_positivos_total'])}.",
        "",
        "## 2. Protocolo de avaliação",
        "",
        f"- Split **temporal**: {s['criterio']}.",
        f"- Treino: {s['n_treino']:,} linhas, {len(s['cortes_treino'])} cortes ({s['cortes_treino'][0]} → {s['cortes_treino'][-1]}), {s['alunos_treino']} alunos, positivos {_pct(s['taxa_positivos_treino'])}.",
        f"- Cortes descartados por embargo (janela de rótulo invadiria o teste): {', '.join(s['cortes_embargo']) or 'nenhum'}.",
        f"- Teste: {s['n_teste']:,} linhas, {len(s['cortes_teste'])} cortes ({s['cortes_teste'][0]} → {s['cortes_teste'][-1]}), {s['alunos_teste']} alunos, positivos {_pct(s['taxa_positivos_teste'])}.",
        "- Hiperparâmetros do HGB escolhidos por validação temporal interna ao treino (últimos 4 cortes de treino), critério AUC-PR: "
        f"`{m['hiperparametros_hgb']}`.",
        "- Depois da avaliação, o modelo foi **retreinado no conjunto completo rotulado** e é esse o artefato usado no scoring.",
        "",
        "## 3. Modelo principal — métricas no teste (jun–ago/2026)",
        "",
        "| Métrica | HistGradientBoosting | Regressão Logística (baseline) |",
        "|---|---|---|",
        f"| AUC-ROC | **{_f(h['auc_roc'])}** | {_f(l['auc_roc'])} |",
        f"| AUC-PR (average precision) | **{_f(h['auc_pr'])}** | {_f(l['auc_pr'])} |",
        f"| Taxa de positivos (referência da AUC-PR) | {_pct(h['taxa_positivos'])} | {_pct(l['taxa_positivos'])} |",
        f"| Brier score (menor é melhor) | {_f(h['brier'])} | {_f(l['brier'])} |",
        f"| Precisão @ limiar 0,5 | {_f(h['precisao'])} | {_f(l['precisao'])} |",
        f"| Recall @ limiar 0,5 | {_f(h['recall'])} | {_f(l['recall'])} |",
        f"| F1 @ limiar 0,5 | {_f(h['f1'])} | {_f(l['f1'])} |",
        f"| Precisão @ top-20% de risco (k={h['top20']['k']}) | **{_f(h['top20']['precisao'])}** | {_f(l['top20']['precisao'])} |",
        f"| Recall capturado no top-20% | {_f(h['top20']['recall_capturado'])} | {_f(l['top20']['recall_capturado'])} |",
        f"| Lift no top-20% vs. base | {_f(h['top20']['lift'], 2)}× | {_f(l['top20']['lift'], 2)}× |",
        "",
        f"**Matriz de confusão (HGB, limiar 0,5)** — VN={cm['vn']}, FP={cm['fp']}, FN={cm['fn']}, VP={cm['vp']} (n={h['n']}).",
        "",
        "### 3.1 Subconjunto acionável (alunos com ≥ 1 evento nos 28 dias anteriores ao corte)",
        "",
        "Parte dos positivos é trivial: alunos já sumidos há semanas continuam sumidos. O subconjunto abaixo exclui esses casos e mede o que interessa à operação — antecipar o desligamento de quem ainda está presente.",
        "",
        "| Métrica | HGB | Logística |",
        "|---|---|---|",
        f"| n / positivos | {ha['n']} / {ha['positivos']} ({_pct(ha['taxa_positivos'])}) | idem |",
        f"| AUC-ROC | **{_f(ha['auc_roc'])}** | {_f(la['auc_roc'])} |",
        f"| AUC-PR | **{_f(ha['auc_pr'])}** | {_f(la['auc_pr'])} |",
        f"| Precisão @ top-20% (k={ha['top20']['k']}) | {_f(ha['top20']['precisao'])} | {_f(la['top20']['precisao'])} |",
        f"| Lift no top-20% | {_f(ha['top20']['lift'], 2)}× | {_f(la['top20']['lift'], 2)}× |",
        f"| Recall @ 0,5 | {_f(ha['recall'])} | {_f(la['recall'])} |",
        f"| Precisão @ 0,5 | {_f(ha['precisao'])} | {_f(la['precisao'])} |",
        "",
        "### 3.2 Estabilidade por corte de teste (HGB)",
        "",
        "| Corte | n | Positivos | AUC-ROC | AUC-PR |",
        "|---|---|---|---|---|",
    ]
    for r in m["por_corte_teste"]:
        L.append(f"| {r['corte']} | {r['n']} | {_pct(r['taxa_positivos'])} | {_f(r['auc_roc_hgb'])} | {_f(r['auc_pr_hgb'])} |")
    L += [
        "",
        "### 3.3 Calibração (HGB, teste, bins uniformes de 0,1)",
        "",
        "| Bin de probabilidade | n | Prob. média prevista | Taxa observada |",
        "|---|---|---|---|",
    ]
    for c in h["calibracao"]:
        L.append(f"| {c['bin']} | {c['n']} | {_f(c['prob_media_prevista'])} | {_pct(c['taxa_observada'])} |")
    L += [
        "",
        "### 3.4 Faixas de risco",
        "",
        f"Faixas adotadas: **Alto** ≥ {LIMIAR_ALTO:.2f}, **Médio** {LIMIAR_MEDIO:.2f}–{LIMIAR_ALTO:.2f}, **Baixo** < {LIMIAR_MEDIO:.2f}. "
        "Justificativa: 0,60 significa \"mais provável ficar inativo do que não\", com margem para erro de calibração — é o ponto em que compensa uma ação humana (contato do tutor). "
        f"0,30 é cerca de 1,5–2× a taxa média de positivos ({_pct(s['taxa_positivos_total'])}), suficiente para acionar uma intervenção automática barata (mensagem). A tabela mostra a taxa observada em cada faixa no teste:",
        "",
        "| Faixa | n | % das linhas | Taxa observada de inatividade |",
        "|---|---|---|---|",
    ]
    for f_ in ["Alto", "Médio", "Baixo"]:
        r = h["por_faixa"][f_]
        L.append(f"| {f_} | {r['n']} | {_pct(r['share'])} | {_pct(r['taxa_observada'])} |")
    L += [
        "",
        "### 3.5 Importância por permutação (HGB, teste, métrica AUC-ROC, 15 repetições) — top 12",
        "",
        "| # | Feature | Queda média de AUC | DP |",
        "|---|---|---|---|",
    ]
    for i, r in enumerate(m["importancia_permutacao_top12"], 1):
        L.append(f"| {i} | `{r['feature']}` | {_f(r['importancia_media'], 4)} | {_f(r['importancia_dp'], 4)} |")
    L += [
        "",
        "Coeficientes padronizados da regressão logística (sinal positivo = aumenta o risco), 8 maiores em módulo: "
        + "; ".join(f"`{r['feature']}` {r['coef_padronizado']:+.2f}" for r in m["coeficientes_logistica"][:8]) + ".",
        "",
        "## 4. Modelo secundário — evasão entre fases",
        "",
        f"- Grão aluno-fase (fases 1–4): {t['n']} linhas, {t['alunos']} alunos, taxa de evasão para a fase seguinte {_pct(t['taxa_positivos'])}.",
        "- Modelo: regressão logística (StandardScaler, `class_weight='balanced'`), validação **leave-one-phase-out** (treina em 3 transições, testa na 4ª).",
        "",
        "| Transição testada | n | Evadiram | AUC-ROC | AUC-PR | Precisão @ top-20% |",
        "|---|---|---|---|---|---|",
    ]
    for f_ in t["folds"]:
        L.append(f"| {f_['transicao']} | {f_['n']} | {f_['positivos']} | {_f(f_['auc_roc'])} | {_f(f_['auc_pr'])} | {_f(f_['top20']['precisao'])} |")
    L += [
        f"| **Média** | | | **{_f(t['auc_roc_medio'])}** | **{_f(t['auc_pr_medio'])}** | |",
        "",
        "Coeficientes padronizados (sinal positivo = aumenta a chance de não iniciar a fase seguinte), 6 maiores em módulo: "
        + "; ".join(f"`{r['feature']}` {r['coef_padronizado']:+.2f}" for r in t["coeficientes"][:6]) + ".",
        "",
        "## 5. Interpretação honesta e limitações",
        "",
        "- **Amostra pequena e curso único**: ~200 alunos de um só curso/instituição. As linhas aluno-semana são correlacionadas (o mesmo aluno aparece em vários cortes), então o número efetivo de observações independentes é muito menor que o número de linhas. Os intervalos de confiança das métricas são largos e o modelo **não deve ser considerado validado para outras instituições** sem re-treino.",
        "- **Positivos fáceis**: parte do desempenho global vem de alunos que já estavam inativos há semanas (recência alta) e permaneceram inativos. A seção 3.1 mostra o desempenho no subconjunto acionável, que é o número relevante para a operação e é naturalmente mais baixo.",
        "- **Não-estacionariedade**: a taxa de positivos varia muito ao longo do semestre (baixa em fev–abr, alta em jun–jul, com o intervalo entre F4 e F5). O período de teste (jun–ago) é estruturalmente diferente do treino (fev–mai); isso é realista para uso em produção, mas penaliza as métricas e afeta a calibração.",
        "- **Rótulo comportamental, não administrativo**: `inativo_21d` mede silêncio no LMS, não cancelamento de matrícula. Um aluno pode ficar 3 semanas sem acessar e voltar (ex.: férias, avaliação presencial). Trata-se de um proxy operacional de risco, cuja utilidade é priorizar contato do tutor.",
        "- **Transição de fases**: com 8–19 evasões por transição, as AUCs por fold oscilam bastante; o valor médio é indicativo, não conclusivo.",
        "- **Sem dados socioeconômicos, notas ou histórico acadêmico**: só logs de navegação. Isso limita o teto de desempenho, mas torna a solução portátil para qualquer LMS Moodle-like.",
        "- **Calibração**: as probabilidades do gradient boosting são razoavelmente ordenadas (AUC), mas as faixas devem ser lidas como prioridades relativas; a tabela 3.3 indica onde o modelo super/subestima.",
        "",
        "## 6. Artefatos",
        "",
        "- `model/modelo_risco_21d.joblib` — HGB retreinado em todo o conjunto rotulado (+ baseline logístico).",
        "- `model/modelo_transicao_fases.joblib` — regressão logística de transição de fases.",
        "- `model/metadados.json` — features, datas, hiperparâmetros e métricas.",
        "- `outputs/metricas.json` — todas as métricas, curvas ROC/PR e calibração usadas nas figuras e no dashboard.",
        "",
    ]
    ARQ_RESULTADOS.write_text("\n".join(L), encoding="utf-8")
    log(f"Salvo {ARQ_RESULTADOS}")


def main() -> None:
    log(f"Lendo {ARQ_TREINO}")
    base = pd.read_parquet(ARQ_TREINO)
    base = base[base[ROTULO].notna()].copy()
    log("=== Modelo principal: inatividade em 21 dias ===")
    met_principal = treinar_modelo_principal(base)

    log("=== Modelo secundário: transição de fases ===")
    trans = pd.read_parquet(ARQ_TRANSICAO)
    met_trans = treinar_modelo_transicao(trans)

    metricas = {
        "gerado_em": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "modelo_principal": met_principal,
        "modelo_transicao": met_trans,
    }
    salvar_json(metricas, ARQ_METRICAS)
    log(f"Salvo {ARQ_METRICAS}")

    metadados = {
        "nome": "modelo_risco_21d",
        "algoritmo": "HistGradientBoostingClassifier (scikit-learn)",
        "gerado_em": metricas["gerado_em"],
        "features": FEATURES,
        "rotulo": ROTULO,
        "horizonte_dias": HORIZONTE_ROTULO_DIAS,
        "hiperparametros": met_principal["hiperparametros_hgb"],
        "treino_final": {
            "n_linhas": met_principal["split"]["n_total_rotulado"],
            "alunos": met_principal["split"]["alunos_total"],
            "taxa_positivos": met_principal["split"]["taxa_positivos_total"],
            "primeiro_corte": met_principal["split"]["cortes_treino"][0],
            "ultimo_corte": met_principal["split"]["cortes_teste"][-1],
        },
        "avaliacao_temporal": {
            "split": met_principal["split"]["criterio"],
            "auc_roc": met_principal["hgb"]["auc_roc"],
            "auc_pr": met_principal["hgb"]["auc_pr"],
            "f1_05": met_principal["hgb"]["f1"],
            "precisao_top20": met_principal["hgb"]["top20"]["precisao"],
            "auc_roc_acionavel": met_principal["hgb_acionavel"]["auc_roc"],
            "auc_pr_acionavel": met_principal["hgb_acionavel"]["auc_pr"],
            "baseline_logistica_auc_roc": met_principal["logistica"]["auc_roc"],
        },
        "faixas_risco": {"Alto": f">= {LIMIAR_ALTO}", "Médio": f"[{LIMIAR_MEDIO}, {LIMIAR_ALTO})", "Baixo": f"< {LIMIAR_MEDIO}"},
        "modelo_transicao": {
            "arquivo": ARQ_MODELO_TRANSICAO.name,
            "features": FEATURES_TRANSICAO,
            "auc_roc_medio_lopo": met_trans["auc_roc_medio"],
            "auc_pr_medio_lopo": met_trans["auc_pr_medio"],
        },
    }
    salvar_json(metadados, ARQ_METADADOS)
    log(f"Salvo {ARQ_METADADOS}")

    escrever_resultados(met_principal, met_trans)


if __name__ == "__main__":
    main()
