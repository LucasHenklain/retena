# -*- coding: utf-8 -*-
"""
Etapa 06 — Dashboard HTML autocontido em `dashboard/index.html`.

Um único arquivo, sem CDN: CSS e JS inline, gráficos SVG gerados aqui em
Python e dados embutidos como JSON em <script type="application/json">.
Abre por duplo clique (file://). Logo e fontes vêm de ../../03_Marca (paths
relativos), com fallback para "Segoe UI" quando o navegador bloquear fontes
locais.

Fontes de dados (somente leitura): kpis.json, metricas.json,
risco_alunos_atual.csv, atrito_conteudo.csv, recomendacoes_conteudo.csv.
"""
from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    CAPITULOS_POR_FASE,
    DIR_DASHBOARD,
    DIR_OUTPUTS,
    LIMIAR_ALTO,
    LIMIAR_MEDIO,
    carregar_json,
    log,
)

# ---------------------------------------------------------------------------
# Marca
# ---------------------------------------------------------------------------
COR = {
    "primaria": "#0B2545",
    "secundaria": "#13315C",
    "acento": "#2EC4B6",
    "alerta": "#FFB703",
    "critico": "#FF6B4A",
    "fundo": "#F6F7F9",
    "texto": "#0B2545",
    "texto_corrido": "#3A4A5C",
    "neutra": "#94A3B8",
    "grade": "#E3E8EF",
    "tinta_media": "#4F6D95",
    "tinta_clara": "#B8C7DB",
}
CORES_FAIXA = {"Alto": COR["critico"], "Médio": COR["alerta"], "Baixo": COR["acento"]}
ORDEM_FAIXA = ["Alto", "Médio", "Baixo"]
SITUACOES = ["Ativo (28d)", "Inativo 29–60d", "Inativo >60d"]
LOGO_REL = "../../03_Marca/logo/retena_horizontal_claro_sobre_escuro.svg"
FONTE_SORA_REL = "../../03_Marca/fontes/Sora-Variable.ttf"
FONTE_INTER_REL = "../../03_Marca/fontes/Inter-Variable.ttf"

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


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def e(txt) -> str:
    """Escapa texto para HTML/SVG."""
    return html.escape("" if txt is None else str(txt), quote=True)


