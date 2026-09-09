# -*- coding: utf-8 -*-
"""
Gera o logo da Retena (SVG com texto convertido em curvas + PNGs) a partir da fonte Sora.

Símbolo: a "linha do batimento" — um pulso que ameaça cair, é sustentado e vira trilha
ascendente até um ponto final (a formatura). Verde-sinal sobre azul-profundo.

Uso: python gerar_logo.py   (gera em ./logo/)
Requer: fontTools (instalado com matplotlib), Microsoft Edge para os PNGs.
"""
import json, os, subprocess
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

BASE = Path(__file__).resolve().parent
OUT = BASE / "logo"; OUT.mkdir(exist_ok=True)
M = json.loads((BASE / "marca.json").read_text(encoding="utf-8-sig"))
C = M["cores"]
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def text_to_path(text, font_path, size, wght=700, letter_spacing=-0.02):
    """Retorna (path_d, largura) com o texto convertido em curvas, unidades = px do tamanho dado."""
    font = TTFont(font_path)
    if "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": wght})
    gs = font.getGlyphSet(); cmap = font.getBestCmap(); upm = font["head"].unitsPerEm
    scale = size / upm
    x = 0.0; d = ""
    for ch in text:
        gname = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x, 0))  # y invertido (SVG)
        gs[gname].draw(tpen)
        d += pen.getCommands() + " "
        x += gs[gname].width * scale + letter_spacing * size
    return d.strip(), x - letter_spacing * size


def simbolo_paths(cor_linha, cor_ponto):
    """Marca gráfica em viewBox 0 0 120 120."""
    linha = ("M 8 72 H 32 L 43 88 L 55 50 L 65 72 H 78 L 99 44")
    return (f"<path d='{linha}' fill='none' stroke='{cor_linha}' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='104' cy='38' r='8.5' fill='{cor_ponto}'/>")


def svg_simbolo(fundo=None, cor_linha=None, cor_ponto=None, raio=26):
    cor_linha = cor_linha or C["acento"]; cor_ponto = cor_ponto or C["acento"]
    bg = f"<rect width='120' height='120' rx='{raio}' fill='{fundo}'/>" if fundo else ""
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120' width='120' height='120'>{bg}{simbolo_paths(cor_linha, cor_ponto)}</svg>"


def svg_horizontal(cor_texto, cor_linha, cor_ponto, fundo=None, tagline=None, cor_tagline=None):
    d, w = text_to_path("Retena", BASE / "fontes" / "Sora-Variable.ttf", 76, 700, -0.025)
    tx = 140; ty = 86
    largura = int(tx + w + 16)
    altura = 120 if not tagline else 160
    tag = ""
    if tagline:
        td, tw = text_to_path(tagline, BASE / "fontes" / "Inter-Variable.ttf", 22, 500, 0.0)
        largura = int(max(largura, tx + tw + 16))
        tag = f"<g transform='translate({tx} 128)'><path d='{td}' fill='{cor_tagline or cor_texto}' opacity='.85'/></g>"
    bg = f"<rect width='{largura}' height='{altura}' rx='0' fill='{fundo}'/>" if fundo else ""
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {largura} {altura}' width='{largura}' height='{altura}'>{bg}"
            f"<g transform='translate(8 0)'>{simbolo_paths(cor_linha, cor_ponto)}</g>"
            f"<g transform='translate({tx} {ty})'><path d='{d}' fill='{cor_texto}'/></g>{tag}</svg>")


def svg_vertical(cor_texto, cor_linha, cor_ponto, fundo=None):
    d, w = text_to_path("Retena", BASE / "fontes" / "Sora-Variable.ttf", 64, 700, -0.025)
    W = int(max(w, 120) + 80); H = 214
    bg = f"<rect width='{W}' height='{H}' fill='{fundo}'/>" if fundo else ""
    sx = (W - 120) / 2
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}'>{bg}"
            f"<g transform='translate({sx} 4)'>{simbolo_paths(cor_linha, cor_ponto)}</g>"
            f"<g transform='translate({(W - w) / 2} 178)'><path d='{d}' fill='{cor_texto}'/></g></svg>")


arquivos = {
    # nome: (svg, fundo do PNG para conferência)
    "retena_horizontal_claro_sobre_escuro": (svg_horizontal("#FFFFFF", C["acento"], C["acento"]), C["primaria"]),
    "retena_horizontal_escuro_sobre_claro": (svg_horizontal(C["primaria"], C["acento"], C["acento"]), "#FFFFFF"),
    "retena_horizontal_mono_azul": (svg_horizontal(C["primaria"], C["primaria"], C["primaria"]), "#FFFFFF"),
    "retena_horizontal_mono_branco": (svg_horizontal("#FFFFFF", "#FFFFFF", "#FFFFFF"), C["primaria"]),
    "retena_horizontal_com_tagline_escuro": (svg_horizontal("#FFFFFF", C["acento"], C["acento"], tagline=M["tagline"], cor_tagline="#FFFFFF"), C["primaria"]),
    "retena_horizontal_com_tagline_claro": (svg_horizontal(C["primaria"], C["acento"], C["acento"], tagline=M["tagline"], cor_tagline=C["texto_corrido"]), "#FFFFFF"),
    "retena_vertical_claro_sobre_escuro": (svg_vertical("#FFFFFF", C["acento"], C["acento"]), C["primaria"]),
    "retena_vertical_escuro_sobre_claro": (svg_vertical(C["primaria"], C["acento"], C["acento"]), "#FFFFFF"),
    "retena_simbolo": (svg_simbolo(), C["primaria"]),
    "retena_simbolo_app": (svg_simbolo(fundo=C["primaria"]), "#FFFFFF"),
    "retena_simbolo_mono_azul": (svg_simbolo(cor_linha=C["primaria"], cor_ponto=C["primaria"]), "#FFFFFF"),
    "retena_favicon": (svg_simbolo(fundo=C["primaria"], raio=30), "#FFFFFF"),
}

for nome, (svg, fundo) in arquivos.items():
    (OUT / f"{nome}.svg").write_text(svg, encoding="utf-8")
    # PNG transparente em 4x via Edge headless (fundo transparente) + versão de conferência com fundo
    for sufixo, bgcss in (("", "transparent"), ("_preview", fundo)):
        import re
        vb = re.search(r"viewBox='0 0 (\d+) (\d+)'", svg)
        w, h = int(vb.group(1)), int(vb.group(2)); esc = 4
        html = (f"<html><body style='margin:0;background:{bgcss};width:{w*esc}px;height:{h*esc}px'>"
                f"<img src='{nome}.svg' style='width:{w*esc}px;height:{h*esc}px;display:block'/></body></html>")
        hp = OUT / f"_{nome}{sufixo}.html"; hp.write_text(html, encoding="utf-8")
        png = OUT / f"{nome}{sufixo}.png"
        profile = Path(os.environ.get("TEMP", ".")) / "retena_edge_profile"
        try:
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
                            "--disable-extensions", f"--user-data-dir={profile}", "--default-background-color=00000000",
                            f"--window-size={w*esc},{h*esc}", f"--screenshot={png}", "file:///" + str(hp).replace("\\", "/")],
                           capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            print("timeout ao renderizar", nome, sufixo)
        hp.unlink(missing_ok=True)
    print("ok", nome)
print("Logos em", OUT)
