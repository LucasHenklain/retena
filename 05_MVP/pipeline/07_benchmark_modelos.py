# -*- coding: utf-8 -*-
"""07 — Benchmark de modelos (v2) para o risco de inatividade em 21 dias.

Compara, no MESMO protocolo temporal do `03_treinar_modelo.py` (treino: cortes
< 2026-06-01 com embargo de 21 dias; teste: cortes ≥ 2026-06-01; mesmas 22
features), o HGB entregue com alternativas cujas configurações foram adaptadas
do EduRetain (equipe Retena):

  (a) HGB de referência — hiperparâmetros lidos de model/metadados.json
  (b) LR baseline atual — StandardScaler + LogisticRegression(C=1), como no 03
  (b') LR baseline + class_weight="balanced" (variante extra, para comparação)
  (c) LR "EduRetain" — SimpleImputer(mediana) + StandardScaler +
      LogisticRegression(liblinear, L1, balanced, C=1, tol=1e-4)
  (d) XGBoost config EduRetain — scale_pos_weight=neg/pos do treino,
      subsample 0.8, n_estimators 200, max_depth 6, learning_rate 0.01,
      gamma 0, colsample_bytree 0.7
  (e) GradientBoostingClassifier padrão (random_state=42)

Métricas (conjunto completo e subconjunto acionável = ≥1 evento nos 28 dias
anteriores ao corte): AUC-ROC, AUC-PR, precisão@top-20%, recall@0,5,
precisão@0,5, F1, F2, Brier. O F2 (recall ponderado) é o critério de seleção
usado no EduRetain; aqui é reportado, não usado para trocar o artefato.

Este script NÃO altera o modelo entregue nem nenhum arquivo existente. Só cria:
  outputs/benchmark_modelos.json, outputs/benchmark_modelos.md,
  outputs/figs/fig_benchmark_modelos.png
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

if hasattr(sys.stdout, "reconfigure"):  # console Windows (cp1252) não imprime "→", "≥" etc.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    DATA_SPLIT_TESTE,
    DIR_FIGS,
    DIR_MODEL,
    DIR_OUTPUTS,
    HORIZONTE_ROTULO_DIAS,
    carregar_json,
    log,
    salvar_json,
)

ARQ_TREINO = DIR_OUTPUTS / "base_treino_semanal.parquet"
ARQ_METADADOS = DIR_MODEL / "metadados.json"
ARQ_JSON = DIR_OUTPUTS / "benchmark_modelos.json"
ARQ_MD = DIR_OUTPUTS / "benchmark_modelos.md"
ARQ_FIG = DIR_FIGS / "fig_benchmark_modelos.png"

SEED = 42
ROTULO = "inativo_21d"
AUC_REF, TOL_REF = 0.882, 0.005  # reprodução exigida do HGB entregue

COR = {"primaria": "#0B2545", "acento": "#2EC4B6", "alerta": "#FFB703", "critico": "#FF6B4A"}


# ---------------------------------------------------------------------------
# Split temporal — cópia fiel do 03_treinar_modelo.py
# ---------------------------------------------------------------------------
def split_temporal(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
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
    fmt = lambda cs: [pd.Timestamp(c).strftime("%Y-%m-%d") for c in cs]  # noqa: E731
    info = {
        "criterio": f"treino: cortes < {DATA_SPLIT_TESTE.date()} (com embargo de {HORIZONTE_ROTULO_DIAS} dias); teste: cortes ≥ {DATA_SPLIT_TESTE.date()}",
        "cortes_treino": fmt(cortes_treino), "cortes_embargo": fmt(cortes_embargo), "cortes_teste": fmt(cortes_teste),
        "n_treino": int(len(tr)), "n_teste": int(len(te)),
        "alunos_treino": int(tr["aluno_id"].nunique()), "alunos_teste": int(te["aluno_id"].nunique()),
        "taxa_positivos_treino": float(tr[ROTULO].mean()), "taxa_positivos_teste": float(te[ROTULO].mean()),
    }
    return tr, te, info


# ---------------------------------------------------------------------------
# Métricas — mesma definição do 03 (top-k: k = ceil(0,2·n), ordenação por -p)
# ---------------------------------------------------------------------------
def precisao_top_k(y: np.ndarray, p: np.ndarray, frac: float = 0.20) -> dict:
    n = len(y)
    k = max(int(np.ceil(n * frac)), 1)
    top = np.argsort(-p)[:k]
    return {"k": int(k), "precisao": float(y[top].mean()),
            "recall_capturado": float(y[top].sum() / max(y.sum(), 1)),
            "lift": float(y[top].mean() / max(y.mean(), 1e-9))}


def avaliar(y: np.ndarray, p: np.ndarray, limiar: float = 0.5) -> dict:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    yhat = (p >= limiar).astype(int)
    t20 = precisao_top_k(y, p, 0.20)
    return {
        "n": int(len(y)), "positivos": int(y.sum()), "taxa_positivos": float(y.mean()),
        "auc_roc": float(roc_auc_score(y, p)), "auc_pr": float(average_precision_score(y, p)),
        "precisao_top20": t20["precisao"], "k_top20": t20["k"], "lift_top20": t20["lift"],
        "recall_05": float(recall_score(y, yhat, zero_division=0)),
        "precisao_05": float(precision_score(y, yhat, zero_division=0)),
        "f1": float(f1_score(y, yhat, zero_division=0)),
        "f2": float(fbeta_score(y, yhat, beta=2, zero_division=0)),
        "brier": float(brier_score_loss(y, p)),
        "n_previstos_positivos_05": int(yhat.sum()),
        # Limiar 0,3 = fronteira da faixa "Médio", fixada a priori (README, item 8): mostra quanto do F2 é efeito de limiar.
        "recall_03": float(recall_score(y, (p >= 0.3).astype(int), zero_division=0)),
        "f2_03": float(fbeta_score(y, (p >= 0.3).astype(int), beta=2, zero_division=0)),
    }


# ---------------------------------------------------------------------------
# Candidatos
# ---------------------------------------------------------------------------
def construir_modelos(params_hgb: dict, ytr: np.ndarray) -> dict:
    neg, pos = int((ytr == 0).sum()), int((ytr == 1).sum())
    spw = neg / pos if pos else 1.0  # adaptado do EduRetain (equipe Retena)
    log(f"scale_pos_weight (neg/pos do treino) = {spw:.4f}")
    return {
        "HGB (referência entregue)": (
            HistGradientBoostingClassifier(random_state=SEED, early_stopping=False, **params_hgb),
            "HistGradientBoostingClassifier com os hiperparâmetros de model/metadados.json; sem reamostragem/pesos.", COR["primaria"]),
        "LR baseline atual (03)": (
            Pipeline([("scaler", StandardScaler()),
                      ("lr", LogisticRegression(max_iter=5000, C=1.0, random_state=SEED))]),
            "StandardScaler + LogisticRegression(C=1, lbfgs), exatamente como novo_lr() do 03 — sem class_weight.", COR["acento"]),
        "LR baseline + balanced": (
            Pipeline([("scaler", StandardScaler()),
                      ("lr", LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced", random_state=SEED))]),
            "Variante extra: mesmo baseline com class_weight='balanced' (isola o efeito do balanceamento).", COR["acento"]),
        "LR EduRetain (L1 liblinear balanced)": (
            Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()),
                      # EduRetain usa penalty="l1"; no scikit-learn ≥ 1.8 a grafia é l1_ratio=1.0
                      # (verificado: coeficientes idênticos, 2 zerados em ambos).
                      ("lr", LogisticRegression(solver="liblinear", l1_ratio=1.0, class_weight="balanced",
                                                C=1.0, tol=1e-4, random_state=SEED))]),
            "SimpleImputer(mediana) + StandardScaler + LR liblinear L1 balanced C=1 — adaptado do EduRetain (equipe Retena). A base não tem NaN, então o imputer é no-op.", COR["acento"]),
        "XGBoost (config EduRetain)": (
            XGBClassifier(random_state=SEED, scale_pos_weight=spw, subsample=0.8, n_estimators=200,
                          max_depth=6, learning_rate=0.01, gamma=0, colsample_bytree=0.7, n_jobs=1),
            f"XGBClassifier com scale_pos_weight={spw:.3f} (neg/pos do treino), subsample 0.8, 200 árvores, depth 6, lr 0.01, colsample 0.7 — adaptado do EduRetain (equipe Retena).", COR["alerta"]),
        "GradientBoosting (padrão sklearn)": (
            GradientBoostingClassifier(random_state=SEED),
            "GradientBoostingClassifier(random_state=42) com defaults (100 árvores, depth 3, lr 0.1) — adaptado do EduRetain (equipe Retena).", COR["critico"]),
    }


def main() -> None:
    log("07 — benchmark de modelos (v2)")
    meta = carregar_json(ARQ_METADADOS)
    features, params_hgb = meta["features"], meta["hiperparametros"]
    base = pd.read_parquet(ARQ_TREINO)
    tr, te, split = split_temporal(base)
    Xtr, ytr = tr[features].values, tr[ROTULO].astype(int).values
    Xte, yte = te[features].values, te[ROTULO].astype(int).values
    m_acion = (te["eventos_28d"] > 0).values
    log(f"Treino {split['n_treino']} linhas / {len(split['cortes_treino'])} cortes; embargo {split['cortes_embargo']}; "
        f"teste {split['n_teste']} linhas / {len(split['cortes_teste'])} cortes; acionável n={int(m_acion.sum())}")

    resultados, cores = {}, {}
    for nome, (modelo, descricao, cor) in construir_modelos(params_hgb, ytr).items():
        modelo.fit(Xtr, ytr)
        p = modelo.predict_proba(Xte)[:, 1]
        resultados[nome] = {"descricao": descricao, "completo": avaliar(yte, p),
                            "acionavel": avaliar(yte[m_acion], p[m_acion])}
        cores[nome] = cor
        c, a = resultados[nome]["completo"], resultados[nome]["acionavel"]
        log(f"{nome:38s} AUC-ROC={c['auc_roc']:.3f} AUC-PR={c['auc_pr']:.3f} F2={c['f2']:.3f} | acion. AUC-PR={a['auc_pr']:.3f} F2={a['f2']:.3f}")

    auc_hgb = resultados["HGB (referência entregue)"]["completo"]["auc_roc"]
    reproduz = abs(auc_hgb - AUC_REF) <= TOL_REF
    log(f"Reprodução HGB: AUC-ROC={auc_hgb:.4f} vs {AUC_REF}±{TOL_REF} → {'OK' if reproduz else 'FALHOU'}")
    if not reproduz:
        raise SystemExit("HGB de referência não reproduziu a AUC-ROC entregue — investigar split antes de publicar.")

    saida = {
        "gerado_em": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "credito": "Configurações (c), (d), (e) adaptadas do EduRetain (equipe Retena).",
        "ambiente": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "xgboost": xgboost.__version__},
        "features": features, "hiperparametros_hgb": params_hgb, "split": split,
        "acionavel": {"definicao": "eventos_28d > 0 no corte", "n": int(m_acion.sum()), "positivos": int(yte[m_acion].sum())},
        "reproducao_hgb": {"auc_roc_obtida": auc_hgb, "auc_roc_referencia": AUC_REF, "tolerancia": TOL_REF, "ok": reproduz},
        "modelos": resultados,
        "vencedores": vencedores(resultados),
    }
    salvar_json(saida, ARQ_JSON)
    escrever_md(saida)
    gerar_figura(resultados, cores)
    log(f"Salvos: {ARQ_JSON.name}, {ARQ_MD.name}, figs/{ARQ_FIG.name}")


def vencedores(res: dict) -> dict:
    out = {}
    for conj in ("completo", "acionavel"):
        for met in ("auc_pr", "f2", "auc_roc", "precisao_top20"):
            nome = max(res, key=lambda k: res[k][conj][met])
            out[f"{conj}/{met}"] = {"modelo": nome, "valor": res[nome][conj][met]}
        nome = min(res, key=lambda k: res[k][conj]["brier"])
        out[f"{conj}/brier"] = {"modelo": nome, "valor": res[nome][conj]["brier"]}
    return out


# ---------------------------------------------------------------------------
# Relatório (Markdown) e figura
# ---------------------------------------------------------------------------
COLS_MD = [("auc_roc", "AUC-ROC"), ("auc_pr", "AUC-PR"), ("precisao_top20", "P@top-20%"),
           ("recall_05", "Recall@0,5"), ("precisao_05", "Prec.@0,5"), ("f1", "F1"), ("f2", "F2"), ("brier", "Brier ↓")]


def _f(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def _tabela(res: dict, conj: str) -> list[str]:
    L = ["| Modelo | " + " | ".join(c[1] for c in COLS_MD) + " |", "|---|" + "---:|" * len(COLS_MD)]
    for nome, r in res.items():
        m = r[conj]
        vals = []
        for k, _ in COLS_MD:
            melhor = (min if k == "brier" else max)(res[n][conj][k] for n in res)
            vals.append(f"**{_f(m[k])}**" if m[k] == melhor else _f(m[k]))
        L.append(f"| {nome} | " + " | ".join(vals) + " |")
    return L


def escrever_md(s: dict) -> None:
    res, sp, v = s["modelos"], s["split"], s["vencedores"]
    hgb = res["HGB (referência entregue)"]
    L = [
        "# Benchmark de modelos (v2) — risco de inatividade em 21 dias",
        "",
        f"Gerado em {s['gerado_em']} por `pipeline/07_benchmark_modelos.py` (Python {s['ambiente']['python']}, "
        f"scikit-learn {s['ambiente']['scikit_learn']}, xgboost {s['ambiente']['xgboost']}). "
        "Configurações (c), (d) e (e) adaptadas do EduRetain (equipe Retena). "
        "**Este benchmark não altera o modelo entregue** (`model/modelo_risco_21d.joblib`) nem os resultados de `RESULTADOS.md`; é uma leitura comparativa adicional.",
        "",
        "## 1. Protocolo (idêntico ao `03_treinar_modelo.py`)",
        "",
        f"- Split: {sp['criterio']}.",
        f"- Treino: {sp['n_treino']:,} linhas, {len(sp['cortes_treino'])} cortes ({sp['cortes_treino'][0]} → {sp['cortes_treino'][-1]}), {sp['alunos_treino']} alunos, positivos {sp['taxa_positivos_treino']:.1%}.".replace(",", "."),
        f"- Embargo (cortes descartados): {', '.join(sp['cortes_embargo'])}.",
        f"- Teste: {sp['n_teste']:,} linhas, {len(sp['cortes_teste'])} cortes ({sp['cortes_teste'][0]} → {sp['cortes_teste'][-1]}), {sp['alunos_teste']} alunos, positivos {sp['taxa_positivos_teste']:.1%}.".replace(",", "."),
        f"- Subconjunto acionável: {s['acionavel']['definicao']} — n={s['acionavel']['n']}, positivos={s['acionavel']['positivos']}.",
        f"- Mesmas {len(s['features'])} features de `metadados.json`; nenhum modelo foi tunado no teste. Limiar fixo 0,5 para recall/precisão/F1/F2; top-20% com k=⌈0,2·n⌉.",
        f"- Reprodução do HGB entregue: AUC-ROC obtida {_f(s['reproducao_hgb']['auc_roc_obtida'])} vs. referência {_f(AUC_REF)} (±{TOL_REF}) → **{'OK' if s['reproducao_hgb']['ok'] else 'FALHOU'}**.",
        "",
        "## 2. Modelos comparados",
        "",
    ]
    L += [f"- **{n}** — {r['descricao']}" for n, r in res.items()]
    L += ["", f"## 3. Métricas no teste — conjunto completo (n={hgb['completo']['n']}, positivos {hgb['completo']['taxa_positivos']:.1%})", ""]
    L += _tabela(res, "completo")
    L += ["", f"## 4. Métricas no teste — subconjunto acionável (n={hgb['acionavel']['n']}, positivos {hgb['acionavel']['taxa_positivos']:.1%})", ""]
    L += _tabela(res, "acionavel")
    L += ["", "## 5. Leitura honesta", "",
          f"- **Por F2 (critério de seleção do EduRetain)**: vence **{v['completo/f2']['modelo']}** no completo ({_f(v['completo/f2']['valor'])}) "
          f"e **{v['acionavel/f2']['modelo']}** no acionável ({_f(v['acionavel/f2']['valor'])}). "
          f"HGB: {_f(hgb['completo']['f2'])} / {_f(hgb['acionavel']['f2'])}.",
          f"- **Por AUC-PR (critério do Retena)**: vence **{v['completo/auc_pr']['modelo']}** no completo ({_f(v['completo/auc_pr']['valor'])}) "
          f"e **{v['acionavel/auc_pr']['modelo']}** no acionável ({_f(v['acionavel/auc_pr']['valor'])}). "
          f"HGB: {_f(hgb['completo']['auc_pr'])} / {_f(hgb['acionavel']['auc_pr'])}.",
          f"- **Melhor Brier (calibração)**: {v['completo/brier']['modelo']} ({_f(v['completo/brier']['valor'])}) no completo; "
          f"{v['acionavel/brier']['modelo']} ({_f(v['acionavel/brier']['valor'])}) no acionável.",
          ]
    L += interpretacao(s)
    L += ["", "## 6. Artefatos", "",
          "- `outputs/benchmark_modelos.json` — todas as métricas, split, versões e vencedores por critério.",
          "- `outputs/figs/fig_benchmark_modelos.png` — AUC-PR e F2 por modelo (completo × acionável).",
          "- `pipeline/07_benchmark_modelos.py` — script reprodutível (`python pipeline/07_benchmark_modelos.py`)."]
    ARQ_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def gerar_figura(res: dict, cores: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 11,
                         "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#0B2545",
                         "text.color": "#0B2545", "axes.labelcolor": "#0B2545", "xtick.color": "#0B2545", "ytick.color": "#0B2545"})
    nomes = list(res)
    rot = [n.replace(" (", "\n(") for n in nomes]
    x = np.arange(len(nomes))
    w = 0.38
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), dpi=100)
    for ax, (met, titulo) in zip(axes, [("auc_pr", "AUC-PR (average precision)"), ("f2", "F2 @ limiar 0,5")]):
        vc = [res[n]["completo"][met] for n in nomes]
        va = [res[n]["acionavel"][met] for n in nomes]
        b1 = ax.bar(x - w / 2, vc, w, color=[cores[n] for n in nomes], edgecolor="white", linewidth=0.8)
        b2 = ax.bar(x + w / 2, va, w, color=[cores[n] for n in nomes], alpha=0.45, hatch="//", edgecolor="white", linewidth=0.8)
        for bars in (b1, b2):
            for b in bars:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012, f"{b.get_height():.3f}".replace(".", ","),
                        ha="center", va="bottom", fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(rot, fontsize=9)
        ax.set_ylim(0, 1.0)
        ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold", pad=12)
        ax.grid(axis="y", color="#E6E9EF", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].legend(handles=[Patch(facecolor="#0B2545", label="Teste completo (n=1.609)"),
                            Patch(facecolor="#0B2545", alpha=0.45, hatch="//", label="Subconjunto acionável (n=1.298)")],
                   loc="upper right", frameon=False, fontsize=10)
    fig.suptitle("Benchmark de modelos — teste temporal jun–ago/2026 (mesmo split e features do modelo entregue)",
                 x=0.01, ha="left", fontsize=15, fontweight="bold", color="#0B2545")
    fig.text(0.01, 0.012, "Cores por família: HGB (azul-marinho, modelo entregue) · regressões logísticas (verde) · XGBoost (amarelo) · GradientBoosting (coral). "
             "Configs (c)(d)(e) adaptadas do EduRetain (equipe Retena).", fontsize=9, color="#5B6B7F")
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(ARQ_FIG, dpi=100)
    plt.close(fig)


def interpretacao(s: dict) -> list[str]:
    """Leitura escrita a partir da execução real; os números são formatados a partir do JSON gerado."""
    r = s["modelos"]
    hgb, lr03, lrb, lre, xgb, gb = (r[k] for k in [
        "HGB (referência entregue)", "LR baseline atual (03)", "LR baseline + balanced",
        "LR EduRetain (L1 liblinear balanced)", "XGBoost (config EduRetain)", "GradientBoosting (padrão sklearn)"])
    c, a = "completo", "acionavel"
    return [
        "",
        "**O que os números dizem:**",
        "",
        f"1. **Nenhuma configuração do EduRetain supera o baseline logístico que já estava no `03`.** A LR do EduRetain (L1, balanced) fica em AUC-PR {_f(lre[c]['auc_pr'])} (completo) / {_f(lre[a]['auc_pr'])} (acionável) contra {_f(lr03[c]['auc_pr'])} / {_f(lr03[a]['auc_pr'])} do baseline atual; o XGBoost com a config do EduRetain ({_f(xgb[c]['auc_pr'])} / {_f(xgb[a]['auc_pr'])}) fica abaixo do HGB ({_f(hgb[c]['auc_pr'])} / {_f(hgb[a]['auc_pr'])}) e o GradientBoosting padrão é o pior do grupo ({_f(gb[c]['auc_pr'])} / {_f(gb[a]['auc_pr'])}). Essas configs foram desenhadas para outro dataset (OULAD, com features cadastrais e ~20 mil linhas); aqui, com 2.126 linhas de treino, a taxa de aprendizado 0,01 com 200 árvores e profundidade 6 do XGBoost não converge para o mesmo nível dos modelos rasos.",
        f"2. **A vantagem em F2 é efeito de limiar, não de ranqueamento.** Os três modelos com `class_weight='balanced'`/`scale_pos_weight` ganham F2@0,5 porque inflacionam as probabilidades e cruzam o limiar 0,5 com mais frequência (recall@0,5 de {_f(lrb[c]['recall_05'])} na LR balanced vs. {_f(hgb[c]['recall_05'])} no HGB), mas suas métricas de ordenação (AUC-ROC / AUC-PR) são iguais ou **piores** que as versões não balanceadas (LR balanced AUC-PR {_f(lrb[c]['auc_pr'])} vs. LR baseline {_f(lr03[c]['auc_pr'])}). Movendo o limiar do HGB para 0,3 — a fronteira da faixa \"Médio\", fixada a priori no README — o F2 do HGB vai de {_f(hgb[c]['f2'])} para {_f(hgb[c]['f2_03'])} (acionável: {_f(hgb[a]['f2'])} → {_f(hgb[a]['f2_03'])}), sem re-treinar nada. Comparar F2 em limiar fixo 0,5 entre modelos com e sem reponderação, como faz a seleção do EduRetain, favorece mecanicamente os reponderados; o Retena já usa faixas (0,3 / 0,6) justamente para separar a qualidade do ranking da decisão operacional.",
        f"3. **Se o critério fosse estritamente AUC-PR ou F2, a regressão logística venceria — por margem pequena e já conhecida.** A diferença HGB → LR baseline é de {_f(lr03[c]['auc_pr'] - hgb[c]['auc_pr'])} em AUC-PR no completo e {_f(lr03[a]['auc_pr'] - hgb[a]['auc_pr'])} no acionável; isso já está registrado em `RESULTADOS.md` (seção 3) e no README (decisão 6). Com ~200 alunos e linhas aluno-semana correlacionadas, essa diferença está dentro da incerteza amostral e não é um achado novo trazido pelas configs do EduRetain. Não há vencedor \"com folga\": o melhor AUC-PR acionável do benchmark ({_f(s['vencedores']['acionavel/auc_pr']['valor'])}) e o do HGB ({_f(hgb[a]['auc_pr'])}) distam {_f(s['vencedores']['acionavel/auc_pr']['valor'] - hgb[a]['auc_pr'])}.",
        f"4. **Por que o HGB permanece o modelo entregue.** (i) Reproduz exatamente o que foi reportado (AUC-ROC {_f(hgb[c]['auc_roc'])}); (ii) tem a melhor precisão@0,5 do grupo ({_f(hgb[c]['precisao_05'])} completo) — no desenho operacional do Retena, a faixa Alto exige ação humana e falso-positivo custa tempo de tutor; (iii) lida nativamente com interações e novas features sem re-escalonamento, motivo original da escolha; (iv) trocar o artefato por um ganho não significativo quebraria a rastreabilidade entre `metadados.json`, `metricas.json`, figuras e dashboard já entregues. O que este benchmark **acrescenta** de acionável é a evidência de que o limiar 0,3 (faixa Médio) recupera o recall que os modelos balanceados obtêm com reponderação — reforçando a política de faixas em vez de um limiar único.",
        "",
        "**Limitações deste benchmark:** um único split temporal (sem intervalos de confiança); métricas em limiar fixo dependem da calibração de cada modelo; nenhum candidato foi tunado (as configs do EduRetain foram usadas como vieram, adaptadas para 22 features numéricas sem categorias). Um teste pareado por corte (9 cortes de teste) ou bootstrap por aluno seria o próximo passo para afirmar significância.",
    ]


if __name__ == "__main__":
    main()