def pt(v: float, casas: int = 1) -> str:
    """Número em pt-BR (vírgula decimal)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:,.{casas}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def pct(v: float, casas: int = 1) -> str:
    return pt(v * 100, casas) + "%"


def data_br(s) -> str:
    return pd.Timestamp(s).strftime("%d/%m/%Y")


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def cor_rampa(t: float, stops=("#FFF4F0", "#FFB59F", "#FF6B4A", "#A83A1E")) -> str:
    """Rampa sequencial de um só matiz (coral) para o heatmap de atrito."""
    t = min(max(t, 0.0), 1.0)
    n = len(stops) - 1
    pos = t * n
    i = min(int(pos), n - 1)
    f = pos - i
    a, b = _hex_rgb(stops[i]), _hex_rgb(stops[i + 1])
    rgb = tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))
    return "#%02X%02X%02X" % rgb


def _nice_max(v: float, passo: float) -> float:
    return math.ceil(v / passo) * passo


# ---------------------------------------------------------------------------
# SVGs
# ---------------------------------------------------------------------------
def svg_ativos_semana(curva: list[dict]) -> str:
    df = pd.DataFrame(curva)
    df["semana_fim"] = pd.to_datetime(df["semana_fim"])
    df = df[df["semana_fim"] >= "2026-02-01"].reset_index(drop=True)
    W, H = 980, 300
    ml, mr, mt, mb = 46, 18, 26, 40
    pw, ph = W - ml - mr, H - mt - mb
    n = len(df)
    ymax = _nice_max(df["alunos_ativos"].max() * 1.12, 20)

    def X(i):
        return ml + pw * i / (n - 1)

    def Y(v):
        return mt + ph * (1 - v / ymax)

    out = [f'<svg class="grafico" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Alunos ativos por semana" xmlns="http://www.w3.org/2000/svg">']
    # Intervalo F4 -> F5
    i0 = int(df.index[df["semana_fim"] == "2026-07-05"][0])
    i1 = int(df.index[df["semana_fim"] == "2026-08-02"][0])
    out.append(f'<rect x="{X(i0):.1f}" y="{mt}" width="{X(i1) - X(i0):.1f}" height="{ph}" fill="{COR["fundo"]}"/>')
    out.append(f'<text x="{(X(i0) + X(i1)) / 2:.1f}" y="{mt + 14}" text-anchor="middle" class="svg-nota">intervalo F4 → F5</text>')
    # Grade + eixo Y
    ticks = int(ymax / 20)
    for k in range(ticks + 1):
        v = k * 20
        y = Y(v)
        out.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W - mr}" y2="{y:.1f}" class="svg-grade"/>')
        out.append(f'<text x="{ml - 8}" y="{y + 4:.1f}" text-anchor="end" class="svg-tick">{v}</text>')
    # Área + linha (última semana é parcial: linha tracejada até ela)
    pts_full = [(X(i), Y(v)) for i, v in enumerate(df["alunos_ativos"])]
    area = f"M{pts_full[0][0]:.1f},{Y(0):.1f} " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts_full[:-1]) + \
        f" L{pts_full[-2][0]:.1f},{Y(0):.1f} Z"
    out.append(f'<path d="{area}" fill="{COR["acento"]}" fill-opacity="0.16"/>')
    linha = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts_full[:-1])
    out.append(f'<path d="{linha}" fill="none" stroke="{COR["primaria"]}" stroke-width="2.2" stroke-linejoin="round"/>')
    (xa, ya), (xb, yb) = pts_full[-2], pts_full[-1]
    out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{COR["primaria"]}" '
               f'stroke-width="2" stroke-dasharray="4 4"/>')
    # Pontos com tooltip
    for i, r in df.iterrows():
        x, y = X(i), Y(r["alunos_ativos"])
        parcial = i == n - 1
        fill = "white" if parcial else COR["primaria"]
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if parcial else 3.5}" fill="{fill}" '
                   f'stroke="{COR["primaria"]}" stroke-width="2">'
                   f'<title>Semana até {r["semana_fim"]:%d/%m/%Y}{" (parcial)" if parcial else ""}\n'
                   f'{int(r["alunos_ativos"])} alunos ativos · {int(r["eventos"]):,} eventos</title></circle>'.replace(",", "."))
        # alvo de hover maior que o ponto
        out.append(f'<rect x="{x - pw / n / 2:.1f}" y="{mt}" width="{pw / n:.1f}" height="{ph}" fill="transparent">'
                   f'<title>Semana até {r["semana_fim"]:%d/%m/%Y}{" (parcial)" if parcial else ""}\n'
                   f'{int(r["alunos_ativos"])} alunos ativos · {int(r["eventos"]):,} eventos</title></rect>'.replace(",", "."))
    # Rótulos diretos: último completo e parcial
    ult = df.iloc[-2]
    out.append(f'<text x="{X(n - 2) - 8:.1f}" y="{Y(ult["alunos_ativos"]) - 12:.1f}" text-anchor="end" class="svg-rotulo">'
               f'{int(ult["alunos_ativos"])} ativos (até {ult["semana_fim"]:%d/%m})</text>')
    out.append(f'<text x="{X(n - 1):.1f}" y="{Y(df.iloc[-1]["alunos_ativos"]) + 22:.1f}" text-anchor="middle" class="svg-nota">parcial</text>')
    # Eixo X
    for i in range(0, n, 3):
        out.append(f'<text x="{X(i):.1f}" y="{H - 14}" text-anchor="middle" class="svg-tick">{df.iloc[i]["semana_fim"]:%d/%m}</text>')
    out.append(f'<line x1="{ml}" y1="{Y(0):.1f}" x2="{W - mr}" y2="{Y(0):.1f}" class="svg-eixo"/>')
    out.append("</svg>")
    return "\n".join(out)


def svg_barras_faixas(risco: pd.DataFrame) -> str:
    tab = pd.crosstab(risco["faixa"], risco["situacao"]).reindex(index=ORDEM_FAIXA, columns=SITUACOES, fill_value=0)
    tot = tab.sum(axis=1)
    total = int(tot.sum())
    W, H = 700, 290
    ml, mr, mt = 78, 128, 20
    linha_h, barra_h = 64, 30
    pw = W - ml - mr
    vmax = float(tot.max())
    opac = [1.0, 0.62, 0.32]
    out = [f'<svg class="grafico" viewBox="0 0 {W} {H}" role="img" aria-label="Distribuição das faixas de risco" '
           f'xmlns="http://www.w3.org/2000/svg">']
    for i, faixa in enumerate(ORDEM_FAIXA):
        y = mt + i * linha_h
        cor = CORES_FAIXA[faixa]
        out.append(f'<text x="{ml - 14}" y="{y + barra_h / 2 + 5}" text-anchor="end" class="svg-rotulo-forte">{faixa}</text>')
        x = ml
        for s, o in zip(SITUACOES, opac):
            v = int(tab.loc[faixa, s])
            if v == 0:
                continue
            w = pw * v / vmax
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 1):.1f}" height="{barra_h}" rx="3" fill="{cor}" '
                       f'fill-opacity="{o}"><title>{faixa} · {s}: {v} alunos</title></rect>')
            if w > 26:
                cor_txt = "white" if (o == 1.0 and faixa != "Médio") else COR["texto"]
                out.append(f'<text x="{x + w / 2 - 1:.1f}" y="{y + barra_h / 2 + 4}" text-anchor="middle" '
                           f'class="svg-valor" fill="{cor_txt}">{v}</text>')
            x += w
        out.append(f'<text x="{ml + pw * tot[faixa] / vmax + 10:.1f}" y="{y + barra_h / 2 + 5}" class="svg-rotulo">'
                   f'{int(tot[faixa])} alunos · {pct(tot[faixa] / total, 0)}</text>')
        sub = {"Alto": f"prob. ≥ {pt(LIMIAR_ALTO, 2)}", "Médio": f"{pt(LIMIAR_MEDIO, 2)}–{pt(LIMIAR_ALTO, 2)}",
               "Baixo": f"prob. &lt; {pt(LIMIAR_MEDIO, 2)}"}[faixa]
        out.append(f'<text x="{ml - 14}" y="{y + barra_h / 2 + 20}" text-anchor="end" class="svg-nota">{sub}</text>')
    # Legenda de situação (opacidade)
    ly = mt + 3 * linha_h + 14
    lx = ml
    for s, o in zip(SITUACOES, opac):
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="14" height="14" rx="3" fill="{COR["primaria"]}" fill-opacity="{o}"/>')
        out.append(f'<text x="{lx + 20}" y="{ly + 1}" class="svg-tick">{s.replace("(28d)", "(28 d)")}</text>')
        lx += 140
    out.append(f'<text x="{W - 8}" y="{ly + 1}" text-anchor="end" class="svg-nota">{total} alunos avaliados</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_heatmap_atrito(at: pd.DataFrame) -> str:
    fases = sorted(at["fase"].unique())
    max_cap = max(CAPITULOS_POR_FASE.values())
    cw, ch = 74, 58
    ml, mt = 118, 28
    W = ml + cw * max_cap + 16
    H = mt + ch * len(fases) + 64
    VMAX = 0.10
    out = [f'<svg class="grafico" viewBox="0 0 {W} {H}" role="img" aria-label="Mapa de atrito fase × capítulo" '
           f'xmlns="http://www.w3.org/2000/svg">']
    for j in range(max_cap):
        out.append(f'<text x="{ml + j * cw + cw / 2}" y="{mt - 10}" text-anchor="middle" class="svg-tick">Cap {j + 1}</text>')
    idx = {(int(r.fase), int(r.capitulo)): r for r in at.itertuples(index=False)}
    for i, f in enumerate(fases):
        y = mt + i * ch
        andamento = bool(at.loc[at["fase"] == f, "fase_em_andamento"].iloc[0])
        out.append(f'<text x="{ml - 12}" y="{y + ch / 2 + (0 if andamento else 5)}" text-anchor="end" class="svg-rotulo-forte">Fase {f}</text>')
        if andamento:
            out.append(f'<text x="{ml - 12}" y="{y + ch / 2 + 16}" text-anchor="end" class="svg-nota">em andamento</text>')
        for j in range(max_cap):
            x = ml + j * cw
            cap = j + 1
            if cap > CAPITULOS_POR_FASE[f]:
                out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" rx="4" fill="none" '
                           f'stroke="{COR["grade"]}" stroke-dasharray="3 3"/>')
                continue
            r = idx.get((f, cap))
            if r is None:
                continue
            v = float(r.indice_atrito)
            fill = cor_rampa(v / VMAX)
            escuro = v / VMAX > 0.55
            cor_txt = "white" if escuro else COR["texto"]
            ultimo = pd.isna(r.taxa_queda)
            if ultimo:
                l1, l2 = "último", "cap."
                tip_queda = "Último capítulo da fase (sem capítulo seguinte para medir queda)."
            else:
                l1, l2 = pct(float(r.taxa_queda)), f"({pt(v, 2)})"
                tip_queda = (f"Queda para o próximo capítulo: {pct(float(r.taxa_queda))} "
                             f"({int(r.alunos_perdidos)} de {int(r.alunos_alcancaram)} alunos não avançaram)")
            tip = (f"Fase {f} · Cap {cap} — {r.titulo}\n{tip_queda}\n"
                   f"Esforço relativo: {pt(float(r.esforco_relativo), 2)}× a mediana da fase\n"
                   f"Índice de atrito: {pt(v, 3)}\nAlunos com eventos no capítulo: {int(r.alunos_com_eventos)}")
            out.append(f'<g class="celula"><rect x="{x + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" rx="4" fill="{fill}"/>'
                       f'<text x="{x + cw / 2}" y="{y + ch / 2 - 2}" text-anchor="middle" class="svg-valor" fill="{cor_txt}">{l1}</text>'
                       f'<text x="{x + cw / 2}" y="{y + ch / 2 + 14}" text-anchor="middle" class="svg-nota" fill="{cor_txt}" '
                       f'fill-opacity="0.85">{l2}</text><title>{e(tip)}</title></g>')
    # Legenda de escala
    ly = mt + ch * len(fases) + 22
    lw = 220
    out.append('<defs><linearGradient id="rampa-atrito" x1="0" x2="1" y1="0" y2="0">')
    for k in range(6):
        out.append(f'<stop offset="{k / 5:.2f}" stop-color="{cor_rampa(k / 5)}"/>')
    out.append("</linearGradient></defs>")
    out.append(f'<rect x="{ml}" y="{ly}" width="{lw}" height="12" rx="3" fill="url(#rampa-atrito)"/>')
    out.append(f'<text x="{ml}" y="{ly + 28}" class="svg-tick">0</text>')
    out.append(f'<text x="{ml + lw}" y="{ly + 28}" text-anchor="end" class="svg-tick">≥ 0,10</text>')
    out.append(f'<text x="{ml + lw + 16}" y="{ly + 11}" class="svg-nota">Índice de atrito = taxa de queda × esforço relativo. '
               f'Célula: % que não avançou (índice). Tracejado = capítulo inexistente.</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_barras_importancia(imp: list[dict]) -> str:
    W = 620
    linha_h = 30
    ml, mr, mt = 250, 70, 10
    H = mt + linha_h * len(imp) + 10
    pw = W - ml - mr
    vmax = max(r["importancia_media"] + r["importancia_dp"] for r in imp)
    out = [f'<svg class="grafico" viewBox="0 0 {W} {H}" role="img" aria-label="Importância das features" '
           f'xmlns="http://www.w3.org/2000/svg">']
    for i, r in enumerate(imp):
        y = mt + i * linha_h
        w = pw * r["importancia_media"] / vmax
        dp = pw * r["importancia_dp"] / vmax
        nome = NOMES_FEATURES.get(r["feature"], r["feature"])
        out.append(f'<text x="{ml - 10}" y="{y + 18}" text-anchor="end" class="svg-rotulo">{e(nome)}</text>')
        out.append(f'<rect x="{ml}" y="{y + 6}" width="{max(w, 1):.1f}" height="18" rx="3" fill="{COR["secundaria"]}">'
                   f'<title>{e(nome)} ({r["feature"]})\nQueda média de AUC-ROC: {pt(r["importancia_media"], 4)} '
                   f'± {pt(r["importancia_dp"], 4)}</title></rect>')
        out.append(f'<line x1="{ml + w - dp:.1f}" y1="{y + 15}" x2="{ml + w + dp:.1f}" y2="{y + 15}" stroke="{COR["neutra"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{ml + w + dp + 8:.1f}" y="{y + 19}" class="svg-tick">{pt(r["importancia_media"], 4)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_curva(series: list[tuple[str, list, list, str, str]], xlabel: str, ylabel: str, baseline: float | None,
              diagonal: bool, titulo: str) -> str:
    """Gráfico de linhas pequeno em [0,1]×[0,1] (ROC ou PR)."""
    W, H = 320, 270
    ml, mr, mt, mb = 40, 12, 26, 36
    pw, ph = W - ml - mr, H - mt - mb

    def X(v):
        return ml + pw * v

    def Y(v):
        return mt + ph * (1 - v)

    out = [f'<svg class="grafico" viewBox="0 0 {W} {H}" role="img" aria-label="{e(titulo)}" xmlns="http://www.w3.org/2000/svg">']
    out.append(f'<text x="{ml}" y="14" class="svg-rotulo-forte">{e(titulo)}</text>')
    for k in range(5):
        v = k / 4
        out.append(f'<line x1="{ml}" y1="{Y(v):.1f}" x2="{W - mr}" y2="{Y(v):.1f}" class="svg-grade"/>')
        out.append(f'<text x="{ml - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" class="svg-tick">{pt(v, 2)}</text>')
        out.append(f'<text x="{X(v):.1f}" y="{H - 20}" text-anchor="middle" class="svg-tick">{pt(v, 2)}</text>')
    if diagonal:
        out.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="{COR["grade"]}" stroke-width="1.2"/>')
    if baseline is not None:
        out.append(f'<line x1="{X(0)}" y1="{Y(baseline):.1f}" x2="{X(1)}" y2="{Y(baseline):.1f}" stroke="{COR["neutra"]}" '
                   f'stroke-width="1" stroke-dasharray="3 3"/>')
        out.append(f'<text x="{X(1) - 4}" y="{Y(baseline) - 5:.1f}" text-anchor="end" class="svg-nota">taxa de positivos {pct(baseline)}</text>')
    for nome, xs, ys, cor, dash in series:
        # Subamostra para o SVG não ficar pesado
        passo = max(1, len(xs) // 250)
        pts = list(zip(xs[::passo], ys[::passo]))
        if pts[-1] != (xs[-1], ys[-1]):
            pts.append((xs[-1], ys[-1]))
        d = "M" + " L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2"{dash_attr}><title>{e(nome)}</title></path>')
    out.append(f'<text x="{ml + pw / 2:.1f}" y="{H - 4}" text-anchor="middle" class="svg-tick">{e(xlabel)}</text>')
    out.append(f'<text transform="translate(11,{mt + ph / 2:.1f}) rotate(-90)" text-anchor="middle" class="svg-tick">{e(ylabel)}</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Blocos HTML
# ---------------------------------------------------------------------------
def badge(faixa: str) -> str:
    cls = {"Alto": "alto", "Médio": "medio", "Baixo": "baixo"}[faixa]
    return f'<span class="badge badge-{cls}"><i></i>{faixa}</span>'


def card_kpi(rotulo: str, valor: str, sub: str, tom: str = "neutro", destaque: bool = False) -> str:
    return (f'<div class="kpi kpi-{tom}{" kpi-destaque" if destaque else ""}"><div class="kpi-rotulo">{rotulo}</div>'
            f'<div class="kpi-valor">{valor}</div><div class="kpi-sub">{sub}</div></div>')


def bloco_kpis(k: dict) -> str:
    r = k["risco"]
    n = k["alunos_com_atividade"]
    return "\n".join([
        card_kpi("Alunos com atividade", str(n), f"de {k['alunos_matriculados']} matriculados · {k['alunos_matriculados'] - n} nunca acessaram"),
        card_kpi("Ativos nos últimos 7 dias", str(k["alunos_ativos_7d"]), f"{pct(k['alunos_ativos_7d'] / n, 0)} dos alunos com atividade", "ok"),
        card_kpi("Ativos nos últimos 28 dias", str(k["alunos_ativos_28d"]), f"{pct(k['alunos_ativos_28d'] / n, 0)} dos alunos com atividade", "ok"),
        card_kpi("Sem acesso há mais de 14 dias", str(k["alunos_inativos_14d"]), f"{pct(k['pct_inativos_14d'], 1)} · {k['alunos_inativos_30d']} há mais de 30 dias", "atencao"),
        card_kpi("Alto risco de evasão", pct(r["pct_alto_risco"], 1), f"{r['alto']} alunos com prob. ≥ {pt(LIMIAR_ALTO, 2)} · {r['medio']} em risco médio", "critico"),
        card_kpi("Alto risco e ainda ativos (28 d)", str(r["alto_risco_ainda_ativos_28d"]), "quem chamar primeiro: ainda estão por aqui, mas o ritmo caiu", "critico", destaque=True),
    ])


def tabela_metricas(mp: dict) -> str:
    h, l, ha, la = mp["hgb"], mp["logistica"], mp["hgb_acionavel"], mp["logistica_acionavel"]

    def lift(m):
        return m["top20"]["precisao"] / m["taxa_positivos"]

    linhas = [
        ("AUC-ROC", *(pt(m["auc_roc"], 3) for m in (h, l, ha, la))),
        ("AUC-PR (average precision)", *(pt(m["auc_pr"], 3) for m in (h, l, ha, la))),
        ("Taxa de positivos (referência)", *(pct(m["taxa_positivos"]) for m in (h, l, ha, la))),
        ("Brier score (menor é melhor)", *(pt(m["brier"], 3) for m in (h, l, ha, la))),
        ("Precisão @ limiar 0,5", *(pt(m["precisao"], 3) for m in (h, l, ha, la))),
        ("Recall @ limiar 0,5", *(pt(m["recall"], 3) for m in (h, l, ha, la))),
        (f"Precisão @ top-20% (k={h['top20']['k']} / {ha['top20']['k']})", *(pt(m["top20"]["precisao"], 3) for m in (h, l, ha, la))),
        ("Recall capturado no top-20%", *(pt(m["top20"]["recall_capturado"], 3) for m in (h, l, ha, la))),
        ("Lift no top-20% vs. base", *(pt(lift(m), 2) + "×" for m in (h, l, ha, la))),
        ("n linhas / positivos", *(f"{m['n']} / {m['positivos']}" for m in (h, l, ha, la))),
    ]
    tr = "".join(f"<tr><th scope=\"row\">{e(a)}</th><td class=\"num forte\">{b}</td><td class=\"num\">{c}</td>"
                 f"<td class=\"num forte\">{d}</td><td class=\"num\">{f}</td></tr>" for a, b, c, d, f in linhas)
    return f"""<div class="tabela-wrap"><table class="tabela tabela-metricas">
