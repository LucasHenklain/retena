# -*- coding: utf-8 -*-
"""treinar_oulad.py — Avalia o método Retena no OULAD e reproduz o setup EduRetain para comparação.

Parte A (método Retena, base aluno-semana de preparar_oulad.py)
  - split TEMPORAL por apresentação: treino 2013B+2013J, teste 2014B+2014J;
  - HistGradientBoosting com os hiperparâmetros do Retena + regressão logística balanced (StandardScaler);
  - métricas no teste completo e no subconjunto acionável (cliques_28d > 0), para
    `inativo_21d` (rótulo principal) e `evadiu_28d` (rótulo administrativo).

Parte B (setup EduRetain, para comparação honesta)
  - alvo final_result == 'Withdrawn'; features até o dia 30 (VLE + avaliações + cadastro);
  - (a) split aleatório 80/20 estratificado (como no EduRetain) vs. (b) split temporal 2013 -> 2014;
  - LR liblinear L1 balanced C=1 (EduRetain) e HGB (Retena); diferença (a)-(b) = inflação do split aleatório;
  - (c) extra: (b) excluindo alunos já desmatriculados até o dia 30 (alvo trivial).

Saídas: metricas_oulad.json e figs/fig_oulad_roc_pr.png nesta pasta. Nenhum número é digitado à mão.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, precision_recall_curve,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get(
    "OULAD_WORK_DIR",
    r"C:\Users\lmhsilva\AppData\Local\Temp\claude\C--Users-lmhsilva-Projetos-StartupOne"
    r"\f6a65157-5d50-471e-86f3-c1f77a65cee8\scratchpad\oulad",
))
RAW = Path(os.environ.get("OULAD_RAW_DIR", SCRATCH / "raw"))
FIGS = AQUI / "figs"

COR = {"hgb": "#0B2545", "lr": "#2EC4B6", "amarelo": "#FFB703", "coral": "#FF6B4A"}
TREINO = ["2013B", "2013J"]
TESTE = ["2014B", "2014J"]
FEATURES = [
    "cliques_7d", "cliques_14d", "cliques_28d", "dias_ativos_7d", "dias_ativos_14d", "dias_ativos_28d",
    "recencia_dias", "cliques_acumulados", "dias_ativos_acumulados", "tendencia", "semanas_ativas_ultimas_8",
    "entregas_ate_t", "entregas_28d", "semanas_desde_primeiro_clique", "dia_corte",
]
HGB_PARAMS = dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=8, min_samples_leaf=40,
                  l2_regularization=2.0, random_state=42)
FAIXAS = [("Alto", 0.60, 1.01), ("Médio", 0.30, 0.60), ("Baixo", -0.01, 0.30)]
T0 = time.time()
TEMPOS: dict[str, float] = {}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def metricas(y: np.ndarray, p: np.ndarray, frac: float = 0.2) -> dict:
    y = np.asarray(y, dtype=int)
    n, npos = len(y), int(y.sum())
    k = max(1, int(round(frac * n)))
    top = np.argsort(-p, kind="stable")[:k]
    prec = float(y[top].mean())
    base = npos / n
    return {
        "n": int(n), "positivos": npos, "taxa_positivos": round(base, 4),
        "auc_roc": round(float(roc_auc_score(y, p)), 4) if 0 < npos < n else None,
        "auc_pr": round(float(average_precision_score(y, p)), 4) if npos else None,
        "brier": round(float(brier_score_loss(y, p)), 4),
        "k_top20": int(k), "precisao_top20": round(prec, 4),
        "recall_top20": round(float(y[top].sum() / npos), 4) if npos else None,
        "lift_top20": round(prec / base, 2) if base else None,
    }


def curvas(y, p, npts: int = 150) -> dict:
    fpr, tpr, _ = roc_curve(y, p)
    pr, rc, _ = precision_recall_curve(y, p)
    ir = np.linspace(0, len(fpr) - 1, min(npts, len(fpr))).astype(int)
    ip = np.linspace(0, len(pr) - 1, min(npts, len(pr))).astype(int)
    return {"fpr": fpr[ir].round(4).tolist(), "tpr": tpr[ir].round(4).tolist(),
            "recall": rc[ip].round(4).tolist(), "precisao": pr[ip].round(4).tolist()}


def modelo_lr_retena() -> Pipeline:
    return Pipeline([("scaler", StandardScaler()),
                     ("lr", LogisticRegression(class_weight="balanced", max_iter=3000, random_state=42))])


# ----------------------------------------------------------------------------- Parte A
def parte_a(res: dict) -> dict:
    base = pd.read_parquet(SCRATCH / "oulad_base_semanal.parquet")
    tr = base[base["code_presentation"].isin(TREINO)].reset_index(drop=True)
    te = base[base["code_presentation"].isin(TESTE)].reset_index(drop=True)
    acion_te = (te["cliques_28d"] > 0).to_numpy()
    Xtr, Xte = tr[FEATURES].to_numpy(dtype=np.float32), te[FEATURES].to_numpy(dtype=np.float32)

    def bloco(df, mask):
        d = df[mask] if mask is not None else df
        return {"linhas": int(len(d)), "alunos": int(d["id_student"].nunique()),
                "matriculas": int(d.groupby(["code_module", "code_presentation", "id_student"], observed=True).ngroups),
                "cortes": int(d["dia_corte"].nunique()),
                "taxa_inativo_21d": round(float(d["inativo_21d"].mean()), 4),
                "taxa_evadiu_28d": round(float(d["evadiu_28d"].mean()), 4)}

    res["retena_oulad"] = {
        "features": FEATURES, "hgb_params": {k: v for k, v in HGB_PARAMS.items() if k != "random_state"},
        "split": {"treino": TREINO, "teste": TESTE},
        "base": {"total": bloco(base, None), "treino": bloco(tr, None), "teste": bloco(te, None),
                 "teste_acionavel": bloco(te, acion_te)},
        "rotulos": {},
    }
    curvas_fig = {}
    for rotulo in ("inativo_21d", "evadiu_28d"):
        ytr, yte = tr[rotulo].to_numpy(), te[rotulo].to_numpy()
        saida = {"modelos": {}}
        probs = {}
        for nome, mod in (("hgb", HistGradientBoostingClassifier(**HGB_PARAMS)), ("lr", modelo_lr_retena())):
            t = time.time()
            mod.fit(Xtr, ytr)
            TEMPOS[f"fit_{rotulo}_{nome}"] = round(time.time() - t, 1)
            p = mod.predict_proba(Xte)[:, 1]
            probs[nome] = p
            saida["modelos"][nome] = {
                "completo": metricas(yte, p),
                "acionavel": metricas(yte[acion_te], p[acion_te]),
                "por_apresentacao": {pres: metricas(yte[m], p[m]) for pres in TESTE
                                     for m in [(te["code_presentation"] == pres).to_numpy()]},
                "por_modulo": {f"{mo}-{pr}": metricas(yte[m], p[m])
                               for (mo, pr), m in [((mo, pr), ((te["code_module"] == mo) & (te["code_presentation"] == pr)).to_numpy())
                                                   for mo, pr in te.groupby(["code_module", "code_presentation"], observed=True).size().index]},
            }
            if nome == "lr":
                coef = mod.named_steps["lr"].coef_[0]
                saida["modelos"][nome]["coef_padronizados"] = {f: round(float(c), 3) for f, c in
                                                               sorted(zip(FEATURES, coef), key=lambda z: -abs(z[1]))}
            log(f"{rotulo} / {nome}: AUC-ROC {saida['modelos'][nome]['completo']['auc_roc']} | "
                f"AUC-PR {saida['modelos'][nome]['completo']['auc_pr']} | acionável AUC-ROC "
                f"{saida['modelos'][nome]['acionavel']['auc_roc']} AUC-PR {saida['modelos'][nome]['acionavel']['auc_pr']}")
            if rotulo == "inativo_21d":
                curvas_fig[nome] = {"completo": curvas(yte, p), "acionavel": curvas(yte[acion_te], p[acion_te])}
                if nome == "hgb":
                    hgb, p_hgb = mod, p
        if rotulo == "inativo_21d":
            # estabilidade por corte, faixas de risco e importância por permutação (HGB)
            saida["hgb_por_corte"] = {int(t): {"n": int(m.sum()), "taxa": round(float(yte[m].mean()), 4),
                                               "auc_roc": round(float(roc_auc_score(yte[m], p_hgb[m])), 4),
                                               "auc_pr": round(float(average_precision_score(yte[m], p_hgb[m])), 4)}
                                     for t in sorted(te["dia_corte"].unique()) for m in [(te["dia_corte"] == t).to_numpy()]}
            saida["hgb_faixas"] = {}
            for nome_f, lo, hi in FAIXAS:
                m = (p_hgb >= lo) & (p_hgb < hi)
                saida["hgb_faixas"][nome_f] = {"n": int(m.sum()), "pct_linhas": round(float(m.mean()), 4),
                                               "taxa_observada": round(float(yte[m].mean()), 4) if m.any() else None}
            saida["hgb_calibracao"] = []
            for lo in np.arange(0, 1, 0.1):
                m = (p_hgb >= lo) & (p_hgb < lo + 0.1)
                if m.any():
                    saida["hgb_calibracao"].append({"bin": f"{lo:.1f}-{lo + 0.1:.1f}", "n": int(m.sum()),
                                                    "prob_media": round(float(p_hgb[m].mean()), 3),
                                                    "taxa_observada": round(float(yte[m].mean()), 3)})
            t = time.time()
            rng = np.random.RandomState(42)
            amostra = rng.choice(len(te), size=min(100_000, len(te)), replace=False)
            pi = permutation_importance(hgb, Xte[amostra], yte[amostra], scoring="roc_auc",
                                        n_repeats=5, random_state=42, n_jobs=1)
            saida["hgb_importancia_permutacao"] = {
                "amostra": int(len(amostra)), "repeticoes": 5,
                "features": [{"feature": FEATURES[i], "queda_auc": round(float(pi.importances_mean[i]), 4),
                              "dp": round(float(pi.importances_std[i]), 4)}
                             for i in np.argsort(-pi.importances_mean)]}
            TEMPOS["permutacao_hgb"] = round(time.time() - t, 1)
        res["retena_oulad"]["rotulos"][rotulo] = saida
    res["retena_oulad"]["curvas_inativo_21d"] = curvas_fig
    return curvas_fig


# ----------------------------------------------------------------------------- Parte B
NUM_COLS = ["num_of_prev_attempts", "studied_credits", "vle_total_clicks", "vle_active_days",
            "vle_max_clicks_single_day", "vle_clicks_per_active_day", "assess_avg_score",
            "assess_submitted_count", "assess_total_days_late"]
ORDINAL_COLS = ["highest_education", "age_band"]
NOMINAL_COLS = ["gender", "disability", "code_module"]
EDUCATION_ORDER = ["No Formal quals", "Lower Than A Level", "A Level or Equivalent",
                   "HE Qualification", "Post Graduate Qualification"]
AGE_ORDER = ["0-35", "35-55", "55<="]


def preprocessador_eduretain() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM_COLS),
        ("ord", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("enc", OrdinalEncoder(categories=[EDUCATION_ORDER, AGE_ORDER],
                                                 handle_unknown="use_encoded_value", unknown_value=-1))]), ORDINAL_COLS),
        ("nom", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("enc", OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"))]), NOMINAL_COLS),
    ])


def base_eduretain(cutoff: int = 30) -> pd.DataFrame:
    chaves = ["code_module", "code_presentation", "id_student"]
    info = pd.read_csv(RAW / "studentInfo.csv", na_values=["?"], dtype={"id_student": "int32"})
    reg = pd.read_csv(RAW / "studentRegistration.csv", na_values=["?"], dtype={"id_student": "int32"})
    info = info.merge(reg, on=chaves, how="left")
    info["target"] = (info["final_result"] == "Withdrawn").astype(int)
    dia = pd.read_parquet(SCRATCH / "oulad_cliques_dia.parquet")
    dia = dia[dia["date"] <= cutoff].astype({"code_module": "object", "code_presentation": "object"})
    vle = dia.groupby(chaves).agg(vle_total_clicks=("sum_click", "sum"), vle_active_days=("date", "nunique"),
                                  vle_max_clicks_single_day=("sum_click", "max")).reset_index()
    vle["vle_clicks_per_active_day"] = vle["vle_total_clicks"] / vle["vle_active_days"]
    assess = pd.read_csv(RAW / "assessments.csv", na_values=["?"])
    sa = pd.read_csv(RAW / "studentAssessment.csv", na_values=["?"], dtype={"id_student": "int32"})
    sa = sa.merge(assess[["id_assessment", "code_module", "code_presentation", "date"]], on="id_assessment")
    sa = sa[sa["date_submitted"] <= cutoff]
    sa["atraso"] = (sa["date_submitted"] - sa["date"]).clip(lower=0).fillna(0)
    av = sa.groupby(chaves).agg(assess_avg_score=("score", "mean"), assess_submitted_count=("id_assessment", "count"),
                                assess_total_days_late=("atraso", "sum")).reset_index()
    df = info.merge(vle, on=chaves, how="left").merge(av, on=chaves, how="left")
    zero = ["vle_total_clicks", "vle_active_days", "vle_max_clicks_single_day", "vle_clicks_per_active_day",
            "assess_submitted_count", "assess_total_days_late"]
    df[zero] = df[zero].fillna(0)
    df["ja_desmatriculado"] = (df["date_unregistration"] <= cutoff).fillna(False).astype(int)
    return df


def parte_b(res: dict) -> None:
    df = base_eduretain(30)
    X = df[NUM_COLS + ORDINAL_COLS + NOMINAL_COLS]
    y = df["target"].to_numpy()
    tr_m = df["code_presentation"].isin(TREINO).to_numpy()
    te_m = df["code_presentation"].isin(TESTE).to_numpy()
    Xa_tr, Xa_te, ya_tr, ya_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    cenarios = {
        "a_aleatorio_80_20": (Xa_tr, ya_tr, Xa_te, ya_te),
        "b_temporal_2013_2014": (X[tr_m], y[tr_m], X[te_m], y[te_m]),
    }
    ativo_te = te_m & (df["ja_desmatriculado"].to_numpy() == 0)
    cenarios["c_temporal_sem_ja_desmatriculados"] = (X[tr_m], y[tr_m], X[ativo_te], y[ativo_te])
    modelos = {
        # EduRetain usa penalty="l1"; no sklearn >= 1.8 a forma não depreciada equivalente é l1_ratio=1.0
        "lr_eduretain": lambda: LogisticRegression(solver="liblinear", l1_ratio=1.0, class_weight="balanced",
                                                   C=1.0, tol=1e-4, random_state=42),
        "hgb_retena": lambda: HistGradientBoostingClassifier(**HGB_PARAMS),
    }
    out = {"alvo": "final_result == 'Withdrawn'", "cutoff_dias": 30, "n_alunos": int(len(df)),
           "taxa_withdrawn": round(float(y.mean()), 4),
           "ja_desmatriculados_ate_30": int(df["ja_desmatriculado"].sum()),
           "taxa_withdrawn_entre_ja_desmatriculados": round(float(df.loc[df["ja_desmatriculado"] == 1, "target"].mean()), 4),
           "features": NUM_COLS + ORDINAL_COLS + NOMINAL_COLS, "cenarios": {}}
    for cen, (Xtr, ytr, Xte, yte) in cenarios.items():
        out["cenarios"][cen] = {"n_treino": int(len(ytr)), "n_teste": int(len(yte)), "modelos": {}}
        for nome, fabrica in modelos.items():
            t = time.time()
            pipe = Pipeline([("prep", preprocessador_eduretain()), ("m", fabrica())]).fit(Xtr, ytr)
            p = pipe.predict_proba(Xte)[:, 1]
            out["cenarios"][cen]["modelos"][nome] = metricas(yte, p)
            TEMPOS[f"fit_eduretain_{cen}_{nome}"] = round(time.time() - t, 1)
            log(f"EduRetain {cen} / {nome}: AUC-ROC {out['cenarios'][cen]['modelos'][nome]['auc_roc']} "
                f"AUC-PR {out['cenarios'][cen]['modelos'][nome]['auc_pr']}")
    out["inflacao_a_menos_b"] = {
        nome: {m: round(out["cenarios"]["a_aleatorio_80_20"]["modelos"][nome][m]
                        - out["cenarios"]["b_temporal_2013_2014"]["modelos"][nome][m], 4)
               for m in ("auc_roc", "auc_pr")} for nome in modelos}
    res["eduretain_oulad"] = out


# ----------------------------------------------------------------------------- Figura
def figura(cv: dict, res: dict) -> None:
    FIGS.mkdir(exist_ok=True)
    r = res["retena_oulad"]["rotulos"]["inativo_21d"]["modelos"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9.5), dpi=140, facecolor="white")
    for i, (sub, titulo) in enumerate((("completo", "Teste completo (2014B+2014J)"),
                                       ("acionavel", "Subconjunto acionável (cliques 28d > 0)"))):
        ax_roc, ax_pr = axes[i]
        for nome, rot in (("hgb", "HistGradientBoosting"), ("lr", "Regressão logística")):
            c = cv[nome][sub]
            m = r[nome][sub]
            ax_roc.plot(c["fpr"], c["tpr"], color=COR[nome], lw=2.2, label=f"{rot} — AUC {m['auc_roc']:.3f}")
            ax_pr.plot(c["recall"], c["precisao"], color=COR[nome], lw=2.2, label=f"{rot} — AUC-PR {m['auc_pr']:.3f}")
        ax_roc.plot([0, 1], [0, 1], color=COR["amarelo"], ls="--", lw=1.4, label="aleatório")
        taxa = r["hgb"][sub]["taxa_positivos"]
        ax_pr.axhline(taxa, color=COR["coral"], ls="--", lw=1.4, label=f"taxa de positivos {taxa:.1%}")
        ax_roc.set(xlabel="Taxa de falsos positivos", ylabel="Taxa de verdadeiros positivos",
                   title=f"ROC — {titulo}", xlim=(0, 1), ylim=(0, 1))
        ax_pr.set(xlabel="Recall", ylabel="Precisão", title=f"Precisão-Recall — {titulo}", xlim=(0, 1), ylim=(0, 1))
        for ax in (ax_roc, ax_pr):
            ax.set_facecolor("white")
            ax.grid(alpha=0.25)
            ax.legend(loc="lower right" if ax is ax_roc else "upper right", frameon=False, fontsize=9)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
    fig.suptitle("Método Retena aplicado ao OULAD — rótulo inativo_21d, split temporal 2013 → 2014",
                 color=COR["hgb"], fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGS / "fig_oulad_roc_pr.png", facecolor="white")
    plt.close(fig)


def main() -> None:
    res: dict = {"gerado_em": time.strftime("%Y-%m-%d %H:%M"), "ambiente": {}}
    import sklearn
    res["ambiente"] = {"python": os.sys.version.split()[0], "sklearn": sklearn.__version__, "pandas": pd.__version__}
    cv = parte_a(res)
    parte_b(res)
    figura(cv, res)
    TEMPOS["total_treinar_oulad"] = round(time.time() - T0, 1)
    res["tempos_s"] = TEMPOS
    (AQUI / "metricas_oulad.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"metricas_oulad.json e figs/fig_oulad_roc_pr.png gravados; total {TEMPOS['total_treinar_oulad']}s")


if __name__ == "__main__":
    main()
