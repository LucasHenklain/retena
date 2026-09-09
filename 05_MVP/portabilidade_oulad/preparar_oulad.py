# -*- coding: utf-8 -*-
"""preparar_oulad.py — Portabilidade do método Retena para o OULAD (Open University, UK).

Reproduz, sobre um segundo dataset público, a construção da base aluno-semana do
Retena (`pipeline/02_features_semanais.py`): cortes a cada 7 dias, features de
comportamento usando apenas cliques com data <= t e rótulo `inativo_21d`
(zero cliques em (t, t+21]). Rótulo secundário administrativo: `evadiu_28d`
(date_unregistration em (t, t+28]).

Diferenças em relação ao Retena, impostas pelo OULAD:
- o tempo é relativo ao início de cada apresentação (dia 0), não calendário;
- não há hora do dia nem capítulo, então `share_noite`, `share_fim_semana`,
  `progresso` e `capitulo_*` não têm análogo;
- "quiz entregue" vira entrega de avaliação (studentAssessment).

Entrada: CSVs do OULAD descompactados fora da entrega (variável OULAD_RAW_DIR).
Saída : parquet no scratchpad (OULAD_WORK_DIR) + resumo_preparacao.txt nesta pasta.
Nenhum dado bruto é copiado para a entrega.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get(
    "OULAD_WORK_DIR",
    r"C:\Users\lmhsilva\AppData\Local\Temp\claude\C--Users-lmhsilva-Projetos-StartupOne"
    r"\f6a65157-5d50-471e-86f3-c1f77a65cee8\scratchpad\oulad",
))
RAW = Path(os.environ.get("OULAD_RAW_DIR", SCRATCH / "raw"))

HORIZONTE = 21          # dias do rótulo inativo_21d
JANELA_EVASAO = 28      # dias do rótulo evadiu_28d
PRIMEIRO_CORTE = 28     # primeiro corte t (dias após o início da apresentação)
PASSO = 7               # cortes semanais
RECENCIA_NUNCA = 999    # mesmo sentinela do Retena (não ocorre após o filtro >= 1 clique)

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def ler_dados():
    """Lê os 7 CSVs com dtypes enxutos. O espelho UCI usa '?' como ausente."""
    courses = pd.read_csv(RAW / "courses.csv")
    reg = pd.read_csv(RAW / "studentRegistration.csv", na_values=["?"],
                      dtype={"id_student": "int32", "date_registration": "float32",
                             "date_unregistration": "float32"})
    info = pd.read_csv(RAW / "studentInfo.csv", na_values=["?"],
                       usecols=["code_module", "code_presentation", "id_student", "final_result"],
                       dtype={"id_student": "int32"})
    assess = pd.read_csv(RAW / "assessments.csv", na_values=["?"],
                         dtype={"id_assessment": "int32", "date": "float32"})
    sa = pd.read_csv(RAW / "studentAssessment.csv", na_values=["?"],
                     dtype={"id_assessment": "int32", "id_student": "int32",
                            "date_submitted": "float32", "is_banked": "int8", "score": "float32"})
    log("tabelas pequenas lidas")
    vle = pd.read_csv(
        RAW / "studentVle.csv",
        usecols=["code_module", "code_presentation", "id_student", "date", "sum_click"],
        dtype={"code_module": "category", "code_presentation": "category",
               "id_student": "int32", "date": "int16", "sum_click": "int32"},
    )
    log(f"studentVle lido: {len(vle):,} linhas, {vle.memory_usage(deep=True).sum() / 1e6:.0f} MB em memória")
    return courses, reg, info, assess, sa, vle


def agregar_dia(vle: pd.DataFrame) -> pd.DataFrame:
    dia = (vle.groupby(["code_module", "code_presentation", "id_student", "date"],
                       observed=True, sort=False)["sum_click"].sum().reset_index())
    dia["sum_click"] = dia["sum_click"].astype("int32")
    log(f"agregado aluno x módulo x apresentação x dia: {len(dia):,} linhas")
    return dia


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    courses, reg, info, assess, sa, vle = ler_dados()
    dia = agregar_dia(vle)
    del vle
    dia.to_parquet(SCRATCH / "oulad_cliques_dia.parquet", index=False)

    # --- índice de matrículas (aluno x módulo x apresentação) -------------------------
    chaves = ["code_module", "code_presentation", "id_student"]
    reg = reg.drop_duplicates(chaves).reset_index(drop=True)
    reg["rid"] = np.arange(len(reg), dtype=np.int32)
    reg = reg.merge(info, on=chaves, how="left")
    n_reg = len(reg)

    dia = dia.astype({"code_module": "object", "code_presentation": "object"})
    dia = dia.merge(reg[chaves + ["rid"]], on=chaves, how="left")
    sem_matricula = int(dia["rid"].isna().sum())
    dia = dia.dropna(subset=["rid"])
    dia["rid"] = dia["rid"].astype("int32")

    # --- entregas de avaliação (studentAssessment -> apresentação via assessments) -----
    sub = sa.dropna(subset=["date_submitted"]).merge(
        assess[["id_assessment", "code_module", "code_presentation"]], on="id_assessment", how="inner")
    sub = sub.merge(reg[chaves + ["rid"]], on=chaves, how="inner")
    sub["date_submitted"] = sub["date_submitted"].astype("int32")

    # --- eixo de dias: índice j = dia + off -------------------------------------------
    # entregas após o fim da apresentação + 28 nunca entram em nenhum corte: descartadas para poupar memória
    dmin = int(min(dia["date"].min(), sub["date_submitted"].min(), -30))
    dmax = int(max(dia["date"].max(), courses["module_presentation_length"].max() + JANELA_EVASAO))
    n_sub_tardias = int((sub["date_submitted"] > dmax).sum())
    sub = sub[sub["date_submitted"] <= dmax]
    off = -dmin
    n_dias = dmax - dmin + 1
    log(f"entregas com data > {dmax} ignoradas: {n_sub_tardias}")
    log(f"matrículas: {n_reg:,}; dias {dmin}..{dmax} ({n_dias}); cliques sem matrícula descartados: {sem_matricula}")

    C = np.zeros((n_reg, n_dias), dtype=np.int32)
    C[dia["rid"].to_numpy(), dia["date"].to_numpy().astype(np.int32) + off] = dia["sum_click"].to_numpy()
    A = (C > 0).astype(np.int8)
    S = np.zeros((n_reg, n_dias), dtype=np.int16)
    np.add.at(S, (sub["rid"].to_numpy(), sub["date_submitted"].to_numpy() + off), 1)

    # acumulados com coluna zero à esquerda: soma em dias (a, b] = cum[:, b+off+1] - cum[:, a+off+1]
    def cum(m):
        out = np.zeros((n_reg, n_dias + 1), dtype=np.int64)
        np.cumsum(m, axis=1, out=out[:, 1:])
        return out

    cumC, cumA, cumS = cum(C), cum(A), cum(S)
    del S

    def soma(cm, a, b):
        return cm[:, b + off + 1] - cm[:, a + off + 1]

    # último dia ativo até cada j (−1 = nunca) e primeiro dia ativo
    idx = np.where(A > 0, np.arange(n_dias, dtype=np.int32)[None, :], np.int32(-1))
    ultimo = np.maximum.accumulate(idx, axis=1)
    del idx
    primeiro = np.where(A.any(axis=1), A.argmax(axis=1), -1).astype(np.int32)
    del A, C
    log(f"matrizes prontas ({cumC.nbytes * 3 / 1e6:.0f} MB de acumulados)")

    date_reg = reg["date_registration"].to_numpy()
    date_unreg = reg["date_unregistration"].to_numpy()
    mod_arr = reg["code_module"].to_numpy()
    pres_arr = reg["code_presentation"].to_numpy()

    partes = []
    n_excl_reg = n_excl_click = 0
    for mod, pres, L in courses[["code_module", "code_presentation", "module_presentation_length"]].itertuples(index=False):
        rids_p = np.where((mod_arr == mod) & (pres_arr == pres))[0]
        for t in range(PRIMEIRO_CORTE, int(L) - HORIZONTE + 1, PASSO):
            j = t + off
            dr, du = date_reg[rids_p], date_unreg[rids_p]
            reg_ok = (np.isnan(dr) | (dr <= t)) & (np.isnan(du) | (du > t))
            clicou = cumC[rids_p, j + 1] > 0
            n_excl_reg += int((~reg_ok).sum())
            n_excl_click += int((reg_ok & ~clicou).sum())
            r = rids_p[reg_ok & clicou]
            if len(r) == 0:
                continue
            c7, c14, c28 = soma(cumC[r], t - 7, t), soma(cumC[r], t - 14, t), soma(cumC[r], t - 28, t)
            sem8 = np.zeros(len(r), dtype=np.int8)
            for k in range(8):
                sem8 += (soma(cumA[r], t - 7 * (k + 1), t - 7 * k) > 0)
            du_r = date_unreg[r]
            partes.append(pd.DataFrame({
                "code_module": mod, "code_presentation": pres,
                "id_student": reg["id_student"].to_numpy()[r], "dia_corte": np.int16(t),
                "cliques_7d": c7.astype("int32"), "cliques_14d": c14.astype("int32"), "cliques_28d": c28.astype("int32"),
                "dias_ativos_7d": soma(cumA[r], t - 7, t).astype("int8"),
                "dias_ativos_14d": soma(cumA[r], t - 14, t).astype("int8"),
                "dias_ativos_28d": soma(cumA[r], t - 28, t).astype("int8"),
                "recencia_dias": np.where(ultimo[r, j] >= 0, j - ultimo[r, j], RECENCIA_NUNCA).astype("int16"),
                "cliques_acumulados": cumC[r, j + 1].astype("int32"),
                "dias_ativos_acumulados": cumA[r, j + 1].astype("int16"),
                "tendencia": (c7 / (c28 / 4.0 + 1.0)).astype("float32"),
                "semanas_ativas_ultimas_8": sem8,
                "entregas_ate_t": cumS[r, j + 1].astype("int16"),
                "entregas_28d": soma(cumS[r], t - 28, t).astype("int16"),
                "semanas_desde_primeiro_clique": ((j - primeiro[r]) // 7).astype("int16"),
                "dias_desde_registro": np.where(np.isnan(date_reg[r]), -1, t - np.nan_to_num(date_reg[r])).astype("int16"),
                "inativo_21d": (soma(cumC[r], t, t + HORIZONTE) == 0).astype("int8"),
                "evadiu_28d": (~np.isnan(du_r) & (du_r > t) & (du_r <= t + JANELA_EVASAO)).astype("int8"),
                "final_result": reg["final_result"].to_numpy()[r],
            }))
    base = pd.concat(partes, ignore_index=True)
    for c in ("code_module", "code_presentation", "final_result"):
        base[c] = base[c].astype("category")
    log(f"base aluno-semana: {len(base):,} linhas")

    out = SCRATCH / "oulad_base_semanal.parquet"
    base.to_parquet(out, index=False)
    tam_mb = out.stat().st_size / 1e6

    # --- resumo em texto (vai para a entrega; o parquet não) -------------------------
    por_pres = (base.groupby(["code_presentation"], observed=True)
                .agg(linhas=("inativo_21d", "size"), alunos=("id_student", "nunique"),
                     cortes=("dia_corte", "nunique"), inativo_21d=("inativo_21d", "mean"),
                     evadiu_28d=("evadiu_28d", "mean")))
    por_mod = (base.groupby(["code_module", "code_presentation"], observed=True)
               .agg(linhas=("inativo_21d", "size"), alunos=("id_student", "nunique"),
                    cortes=("dia_corte", "nunique"), inativo_21d=("inativo_21d", "mean"),
                    evadiu_28d=("evadiu_28d", "mean")))
    por_corte = base.groupby("dia_corte").agg(linhas=("inativo_21d", "size"), inativo_21d=("inativo_21d", "mean"),
                                              evadiu_28d=("evadiu_28d", "mean"))
    acion = base["cliques_28d"] > 0
    dur = time.time() - T0
    linhas = [
        "RESUMO DA PREPARACAO — OULAD (método Retena)",
        f"Gerado por preparar_oulad.py em {time.strftime('%Y-%m-%d %H:%M')}; tempo total {dur:.0f}s",
        f"studentVle bruto: 10.655.280 linhas -> {len(dia):,} linhas aluno x apresentacao x dia (parquet oulad_cliques_dia.parquet)",
        f"Matriculas (studentRegistration): {n_reg:,}; cliques sem matricula descartados: {sem_matricula}",
        f"Cortes: t = {PRIMEIRO_CORTE}, {PRIMEIRO_CORTE + PASSO}, ... <= duracao - {HORIZONTE}, por apresentacao (22 apresentacoes, 7 modulos)",
        f"Filtro por corte: registro ativo em t (unregistration nula ou > t; registration <= t) E >= 1 clique ate t",
        f"  excluidos (aluno-corte): sem registro ativo {n_excl_reg:,}; registrado mas sem nenhum clique ate t {n_excl_click:,}",
        f"Base aluno-semana: {len(base):,} linhas, {base['id_student'].nunique():,} alunos distintos, "
        f"{base.groupby(chaves, observed=True).ngroups:,} matriculas, {base['dia_corte'].nunique()} valores de corte",
        f"Taxa global inativo_21d = {base['inativo_21d'].mean():.3%}; evadiu_28d = {base['evadiu_28d'].mean():.3%}",
        f"Subconjunto acionavel (cliques_28d > 0): {int(acion.sum()):,} linhas ({acion.mean():.1%}); "
        f"inativo_21d = {base.loc[acion, 'inativo_21d'].mean():.3%}; evadiu_28d = {base.loc[acion, 'evadiu_28d'].mean():.3%}",
        f"Parquet: {out.name} ({tam_mb:.1f} MB), {base.shape[1]} colunas",
        "",
        "Por apresentacao (taxa de positivos):",
        por_pres.to_string(float_format=lambda x: f"{x:.3f}"),
        "",
        "Por modulo x apresentacao:",
        por_mod.to_string(float_format=lambda x: f"{x:.3f}"),
        "",
        "Por dia de corte (todas as apresentacoes):",
        por_corte.to_string(float_format=lambda x: f"{x:.3f}"),
    ]
    (AQUI / "resumo_preparacao.txt").write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas[:12]))
    log("fim")


if __name__ == "__main__":
    main()