<thead><tr><th rowspan="2">Métrica (teste temporal, jun–ago/2026)</th><th colspan="2">Todos os alunos</th><th colspan="2">Subconjunto acionável*</th></tr>
<tr><th>Gradient Boosting</th><th>Logística (baseline)</th><th>Gradient Boosting</th><th>Logística (baseline)</th></tr></thead>
<tbody>{tr}</tbody></table></div>
<p class="nota">* Acionável = alunos com ≥ 1 evento nos 28 dias anteriores ao corte. Exclui os positivos "fáceis" (quem já estava sumido e continuou sumido) e mede o que interessa à operação: antecipar o desligamento de quem ainda está presente.</p>"""


def tabela_faixas(mp: dict) -> str:
    pf = mp["hgb"]["por_faixa"]
    lim = {"Alto": f"≥ {pt(LIMIAR_ALTO, 2)}", "Médio": f"{pt(LIMIAR_MEDIO, 2)} – {pt(LIMIAR_ALTO, 2)}", "Baixo": f"&lt; {pt(LIMIAR_MEDIO, 2)}"}
    tr = "".join(f"<tr><td>{badge(f)}</td><td class=\"num\">{lim[f]}</td><td class=\"num\">{pf[f]['n']}</td>"
                 f"<td class=\"num\">{pct(pf[f]['share'])}</td><td class=\"num forte\">{pct(pf[f]['taxa_observada'])}</td></tr>"
                 for f in ORDEM_FAIXA)
    return f"""<div class="tabela-wrap"><table class="tabela">
<thead><tr><th>Faixa</th><th class="num">Probabilidade</th><th class="num">n (teste)</th><th class="num">% das linhas</th><th class="num">Taxa observada de inatividade</th></tr></thead>
<tbody>{tr}</tbody></table></div>"""


def tabela_cortes(mp: dict) -> str:
    tr = "".join(f"<tr><td>{data_br(c['corte'])}</td><td class=\"num\">{c['n']}</td><td class=\"num\">{pct(c['taxa_positivos'])}</td>"
                 f"<td class=\"num forte\">{pt(c['auc_roc_hgb'], 3)}</td><td class=\"num\">{pt(c['auc_pr_hgb'], 3)}</td></tr>"
                 for c in mp["por_corte_teste"])
    return f"""<div class="tabela-wrap"><table class="tabela tabela-compacta">
<thead><tr><th>Corte de teste</th><th class="num">n</th><th class="num">Positivos</th><th class="num">AUC-ROC</th><th class="num">AUC-PR</th></tr></thead>
<tbody>{tr}</tbody></table></div>"""


def tabela_transicao(mt: dict) -> str:
    tr = "".join(f"<tr><td>{e(f['transicao'])}</td><td class=\"num\">{f['n']}</td><td class=\"num\">{f['positivos']}</td>"
                 f"<td class=\"num forte\">{pt(f['auc_roc'], 3)}</td><td class=\"num\">{pt(f['auc_pr'], 3)}</td></tr>" for f in mt["folds"])
    tr += (f"<tr class=\"total\"><td>Média</td><td></td><td></td><td class=\"num forte\">{pt(mt['auc_roc_medio'], 3)}</td>"
           f"<td class=\"num\">{pt(mt['auc_pr_medio'], 3)}</td></tr>")
    return f"""<div class="tabela-wrap"><table class="tabela tabela-compacta">
