# -*- coding: utf-8 -*-
"""
Etapa 05 — Figuras PNG (matplotlib) em `outputs/figs/`.

Todas as figuras têm 1600 px de largura (16 pol. × 100 dpi), fundo branco,
paleta da marca Retena e títulos em português. Os dados vêm exclusivamente
dos artefatos gerados nas etapas anteriores (kpis.json, metricas.json, CSVs);
nada é recalculado aqui.

Arquivos gerados:
  fig_funil_fases.png, fig_ativos_semana.png, fig_recencia.png, fig_roc_pr.png,
  fig_calibracao.png, fig_importancia.png, fig_atrito_heatmap.png, fig_faixas_risco.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    CAPITULOS_POR_FASE,
    DATA_REFERENCIA,
    DIR_FIGS,
    DIR_OUTPUTS,
    RAIZ_MVP,
    carregar_json,
    log,
)

DPI = 100
LARGURA = 16  # polegadas → 1600 px

# ---------------------------------------------------------------------------
# Marca Retena
# ---------------------------------------------------------------------------
COR = {
    "primaria": "#0B2545",
    "secundaria": "#13315C",
    "acento": "#2EC4B6",   # verde-sinal: ativo, baixo risco
    "alerta": "#FFB703",   # médio
    "critico": "#FF6B4A",  # alto risco (coral)
    "fundo": "#F6F7F9",
    "texto": "#0B2545",
    "texto_corrido": "#3A4A5C",
    "neutra": "#94A3B8",
    "grade": "#E3E8EF",
    "tinta_media": "#4F6D95",
    "tinta_clara": "#B8C7DB",
}
CORES_FAIXA = {"Alto": COR["critico"], "Médio": COR["alerta"], "Baixo": COR["acento"]}
DIR_FONTES = RAIZ_MVP.parent / "03_Marca" / "fontes"


def _registrar_fontes() -> tuple[str, str]:
    """Registra Sora (títulos) e Inter (texto) a partir de 03_Marca; cai para Segoe UI."""
    titulo, texto = "Segoe UI", "Segoe UI"
    for arq, nome in (("Sora-Variable.ttf", "Sora"), ("Inter-Variable.ttf", "Inter")):
        caminho = DIR_FONTES / arq
        if caminho.exists():
            try:
                font_manager.fontManager.addfont(str(caminho))
                if nome == "Sora":
                    titulo = "Sora"
                else:
                    texto = "Inter"
            except Exception as exc:  # pragma: no cover - fonte opcional
                log(f"  aviso: não foi possível registrar {arq}: {exc}")
    return titulo, texto


FONTE_TITULO, FONTE_TEXTO = _registrar_fontes()

plt.rcParams.update({
    "font.family": [FONTE_TEXTO, "Segoe UI", "DejaVu Sans", "sans-serif"],
    "font.size": 12,
    "text.color": COR["texto_corrido"],
    "axes.labelcolor": COR["texto_corrido"],
    "xtick.color": COR["texto_corrido"],
    "ytick.color": COR["texto_corrido"],
    "axes.titlesize": 16,
    "axes.titleweight": "semibold",
    "axes.titlecolor": COR["texto"],
    "axes.labelsize": 12,
    "axes.edgecolor": COR["grade"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": COR["grade"],
    "grid.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "legend.frameon": False,
})


def _titulo(ax, txt: str, **kw) -> None:
    # Lista de famílias: o matplotlib usa a próxima quando falta um glifo (ex.: "→" não existe na Sora).
    ax.set_title(txt, fontfamily=[FONTE_TITULO, FONTE_TEXTO, "Segoe UI", "DejaVu Sans"], loc="left", pad=14, **kw)


def _rodape(fig, txt: str) -> None:
    fig.text(0.01, 0.012, txt, fontsize=10, color=COR["neutra"])


def _salvar(fig, nome: str) -> None:
    caminho = DIR_FIGS / nome
    fig.savefig(caminho, dpi=DPI, bbox_inches=None)
    plt.close(fig)
    log(f"  figura salva: {caminho.name}")


def _pt(v: float, casas: int = 1) -> str:
    """Formata número em pt-BR (vírgula decimal)."""
    return f"{v:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------------------
def fig_funil(kpis: dict) -> None:
    funil = kpis["funil_fases"]
    concl = {c["fase"]: c for c in kpis["conclusao_por_fase"]}
    fig, ax = plt.subplots(figsize=(LARGURA, 7), dpi=DPI)
    x = np.arange(len(funil))
    vals = [f["alunos_ativos"] for f in funil]
    cores = [COR["tinta_clara"] if f["em_andamento"] else COR["primaria"] for f in funil]
    barras = ax.bar(x, vals, color=cores, width=0.62, zorder=3)
    for b, f in zip(barras, funil):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3,
                f"{f['alunos_ativos']} alunos\n{f['pct_dos_ingressantes_f1']:.0%} dos ingressantes",
                ha="center", va="bottom", fontsize=11, color=COR["texto"])
        tc = concl[f["fase"]]["taxa_conclusao"]
        cor_txt = COR["texto"] if f["em_andamento"] else "white"
        ax.text(b.get_x() + b.get_width() / 2, 8, f"chegaram ao\núltimo cap.: {tc:.0%}",
                ha="center", va="bottom", fontsize=10, color=cor_txt)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Fase {f['fase']}" + ("\n(em andamento)" if f["em_andamento"] else "") for f in funil])
    ax.set_ylabel("Alunos com atividade na fase")
    ax.set_ylim(0, max(vals) * 1.28)
    _titulo(ax, "Funil de alunos por fase (F1 → F5) — IES Demo")
    ax.grid(axis="x", visible=False)
    _rodape(fig, f"Alunos com ≥ 1 ação própria no LMS em cada fase. Dados até {DATA_REFERENCIA:%d/%m/%Y}. "
                 "A Fase 5 ainda está em andamento, por isso a taxa de chegada ao último capítulo é baixa.")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.15)
    _salvar(fig, "fig_funil_fases.png")


def fig_ativos_semana(kpis: dict) -> None:
    curva = pd.DataFrame(kpis["curva_semanal_ativos"])
    curva["semana_fim"] = pd.to_datetime(curva["semana_fim"])
    curva = curva[curva["semana_fim"] >= "2026-02-01"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(LARGURA, 6.5), dpi=DPI)
    ax.fill_between(curva["semana_fim"], curva["alunos_ativos"], color=COR["acento"], alpha=0.16, zorder=2)
    ax.plot(curva["semana_fim"], curva["alunos_ativos"], color=COR["primaria"], lw=2.2, marker="o", ms=5, zorder=3)
    # Última semana completa e a parcial.
    ult = curva.iloc[-2]
    ax.annotate(f"{int(ult['alunos_ativos'])} alunos ativos\n(semana até {ult['semana_fim']:%d/%m})",
                xy=(ult["semana_fim"], ult["alunos_ativos"]), xytext=(-110, 28), textcoords="offset points",
                fontsize=10.5, color=COR["texto"], arrowprops=dict(arrowstyle="-", color=COR["neutra"]))
    parcial = curva.iloc[-1]
    ax.scatter([parcial["semana_fim"]], [parcial["alunos_ativos"]], facecolor="white", edgecolor=COR["primaria"],
               s=70, zorder=4, linewidths=2)
    ax.text(parcial["semana_fim"], parcial["alunos_ativos"] - 9, "semana\nparcial", ha="center", va="top",
            fontsize=9.5, color=COR["neutra"])
    # Marca o intervalo entre F4 e F5.
    ax.axvspan(pd.Timestamp("2026-07-05"), pd.Timestamp("2026-08-02"), color=COR["fundo"], zorder=1)
    ax.text(pd.Timestamp("2026-07-19"), curva["alunos_ativos"].max() * 1.1, "intervalo F4 → F5",
            ha="center", fontsize=10, color=COR["neutra"])
    ax.set_ylabel("Alunos distintos com atividade na semana")
    _titulo(ax, "Alunos ativos por semana (semanas terminando no domingo)")
    ax.set_ylim(0, curva["alunos_ativos"].max() * 1.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=6, interval=2))
    ax.grid(axis="x", visible=False)
    _rodape(fig, "Atividade = ação do próprio aluno (origem web, evento não administrativo). "
                 "A queda de julho coincide com o intervalo entre a Fase 4 e a Fase 5.")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.15)
    _salvar(fig, "fig_ativos_semana.png")


def fig_recencia(kpis: dict) -> None:
    dist = kpis["distribuicao_recencia"]
    ordem = ["0-7", "8-14", "15-30", "31-60", ">60"]
    rotulos = ["0–7 dias", "8–14 dias", "15–30 dias", "31–60 dias", "> 60 dias"]
    vals = [int(dist[k]) for k in ordem]
    total = sum(vals)
    cores = [COR["acento"], COR["acento"], COR["alerta"], COR["critico"], COR["critico"]]
    alphas = [1.0, 0.65, 1.0, 0.7, 1.0]
    fig, ax = plt.subplots(figsize=(LARGURA, 6.5), dpi=DPI)
    b = ax.bar(rotulos, vals, color=cores, zorder=3, width=0.66)
    for r_, a in zip(b, alphas):
        r_.set_alpha(a)
    for r_, v in zip(b, vals):
        ax.text(r_.get_x() + r_.get_width() / 2, v + 1.5, f"{v} alunos\n({v / total:.0%})",
                ha="center", va="bottom", fontsize=11, color=COR["texto"])
    ax.set_ylim(0, max(vals) * 1.3)
    ax.set_ylabel("Nº de alunos")
    ax.set_xlabel(f"Dias desde o último acesso (referência {DATA_REFERENCIA:%d/%m/%Y})")
    ax.grid(axis="x", visible=False)
    _titulo(ax, f"Recência de acesso — {total} alunos com atividade · mediana {_pt(kpis['recencia_mediana_dias'], 0)} dias")
    # Linha separando "presentes" (≤ 14 d) de "sumidos".
    ax.axvline(1.5, color=COR["neutra"], ls="--", lw=1.2, zorder=2)
    ax.text(1.5, max(vals) * 1.22, f"  ≤ 14 dias: {vals[0] + vals[1]} alunos    |    > 14 dias: {sum(vals[2:])} alunos "
            f"({kpis['pct_inativos_14d']:.0%})", ha="center", fontsize=10.5, color=COR["texto_corrido"])
    _rodape(fig, "Verde = presença recente; amarelo = zona de atenção (15–30 dias); coral = provavelmente desligado. "
                 "Recência é uma das 4 features mais importantes do modelo.")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.16)
    _salvar(fig, "fig_recencia.png")


def fig_roc_pr(met: dict) -> None:
    h, l = met["hgb"], met["logistica"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(LARGURA, 7), dpi=DPI)
    ax1.plot(h["curva_roc"]["fpr"], h["curva_roc"]["tpr"], color=COR["primaria"], lw=2.4,
             label=f"Gradient Boosting (AUC = {_pt(h['auc_roc'], 3)})")
    ax1.plot(l["curva_roc"]["fpr"], l["curva_roc"]["tpr"], color=COR["neutra"], lw=2, ls="--",
             label=f"Regressão logística (AUC = {_pt(l['auc_roc'], 3)})")
    ax1.plot([0, 1], [0, 1], color=COR["grade"], lw=1.2)
    ax1.set_xlabel("Taxa de falsos positivos")
    ax1.set_ylabel("Taxa de verdadeiros positivos")
    _titulo(ax1, "Curva ROC — teste temporal (jun–ago/2026)")
    ax1.legend(loc="lower right")
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1.02)

    ax2.plot(h["curva_pr"]["recall"], h["curva_pr"]["precisao"], color=COR["primaria"], lw=2.4,
             label=f"Gradient Boosting (AUC-PR = {_pt(h['auc_pr'], 3)})")
    ax2.plot(l["curva_pr"]["recall"], l["curva_pr"]["precisao"], color=COR["neutra"], lw=2, ls="--",
             label=f"Regressão logística (AUC-PR = {_pt(l['auc_pr'], 3)})")
    ax2.axhline(h["taxa_positivos"], color=COR["grade"], lw=1.2)
    ax2.text(0.01, h["taxa_positivos"] + 0.015, f"taxa de positivos = {_pt(h['taxa_positivos'] * 100)} %",
             fontsize=10, color=COR["neutra"])
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precisão")
    _titulo(ax2, "Curva Precisão–Recall — teste temporal")
    ax2.legend(loc="lower left")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1.02)
    _rodape(fig, f"n teste = {h['n']:,} linhas aluno-semana; positivos = {h['positivos']}. "
                 "Rótulo: 21 dias sem atividade após o corte.".replace(",", "."))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.14, wspace=0.2)
    _salvar(fig, "fig_roc_pr.png")


def fig_calibracao(met: dict) -> None:
    h = met["hgb"]
    cal = pd.DataFrame(h["calibracao"])
    fig, ax = plt.subplots(figsize=(LARGURA, 7), dpi=DPI)
    ax.plot([0, 1], [0, 1], color=COR["neutra"], lw=1.4, ls="--", label="Calibração perfeita")
    tam = 60 + 700 * cal["n"] / cal["n"].max()
    ax.scatter(cal["prob_media_prevista"], cal["taxa_observada"], s=tam, color=COR["primaria"], alpha=0.85,
               zorder=3, label="Bins de 0,1 (tamanho ∝ nº de linhas)", edgecolor="white", linewidths=1.5)
    ax.plot(cal["prob_media_prevista"], cal["taxa_observada"], color=COR["primaria"], lw=1.4, zorder=2)
    for _, r in cal.iterrows():
        ax.annotate(f"n={int(r['n'])}", (r["prob_media_prevista"], r["taxa_observada"]), xytext=(10, -14),
                    textcoords="offset points", fontsize=9.5, color=COR["neutra"])
    ax.set_xlabel("Probabilidade média prevista no bin")
    ax.set_ylabel("Taxa observada de inatividade em 21 dias")
    _titulo(ax, f"Curva de calibração — Gradient Boosting (teste, Brier = {_pt(h['brier'], 3)})")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.legend(loc="upper left")
    _rodape(fig, "Acima da diagonal = o modelo subestima o risco; abaixo = superestima. "
                 "O teste tem taxa de positivos maior que o treino (28,8 % vs. 10,1 %), o que empurra os bins para cima.")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.14)
    _salvar(fig, "fig_calibracao.png")


NOMES_FEATURES = {
    "dias_ativos_acumulados": "Dias ativos acumulados",
    "dias_ativos_28d": "Dias ativos (28 d)",
    "dias_ativos_14d": "Dias ativos (14 d)",
    "dias_ativos_7d": "Dias ativos (7 d)",
    "eventos_acumulados": "Eventos acumulados",
    "eventos_28d": "Eventos (28 d)",
    "eventos_14d": "Eventos (14 d)",
    "eventos_7d": "Eventos (7 d)",
    "recencia_dias": "Recência (dias sem acesso)",
    "share_noite_28d": "% eventos à noite (28 d)",
    "share_fim_semana_28d": "% eventos no fim de semana (28 d)",
    "capitulo_max_fase_atual": "Capítulo máximo na fase atual",
    "pct_capitulos_fase_atual": "% capítulos da fase atual",
    "progresso_28d": "Eventos de progresso (28 d)",
    "semanas_ativas_ultimas_8": "Semanas ativas (últimas 8)",
    "quiz_iniciados_28d": "Questionários iniciados (28 d)",
    "quiz_entregues_28d": "Questionários entregues (28 d)",
    "entregas_28d": "Entregas de tarefa (28 d)",
    "tendencia": "Tendência (7 d vs. média 28 d)",
    "capitulos_distintos_28d": "Capítulos distintos (28 d)",
    "fase_atual": "Fase atual",
    "semanas_desde_primeiro_evento": "Semanas desde o 1º acesso",
}


def fig_importancia(met: dict) -> None:
    imp = pd.DataFrame(met["importancia_permutacao_top12"]).iloc[::-1]
    fig, ax = plt.subplots(figsize=(LARGURA, 7), dpi=DPI)
    nomes = [NOMES_FEATURES.get(f, f) for f in imp["feature"]]
    ax.barh(nomes, imp["importancia_media"], xerr=imp["importancia_dp"], color=COR["secundaria"],
            ecolor=COR["neutra"], capsize=3, zorder=3, height=0.62)
    for i, (v, dp) in enumerate(zip(imp["importancia_media"], imp["importancia_dp"])):
        ax.text(v + dp + 0.0006, i, _pt(v, 4), va="center", fontsize=10, color=COR["texto_corrido"])
    ax.set_xlabel("Queda média na AUC-ROC ao permutar a feature (teste, 15 repetições)")
    _titulo(ax, "Importância por permutação — 12 features mais relevantes")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, (imp["importancia_media"] + imp["importancia_dp"]).max() * 1.18)
    _rodape(fig, "Quanto o modelo perde de AUC quando a feature é embaralhada. Volume acumulado de atividade e presença "
                 "nos últimos 28 dias dominam; recência vem em seguida.")
    fig.subplots_adjust(left=0.24, right=0.97, top=0.88, bottom=0.12)
    _salvar(fig, "fig_importancia.png")


def fig_mapa_atrito(at: pd.DataFrame) -> None:
    fases = sorted(at["fase"].unique())
    max_cap = max(CAPITULOS_POR_FASE.values())
    mat = np.full((len(fases), max_cap), np.nan)
    queda = np.full((len(fases), max_cap), np.nan)
    for _, r in at.iterrows():
        i, j = fases.index(r["fase"]), int(r["capitulo"]) - 1
        mat[i, j] = r["indice_atrito"]
        queda[i, j] = r["taxa_queda"]
    # Rampa sequencial de um só matiz (coral), do fundo claro ao coral escuro.
    cmap = LinearSegmentedColormap.from_list("atrito", ["#FFF4F0", "#FFB59F", COR["critico"], "#A83A1E"])
    vmax = 0.10  # truncado: a Fase 5 (em andamento) tem valores altos por progresso em curso, não abandono
    fig, ax = plt.subplots(figsize=(LARGURA, 6.4), dpi=DPI)
    im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(max_cap))
    ax.set_xticklabels([f"Cap {c}" for c in range(1, max_cap + 1)])
    ax.set_yticks(range(len(fases)))
    ax.set_yticklabels([f"Fase {f}" + ("\n(em andamento)" if f == 5 else "") for f in fases])
    ax.grid(False)
    # Linhas brancas separando células.
    for k in range(max_cap + 1):
        ax.axvline(k - 0.5, color="white", lw=2)
    for k in range(len(fases) + 1):
        ax.axhline(k - 0.5, color="white", lw=2)
    for i in range(len(fases)):
        for j in range(max_cap):
            if j >= CAPITULOS_POR_FASE[fases[i]]:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color="white", hatch="///",
                                           ec=COR["grade"], lw=0))
                continue
            v, q = mat[i, j], queda[i, j]
            txt = "último\ncap." if np.isnan(q) else f"{_pt(q * 100)} %\n({_pt(v, 2)})"
            cor_txt = "white" if (not np.isnan(v) and v > vmax * 0.55) else COR["texto"]
            ax.text(j, i, txt, ha="center", va="center", fontsize=9.5, color=cor_txt)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, extend="max")
    cb.set_label("Índice de atrito = taxa de queda × esforço relativo (escala truncada em 0,10)")
    cb.outline.set_visible(False)
    _titulo(ax, "Mapa de atrito de conteúdo por fase × capítulo — célula: taxa de queda para o capítulo seguinte (índice)")
    _rodape(fig, "Taxa de queda = % dos alunos que chegaram ao capítulo e não avançaram ao seguinte. Esforço relativo = mediana de "
                 "eventos no capítulo ÷ mediana da fase. Na Fase 5 a queda reflete progresso em curso, não abandono.")
    fig.subplots_adjust(left=0.10, right=0.98, top=0.88, bottom=0.15)
    _salvar(fig, "fig_atrito_heatmap.png")


def fig_faixas_risco(risco: pd.DataFrame) -> None:
    ordem = ["Alto", "Médio", "Baixo"]
    sit = ["Ativo (28d)", "Inativo 29–60d", "Inativo >60d"]
    cores_sit = [COR["primaria"], COR["tinta_media"], COR["tinta_clara"]]
    tab = pd.crosstab(risco["faixa"], risco["situacao"]).reindex(index=ordem, columns=sit, fill_value=0)
    corte = pd.Timestamp(risco["corte"].iloc[0])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(LARGURA, 6.5), dpi=DPI, gridspec_kw={"width_ratios": [1, 1.4]})
    tot = tab.sum(axis=1)
    b = ax1.bar(ordem, tot, color=[CORES_FAIXA[f] for f in ordem], zorder=3, width=0.65)
    for r_, v in zip(b, tot):
        ax1.text(r_.get_x() + r_.get_width() / 2, v + 2, f"{v} alunos\n({v / tot.sum():.0%})", ha="center",
                 va="bottom", fontsize=11, color=COR["texto"])
    ax1.set_ylim(0, tot.max() * 1.3)
    ax1.set_ylabel("Nº de alunos")
    ax1.grid(axis="x", visible=False)
    _titulo(ax1, f"Alunos por faixa de risco (corte {corte:%d/%m/%Y})")
    base = np.zeros(len(ordem))
    for s, c in zip(sit, cores_sit):
        ax2.bar(ordem, tab[s], bottom=base, color=c, label=s.replace("(28d)", "(28 d)"), zorder=3, width=0.65,
                edgecolor="white", linewidth=2)
        for i, v in enumerate(tab[s]):
            if v > 0:
                ax2.text(i, base[i] + v / 2, str(int(v)), ha="center", va="center",
                         color="white" if c != COR["tinta_clara"] else COR["texto"], fontsize=10.5)
        base += tab[s].values
    _titulo(ax2, "Composição de cada faixa por situação de acesso")
    ax2.legend(loc="upper left", title="Situação")
    ax2.grid(axis="x", visible=False)
    ax2.set_ylim(0, tot.max() * 1.3)
    _rodape(fig, "Alto ≥ 0,60 · Médio 0,30–0,60 · Baixo < 0,30 (probabilidade de 21 dias sem atividade). "
                 "Alunos de alto risco ainda ativos nos últimos 28 dias são quem chamar primeiro.")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.14, wspace=0.18)
    _salvar(fig, "fig_faixas_risco.png")


def main() -> None:
    log("Gerando figuras...")
    log(f"  fontes: títulos={FONTE_TITULO}, texto={FONTE_TEXTO}")
    kpis = carregar_json(DIR_OUTPUTS / "kpis.json")
    metricas = carregar_json(DIR_OUTPUTS / "metricas.json")["modelo_principal"]
    at = pd.read_csv(DIR_OUTPUTS / "atrito_conteudo.csv")
    risco = pd.read_csv(DIR_OUTPUTS / "risco_alunos_atual.csv")

    fig_funil(kpis)
    fig_ativos_semana(kpis)
    fig_recencia(kpis)
    fig_roc_pr(metricas)
    fig_calibracao(metricas)
    fig_importancia(metricas)
    fig_mapa_atrito(at)
    fig_faixas_risco(risco)
    log(f"Figuras em {DIR_FIGS}")


if __name__ == "__main__":
    main()