<thead><tr><th>Transição testada</th><th class="num">n</th><th class="num">Evadiram</th><th class="num">AUC-ROC</th><th class="num">AUC-PR</th></tr></thead>
<tbody>{tr}</tbody></table></div>"""


def tabela_top_atrito(at: pd.DataFrame, rec: pd.DataFrame) -> str:
    concl = at[(~at["fase_em_andamento"].astype(bool)) & at["taxa_queda"].notna()].copy()
    top = concl.sort_values("indice_atrito", ascending=False).head(8)
    rec_idx = {(int(r.fase), int(r.capitulo)): r for r in rec.itertuples(index=False)}
    linhas = []
    for r in top.itertuples(index=False):
        rr = rec_idx.get((int(r.fase), int(r.capitulo)))
        acao = f'<span class="chip chip-{e(rr.tipo_acao.lower())}">{e(rr.tipo_acao)}</span> {e(rr.recomendacao)}' if rr is not None else \
            '<span class="texto-mudo">Sem recomendação específica; acompanhar.</span>'
        linhas.append(
            f"<tr><td class=\"nowrap\">F{int(r.fase)} · Cap {int(r.capitulo)}</td><td class=\"titulo\">{e(r.titulo)}</td>"
            f"<td class=\"num\">{int(r.alunos_alcancaram)}</td><td class=\"num\">{int(r.alunos_perdidos)}</td>"
            f"<td class=\"num\">{pct(float(r.taxa_queda))}</td><td class=\"num\">{pt(float(r.esforco_relativo), 2)}×</td>"
            f"<td class=\"num forte\">{pt(float(r.indice_atrito), 3)}</td><td class=\"acao\">{acao}</td></tr>")
    return f"""<div class="tabela-wrap"><table class="tabela">
<thead><tr><th>Onde</th><th>Capítulo</th><th class="num">Chegaram</th><th class="num">Não avançaram</th><th class="num">Queda</th><th class="num">Esforço rel.</th><th class="num">Índice</th><th>O que fazer</th></tr></thead>
<tbody>{''.join(linhas)}</tbody></table></div>"""


def tabela_recomendacoes(rec: pd.DataFrame) -> str:
    rec = rec.sort_values(["prioridade", "indice_atrito"], ascending=[True, False])
    tr = "".join(
        f"<tr><td class=\"num\">{int(r.prioridade)}</td><td class=\"nowrap\">F{int(r.fase)} · Cap {int(r.capitulo)}</td><td class=\"titulo\">{e(r.titulo)}</td>"
        f"<td><span class=\"chip chip-{e(r.tipo_acao.lower())}\">{e(r.tipo_acao)}</span></td><td class=\"acao\">{e(r.recomendacao)}</td></tr>"
        for r in rec.itertuples(index=False))
    return f"""<div class="tabela-wrap tabela-rolagem"><table class="tabela tabela-compacta">
<thead><tr><th class="num">Prior.</th><th>Onde</th><th>Capítulo</th><th>Tipo</th><th>Recomendação</th></tr></thead>
<tbody>{tr}</tbody></table></div>"""


# ---------------------------------------------------------------------------
# CSS e JS
# ---------------------------------------------------------------------------
CSS = """
:root{
  --cor-primaria:#0B2545; --cor-secundaria:#13315C; --cor-acento:#2EC4B6; --cor-alerta:#FFB703;
  --cor-critico:#FF6B4A; --cor-fundo:#F6F7F9; --cor-texto:#0B2545; --cor-texto-corrido:#3A4A5C;
  --cor-neutra:#94A3B8; --cor-grade:#E3E8EF; --cor-cartao:#FFFFFF;
  --fonte-titulo:"Sora","Segoe UI",system-ui,sans-serif; --fonte-texto:"Inter","Segoe UI",system-ui,sans-serif;
  --raio:12px; --sombra:0 1px 2px rgba(11,37,69,.06),0 4px 14px rgba(11,37,69,.05);
}
@font-face{font-family:"Sora";src:url('__SORA__') format('truetype');font-weight:100 900;font-display:swap;}
@font-face{font-family:"Inter";src:url('__INTER__') format('truetype');font-weight:100 900;font-display:swap;}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--cor-fundo);color:var(--cor-texto-corrido);font-family:var(--fonte-texto);font-size:14px;line-height:1.45;-webkit-font-smoothing:antialiased}
h1,h2,h3,.kpi-valor{font-family:var(--fonte-titulo);color:var(--cor-texto);margin:0;letter-spacing:-.01em}
h1{font-size:28px;font-weight:600}
h2{font-size:20px;font-weight:600}
h3{font-size:15px;font-weight:600}
p{margin:0}
a{color:inherit}
.texto-mudo{color:var(--cor-neutra)}
.nota{font-size:12.5px;color:var(--cor-neutra);margin-top:10px}
.nowrap{white-space:nowrap}

/* Cabeçalho */
.topo{background:var(--cor-primaria);color:#fff;position:sticky;top:0;z-index:20;box-shadow:0 2px 10px rgba(0,0,0,.18)}
.topo-inner{max-width:1440px;margin:0 auto;padding:12px 28px;display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.logo{height:36px;width:auto;display:block}
.topo-sep{width:1px;height:34px;background:rgba(255,255,255,.18)}
.topo-meta .ies{font-family:var(--fonte-titulo);font-weight:600;font-size:17px;color:#fff}
.topo-meta .ref{font-size:12.5px;color:rgba(255,255,255,.72)}
.topo nav{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
.topo nav a{color:rgba(255,255,255,.82);text-decoration:none;font-size:13px;padding:7px 12px;border-radius:8px}
.topo nav a:hover{background:rgba(255,255,255,.1);color:#fff}

main{max-width:1440px;margin:0 auto;padding:26px 28px 40px}
section{margin-bottom:34px}
.sec-cab{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:14px}
.sec-cab p{max-width:820px;color:var(--cor-texto-corrido)}
.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:18px}
.hero p{margin-top:6px;max-width:760px;font-size:15px}
.hero .quando{font-size:13px;color:var(--cor-neutra);text-align:right}

/* Cartões */
.cartao{background:var(--cor-cartao);border:1px solid var(--cor-grade);border-radius:var(--raio);box-shadow:var(--sombra);padding:18px 20px}
.cartao h3{margin-bottom:4px}
.cartao .sub{font-size:12.5px;color:var(--cor-neutra);margin-bottom:12px}
/* minmax(0, …) impede que conteúdo largo (SVG, tabelas) expanda a trilha além da página */
.grid-2{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:18px}
.grid-3{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr) minmax(0,1fr);gap:18px}
.grid-modelo{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:18px}
.grid-iguais{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.pilha{display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
.cartao{min-width:0}
@media (max-width:1100px){.grid-2,.grid-3,.grid-modelo{grid-template-columns:1fr}}

/* KPIs */
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin-bottom:18px}
@media (max-width:1250px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:700px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kpi{background:var(--cor-cartao);border:1px solid var(--cor-grade);border-radius:var(--raio);box-shadow:var(--sombra);padding:16px 18px 14px;position:relative;overflow:hidden}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cor-neutra)}
.kpi-ok::before{background:var(--cor-acento)}
.kpi-atencao::before{background:var(--cor-alerta)}
.kpi-critico::before{background:var(--cor-critico)}
.kpi-destaque{background:linear-gradient(180deg,#fff 0%,#FFF4F0 100%);border-color:#FFD3C6}
.kpi-rotulo{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--cor-neutra);font-weight:600}
.kpi-valor{font-size:34px;font-weight:600;line-height:1.1;margin:6px 0 4px}
.kpi-sub{font-size:12.5px;color:var(--cor-texto-corrido)}

/* SVG */
.grafico{width:100%;max-width:100%;height:auto;display:block;font-family:var(--fonte-texto)}
.svg-grade{stroke:var(--cor-grade);stroke-width:1}
.svg-eixo{stroke:#CBD3DE;stroke-width:1}
.svg-tick{font-size:11.5px;fill:var(--cor-texto-corrido)}
.svg-nota{font-size:11px;fill:var(--cor-neutra)}
.svg-rotulo{font-size:12.5px;fill:var(--cor-texto-corrido)}
.svg-rotulo-forte{font-size:13px;font-weight:600;fill:var(--cor-texto)}
.svg-valor{font-size:12.5px;font-weight:600}
.celula rect{transition:opacity .12s}
.celula:hover rect{stroke:var(--cor-primaria);stroke-width:2}

/* Badges e chips */
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:3px 9px 3px 7px;border-radius:999px;white-space:nowrap}
.badge i{width:8px;height:8px;border-radius:50%;display:inline-block}
.badge-alto{background:#FFEDE7;color:#A33A1C}.badge-alto i{background:var(--cor-critico)}
.badge-medio{background:#FFF4D6;color:#7A5300}.badge-medio i{background:var(--cor-alerta)}
.badge-baixo{background:#E3F8F5;color:#0F6F68}.badge-baixo i{background:var(--cor-acento)}
.chip{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;background:#EEF2F7;color:var(--cor-secundaria);margin-right:6px;white-space:nowrap}
.chip-reforçar,.chip-reforcar{background:#FFEDE7;color:#A33A1C}
.chip-simplificar{background:#FFF4D6;color:#7A5300}
.chip-monitorar{background:#E6EEF7;color:var(--cor-secundaria)}
.chip-onboarding{background:#E3F8F5;color:#0F6F68}
.chip-formato{background:#EEF2F7;color:#3A4A5C}
.sit{font-size:12px;color:var(--cor-texto-corrido);white-space:nowrap}
.sit i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;background:var(--cor-neutra);vertical-align:1px}
.sit-ativo i{background:var(--cor-acento)}
.sit-inativo i{background:var(--cor-alerta)}
.sit-sumido i{background:var(--cor-critico)}
.tend{white-space:nowrap;font-variant-numeric:tabular-nums}
.tend b{font-weight:600;margin-right:4px}
.tend-queda b{color:#A33A1C}.tend-estavel b{color:var(--cor-texto-corrido)}.tend-alta b{color:#0F6F68}
.tend small{color:var(--cor-neutra)}

/* Tabelas */
.tabela-wrap{overflow-x:auto;border:1px solid var(--cor-grade);border-radius:10px;background:#fff}
.tabela-rolagem{max-height:420px;overflow-y:auto}
.tabela-fila{max-height:640px}
.tabela{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}
.tabela th,.tabela td{padding:9px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--cor-grade)}
.tabela thead th{position:sticky;top:0;background:#F9FAFC;color:var(--cor-texto);font-weight:600;font-size:12px;letter-spacing:.02em;z-index:2;text-align:center}
.tabela thead th:first-child{text-align:left}
.tabela tbody tr:last-child td{border-bottom:none}
.tabela tbody tr:hover{background:#FAFBFD}
.tabela tbody th{font-weight:500;color:var(--cor-texto-corrido);border-bottom:1px solid var(--cor-grade);text-align:left;padding:9px 12px}
.tabela .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tabela .forte{font-weight:600;color:var(--cor-texto)}
.tabela .acao{min-width:260px;color:var(--cor-texto-corrido)}
.tabela .titulo{min-width:170px}
.tabela-compacta th,.tabela-compacta td{padding:6px 10px;font-size:12.5px}
.tabela tr.total td{font-weight:600;background:#F9FAFC}
.tabela-metricas thead th{text-align:center}
.tabela-metricas tbody th{white-space:nowrap}

/* Fila */
.fila-barra{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.fila-barra input,.fila-barra select{font:inherit;font-size:13px;padding:8px 11px;border:1px solid #CBD3DE;border-radius:8px;background:#fff;color:var(--cor-texto)}
.fila-barra input{min-width:220px}
.fila-barra input:focus,.fila-barra select:focus{outline:2px solid rgba(46,196,182,.45);border-color:var(--cor-acento)}
.botao{font:inherit;font-size:13px;font-weight:600;padding:8px 13px;border-radius:8px;border:1px solid var(--cor-primaria);background:var(--cor-primaria);color:#fff;cursor:pointer}
.botao:hover{background:var(--cor-secundaria)}
.botao-suave{background:#fff;color:var(--cor-primaria)}
.botao-suave:hover{background:#EEF2F7}
.contagem{margin-left:auto;font-size:13px;color:var(--cor-texto-corrido)}
.contagem b{color:var(--cor-texto)}
#tab-fila thead th{cursor:pointer;user-select:none;white-space:nowrap;text-align:left}
#tab-fila thead th.num{text-align:right}
#tab-fila thead th .seta{display:inline-block;width:10px;color:var(--cor-neutra);margin-left:4px}
#tab-fila thead th.ativa{color:var(--cor-primaria)}
#tab-fila thead th.ativa .seta{color:var(--cor-acento)}
#tab-fila tbody tr{cursor:pointer}
#tab-fila tbody tr:hover{background:#F3FBFA}
#tab-fila td.aluno{font-weight:600;color:var(--cor-texto);white-space:nowrap}
#tab-fila td.fatores{max-width:360px;font-size:12.5px;color:var(--cor-texto-corrido)}
#tab-fila td.acao{max-width:360px;font-size:12.5px}
#tab-fila td.prob{font-weight:600;color:var(--cor-texto)}
.barra-prob{display:inline-block;width:56px;height:6px;border-radius:3px;background:#EEF2F7;vertical-align:middle;margin-left:8px;overflow:hidden}
.barra-prob i{display:block;height:100%;border-radius:3px}
.vazio{padding:28px;text-align:center;color:var(--cor-neutra)}

/* Painel lateral do aluno */
.veu{position:fixed;inset:0;background:rgba(11,37,69,.38);opacity:0;pointer-events:none;transition:opacity .18s;z-index:40}
.veu.aberto{opacity:1;pointer-events:auto}
.painel{position:fixed;top:0;right:0;bottom:0;width:min(520px,100%);background:#fff;box-shadow:-8px 0 30px rgba(11,37,69,.18);transform:translateX(100%);transition:transform .22s ease;z-index:50;display:flex;flex-direction:column}
.painel.aberto{transform:translateX(0)}
.painel-cab{padding:18px 22px 14px;border-bottom:1px solid var(--cor-grade);display:flex;align-items:flex-start;gap:12px}
.painel-cab h2{font-size:22px}
.painel-cab .fechar{margin-left:auto;border:none;background:#EEF2F7;color:var(--cor-texto);width:34px;height:34px;border-radius:8px;font-size:18px;cursor:pointer}
.painel-cab .fechar:hover{background:#E3E8EF}
.painel-corpo{padding:16px 22px 28px;overflow-y:auto}
.painel-resumo{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px}
.mini{background:var(--cor-fundo);border-radius:10px;padding:10px 12px}
.mini .r{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--cor-neutra);font-weight:600}
.mini .v{font-family:var(--fonte-titulo);font-size:20px;font-weight:600;color:var(--cor-texto);margin-top:2px}
.mini .s{font-size:11.5px;color:var(--cor-texto-corrido)}
.painel h3{margin:16px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--cor-neutra)}
.fatores-lista{margin:0;padding-left:18px;color:var(--cor-texto)}
.fatores-lista li{margin-bottom:4px}
.acao-caixa{background:#E3F8F5;border-left:4px solid var(--cor-acento);border-radius:8px;padding:10px 14px;color:var(--cor-texto)}
.acao-caixa.alto{background:#FFF1EC;border-left-color:var(--cor-critico)}
.acao-caixa.medio{background:#FFF7E0;border-left-color:var(--cor-alerta)}
.feat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px}
.feat{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px dashed var(--cor-grade);font-size:12.5px}
.feat span{color:var(--cor-texto-corrido)}
.feat b{color:var(--cor-texto);font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}

/* Rodapé */
footer{border-top:1px solid var(--cor-grade);background:#fff}
.rodape-inner{max-width:1440px;margin:0 auto;padding:24px 28px 30px;display:grid;grid-template-columns:1.4fr 1fr;gap:26px;font-size:12.5px;color:var(--cor-texto-corrido)}
@media (max-width:900px){.rodape-inner{grid-template-columns:1fr}}
footer h3{font-size:13px;margin-bottom:8px}
footer ul{margin:0;padding-left:18px}
footer li{margin-bottom:5px}
.assinatura{color:var(--cor-neutra);margin-top:10px}
@media print{.topo{position:static}.painel,.veu{display:none}}
"""

JS = r"""
(function(){
  const D = JSON.parse(document.getElementById('dados').textContent);
  const alunos = D.alunos;
  const CAPS = D.capitulos_por_fase;
  const fmt = (v, c=1) => (v===null||v===undefined||Number.isNaN(v)) ? '—' : Number(v).toLocaleString('pt-BR',{minimumFractionDigits:c, maximumFractionDigits:c});
  const fmtInt = v => (v===null||v===undefined) ? '—' : Number(v).toLocaleString('pt-BR',{maximumFractionDigits:0});
  const esc = s => String(s??'').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const dataBR = s => { if(!s) return '—'; const [a,m,d] = String(s).slice(0,10).split('-'); return `${d}/${m}/${a}`; };
  const CLS_FAIXA = {'Alto':'alto','Médio':'medio','Baixo':'baixo'};
  const ORD_FAIXA = {'Alto':0,'Médio':1,'Baixo':2};
  const COR_FAIXA = {'Alto':'#FF6B4A','Médio':'#FFB703','Baixo':'#2EC4B6'};
  const badge = f => `<span class="badge badge-${CLS_FAIXA[f]||''}"><i></i>${esc(f)}</span>`;
  const sit = s => { const c = s.startsWith('Ativo') ? 'ativo' : (s.includes('>60') ? 'sumido' : 'inativo'); return `<span class="sit sit-${c}"><i></i>${esc(s).replace('(28d)','(28 d)')}</span>`; };
  const tend = t => {
    if (t===null||t===undefined) return '—';
    let cls='estavel', seta='→', txt='estável';
    if (t < 0.5) { cls='queda'; seta='↓'; txt='em queda'; }
    else if (t > 1.2) { cls='alta'; seta='↑'; txt='acelerando'; }
    return `<span class="tend tend-${cls}" title="eventos 7 d ÷ (eventos 28 d / 4 + 1)"><b>${seta}</b>${fmt(t,2)} <small>${txt}</small></span>`;
  };

  // ---- Fila de segunda-feira -------------------------------------------
  const estado = { ordem:'probabilidade', dir:-1, busca:'', faixa:'', situacao:'' };
  const tbody = document.querySelector('#tab-fila tbody');
  const colunas = [
    {k:'aluno_id', tipo:'txt'}, {k:'fase_atual', tipo:'num'}, {k:'situacao', tipo:'txt'}, {k:'recencia_dias', tipo:'num'},
    {k:'tendencia', tipo:'num'}, {k:'probabilidade', tipo:'num'}, {k:'faixa', tipo:'faixa'}, {k:'fatores', tipo:'txt'}, {k:'acao_sugerida', tipo:'txt'}
  ];
  function comparar(a, b) {
    const col = colunas.find(c => c.k === estado.ordem);
    let va = a[col.k], vb = b[col.k];
    if (col.tipo === 'faixa') { va = ORD_FAIXA[va]; vb = ORD_FAIXA[vb]; }
    let r;
    if (col.tipo === 'txt') r = String(va??'').localeCompare(String(vb??''), 'pt-BR');
    else r = (va??-Infinity) - (vb??-Infinity);
    if (r === 0) r = b.probabilidade - a.probabilidade; // desempate: mais risco primeiro
    return r * estado.dir;
  }
  function filtrar() {
    const q = estado.busca.trim().toLowerCase();
    return alunos.filter(a =>
      (!estado.faixa || a.faixa === estado.faixa) &&
      (!estado.situacao || a.situacao === estado.situacao) &&
      (!q || a.aluno_id.toLowerCase().includes(q) || (a.fatores||'').toLowerCase().includes(q) || (a.acao_sugerida||'').toLowerCase().includes(q))
    );
  }
  function render() {
    const lista = filtrar().sort(comparar);
    document.querySelectorAll('#tab-fila thead th').forEach(th => {
      const ativa = th.dataset.k === estado.ordem;
      th.classList.toggle('ativa', ativa);
      th.querySelector('.seta').textContent = ativa ? (estado.dir === 1 ? '▲' : '▼') : '↕';
    });
    if (!lista.length) { tbody.innerHTML = '<tr><td colspan="9" class="vazio">Nenhum aluno com esses filtros.</td></tr>'; }
    else tbody.innerHTML = lista.map(a => `
      <tr data-id="${esc(a.aluno_id)}" tabindex="0">
        <td class="aluno">${esc(a.aluno_id)}</td>
        <td class="num">F${a.fase_atual}</td>
        <td>${sit(a.situacao)}</td>
        <td class="num">${fmtInt(a.recencia_dias)}</td>
        <td>${tend(a.tendencia)}</td>
        <td class="num prob">${fmt(a.probabilidade*100,1)}%<span class="barra-prob"><i style="width:${Math.round(a.probabilidade*100)}%;background:${COR_FAIXA[a.faixa]}"></i></span></td>
        <td>${badge(a.faixa)}</td>
        <td class="fatores">${esc(a.fatores||'').split(' | ').map(esc).join(' · ')}</td>
        <td class="acao">${esc(a.acao_sugerida)}</td>
      </tr>`).join('');
    const nAlto = lista.filter(a => a.faixa === 'Alto').length;
    const nAltoAtivo = lista.filter(a => a.faixa === 'Alto' && a.situacao.startsWith('Ativo')).length;
    document.getElementById('contagem').innerHTML = `<b>${lista.length}</b> aluno${lista.length===1?'':'s'} · <b>${nAlto}</b> em alto risco · <b>${nAltoAtivo}</b> alto risco e ainda ativos`;
  }
  document.querySelectorAll('#tab-fila thead th').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.k;
    if (estado.ordem === k) estado.dir *= -1;
    else { estado.ordem = k; estado.dir = (colunas.find(c => c.k===k).tipo === 'txt') ? 1 : -1; if (k==='faixa') estado.dir = 1; }
    render();
  }));
  document.getElementById('busca').addEventListener('input', ev => { estado.busca = ev.target.value; render(); });
  document.getElementById('f-faixa').addEventListener('change', ev => { estado.faixa = ev.target.value; render(); });
  document.getElementById('f-situacao').addEventListener('change', ev => { estado.situacao = ev.target.value; render(); });
  document.getElementById('preset-hoje').addEventListener('click', () => {
    estado.faixa = 'Alto'; estado.situacao = 'Ativo (28d)'; estado.busca = ''; estado.ordem = 'probabilidade'; estado.dir = -1;
    document.getElementById('f-faixa').value = 'Alto'; document.getElementById('f-situacao').value = 'Ativo (28d)'; document.getElementById('busca').value = '';
    render();
  });
  document.getElementById('preset-limpar').addEventListener('click', () => {
    estado.faixa = ''; estado.situacao = ''; estado.busca = ''; estado.ordem = 'probabilidade'; estado.dir = -1;
    document.getElementById('f-faixa').value = ''; document.getElementById('f-situacao').value = ''; document.getElementById('busca').value = '';
    render();
  });
  tbody.addEventListener('click', ev => { const tr = ev.target.closest('tr[data-id]'); if (tr) abrir(tr.dataset.id); });
  tbody.addEventListener('keydown', ev => { if (ev.key === 'Enter') { const tr = ev.target.closest('tr[data-id]'); if (tr) abrir(tr.dataset.id); } });

  // ---- Painel do aluno --------------------------------------------------
  const painel = document.getElementById('painel'), veu = document.getElementById('veu');
  function fechar(){ painel.classList.remove('aberto'); veu.classList.remove('aberto'); }
  veu.addEventListener('click', fechar);
  document.getElementById('fechar').addEventListener('click', fechar);
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') fechar(); });
  function feat(rotulo, valor){ return `<div class="feat"><span>${esc(rotulo)}</span><b>${valor}</b></div>`; }
  function abrir(id) {
    const a = alunos.find(x => x.aluno_id === id); if (!a) return;
    const total = CAPS[String(a.fase_atual)] || '?';
    const fatores = [a.fator_1, a.fator_2, a.fator_3].filter(Boolean);
    document.getElementById('painel-titulo').textContent = a.aluno_id;
    document.getElementById('painel-badge').innerHTML = badge(a.faixa) + ' ' + sit(a.situacao);
    document.getElementById('painel-corpo').innerHTML = `
      <div class="painel-resumo">
        <div class="mini"><div class="r">Probabilidade</div><div class="v">${fmt(a.probabilidade*100,1)}%</div><div class="s">de 21 dias sem atividade</div></div>
        <div class="mini"><div class="r">Recência</div><div class="v">${fmtInt(a.recencia_dias)} d</div><div class="s">último acesso ${dataBR(a.ultimo_evento)}</div></div>
        <div class="mini"><div class="r">Fase atual</div><div class="v">F${a.fase_atual}</div><div class="s">cap. ${fmtInt(a.capitulo_max_fase_atual)} de ${total} (${fmt(a.pct_capitulos_fase_atual*100,0)}%)</div></div>
      </div>
      <h3>Por que está nesta faixa</h3>
      <ul class="fatores-lista">${fatores.map(f => `<li>${esc(f)}</li>`).join('') || '<li class="texto-mudo">Sem fatores destacados.</li>'}</ul>
      <h3>Ação sugerida</h3>
      <div class="acao-caixa ${CLS_FAIXA[a.faixa]}">${esc(a.acao_sugerida)}</div>
      <h3>Atividade recente</h3>
      <div class="feat-grid">
        ${feat('Eventos (7 d)', fmtInt(a.eventos_7d))}${feat('Eventos (14 d)', fmtInt(a.eventos_14d))}
        ${feat('Eventos (28 d)', fmtInt(a.eventos_28d))}${feat('Dias ativos (7 d)', fmtInt(a.dias_ativos_7d))}
        ${feat('Dias ativos (28 d)', fmtInt(a.dias_ativos_28d))}${feat('Semanas ativas (últimas 8)', fmtInt(a.semanas_ativas_ultimas_8))}
        ${feat('Tendência 7 d vs. 28 d', tend(a.tendencia))}${feat('Capítulos distintos (28 d)', fmtInt(a.capitulos_distintos_28d))}
      </div>
      <h3>Progresso e avaliações</h3>
      <div class="feat-grid">
        ${feat('Eventos de progresso (28 d)', fmtInt(a.progresso_28d))}${feat('Questionários iniciados (28 d)', fmtInt(a.quiz_iniciados_28d))}
        ${feat('Questionários entregues (28 d)', fmtInt(a.quiz_entregues_28d))}${feat('Entregas de tarefa (28 d)', fmtInt(a.entregas_28d))}
      </div>
      <h3>Histórico e hábitos</h3>
      <div class="feat-grid">
        ${feat('Eventos acumulados', fmtInt(a.eventos_acumulados))}${feat('Dias ativos acumulados', fmtInt(a.dias_ativos_acumulados))}
        ${feat('Semanas desde o 1º acesso', fmtInt(a.semanas_desde_primeiro_evento))}${feat('Primeiro acesso', dataBR(a.primeiro_evento))}
        ${feat('% eventos à noite (28 d)', fmt(a.share_noite_28d*100,0)+'%')}${feat('% eventos no fim de semana (28 d)', fmt(a.share_fim_semana_28d*100,0)+'%')}
      </div>
      <p class="nota">Corte de scoring: ${dataBR(a.corte)}. Features calculadas só com eventos até o corte; a probabilidade é do modelo de gradient boosting retreinado em toda a base rotulada.</p>`;
    painel.classList.add('aberto'); veu.classList.add('aberto');
    document.getElementById('fechar').focus();
  }

  render();
})();
"""


# ---------------------------------------------------------------------------
# Montagem
# ---------------------------------------------------------------------------
def montar_html(k: dict, met: dict, risco: pd.DataFrame, at: pd.DataFrame, rec: pd.DataFrame) -> str:
    mp, mtr = met["modelo_principal"], met["modelo_transicao"]
    h, l = mp["hgb"], mp["logistica"]
    data_ref = data_br(k["data_referencia"])
    corte = data_br(k["corte_scoring"])
    periodo = f"{data_br(k['periodo_dados'][0])} a {data_br(k['periodo_dados'][1])}"
    r = k["risco"]

    # Dados embutidos
    cols_json = [c for c in risco.columns]
    alunos_json = json.loads(risco[cols_json].to_json(orient="records", force_ascii=False, date_format="iso"))
    dados = {"alunos": alunos_json, "capitulos_por_fase": {str(kf): v for kf, v in CAPITULOS_POR_FASE.items()},
             "data_referencia": k["data_referencia"], "corte_scoring": k["corte_scoring"],
             "limiares": {"alto": LIMIAR_ALTO, "medio": LIMIAR_MEDIO}}
    dados_json = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    # SVGs
    svg_ativos = svg_ativos_semana(k["curva_semanal_ativos"])
    svg_faixas = svg_barras_faixas(risco)
    svg_heat = svg_heatmap_atrito(at)
    svg_imp = svg_barras_importancia(mp["importancia_permutacao_top12"])
    svg_roc = svg_curva(
        [(f"Gradient Boosting (AUC {pt(h['auc_roc'], 3)})", h["curva_roc"]["fpr"], h["curva_roc"]["tpr"], COR["primaria"], ""),
         (f"Regressão logística (AUC {pt(l['auc_roc'], 3)})", l["curva_roc"]["fpr"], l["curva_roc"]["tpr"], COR["neutra"], "4 3")],
        "Taxa de falsos positivos", "Taxa de verdadeiros positivos", None, True, f"ROC · AUC {pt(h['auc_roc'], 3)}")
    svg_pr = svg_curva(
        [(f"Gradient Boosting (AUC-PR {pt(h['auc_pr'], 3)})", h["curva_pr"]["recall"], h["curva_pr"]["precisao"], COR["primaria"], ""),
         (f"Regressão logística (AUC-PR {pt(l['auc_pr'], 3)})", l["curva_pr"]["recall"], l["curva_pr"]["precisao"], COR["neutra"], "4 3")],
        "Recall", "Precisão", h["taxa_positivos"], False, f"Precisão–Recall · AUC-PR {pt(h['auc_pr'], 3)}")

    n_cortes_treino = len(mp["split"]["cortes_treino"])
    n_cortes_teste = len(mp["split"]["cortes_teste"])
    css = CSS.replace("__SORA__", FONTE_SORA_REL).replace("__INTER__", FONTE_INTER_REL)
    gerado = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retena · IES Demo — Risco de evasão</title>
<meta name="description" content="Painel Retena: quem chamar hoje, atrito de conteúdo e desempenho do modelo de risco de evasão (IES Demo).">
<style>{css}</style>
</head>
<body>
<header class="topo">
  <div class="topo-inner">
    <img class="logo" src="{LOGO_REL}" alt="Retena">
    <div class="topo-sep"></div>
    <div class="topo-meta">
      <div class="ies">IES Demo</div>
      <div class="ref">Dados até {data_ref} · corte de scoring {corte} (domingo) · logs de {periodo}</div>
    </div>
    <nav aria-label="Seções">
      <a href="#visao">Visão geral</a><a href="#fila">Fila de segunda</a><a href="#atrito">Atrito de conteúdo</a><a href="#modelo">Modelo</a>
    </nav>
  </div>
</header>

<main>
<section id="visao">
  <div class="hero">
    <div>
      <h1>Quem chamar hoje</h1>
      <p>Risco de o aluno passar <strong>21 dias sem nenhuma ação no LMS</strong>, calculado toda semana a partir dos logs de navegação.
      Não é cobrança: é uma lista para o tutor começar a segunda-feira sabendo com quem conversar primeiro.</p>
    </div>
    <div class="quando">Referência {data_ref}<br>Próximo scoring: domingo seguinte ao corte</div>
  </div>
  <div class="kpis">
{bloco_kpis(k)}
  </div>
  <div class="grid-2">
    <div class="cartao">
      <h3>Alunos ativos por semana</h3>
      <div class="sub">Alunos distintos com ≥ 1 ação própria na semana (terminando no domingo). Área sombreada: intervalo entre a Fase 4 e a Fase 5.</div>
      {svg_ativos}
    </div>
    <div class="cartao">
      <h3>Faixas de risco no corte de {corte}</h3>
      <div class="sub">{r['alunos_avaliados']} alunos avaliados. Opacidade indica a situação de acesso: cheia = ativo nos últimos 28 dias.</div>
      {svg_faixas}
    </div>
  </div>
</section>

<section id="fila">
  <div class="sec-cab">
    <div>
      <h2>Fila de segunda-feira</h2>
      <p>Clique no cabeçalho para ordenar e na linha para abrir o aluno. Comece por <strong>alto risco e ainda ativos</strong>: é onde uma conversa curta ainda muda o rumo.
      Quem está sumido há mais de 60 dias já pede resgate pela coordenação, não lembrete.</p>
    </div>
  </div>
  <div class="cartao">
    <div class="fila-barra">
      <input id="busca" type="search" placeholder="Buscar aluno (ex.: Aluno 0227) ou palavra do fator" aria-label="Buscar aluno">
      <select id="f-faixa" aria-label="Filtrar por faixa">
        <option value="">Todas as faixas</option><option value="Alto">Alto</option><option value="Médio">Médio</option><option value="Baixo">Baixo</option>
      </select>
      <select id="f-situacao" aria-label="Filtrar por situação">
        <option value="">Todas as situações</option><option value="Ativo (28d)">Ativo (28 d)</option><option value="Inativo 29–60d">Inativo 29–60 d</option><option value="Inativo >60d">Inativo &gt; 60 d</option>
      </select>
      <button id="preset-hoje" class="botao" type="button">Prioridade de hoje: alto risco e ativos</button>
      <button id="preset-limpar" class="botao botao-suave" type="button">Limpar</button>
      <div id="contagem" class="contagem"></div>
    </div>
    <div class="tabela-wrap tabela-rolagem tabela-fila">
      <table class="tabela" id="tab-fila">
        <thead><tr>
          <th data-k="aluno_id">Aluno<span class="seta">↕</span></th>
          <th data-k="fase_atual" class="num">Fase<span class="seta">↕</span></th>
          <th data-k="situacao">Situação<span class="seta">↕</span></th>
          <th data-k="recencia_dias" class="num">Recência (dias)<span class="seta">↕</span></th>
          <th data-k="tendencia">Tendência<span class="seta">↕</span></th>
          <th data-k="probabilidade" class="num">Probabilidade<span class="seta">↕</span></th>
          <th data-k="faixa">Faixa<span class="seta">↕</span></th>
          <th data-k="fatores">Fatores<span class="seta">↕</span></th>
          <th data-k="acao_sugerida">Ação sugerida<span class="seta">↕</span></th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <p class="nota">Faixas: Alto ≥ {pt(LIMIAR_ALTO, 2)} · Médio {pt(LIMIAR_MEDIO, 2)}–{pt(LIMIAR_ALTO, 2)} · Baixo &lt; {pt(LIMIAR_MEDIO, 2)}. Tendência = eventos dos últimos 7 dias ÷ (média semanal dos 28 dias + 1): ↓ abaixo de 0,5, ↑ acima de 1,2.
    Os fatores são explicações por regra (recência, ritmo, progresso), não coeficientes do modelo.</p>
  </div>
</section>

<section id="atrito">
  <div class="sec-cab">
    <div>
      <h2>Mapa de atrito de conteúdo</h2>
      <p>Onde os alunos travam: para cada capítulo, a fração dos que chegaram nele e não avançaram ao seguinte, ponderada pelo esforço (eventos) que o capítulo exige em relação à fase.
      Passe o mouse sobre a célula para ver os detalhes.</p>
    </div>
  </div>
  <div class="pilha">
    <div class="cartao">
      <h3>Fase × capítulo — {k['atrito']['capitulos_avaliados']} capítulos avaliados</h3>
      <div class="sub">Escala truncada em 0,10: na Fase 5 (em andamento) a "queda" é progresso em curso, não abandono — leia-a como monitoramento, não como fricção confirmada.</div>
      {svg_heat}
    </div>
    <div class="pilha">
      <div class="cartao">
        <h3>As 8 maiores fricções (fases concluídas)</h3>
        <div class="sub">Ordenadas pelo índice de atrito; recomendações de <code>recomendacoes_conteudo.csv</code>.</div>
        {tabela_top_atrito(at, rec)}
      </div>
      <div class="cartao">
        <h3>Recomendações de conteúdo ({len(rec)})</h3>
        <div class="sub">Prioridade 1 = agir agora; 2 = próximo ciclo; 3 = ajuste de formato.</div>
        {tabela_recomendacoes(rec)}
      </div>
    </div>
  </div>
</section>

<section id="modelo">
  <div class="sec-cab">
    <div>
      <h2>Modelo</h2>
      <p>HistGradientBoosting (scikit-learn) com {len(mp['features'])} features de comportamento, rótulo <code>inativo_21d</code>. Avaliação com <strong>split temporal</strong>:
      treino em {n_cortes_treino} cortes (fev–mai/2026, embargo de 21 dias), teste em {n_cortes_teste} cortes (jun–ago/2026), {mp['split']['n_teste']:,} linhas aluno-semana de {mp['split']['alunos_teste']} alunos.
      Baseline: regressão logística. Detalhes e discussão em <code>outputs/RESULTADOS.md</code>.</p>
    </div>
  </div>
  <div class="pilha">
    <div class="cartao">
      <h3>Métricas no teste temporal</h3>
      <div class="sub">Em negrito, o modelo usado no scoring. A logística empata ou supera o boosting em vários números — com ~200 alunos, a diferença não é significativa; o HGB foi mantido pela flexibilidade para novas features.</div>
      {tabela_metricas(mp)}
    </div>
    <div class="grid-modelo">
      <div class="pilha">
        <div class="cartao">
          <h3>Faixas de risco — taxa observada no teste</h3>
          <div class="sub">Limiares definidos antes de olhar o teste: 0,60 = "mais provável ficar inativo do que não", com margem para erro de calibração; 0,30 ≈ 1,5–2× a taxa média de positivos.</div>
          {tabela_faixas(mp)}
        </div>
        <div class="cartao">
          <h3>Importância por permutação — top 12</h3>
          <div class="sub">Queda média de AUC-ROC ao embaralhar cada feature no teste (15 repetições; traço = desvio-padrão).</div>
          {svg_imp}
        </div>
      </div>
      <div class="pilha">
        <div class="cartao">
          <h3>Curvas no teste</h3>
          <div class="sub">Linha cheia: gradient boosting. Tracejada: regressão logística.</div>
          <div class="grid-2 grid-iguais" style="gap:8px">{svg_roc}{svg_pr}</div>
        </div>
        <div class="cartao">
          <h3>Estabilidade por corte de teste</h3>
          <div class="sub">A taxa de positivos sobe de 18% para 40% em julho (intervalo entre fases) e a AUC cai junto — o período de teste é estruturalmente diferente do treino.</div>
          {tabela_cortes(mp)}
        </div>
        <div class="cartao">
          <h3>Modelo secundário — evasão entre fases</h3>
          <div class="sub">Regressão logística no grão aluno-fase ({mtr['n']} linhas, {mtr['alunos']} alunos, taxa {pct(mtr['taxa_positivos'])}); validação leave-one-phase-out.</div>
          {tabela_transicao(mtr)}
        </div>
      </div>
    </div>
  </div>
</section>
</main>

<footer>
  <div class="rodape-inner">
    <div>
      <h3>Leia com estas limitações em mente</h3>
      <ul>
        <li><strong>Amostra pequena, curso único:</strong> ~200 alunos de uma só instituição; as linhas aluno-semana são correlacionadas (o mesmo aluno em vários cortes). Intervalos de confiança largos; não está validado para outras IES sem re-treino.</li>
        <li><strong>Rótulo comportamental, não administrativo:</strong> <code>inativo_21d</code> mede silêncio no LMS, não cancelamento de matrícula. Férias ou avaliação presencial podem gerar "falsos" positivos. É um proxy para priorizar contato.</li>
        <li><strong>Positivos fáceis:</strong> parte do desempenho vem de quem já estava sumido e continuou sumido. O número relevante para a operação é o do subconjunto acionável (AUC-ROC {pt(mp['hgb_acionavel']['auc_roc'], 2)}, AUC-PR {pt(mp['hgb_acionavel']['auc_pr'], 2)}).</li>
        <li><strong>Não-estacionariedade e calibração:</strong> a taxa de inatividade varia muito ao longo do semestre; as probabilidades ordenam bem, mas leia as faixas como prioridade relativa.</li>
        <li><strong>Só logs de navegação:</strong> sem notas, dados socioeconômicos ou histórico acadêmico — limita o teto, mas torna a solução portátil para qualquer LMS Moodle-like.</li>
      </ul>
    </div>
    <div>
      <h3>Como este painel foi gerado</h3>
      <p>Arquivo único (HTML + CSS + JS + SVG + dados) produzido por <code>pipeline/06_gerar_dashboard.py</code> a partir de <code>kpis.json</code>, <code>metricas.json</code>,
      <code>risco_alunos_atual.csv</code>, <code>atrito_conteudo.csv</code> e <code>recomendacoes_conteudo.csv</code>. Nenhum número foi editado à mão.
      Eventos considerados: {k['eventos_atividade']:,} ações próprias de alunos entre {k['eventos_total']:,} eventos do LMS.</p>
      <p class="assinatura">Retena · MVP analítico · gerado em {gerado}. Modelos: <code>model/modelo_risco_21d.joblib</code>, <code>model/modelo_transicao_fases.joblib</code>.</p>
    </div>
  </div>
</footer>

<div id="veu" class="veu"></div>
<aside id="painel" class="painel" role="dialog" aria-modal="true" aria-labelledby="painel-titulo">
  <div class="painel-cab">
    <div><h2 id="painel-titulo">Aluno</h2><div id="painel-badge" style="margin-top:6px"></div></div>
    <button id="fechar" class="fechar" type="button" aria-label="Fechar">×</button>
  </div>
  <div id="painel-corpo" class="painel-corpo"></div>
</aside>

<script type="application/json" id="dados">{dados_json}</script>
<script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    log("Gerando dashboard...")
    k = carregar_json(DIR_OUTPUTS / "kpis.json")
    met = carregar_json(DIR_OUTPUTS / "metricas.json")
    risco = pd.read_csv(DIR_OUTPUTS / "risco_alunos_atual.csv")
    at = pd.read_csv(DIR_OUTPUTS / "atrito_conteudo.csv")
    rec = pd.read_csv(DIR_OUTPUTS / "recomendacoes_conteudo.csv")

    # Separador de milhar pt-BR nos números do texto (f-strings usam vírgula; troca por ponto).
    html_txt = montar_html(k, met, risco, at, rec)
    for antigo, novo in ((f"{k['eventos_atividade']:,}", f"{k['eventos_atividade']:,}".replace(",", ".")),
                         (f"{k['eventos_total']:,}", f"{k['eventos_total']:,}".replace(",", ".")),
                         (f"{met['modelo_principal']['split']['n_teste']:,}", f"{met['modelo_principal']['split']['n_teste']:,}".replace(",", "."))):
        html_txt = html_txt.replace(antigo, novo)

    destino = DIR_DASHBOARD / "index.html"
    destino.write_text(html_txt, encoding="utf-8")
    log(f"  dashboard salvo: {destino} ({destino.stat().st_size / 1024:.0f} KB, {len(risco)} alunos embutidos)")


if __name__ == "__main__":
    main()
