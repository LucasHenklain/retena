# -*- coding: utf-8 -*-
"""
Kit oficial da Banca Final — Retena (Startup One / Enterprise Challenge Oracle, FIAP 4ESOA-2026) — versão comercial (v3)

Gera, nesta pasta:
  Retena_Banca_Final.pptx        deck principal (18 slides, um argumento por slide) + apêndice técnico A1–A15 para perguntas
  qr/*.png                       QR codes de marca (vídeo, site, repositório)
  notas_apresentador.json        notas por slide (fonte para o Guia do Apresentador)

Princípios desta versão (fusão do deck técnico v2 com a narrativa do deck EduRetain do colega):
  • história antes do método: gancho → antes/depois → "tarde demais" → solução → como funciona → prova → Oracle → negócio;
  • um número grande por slide, pouco texto, linguagem de compra (quem, onde, quanto em R$);
  • a parte técnica não sumiu: foi para o apêndice (A1–A15) e para os slides 11–12 (evidência e mapa da stack Oracle);
  • todos os números são os da entrega (base real anonimizada, teste temporal, evidências Oracle); estimativas estão rotuladas.
Design: tokens de marca (03_Marca/marca.json). Fonte Segoe UI (fallback oficial da marca em Windows; Sora/Inter ficam no PDF dos materiais HTML).
"""
import os, json
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image
import qrcode

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
OUT = os.path.join(AQUI, "Retena_Banca_Final.pptx")
QR_DIR = os.path.join(AQUI, "qr"); os.makedirs(QR_DIR, exist_ok=True)
IMG = lambda *p: os.path.join(ROOT, *p)

# ---------------------------------------------------------------- tokens de marca
AZUL = RGBColor(0x0B, 0x25, 0x45); AZUL_M = RGBColor(0x13, 0x31, 0x5C); AZUL_C = RGBColor(0x1B, 0x3F, 0x6E)
VERDE = RGBColor(0x2E, 0xC4, 0xB6); VERDE_ESC = RGBColor(0x1F, 0x8F, 0x85); VERDE_CLARO = RGBColor(0xE6, 0xF7, 0xF5)
AMBAR = RGBColor(0xFF, 0xB7, 0x03); AMBAR_CLARO = RGBColor(0xFF, 0xF4, 0xD6)
CORAL = RGBColor(0xFF, 0x6B, 0x4A); CORAL_CLARO = RGBColor(0xFF, 0xEC, 0xE6)
OFF = RGBColor(0xF6, 0xF7, 0xF9); BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRAFITE = RGBColor(0x3A, 0x4A, 0x5C); CINZA = RGBColor(0x94, 0xA3, 0xB8); LINHA = RGBColor(0xE2, 0xE8, 0xF0)
CARD_ESC = RGBColor(0x16, 0x35, 0x5E); CARD_ESC_B = RGBColor(0x2A, 0x4A, 0x73); DIM = RGBColor(0xC9, 0xD6, 0xE4); DIM2 = RGBColor(0x9F, 0xB3, 0xC8)
FONT = "Segoe UI"

LINKS = {
    "video": "https://youtu.be/HZrcLvIJCC4",
    "site": "https://lucashenklain.github.io/retena/",
    "dashboard": "https://lucashenklain.github.io/retena/dashboard/",
    "evidencias": "https://lucashenklain.github.io/retena/evidencias/evidencias.html",
    "repo": "https://github.com/LucasHenklain/retena",
}
EQUIPE = [("Lucas Dalmas", "RM551178", "Líder"), ("Lucas Emanuel", "RM97881", ""), ("Kayque Moraes", "RM97592", ""),
          ("Lucas Henklain", "RM99350", ""), ("Vinicius Pinheiro", "RM99198", "")]

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
NOTAS = []  # (n, titulo, texto)

def P(x): return Inches(x)

# ---------------------------------------------------------------- utilitários de baixo nível
def _alpha(el_color, pct):
    a = el_color.makeelement(qn("a:alpha"), {"val": str(int((100 - pct) * 1000))}); el_color.append(a)

def fill_alpha(shape, pct):
    sf = shape.fill._xPr.find(qn("a:solidFill"))
    if sf is not None:
        c = sf.find(qn("a:srgbClr"))
        if c is not None: _alpha(c, pct)

def line_alpha(shape, pct):
    ln = shape._element.spPr.find(qn("a:ln"))
    if ln is not None:
        sf = ln.find(qn("a:solidFill"))
        if sf is not None:
            c = sf.find(qn("a:srgbClr"))
            if c is not None: _alpha(c, pct)

def transicao(slide, tipo="fade", spd="med"):
    el = slide._element
    tr = etree.SubElement(el, qn("p:transition")); tr.set("spd", spd)
    etree.SubElement(tr, qn(f"p:{tipo}"))
    anchor = el.find(qn("p:clrMapOvr"))
    (anchor if anchor is not None else el.find(qn("p:cSld"))).addnext(tr)

def fundo(slide, escuro):
    f = slide.background.fill; f.gradient(); f.gradient_angle = 135 if escuro else 90
    st = f.gradient_stops
    if escuro:
        st[0].color.rgb = AZUL_M; st[0].position = 0.0; st[1].color.rgb = AZUL; st[1].position = 1.0
    else:
        st[0].color.rgb = BRANCO; st[0].position = 0.0; st[1].color.rgb = OFF; st[1].position = 1.0

def rect(slide, x, y, w, h, cor, radius=None, line=None, line_w=1.0):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, P(x), P(y), P(w), P(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = cor
    if line is not None: shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    else: shp.line.fill.background()
    if radius: shp.adjustments[0] = radius
    shp.shadow.inherit = False; shp.text_frame.text = ""
    return shp

def oval(slide, x, y, d, *args, cor=None, line=None):
    """oval(slide, x, y, d, cor) ou oval(slide, x, y, w, h, cor)."""
    if len(args) == 2: h, cor = args
    elif len(args) == 1: h = d; cor = args[0]
    else: h = d
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, P(x), P(y), P(d), P(h)); o.fill.solid(); o.fill.fore_color.rgb = cor
    if line is not None: o.line.color.rgb = line; o.line.width = Pt(1.5)
    else: o.line.fill.background()
    o.shadow.inherit = False; return o

def text(slide, x, y, w, h, txt, size=14, cor=GRAFITE, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         italic=False, spacing=1.15, margin=0.0, font=FONT, espaco_depois=0):
    tb = slide.shapes.add_textbox(P(x), P(y), P(w), P(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = P(margin); tf.vertical_anchor = anchor
    linhas = txt if isinstance(txt, list) else [txt]
    for i, l in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = spacing
        if espaco_depois: p.space_after = Pt(espaco_depois)
        runs = l if isinstance(l, list) else [(l, bold, cor)]
        for r in runs:
            t, b, c = (r + (bold, cor))[:3] if isinstance(r, tuple) else (r, bold, cor)
            run = p.add_run(); run.text = t; run.font.size = Pt(size); run.font.bold = b; run.font.italic = italic
            run.font.color.rgb = c; run.font.name = font
    return tb

def bullets(slide, x, y, w, itens, size=12.5, cor=GRAFITE, dot=VERDE, gap=0.10, char_por_pol=9.0):
    yy = y
    for it in itens:
        oval(slide, x, yy + 0.085, 0.12, dot)
        plain = it if isinstance(it, str) else "".join(r[0] if isinstance(r, tuple) else r for r in it)
        nlin = max(1, int(len(plain) / ((w - 0.3) * char_por_pol * (12.5 / size))) + 1)
        hh = 0.10 + 0.245 * nlin * (size / 12.5)
        text(slide, x + 0.28, yy - 0.02, w - 0.28, hh, [it] if not isinstance(it, str) else it, size=size, cor=cor)
        yy += hh + gap
    return yy

TRIM_DIR = os.path.join(AQUI, "_tmp_trim"); os.makedirs(TRIM_DIR, exist_ok=True)
def _trim(path, margem=10):
    from PIL import ImageChops
    im = Image.open(path).convert("RGB"); bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0)
    bbox = diff.getbbox()
    if not bbox: return path
    l, t, r, b = bbox; l = max(0, l - margem); t = max(0, t - margem); r = min(im.width, r + margem); b = min(im.height, b + margem)
    out = os.path.join(TRIM_DIR, os.path.basename(path)); im.crop((l, t, r, b)).save(out); return out

def img_fit(slide, path, x, y, w, h, rounded=False, trim=False):
    if not os.path.exists(path):
        rect(slide, x, y, w, h, LINHA); text(slide, x, y, w, h, os.path.basename(path), size=9, cor=CINZA, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE); return None
    if trim: path = _trim(path)
    iw, ih = Image.open(path).size; r = min(w / iw, h / ih); nw, nh = iw * r, ih * r
    pic = slide.shapes.add_picture(path, P(x + (w - nw) / 2), P(y + (h - nh) / 2), P(nw), P(nh))
    if rounded: _arredondar(pic)
    return pic

def img_cover(slide, path, x, y, w, h, rounded=False, radius=0.06):
    if not os.path.exists(path): return rect(slide, x, y, w, h, LINHA)
    iw, ih = Image.open(path).size; box = w / h; src = iw / ih
    pic = slide.shapes.add_picture(path, P(x), P(y), P(w), P(h))
    if src > box: e = 1 - box / src; pic.crop_left = e / 2; pic.crop_right = e / 2
    else: e = 1 - src / box; pic.crop_top = e / 2; pic.crop_bottom = e / 2
    if rounded: _arredondar(pic, radius)
    return pic

def _arredondar(pic, radius=0.06):
    try:
        pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
        prst = pic._element.spPr.find(qn("a:prstGeom")); av = prst.find(qn("a:avLst"))
        if av is None: av = etree.SubElement(prst, qn("a:avLst"))
        for g in list(av): av.remove(g)
        gd = etree.SubElement(av, qn("a:gd")); gd.set("name", "adj"); gd.set("fmla", f"val {int(radius * 100000)}")
    except Exception:
        pass

def veu(slide, x, y, w, h, cor=AZUL, pct=45):
    v = rect(slide, x, y, w, h, cor); fill_alpha(v, pct); return v

def pulso(slide, x, y, w, cor=VERDE, pct=82, espessura=10):
    pts = [(8, 72), (32, 72), (43, 88), (55, 50), (65, 72), (78, 72), (99, 44)]
    esc = P(w) / 120.0
    ff = slide.shapes.build_freeform(start_x=pts[0][0], start_y=pts[0][1], scale=esc)
    ff.add_line_segments(pts[1:], close=False)
    shp = ff.convert_to_shape(P(x), P(y))
    shp.fill.background(); shp.line.color.rgb = cor; shp.line.width = Pt(espessura); shp.shadow.inherit = False
    ln = shp._element.spPr.find(qn("a:ln"))
    if ln is not None:
        ln.set("cap", "rnd"); etree.SubElement(ln, qn("a:round"))
    line_alpha(shp, pct)
    d = 17 * w / 120.0
    o = oval(slide, x + (104 - 8.5) * w / 120.0, y + (38 - 8.5) * w / 120.0, d, cor); fill_alpha(o, pct)
    return shp

def logo(slide, escuro, x=11.45, y=0.42, h=0.44):
    p = IMG("03_Marca", "logo", "retena_horizontal_claro_sobre_escuro.png" if escuro else "retena_horizontal_escuro_sobre_claro.png")
    if os.path.exists(p): slide.shapes.add_picture(p, P(x), P(y), height=P(h))

def kicker(slide, x, y, w, txt, cor=VERDE, size=11):
    text(slide, x, y, w, 0.3, txt.upper(), size=size, cor=cor, bold=True)

def titulo(slide, kick, tit, escuro=False, y=0.55, size=30):
    if size == 30 and kick[:1] == "A" and kick[1:2].isdigit(): size = 24  # apêndice: títulos mais longos, uma linha
    kicker(slide, 0.6, y, 10.5, kick)
    text(slide, 0.6, y + 0.3, 10.6, 1.0, tit, size=size, cor=BRANCO if escuro else AZUL, bold=True, spacing=1.05)

def rodape(slide, escuro, n):
    c = DIM2 if escuro else CINZA
    text(slide, 0.6, 7.05, 9.5, 0.3, "Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026 · Banca Final 23/09/2026", size=9.5, cor=c)
    text(slide, 12.0, 7.05, 0.75, 0.3, f"{n:02d}", size=9.5, cor=c, align=PP_ALIGN.RIGHT)
    logo(slide, escuro)

def card(slide, x, y, w, h, escuro=False, radius=0.06):
    return rect(slide, x, y, w, h, CARD_ESC if escuro else BRANCO, radius=radius, line=CARD_ESC_B if escuro else LINHA)

def pill(slide, x, y, w, txt, bg=VERDE, fg=AZUL, size=9.5, h=0.32):
    r = rect(slide, x, y, w, h, bg, radius=0.5)
    text(slide, x, y, w, h, txt, size=size, cor=fg, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return r

def stat(slide, x, y, w, num, label, sub=None, escuro=False, cor_num=None, size=34):
    text(slide, x, y, w, 0.7, num, size=size, cor=cor_num or (VERDE if escuro else AZUL), bold=True)
    text(slide, x, y + 0.66, w, 0.42, label, size=12, cor=BRANCO if escuro else AZUL, bold=True)
    if sub: text(slide, x, y + 1.02, w, 0.6, sub, size=10, cor=DIM if escuro else GRAFITE)

def numero(slide, x, y, d, n, bg=VERDE, fg=AZUL, size=15):
    oval(slide, x, y, d, bg); text(slide, x, y, d, d, str(n), size=size, cor=fg, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def seta(slide, x, y, escuro=False, size=22):
    text(slide, x, y, 0.3, 0.5, "›", size=size, cor=VERDE, bold=True, align=PP_ALIGN.CENTER)

def tabela(slide, x, y, w, h, cab, linhas, larguras, escuro=False, size=10.5, destaque_linha=None, alinh_centro_apartir=1, cor_cab=None):
    tbl = slide.shapes.add_table(len(linhas) + 1, len(cab), P(x), P(y), P(w), P(h)).table
    for j, lw in enumerate(larguras): tbl.columns[j].width = P(lw)
    cab_bg = cor_cab or (VERDE if escuro else AZUL); cab_fg = AZUL if escuro else BRANCO
    for j, c in enumerate(cab):
        cell = tbl.cell(0, j); cell.text = c; cell.fill.solid(); cell.fill.fore_color.rgb = cab_bg; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = P(0.08); cell.margin_top = cell.margin_bottom = P(0.03)
        pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.LEFT if j < alinh_centro_apartir else PP_ALIGN.CENTER
        for r in pp.runs: r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = cab_fg; r.font.name = FONT
    for i, row in enumerate(linhas, start=1):
        for j, v in enumerate(row):
            cell = tbl.cell(i, j); cell.text = v; cell.fill.solid(); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = P(0.08); cell.margin_top = cell.margin_bottom = P(0.03)
            if escuro: cell.fill.fore_color.rgb = CARD_ESC if i % 2 else AZUL_C
            else: cell.fill.fore_color.rgb = BRANCO if i % 2 else OFF
            if destaque_linha is not None and i == destaque_linha: cell.fill.fore_color.rgb = VERDE_CLARO if not escuro else VERDE_ESC
            pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.LEFT if j < alinh_centro_apartir else PP_ALIGN.CENTER
            for r in pp.runs:
                r.font.size = Pt(size); r.font.name = FONT; r.font.bold = (destaque_linha is not None and i == destaque_linha)
                r.font.color.rgb = BRANCO if escuro else (AZUL if j == 0 else GRAFITE)
    return tbl

def qr(nome, url, cor="#0B2545"):
    p = os.path.join(QR_DIR, f"{nome}.png")
    q = qrcode.QRCode(box_size=12, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M); q.add_data(url); q.make(fit=True)
    q.make_image(fill_color=cor, back_color="white").save(p); return p

def notes(slide, n, titulo_txt, txt):
    slide.notes_slide.notes_text_frame.text = txt; NOTAS.append({"slide": n, "titulo": titulo_txt, "notas": txt})

N = 0
def novo(escuro=False, motivo=True):
    global N; N += 1
    s = prs.slides.add_slide(BLANK); fundo(s, escuro); transicao(s)
    if escuro and motivo: pulso(s, 7.9, 3.3, 6.2, pct=88, espessura=14)
    return s

lg = IMG("03_Marca", "logo", "retena_horizontal_claro_sobre_escuro.png")

# ================================================================= 1 CAPA
s = novo(True, motivo=False)
img_cover(s, IMG("04_Landing_Page", "img", "aluno_noite.jpg"), 7.45, 0, 5.883, 7.5); veu(s, 7.45, 0, 5.883, 7.5, AZUL, 40)
rect(s, 7.45, 0, 0.06, 7.5, VERDE)
pulso(s, 8.6, 4.9, 3.8, pct=45, espessura=16)
if os.path.exists(lg): s.shapes.add_picture(lg, P(0.7), P(0.7), height=P(0.9))
pill(s, 0.7, 2.05, 5.2, "Startup One · Enterprise Challenge Oracle · FIAP 2026", bg=CARD_ESC, fg=VERDE, size=9.5, h=0.34)
text(s, 0.7, 2.6, 6.5, 2.1, [[("Ninguém desiste", True, BRANCO)], [("de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=36, spacing=1.02)
text(s, 0.7, 4.85, 6.3, 0.95, "Radar de permanência para o ensino superior EAD: lê os sinais que o LMS já registra e entrega, toda segunda, quem chamar, por quê e o que dizer. Dentro do Oracle AI Database.", size=13.5, cor=DIM, spacing=1.3)
text(s, 0.7, 6.05, 6.5, 0.7, ["Lucas Dalmas (RM551178) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592)", "Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)"], size=10.5, cor=DIM, spacing=1.3)
text(s, 0.7, 6.95, 6.5, 0.3, "Banca Final · 23 de setembro de 2026 · Engenharia de Software, 4º ano", size=9.5, cor=DIM2)
notes(s, N, "Capa", "Abertura (20 s). Boa noite. Toda noite, milhões de brasileiros abrem o notebook depois do trabalho para estudar a distância. Todo ano, quatro em cada dez desistem. Ninguém desiste de repente — mas a instituição só percebe quando a mensalidade para. Nós somos a Retena.")

# ================================================================= 2 GANCHO
s = novo(True, motivo=False)
img_cover(s, IMG("04_Landing_Page", "img", "campus.jpg"), 0, 0, 13.333, 7.5); veu(s, 0, 0, 13.333, 7.5, AZUL, 66)
pulso(s, 9.0, 5.0, 3.6, pct=35, espessura=16)
logo(s, True, x=0.9, y=0.7, h=0.55)
kicker(s, 0.9, 2.0, 10, "O problema que todo mundo vê e ninguém mede")
text(s, 0.9, 2.4, 11.4, 2.5, [[("5,2 milhões de brasileiros estudam a distância.", True, BRANCO)], [("A maioria, à noite, depois do trabalho.", True, BRANCO)], [("Quatro em cada dez desistem a cada ano.", True, VERDE)]], size=34, spacing=1.08)
text(s, 0.9, 5.15, 9.8, 0.9, "A instituição só percebe quando a mensalidade para. Semanas antes, o LMS já tinha registrado o silêncio — e ninguém estava ouvindo.", size=15, cor=DIM, spacing=1.3)
text(s, 0.9, 6.85, 11.5, 0.3, "Fontes: INEP, Censo da Educação Superior 2024 (5,19 mi matrículas EAD, 50,7% do total); Instituto Semesp, 16º Mapa do Ensino Superior no Brasil 2026 (desistência anual no EAD: 41,6%).", size=9, cor=DIM2)
notes(s, N, "Gancho", "Gancho (15 s). Você já reparou como as turmas EAD começam cheias e vão esvaziando? 5,2 milhões de alunos, metade do ensino superior; 41,6% desistem por ano. É o problema que todo mundo vê e ninguém mede a tempo.")

# ================================================================= 3 ANTES E DEPOIS
s = novo(False)
titulo(s, "Antes e depois", "Hoje a instituição reage. Com a Retena, ela antecipa.")
card(s, 0.6, 1.95, 5.95, 4.75); rect(s, 0.9, 2.2, 0.7, 0.07, CORAL)
text(s, 0.9, 2.35, 5.4, 0.6, "ANTES", size=26, cor=CORAL, bold=True)
antes = [("Descobre tarde", "A evasão aparece no financeiro, quando a mensalidade já parou."), ("Age no genérico", "E-mail padrão, desconto de emergência, ligação de cobrança."), ("Prioriza no escuro", "12 tutores, 30% da turma em silêncio, nenhum critério."), ("Não mede", "Ninguém sabe quantos voltaram nem quanto isso valeu.")]
for i, (a, b) in enumerate(antes):
    y = 3.15 + i * 0.86
    oval(s, 0.9, y + 0.04, 0.34, CORAL_CLARO, line=CORAL); text(s, 0.9, y + 0.04, 0.34, 0.34, "✕", size=11, cor=CORAL, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 1.4, y - 0.03, 4.9, 0.35, a, size=13.5, cor=AZUL, bold=True); text(s, 1.4, y + 0.3, 4.9, 0.5, b, size=10.5, cor=GRAFITE)
rect(s, 6.8, 1.95, 5.95, 4.75, AZUL, radius=0.06); rect(s, 7.1, 2.2, 0.7, 0.07, VERDE)
text(s, 7.1, 2.35, 5.4, 0.6, "COM A RETENA", size=26, cor=VERDE, bold=True)
depois = [("Percebe antes", "Segunda, 8h: a coordenação recebe quem está a duas semanas de sumir."), ("Age no específico", "Por quê, quando (19h–22h) e o que dizer — aluno por aluno."), ("Prioriza com critério", "Alto risco e ainda ativo primeiro: onde uma conversa ainda muda o rumo."), ("Mede em R$", "Resultado registrado em um clique; receita preservada; o modelo aprende.")]
for i, (a, b) in enumerate(depois):
    y = 3.15 + i * 0.86
    oval(s, 7.1, y + 0.04, 0.34, VERDE); text(s, 7.1, y + 0.04, 0.34, 0.34, "✓", size=11, cor=AZUL, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 7.6, y - 0.03, 4.9, 0.35, a, size=13.5, cor=BRANCO, bold=True); text(s, 7.6, y + 0.3, 4.9, 0.5, b, size=10.5, cor=DIM)
rodape(s, False, N)
notes(s, N, "Antes e depois", "Antes e depois (30 s). Hoje: descobre no financeiro, age com e-mail genérico, prioriza no escuro e não mede. Com a Retena: segunda de manhã a coordenação sabe quem chamar, por quê e o que dizer; contata no horário em que o aluno estuda; registra o resultado e mede em reais.")

# ================================================================= 4 TARDE DEMAIS (número grande)
s = novo(False)
titulo(s, "Tarde demais", "Quando a instituição percebe, o aluno já decidiu.")
text(s, 0.6, 1.8, 6.4, 1.9, "30%", size=120, cor=CORAL, bold=True, spacing=0.95)
text(s, 0.6, 3.85, 6.2, 1.1, [[("da turma em silêncio há mais de duas semanas.", True, AZUL)], [("Nenhum alerta disparou.", True, CORAL)]], size=20, spacing=1.1)
text(s, 0.6, 5.1, 6.2, 1.3, "61 de 203 alunos, em um único dia, na base real anonimizada de uma IES parceira: 684.723 eventos de LMS, cinco fases, janeiro a agosto de 2026. O LMS registrou cada sinal. Ninguém estava ouvindo.", size=12, cor=GRAFITE, spacing=1.3)
oval(s, 7.5, 1.9, 4.6, 4.6, AZUL)
text(s, 7.5, 2.95, 4.6, 1.1, "61", size=76, cor=BRANCO, bold=True, align=PP_ALIGN.CENTER)
text(s, 7.5, 4.25, 4.6, 0.9, ["alunos em silêncio", "há mais de 14 dias"], size=14, cor=DIM, align=PP_ALIGN.CENTER)
oval(s, 10.85, 4.85, 2.0, 2.0, VERDE)
text(s, 10.85, 5.15, 2.0, 0.7, "0", size=34, cor=AZUL, bold=True, align=PP_ALIGN.CENTER)
text(s, 10.85, 5.95, 2.0, 0.5, "alertas", size=12, cor=AZUL, bold=True, align=PP_ALIGN.CENTER)
oval(s, 6.75, 5.35, 1.55, 1.55, AMBAR)
text(s, 6.75, 5.55, 1.55, 0.6, "12%", size=22, cor=AZUL, bold=True, align=PP_ALIGN.CENTER)
text(s, 6.75, 6.12, 1.55, 0.7, "ingressantes perdidos em 7 meses", size=8.5, cor=AZUL, align=PP_ALIGN.CENTER)
rodape(s, False, N)
notes(s, N, "Tarde demais", "Tarde demais (25 s). Isto é a base real de uma IES parceira: 685 mil eventos de 203 alunos. Em um único dia, 61 alunos — 30% da turma — estavam há mais de duas semanas sem acessar. Zero alertas. Em sete meses, 12% dos ingressantes se perderam. O LMS sabia; faltava alguém ouvir.")

# ================================================================= 5 PARA QUEM
s = novo(False)
titulo(s, "Para quem", "Quem assina protege receita. Quem usa ganha critério.")
pers = [("coordenadora.jpg", "Renata · Diretora de Operações", "Compra", "Responde pela receita das mensalidades em um centro universitário com ~12 mil alunos EAD.", "Quer ver a evasão em R$ e o retorno em rematrícula."),
        ("tutor.jpg", "Mariana · Coord. de Permanência", "Usa toda segunda", "Lidera 12 tutores. Hoje descobre a evasão tarde e prioriza no escuro.", "Quer a lista de quem chamar, por quê e como."),
        ("aluno_noite.jpg", "Aluno EAD trabalhador", "Beneficiário", "Estuda das 19h às 22h. Trava em um capítulo, perde o ritmo e, sem ninguém perceber, desiste.", "Responde a um plano concreto, não a cobrança.")]
for i, (im, nome, papel, desc, quer) in enumerate(pers):
    x = 0.6 + i * 4.1; card(s, x, 1.95, 3.85, 4.75)
    img_cover(s, IMG("04_Landing_Page", "img", im), x + 0.12, 2.07, 3.61, 1.85, rounded=True, radius=0.08)
    pill(s, x + 0.2, 4.05, 1.75, papel, size=9, h=0.3)
    text(s, x + 0.2, 4.45, 3.45, 0.5, nome, size=13.5, cor=AZUL, bold=True)
    text(s, x + 0.2, 4.95, 3.45, 0.8, desc, size=10.5, cor=GRAFITE)
    rect(s, x + 0.2, 5.8, 3.45, 0.7, VERDE_CLARO, radius=0.1); text(s, x + 0.35, 5.85, 3.2, 0.6, quer, size=10, cor=AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
rodape(s, False, N)
notes(s, N, "Para quem", "Público (20 s). Cliente: a IES privada com EAD. Quem compra é a diretora de operações, que responde pela receita. Quem usa toda segunda é a coordenadora de permanência e seus tutores. Quem ganha é o aluno trabalhador que estuda à noite.")

# ================================================================= 6 SOLUÇÃO
s = novo(True)
titulo(s, "A solução", "Três respostas que o BI não dá: quem, onde e quanto.", escuro=True)
pil = [("QUEM", "Score de risco explicável", "Probabilidade de cada aluno ficar 21 dias sem acessar, recalculada todo domingo, com o motivo em linguagem simples: \"12 dias sem acesso, queda de 70% nos eventos, parado no cap 2\"."),
       ("ONDE", "Mapa de atrito de conteúdo", "Capítulos e formatos onde os alunos travam — com recomendação concreta para a coordenação pedagógica ajustar o curso."),
       ("QUANTO", "Fila semanal com resultado em R$", "Quem contatar, por quê, quando (19h–22h) e o que dizer. Resultado registrado em um clique e receita preservada medida em reais.")]
for i, (k, t, d) in enumerate(pil):
    x = 0.6 + i * 4.1; card(s, x, 1.95, 3.85, 3.6, True)
    text(s, x + 0.3, 2.15, 3.3, 0.6, k, size=26, cor=VERDE, bold=True)
    text(s, x + 0.3, 2.85, 3.3, 0.5, t, size=15, cor=BRANCO, bold=True); text(s, x + 0.3, 3.4, 3.3, 2.0, d, size=11, cor=DIM, spacing=1.25)
rect(s, 0.6, 5.85, 12.15, 0.85, CARD_ESC, radius=0.1, line=CARD_ESC_B)
for i, t in enumerate(["Toda segunda, 8h", "Dentro do Oracle AI Database", "O dado do aluno não sai da instituição", "Primeira fila em 30 dias"]):
    pill(s, 0.85 + i * 3.0, 6.1, 2.75, t, bg=AZUL_C, fg=BRANCO, size=10.5, h=0.36)
rodape(s, True, N)
notes(s, N, "A solução", "Solução (30 s). A Retena transforma os logs em três respostas: QUEM está a duas semanas de sumir, ONDE o conteúdo trava e QUANTO isso vale em reais — com a fila de segunda dizendo quem chamar, por quê, quando e o que dizer. Tudo dentro do banco que a instituição já usa.")

# ================================================================= 7 COMO FUNCIONA EM 4 PASSOS
s = novo(False)
titulo(s, "Como funciona", "Do LMS à segunda-feira, em quatro passos.")
passos = [("Conecte o LMS", "Export CSV padrão ou API para o banco Oracle. Sem projeto de TI: a carga de 684 mil eventos levou 72 segundos.", ["Autonomous AI Database", "Object Storage · DBMS_CLOUD"]),
          ("O risco nasce dentro do banco", "Features em SQL; Oracle Machine Learning treina e pontua cada aluno toda semana. O dado não sai da instituição.", ["OML · DBMS_DATA_MINING", "DBMS_SCHEDULER"]),
          ("A fila chega à coordenação", "Segunda, 8h: quem chamar, por quê, quando (19h–22h) e o que dizer, com o kit de retomada.", ["APEX", "Select AI (perguntas em português)"]),
          ("O resultado volta em R$", "Contato registrado em um clique; receita preservada medida; o modelo retreina com o que funcionou.", ["Views JSON · Duality View", "Retreino mensal"])]
for i, (t, d, tools) in enumerate(passos):
    x = 0.6 + i * 3.1; card(s, x, 1.95, 2.85, 4.35)
    numero(s, x + 0.25, 2.2, 0.62, f"0{i + 1}", size=17)
    text(s, x + 0.25, 3.0, 2.4, 0.75, t, size=14.5, cor=AZUL, bold=True, spacing=1.05)
    text(s, x + 0.25, 3.75, 2.4, 1.5, d, size=10.5, cor=GRAFITE, spacing=1.25)
    kicker(s, x + 0.25, 5.2, 2.4, "Oracle", cor=CINZA, size=8.5)
    for j, tl in enumerate(tools): pill(s, x + 0.25, 5.45 + j * 0.38, 2.35, tl, bg=VERDE_CLARO, fg=AZUL, size=8.5, h=0.3)
    if i < 3: seta(s, x + 2.85, 3.85)
text(s, 0.6, 6.45, 12.1, 0.4, "Sem servidor de ML, sem cientista de dados dedicado, sem ETL externo · LGPD por arquitetura · executado no Oracle AI Database 26ai; caminho para o Autonomous na OCI documentado (runbook de 60 min).", size=10, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "Como funciona", "Como funciona (35 s). Quatro passos: a IES exporta o LMS para o banco Oracle; o risco é calculado dentro do banco com Oracle Machine Learning; a fila de segunda chega à coordenação em APEX; o resultado volta em reais e retreina o modelo. Sem servidor de ML, sem cientista de dados, sem o dado sair da instituição.")

# ================================================================= 8 DEMONSTRAÇÃO
s = novo(False)
titulo(s, "Demonstração ao vivo", "Painel da diretoria, fila da coordenação, base real.")
card(s, 0.6, 1.95, 8.3, 4.75); img_fit(s, IMG("05_MVP", "outputs", "figs", "dashboard_hero_1920x1080.png"), 0.7, 2.05, 8.1, 4.55, rounded=True)
kp = [("Visão da diretoria", "alunos para chamar esta semana e receita anual em risco, em R$ — com o ticket da própria IES"), ("Fila de segunda", "196 alunos ordenados por risco; clique abre o motivo em linguagem simples e a ação sugerida"), ("Mapa de atrito", "fase × capítulo: onde o conteúdo trava e o que ajustar"), ("Para o time técnico", "métricas, calibração e estabilidade do modelo — em uma aba separada")]
for i, (a, b) in enumerate(kp):
    y = 1.95 + i * 1.0; card(s, 9.25, y, 3.5, 0.88); text(s, 9.45, y + 0.08, 3.2, 0.35, a, size=12, cor=AZUL, bold=True); text(s, 9.45, y + 0.4, 3.2, 0.48, b, size=9.3, cor=GRAFITE)
pill(s, 9.25, 6.0, 3.5, "lucashenklain.github.io/retena/dashboard", bg=AZUL, fg=BRANCO, size=10.5, h=0.62)
rodape(s, False, N)
notes(s, N, "Demonstração", "Demonstração (1 min). Dashboard publicado, já aberto. 1) Visão 'Diretoria': alunos para chamar esta semana e receita em risco em R$ — mudar o ticket e mostrar que recalcula. 2) Visão 'Coordenação': buscar 'Aluno 0227', clicar e abrir o motivo e a ação sugerida; mostrar o mapa de atrito. 3) Se perguntarem, visão 'Time técnico'. Tudo com a base real anonimizada. Sem internet: apêndice A1.")

# ================================================================= 9 RESULTADOS EM LINGUAGEM SIMPLES
s = novo(False)
titulo(s, "Funciona? Testamos no futuro, sem retoque.", "Treinado até maio, testado de junho a agosto.")
res = [("95 em 100", "alunos apontados como alto risco de fato ficaram inativos", CORAL), ("3×", "mais acerto do que escolher ao acaso quem chamar (top-20%)", AZUL), ("0,88", "AUC-ROC no teste temporal; 88% de precisão no top-20%", AZUL)]
for i, (a, b, c) in enumerate(res):
    x = 0.6 + i * 2.15; card(s, x, 1.95, 2.0, 2.15); text(s, x + 0.18, 2.05, 1.7, 0.8, a, size=30 if i else 21, cor=c, bold=True, anchor=MSO_ANCHOR.MIDDLE); text(s, x + 0.18, 2.9, 1.7, 1.1, b, size=9.8, cor=GRAFITE)
cd = CategoryChartData(); cd.categories = ["Alto (≥ 0,60)", "Médio (0,30–0,60)", "Baixo (< 0,30)"]; cd.add_series("Inatividade observada", (95.2, 48.7, 14.3))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, P(0.6), P(4.3), P(6.4), P(2.4), cd).chart
gf.has_legend = False; gf.has_title = True; gf.chart_title.text_frame.text = "De cada 100 alunos em cada faixa, quantos realmente sumiram"
tt = gf.chart_title.text_frame.paragraphs[0].runs[0].font; tt.size = Pt(11.5); tt.bold = True; tt.color.rgb = AZUL; tt.name = FONT
pl = gf.plots[0]; pl.gap_width = 50; pl.has_data_labels = True; dl = pl.data_labels; dl.position = XL_LABEL_POSITION.OUTSIDE_END; dl.font.size = Pt(11); dl.font.bold = True; dl.font.color.rgb = AZUL; dl.number_format = '0"%"'; dl.number_format_is_linked = False
ser = pl.series[0]
for idx, c in enumerate((CORAL, AMBAR, VERDE)):
    pt = ser.points[idx]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
gf.category_axis.tick_labels.font.size = Pt(10); gf.category_axis.tick_labels.font.color.rgb = GRAFITE; gf.category_axis.format.line.color.rgb = LINHA; gf.category_axis.reverse_order = True
va = gf.value_axis; va.visible = False; va.has_major_gridlines = False; va.maximum_scale = 112; va.minimum_scale = 0
rect(s, 7.3, 1.95, 5.45, 2.5, AZUL, radius=0.08)
text(s, 7.55, 2.1, 5.0, 0.35, "Não é só a nossa amostra", size=12.5, cor=VERDE, bold=True)
text(s, 7.55, 2.5, 5.0, 1.9, [[("Mesmo método em ", False, BRANCO), ("24.392 alunos", True, VERDE), (" da Open University (OULAD, Reino Unido): ", False, BRANCO), ("AUC 0,92 e 3,5× de acerto", True, VERDE), (" no top-20% — outra instituição, outro país, outro LMS. Também rodou dentro do Oracle: Random Forest in-database com AUC 0,949.", False, BRANCO)]], size=11.5, spacing=1.3)
card(s, 7.3, 4.6, 5.45, 2.1); text(s, 7.5, 4.7, 5.05, 0.35, "O que dizemos com honestidade", size=12, cor=AZUL, bold=True)
bullets(s, 7.5, 5.08, 5.05, ["Amostra de um curso: retreino com os dados de cada IES antes de produção.", "Prevemos 21 dias de silêncio, não o cancelamento: é o ponto em que o contato ainda funciona.", "Entre alunos ainda ativos, antecipar é mais difícil (AUC 0,74) — e é aí que a fila prioriza."], size=9.5, gap=0.03)
rodape(s, False, N)
notes(s, N, "Resultados", "Resultados (40 s). Treinamos nos primeiros meses e testamos nos seguintes, sem olhar o futuro. Dos alunos que apontamos como alto risco, 95 em 100 de fato sumiram; priorizar pela Retena acerta 3 vezes mais do que ao acaso. E não é só a nossa amostra: o mesmo método em 24 mil alunos da Open University deu AUC 0,92. Limitações ditas na cara: amostra de um curso, rótulo comportamental, antecipar é mais difícil do que confirmar.")

# ================================================================= 10 POR QUE ORACLE
s = novo(False)
titulo(s, "Por que dentro do Oracle", "O modelo mora onde o dado já mora.")
pilares = [("Segurança e LGPD", "A objeção nº 1 da diretoria desaparece", ["O dado do aluno nunca sai do banco que a IES já controla: sem ETL externo, sem servidor de ML, sem nuvem de terceiros.", "Pseudonimização fora do painel; TDE, auditoria e perfis de acesso nativos do Autonomous.", "Base legal: execução do contrato educacional e apoio acadêmico."]),
           ("Sem projeto de TI", "Da carga à primeira fila em 30 dias", ["Features em SQL, treino e scoring com Oracle Machine Learning (DBMS_DATA_MINING), job semanal com DBMS_SCHEDULER.", "Painel em APEX e perguntas em português com Select AI — sem cientista de dados dedicado na IES.", "Entrada por CSV padrão do LMS (Object Storage + DBMS_CLOUD)."]),
           ("Escala e canal", "Margem de software, venda por ecossistema", ["Um schema por IES no Autonomous Serverless com auto-scaling: custo marginal por aluno próximo de zero, margem bruta alvo de 80%.", "ERPs acadêmicos e megagrupos já rodam Oracle: a Retena entra como extensão do que a IES tem.", "Portátil para qualquer LMS Moodle-like — provado no OULAD."])]
for i, (t, sub, its) in enumerate(pilares):
    x = 0.6 + i * 4.1; card(s, x, 1.95, 3.85, 4.75); rect(s, x, 1.95, 3.85, 0.09, VERDE if i == 1 else AZUL)
    text(s, x + 0.25, 2.2, 3.4, 0.45, t, size=16, cor=AZUL, bold=True); text(s, x + 0.25, 2.65, 3.4, 0.4, sub, size=10.5, cor=VERDE_ESC, bold=True)
    bullets(s, x + 0.25, 3.15, 3.4, its, size=10.3, gap=0.1)
rodape(s, False, N)
notes(s, N, "Por que dentro do Oracle", "Por que Oracle (30 s). Três razões de negócio, não de tecnologia: LGPD — o dado do aluno não sai do banco da instituição, e a objeção número um da diretoria desaparece; time-to-value — features em SQL, Oracle Machine Learning, APEX, sem cientista de dados, primeira fila em 30 dias; escala e canal — Autonomous Serverless com custo marginal perto de zero e um ecossistema que já roda Oracle nas IES.")

# ================================================================= 11 EVIDÊNCIA ORACLE
s = novo(True)
titulo(s, "Integração executada, não desenhada", "Oracle AI Database 26ai + OML: já roda.", escuro=True)
card(s, 0.6, 1.95, 7.4, 4.75, True); img_fit(s, IMG("06_Oracle", "evidencias", "evidencia_04.png"), 0.7, 2.03, 7.2, 4.6, rounded=True)
ev = [("684.723", "eventos do LMS carregados no banco via python-oracledb em 72 segundos"), ("3 modelos", "Random Forest e GLM treinados dentro do banco com DBMS_DATA_MINING"), ("AUC 0,949", "Random Forest in-database no teste temporal (protocolo próprio, complementar ao 0,88 do pipeline Python)"), ("SQL + JSON", "PREDICTION_PROBABILITY e PREDICTION_DETAILS; views JSON, Duality View, MERGE idempotente e job semanal")]
for i, (a, b) in enumerate(ev):
    y = 1.95 + i * 1.2; card(s, 8.3, y, 4.45, 1.05, True); text(s, 8.5, y + 0.14, 1.8, 0.5, a, size=17, cor=VERDE, bold=True); text(s, 10.2, y + 0.1, 2.45, 0.9, b, size=9.3, cor=BRANCO)
text(s, 8.3, 6.72, 4.45, 0.3, "Evidências com timestamps em 06_Oracle/evidencias · reexecutado em 22/09/2026 sem erros", size=9, cor=DIM)
rodape(s, True, N)
notes(s, N, "Integração executada", "Evidência Oracle (30 s). Isto não é um desenho: carregamos os 685 mil eventos no Oracle AI Database 26ai, calculamos as features em SQL, treinamos três modelos dentro do banco com DBMS_DATA_MINING e expusemos o risco por SQL e JSON. Random Forest com AUC 0,949 no teste temporal. Reexecutamos tudo ontem, do zero, sem erros. Se perguntarem sobre 0,88 × 0,95: duas implementações independentes, ambas com teste temporal; os números não são comparáveis um a um.")

# ================================================================= 12 MAPA DA STACK ORACLE
s = novo(False)
titulo(s, "Ferramentas Oracle, cada uma no seu papel", "O que já roda e o que vem no NEXT.")
linhas12 = [("Oracle AI Database 26ai (Free, Docker)", "Banco da IES: 684.723 eventos, features em SQL, tabelas e snapshot de risco", "Executado"),
            ("Oracle Machine Learning · DBMS_DATA_MINING", "Random Forest e GLM treinados no banco; PREDICTION_PROBABILITY e PREDICTION_DETAILS dão score e motivo", "Executado"),
            ("Views de scoring + JSON Duality View", "Risco por aluno pronto para APEX, API e Select AI", "Executado"),
            ("DBMS_SCHEDULER", "Job semanal: recalcula features e scores todo domingo à noite", "Executado"),
            ("python-oracledb (thin) + MERGE idempotente", "Carga do export do LMS em 72 s; snapshot semanal sem duplicar", "Executado"),
            ("Autonomous AI Database Serverless (OCI)", "Produção multi-IES: um schema por cliente, auto-scaling; runbook de 60 min pronto", "Runbook pronto"),
            ("Object Storage + DBMS_CLOUD.COPY_DATA", "Ingestão do CSV padrão do LMS direto na nuvem", "Runbook pronto"),
            ("APEX", "Painel da coordenação e da diretoria (hoje: dashboard web publicado)", "NEXT 24/10"),
            ("Select AI", "Perguntas em português sobre a base: \"quem parou no capítulo 2 da fase 5?\"", "Roadmap")]
cores_st = {"Executado": (VERDE, AZUL), "Runbook pronto": (AMBAR, AZUL), "NEXT 24/10": (AMBAR_CLARO, GRAFITE), "Roadmap": (LINHA, GRAFITE)}
rect(s, 0.6, 1.95, 12.15, 0.42, AZUL, radius=0.04)
for j, (c, xx, ww) in enumerate([("Ferramenta Oracle", 0.8, 3.8), ("Papel na Retena", 4.7, 6.2), ("Status", 11.0, 1.6)]):
    text(s, xx, 1.98, ww, 0.36, c, size=11, cor=BRANCO, bold=True, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER if j == 2 else PP_ALIGN.LEFT)
for i, (a, b, st) in enumerate(linhas12):
    y = 2.42 + i * 0.47; rect(s, 0.6, y, 12.15, 0.44, BRANCO if i % 2 == 0 else OFF, line=LINHA)
    text(s, 0.8, y, 3.8, 0.44, a, size=10.3, cor=AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 4.7, y, 6.2, 0.44, b, size=9.8, cor=GRAFITE, anchor=MSO_ANCHOR.MIDDLE)
    bg, fg = cores_st[st]; pill(s, 11.0, y + 0.08, 1.6, st, bg=bg, fg=fg, size=8.5, h=0.28)
text(s, 0.6, 6.7, 12.1, 0.3, "5 de 9 componentes executados e evidenciados; os demais têm runbook com números esperados para conferência (06_Oracle/oci).", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "Ferramentas Oracle", "Stack Oracle (25 s). Para a banca ver de uma vez: cinco componentes já executados e evidenciados — banco 26ai, Oracle Machine Learning, views JSON e Duality View, DBMS_SCHEDULER e a carga via python-oracledb. Autonomous e Object Storage têm runbook pronto de 60 minutos; APEX vai ao NEXT em 24/10; Select AI está no roadmap.")

# ================================================================= 13 MODELO DE NEGÓCIO
s = novo(True)
titulo(s, "Modelo de negócio · a instituição paga por quem ainda está lá", "Assinatura por aluno ativo, por mês.", escuro=True)
text(s, 0.6, 1.95, 6.3, 1.0, "R$ 4,00", size=54, cor=VERDE, bold=True)
text(s, 0.6, 2.95, 6.3, 0.4, "por aluno ativo, por mês — faixa de 10 a 50 mil alunos (plano Pro)", size=12, cor=BRANCO, bold=True)
planos = [("Essencial", "R$ 2,00", "até 5 mil alunos · funcionalidades reduzidas · mín. R$ 2,5 mil/mês"), ("Pro", "R$ 6,00 → 4,00", "1 a 50 mil alunos · fila, atrito, painel em R$ · mín. R$ 5 mil/mês"), ("Enterprise", "R$ 3,00", "megagrupos, acima de 50 mil · fase 2, via ecossistema Oracle")]
for i, (a, b, c) in enumerate(planos):
    x = 0.6 + i * 2.15; card(s, x, 3.55, 2.0, 1.75, True); rect(s, x, 3.55, 2.0, 0.07, VERDE if i == 1 else CARD_ESC_B)
    text(s, x + 0.15, 3.7, 1.75, 0.35, a, size=12, cor=VERDE, bold=True); text(s, x + 0.15, 4.02, 1.75, 0.45, b, size=15, cor=BRANCO, bold=True); text(s, x + 0.15, 4.5, 1.75, 0.8, c, size=8.8, cor=DIM)
text(s, 0.6, 5.45, 6.3, 1.2, "Setup e integração ao LMS: R$ 10–25 mil · Porta de entrada: piloto de 90 dias em uma fase de um curso por R$ 5 mil, com meta de rematrícula acordada e conversão automática em contrato anual · Margem bruta alvo: 80%.", size=10.5, cor=DIM, spacing=1.3)
kicker(s, 7.3, 1.95, 5.45, "A conta do cliente-referência · 12 mil alunos EAD")
roi = [("R$ 576 mil / ano", "12.000 alunos × R$ 4,00 × 12 meses (+ setup único de R$ 20 mil)"), ("137 alunos retidos pagam tudo", "1,1% da base, a R$ 4.200/ano de receita preservada por aluno"), ("R$ 500 mil por ponto", "cada 1 p.p. de desistência evitado (~120 alunos) vale ~R$ 500 mil/ano (ticket estimado de R$ 350/mês)")]
for i, (a, b) in enumerate(roi):
    y = 2.4 + i * 1.45; card(s, 7.3, y, 5.45, 1.3, True); text(s, 7.5, y + 0.12, 5.1, 0.5, a, size=18, cor=VERDE, bold=True); text(s, 7.5, y + 0.62, 5.1, 0.65, b, size=10, cor=BRANCO)
text(s, 7.3, 6.75, 5.45, 0.3, "Calculadora com os parâmetros da sua IES em lucashenklain.github.io/retena (seção ROI).", size=9, cor=DIM)
rodape(s, True, N)
notes(s, N, "Modelo de negócio", "Negócio (40 s). Assinatura por aluno ativo por mês: 6 reais até 10 mil alunos, 4 de 10 a 50 mil, 3 para megagrupos; plano Essencial para IES pequenas. Entrada por piloto de 90 dias com meta de rematrícula. A conta: uma IES de 12 mil alunos paga 576 mil por ano; reter 137 alunos — 1,1% da base — já paga o contrato; cada ponto de desistência evitado vale meio milhão. Quem paga é a diretoria de operações, porque compramos rematrícula.")

# ================================================================= 14 MARKETING DIGITAL E AQUISIÇÃO
s = novo(False)
titulo(s, "Marketing digital e aquisição", "Da landing page ao contrato, medindo cada etapa.")
etapas = [("Atrair", "Landing page com vídeo de vendas (VSL), calculadora de ROI e agendamento — já publicados. Conteúdo \"Mapa da evasão EAD\" (INEP/Semesp), LinkedIn/ABM para diretores de operações, eventos Semesp e ABED."),
          ("Diagnosticar", "Diagnóstico gratuito: a IES envia o export do LMS e em 7 dias recebe o painel de receita em risco em R$ — a mesma carga que fizemos em 72 s. É a isca que vende para o sponsor."),
          ("Provar", "Piloto de 90 dias por R$ 5 mil, em uma fase de um curso, com meta de rematrícula contratual. Painel da diretoria acompanha a receita preservada semana a semana."),
          ("Expandir", "Contrato anual e expansão para outras fases e cursos; megagrupos e ERPs acadêmicos via ecossistema Oracle (Oracle for Startups e parceiros).")]
for i, (t, d) in enumerate(etapas):
    x = 0.6 + i * 3.1; card(s, x, 1.95, 2.85, 3.05); numero(s, x + 0.25, 2.15, 0.5, i + 1, size=14)
    text(s, x + 0.9, 2.18, 1.9, 0.45, t, size=15, cor=AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.25, 2.8, 2.4, 2.1, d, size=9.8, cor=GRAFITE, spacing=1.25)
    if i < 3: seta(s, x + 2.85, 3.2)
kicker(s, 0.6, 5.2, 12, "Metas do ano 1 (medidas no funil, não prometidas)")
metas = [("30", "diagnósticos gratuitos", "meta de conversão: 1 em 5 vira piloto"), ("6", "pilotos de 90 dias", "R$ 5 mil cada cobre o custo do diagnóstico"), ("2–3", "contratos anuais", "~R$ 0,5 mi de ARR no fim do ano 1"), ("< 1 trimestre", "para pagar o CAC", "meta: custo de aquisição abaixo de 3 meses de assinatura")]
for i, (a, b, c) in enumerate(metas):
    x = 0.6 + i * 3.1; card(s, x, 5.5, 2.85, 1.2); text(s, x + 0.2, 5.55, 2.5, 0.5, a, size=20, cor=VERDE_ESC, bold=True); text(s, x + 0.2, 6.0, 2.5, 0.3, b, size=10.5, cor=AZUL, bold=True); text(s, x + 0.2, 6.3, 2.5, 0.4, c, size=8.8, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "Marketing digital", "Marketing e aquisição (35 s). Funil em quatro etapas: atrair com a landing page e o vídeo de vendas já publicados, conteúdo com dados do INEP e Semesp e prospecção direta de diretores de operações; diagnosticar de graça — a IES manda o export do LMS e recebe em 7 dias o painel de receita em risco; provar com o piloto de 90 dias pago; expandir por contrato anual e pelo ecossistema Oracle. Metas do ano 1: 30 diagnósticos, 6 pilotos, 2 a 3 contratos, CAC pago em menos de um trimestre.")

# ================================================================= 15 MERCADO
s = novo(False)
titulo(s, "Mercado", "5,2 milhões de alunos EAD · 2.244 IES privadas.")
mk = [("TAM", "R$ 249 mi/ano", "5,19 mi matrículas EAD (INEP 2024) × R$ 4 × 12 meses", AZUL), ("SAM", "R$ 126 mi/ano", "IES privadas fora dos megagrupos: ~2,6 mi alunos (Semesp 2026)", AZUL_M), ("SOM · 3 anos", "R$ 2,5–4,3 mi ARR", "8–12 IES médias (~52 mil alunos) + 1 megagrupo piloto via canal Oracle", VERDE)]
for i, (a, b, c, col) in enumerate(mk):
    x = 0.6 + i * 4.1; rect(s, x, 1.95, 3.85, 2.5, col, radius=0.06); fg = AZUL if col == VERDE else BRANCO
    text(s, x + 0.25, 2.1, 3.4, 0.35, a, size=11.5, cor=fg, bold=True); text(s, x + 0.25, 2.45, 3.4, 0.8, b, size=26, cor=fg, bold=True); text(s, x + 0.25, 3.35, 3.4, 1.0, c, size=10.5, cor=fg if col == VERDE else DIM)
kicker(s, 0.6, 4.7, 12, "Go-to-market")
gtm = [("Ano 1", "3 pilotos de 90 dias + 2–3 contratos (~R$ 0,5 mi ARR); Autonomous Always Free → pago; entrada por CSV padrão do LMS"), ("Ano 2", "6 IES médias (~R$ 1,4 mi ARR); módulo de conteúdo adaptativo; integração WhatsApp; APEX + Select AI em produção"), ("Ano 3", "10–12 IES + 1 megagrupo via ecossistema Oracle (R$ 2,5–4,3 mi ARR); ensino técnico e corporativo com o mesmo método")]
for i, (a, b) in enumerate(gtm):
    x = 0.6 + i * 4.1; card(s, x, 5.1, 3.85, 1.55); text(s, x + 0.2, 5.22, 3.4, 0.35, a, size=12.5, cor=AZUL, bold=True); text(s, x + 0.2, 5.57, 3.45, 1.0, b, size=10.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "Mercado", "Mercado (15 s). 2.244 IES privadas e 5,2 milhões de alunos EAD: TAM de 249 milhões por ano; alvo inicial nas IES médias fora dos megagrupos; SOM de 2,5 a 4,3 milhões de ARR em 3 anos. Megagrupos entram na fase 2 via ecossistema Oracle.")

# ================================================================= 16 IMPACTO E PRÓXIMOS PASSOS
s = novo(True)
titulo(s, "Impacto e próximos passos", "Cada aluno retido é uma formatura e uma receita.", escuro=True)
imp = [("Aluno", "chega à formatura", "porque alguém percebeu o silêncio e ligou na hora certa, com um plano — não uma cobrança."), ("Instituição", "R$ 500 mil por ponto", "cada 1 p.p. de desistência evitado na IES de 12 mil alunos; 137 alunos retidos pagam a Retena."), ("Sociedade", "mais formandos no EAD", "que já é metade do ensino superior brasileiro — e o caminho de quem trabalha de dia.")]
for i, (a, b, c) in enumerate(imp):
    y = 1.95 + i * 1.3; card(s, 0.6, y, 6.1, 1.15, True)
    text(s, 0.85, y + 0.12, 1.5, 0.35, a.upper(), size=10, cor=VERDE, bold=True); text(s, 0.85, y + 0.42, 1.9, 0.6, b, size=13.5, cor=BRANCO, bold=True, spacing=1.05)
    text(s, 2.9, y + 0.15, 3.65, 0.95, c, size=10.5, cor=DIM, spacing=1.25)
kicker(s, 7.1, 1.95, 5.65, "Próximos passos")
tl = [("23/09", "Banca Final", True), ("24/10", "NEXT: demonstração no Autonomous AI Database com painel APEX", False), ("Nov–Fev", "Piloto de 90 dias em uma fase de um curso, com meta de rematrícula", False), ("2027", "Conteúdo adaptativo, WhatsApp e megagrupos via canal Oracle", False)]
for i, (a, b, done) in enumerate(tl):
    y = 2.35 + i * 0.62; oval(s, 7.1, y + 0.06, 0.26, VERDE if done else AZUL_M, line=VERDE)
    if i < 3: rect(s, 7.22, y + 0.34, 0.03, 0.3, CARD_ESC_B)
    text(s, 7.5, y, 1.1, 0.4, a, size=12, cor=VERDE, bold=True); text(s, 8.6, y, 4.15, 0.6, b, size=10.5, cor=BRANCO)
kicker(s, 7.1, 4.95, 5.65, "O que pedimos à banca e ao ecossistema Oracle")
ask = [("Autonomous AI Database", "apoio para o Always Free e a primeira aplicação APEX antes do NEXT"), ("Uma IES parceira", "piloto de 90 dias com dados anonimizados e meta acordada"), ("Mentoria comercial", "venda ao sponsor de operações e acesso a grupos que já rodam Oracle")]
for i, (a, b) in enumerate(ask):
    x = 7.1 + i * 1.9; card(s, x, 5.3, 1.8, 1.4, True); text(s, x + 0.12, 5.38, 1.56, 0.5, a, size=10, cor=VERDE, bold=True, spacing=1.05); text(s, x + 0.12, 5.9, 1.56, 0.8, b, size=8.5, cor=BRANCO)
rodape(s, True, N)
notes(s, N, "Impacto e próximos passos", "Impacto e próximos passos (25 s). Para o aluno, uma formatura; para a instituição, meio milhão por ponto de desistência evitado; para a sociedade, mais formandos no EAD. Próximos passos: NEXT em 24/10 com Autonomous e APEX; piloto de 90 dias com meta de rematrícula. Pedimos apoio ao Always Free, uma IES parceira e mentoria comercial.")

# ================================================================= 17 EQUIPE
s = novo(False)
titulo(s, "Equipe", "Cinco engenheiros, um problema conhecido de perto.")
for i, (nome, rm, papel) in enumerate(EQUIPE):
    x = 0.6 + i * 2.47; card(s, x, 2.05, 2.3, 3.3)
    ini = "".join(p[0] for p in nome.split()[:2])
    oval(s, x + 0.65, 2.35, 1.0, 1.0, VERDE if papel else AZUL); text(s, x + 0.65, 2.35, 1.0, 1.0, ini, size=20, cor=AZUL if papel else BRANCO, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 3.55, 2.0, 0.6, nome, size=13, cor=AZUL, bold=True, align=PP_ALIGN.CENTER); text(s, x + 0.15, 4.1, 2.0, 0.3, rm, size=10.5, cor=GRAFITE, align=PP_ALIGN.CENTER)
    if papel: pill(s, x + 0.65, 4.55, 1.0, papel, size=9, h=0.3)
    else: text(s, x + 0.15, 4.55, 2.0, 0.3, "Engenharia de Software", size=9.5, cor=CINZA, align=PP_ALIGN.CENTER)
card(s, 0.6, 5.6, 12.15, 1.05); text(s, 0.8, 5.7, 11.8, 0.9, [[("Como trabalhamos: ", True, AZUL), ("base real de 684.723 eventos analisada com validação temporal; modelo treinado dentro do Oracle e evidenciado com logs; dashboard, landing page, calculadora de ROI e vídeo produzidos pelo time; benchmark e portabilidade em um segundo dataset público. Tudo reproduzível e publicado em github.com/LucasHenklain/retena.", False, GRAFITE)]], size=10.5)
rodape(s, False, N)
notes(s, N, "Equipe", "Equipe (10 s). Cinco engenheiros de software do 4º ano; Lucas Dalmas lidera. Tudo o que foi mostrado está publicado e reproduzível.")

# ================================================================= 18 FECHAMENTO
s = novo(True, motivo=False)
img_cover(s, IMG("04_Landing_Page", "img", "formatura.jpg"), 0, 0, 13.333, 7.5); veu(s, 0, 0, 13.333, 7.5, AZUL, 18)
pulso(s, 8.3, 0.9, 4.6, pct=50, espessura=16)
if os.path.exists(lg): s.shapes.add_picture(lg, P(0.9), P(0.9), height=P(0.85))
kicker(s, 0.9, 2.05, 8, "Vamos conversar?")
text(s, 0.9, 2.4, 11.5, 2.0, [[("Ninguém desiste de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=42, spacing=1.05)
text(s, 0.9, 4.35, 10.5, 0.9, "A evasão não é um evento. É um silêncio que dura semanas. A Retena escuta esse silêncio, dentro do banco que a instituição já usa, e devolve tempo para quem pode agir.", size=15, cor=DIM, spacing=1.3)
qrs = [("Vídeo pitch (4:48)", "youtu.be/HZrcLvIJCC4", qr("video", LINKS["video"])), ("Site, calculadora e dashboard", "lucashenklain.github.io/retena", qr("site", LINKS["site"])), ("Repositório e evidências", "github.com/LucasHenklain/retena", qr("repo", LINKS["repo"]))]
for i, (a, b, qp) in enumerate(qrs):
    x = 0.9 + i * 4.05; rect(s, x, 5.35, 3.85, 1.35, CARD_ESC, radius=0.1, line=CARD_ESC_B)
    s.shapes.add_picture(qp, P(x + 0.15), P(5.45), height=P(1.15))
    text(s, x + 1.45, 5.5, 2.3, 0.35, a, size=11, cor=VERDE, bold=True); text(s, x + 1.45, 5.88, 2.3, 0.7, b, size=10, cor=BRANCO)
text(s, 0.9, 6.85, 11.5, 0.4, "Lucas Dalmas · Lucas Emanuel · Kayque Moraes · Lucas Henklain · Vinicius Pinheiro — Engenharia de Software, FIAP 4ESOA · Startup One / Enterprise Challenge Oracle 2026 · Obrigado.", size=10, cor=DIM)
notes(s, N, "Fechamento", "Fechamento (20 s). A evasão não é um evento, é um processo silencioso que dura semanas. A Retena escuta esse silêncio e devolve tempo para quem pode agir. Ninguém desiste de repente. A Retena percebe antes. Obrigado. (QR codes: vídeo, site com calculadora e dashboard, repositório.)")

# ================================================================= APÊNDICE
s = novo(True)
text(s, 0.9, 2.6, 11, 0.4, "APÊNDICE TÉCNICO", size=12, cor=VERDE, bold=True)
text(s, 0.9, 3.0, 11, 1.6, [[("Material de apoio", True, BRANCO)], [("para as perguntas da banca.", True, DIM)]], size=36, spacing=1.05)
text(s, 0.9, 4.75, 11.5, 1.5, ["A1 Prints da demonstração (reserva) · A2 Métricas completas · A3 Fluxo de dados e ML · A4 OULAD em detalhe · A5 Por que split temporal", "A6 LGPD e caminho OCI · A7 Jornada da usuária · A8 Riscos e mitigação · A9 Rich picture e stakeholders · A10 Benchmark de modelos", "A11 Diferencial × alternativas · A12 Validação estruturada (H1–H6) · A13 Mapa de atrito · A14 Evidência na base real · A15 Arquitetura Oracle"], size=12, cor=DIM, spacing=1.35)
rodape(s, True, N)
notes(s, N, "Apêndice", "Não apresentar; usar sob demanda nas perguntas. A1 é a reserva da demonstração se a internet falhar.")

# A1 prints da demonstração (reserva)
s = novo(False)
titulo(s, "A1 · Prints da demonstração (reserva)", "Fila de segunda com motivo e ação; mapa de atrito.")
card(s, 0.6, 1.95, 6.0, 4.75); img_fit(s, IMG("07_Video_Pitch", "producao", "demo", "dashboard_fila.png"), 0.7, 2.05, 5.8, 3.6, rounded=True)
pill(s, 0.8, 5.75, 1.6, "Fila de segunda", size=9, h=0.3); text(s, 0.8, 6.12, 5.6, 0.5, "Cada linha: fase, situação, recência, tendência, probabilidade, faixa, fatores em linguagem simples e ação sugerida. Clique no aluno abre o painel de detalhe.", size=9.5, cor=GRAFITE)
card(s, 6.75, 1.95, 6.0, 4.75); img_fit(s, IMG("07_Video_Pitch", "producao", "demo", "dashboard_atrito.png"), 6.85, 2.05, 5.8, 3.6, rounded=True)
pill(s, 6.95, 5.75, 1.9, "Mapa de atrito", size=9, h=0.3); text(s, 6.95, 6.12, 5.6, 0.5, "Fase × capítulo com taxa de queda e esforço; as 8 maiores fricções e as 20 recomendações priorizadas para a coordenação pedagógica.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A1 Prints da demonstração", "Reserva se a internet falhar. Reforçar: motivo em linguagem simples ao lado de cada score, e o resultado do contato é registrado em um clique.")

# A2 métricas completas
s = novo(False)
titulo(s, "A2 · Métricas completas do modelo", "HGB × regressão logística, conjunto completo e subconjunto acionável (teste jun–ago/2026).", size=24)
tabela(s, 0.6, 1.95, 7.2, 3.9, ["Métrica (teste, n = 1.609, positivos 28,8%)", "HGB", "Logística"],
       [["AUC-ROC", "0,882", "0,893"], ["AUC-PR", "0,839", "0,859"], ["Brier (menor é melhor)", "0,120", "0,101"], ["Precisão @ 0,5", "0,924", "0,895"], ["Recall @ 0,5", "0,580", "0,659"], ["F1 @ 0,5", "0,713", "0,759"], ["Precisão @ top-20% (k = 322)", "0,882", "0,919"], ["Recall capturado no top-20%", "0,612", "0,638"], ["Lift no top-20%", "3,06×", "3,19×"]],
       [4.2, 1.7, 1.3], size=10)
tabela(s, 8.1, 1.95, 4.65, 2.2, ["Subconjunto acionável (n = 1.298; 14,7%)", "HGB", "Logística"],
       [["AUC-ROC", "0,743", "0,772"], ["AUC-PR", "0,460", "0,494"], ["Precisão @ top-20%", "0,377", "0,396"], ["Lift no top-20%", "2,56×", "2,69×"]], [2.65, 1.0, 1.0], size=10)
tabela(s, 8.1, 4.4, 4.65, 1.45, ["Faixa", "n", "Inatividade observada"], [["Alto (≥ 0,60)", "273", "95,2%"], ["Médio (0,30–0,60)", "39", "48,7%"], ["Baixo (< 0,30)", "1.297", "14,3%"]], [1.85, 1.0, 1.8], size=10)
text(s, 0.6, 6.0, 12.1, 0.7, "Protocolo: treino cortes < 01/06/2026 com embargo de 21 dias (2.126 linhas, 16 cortes, 167 alunos, 10,1% positivos); teste cortes ≥ 01/06 (1.609 linhas, 9 cortes, 183 alunos, 28,8%). Matriz de confusão do HGB @ 0,5: VN 1.123 · FP 22 · FN 195 · VP 269. Hiperparâmetros por validação temporal interna (learning rate 0,05; 300 iterações; 8 folhas; mín. 40 por folha; L2 = 2). Estabilidade por corte: AUC-ROC de 0,80 a 0,97. Modelo secundário (transição de fases): AUC média 0,926 em leave-one-phase-out. Fonte: 05_MVP/outputs/RESULTADOS.md.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A2 Métricas", "Apoio para perguntas sobre desempenho. A logística é ligeiramente melhor por margem dentro do ruído; o HGB foi mantido por precisão a 0,5 e rastreabilidade.")

# A3 fluxo de dados e ML
s = novo(False)
titulo(s, "A3 · Fluxo de dados e ML", "Do log bruto à fila semanal.")
card(s, 0.6, 1.95, 7.9, 4.75); img_fit(s, IMG("02_Diagramas", "07_fluxo_dados_ml.png"), 0.7, 2.02, 7.7, 4.6, trim=True)
card(s, 8.75, 1.95, 4.0, 4.75); text(s, 8.95, 2.05, 3.6, 0.35, "Importância por permutação (top 12)", size=12, cor=AZUL, bold=True)
img_fit(s, IMG("05_MVP", "outputs", "figs", "fig_importancia.png"), 8.85, 2.45, 3.8, 3.2, trim=True)
text(s, 8.95, 5.7, 3.6, 0.95, "Dias ativos acumulados, dias ativos em 28 dias, eventos acumulados e recência lideram; volume de cliques vale menos que constância — o mesmo padrão observado no OULAD.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A3 Fluxo", "Apoio para perguntas de arquitetura de dados e features.")

# A4 OULAD detalhe
s = novo(False)
titulo(s, "A4 · Portabilidade no OULAD em detalhe", "Mesmo método, 24.392 alunos, split temporal 2013 → 2014.")
card(s, 0.6, 1.95, 6.3, 4.75); img_fit(s, IMG("05_MVP", "portabilidade_oulad", "figs", "fig_oulad_roc_pr.png"), 0.7, 2.02, 6.1, 4.6, trim=True)
tabela(s, 7.15, 1.95, 5.6, 3.55, ["Métrica (inativo_21d)", "IES parceira", "OULAD completo", "OULAD acionável"],
       [["Alunos no teste", "183", "14.293", "—"], ["Taxa de positivos", "28,8%", "20,6%", "10,6%"], ["AUC-ROC (HGB)", "0,882", "0,922", "0,853"], ["AUC-PR (HGB)", "0,839", "0,813", "0,418"], ["Precisão @ top-20%", "0,882", "0,724", "0,342"], ["Lift @ top-20%", "3,06×", "3,51×", "3,23×"], ["Faixa Alto: inatividade observada", "95,2%", "85,0%", "—"], ["Faixa Baixo: inatividade observada", "14,3%", "6,4%", "—"]],
       [2.3, 1.0, 1.2, 1.1], size=9.5)
text(s, 7.15, 5.65, 5.6, 1.05, "Estabilidade: AUC-ROC entre 0,858 e 0,954 nos 14 módulos-apresentações de teste; módulo CCC (só existe em 2014, nunca visto no treino): 0,931 e 0,906. Calibração quase diagonal com 400 mil linhas. Tempo total de execução: ~110 s. Fonte: 05_MVP/portabilidade_oulad/RESULTADOS_OULAD.md.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A4 OULAD", "Apoio para 'a amostra é pequena' e 'funciona em outra IES?'.")

# A5 por que split temporal
s = novo(False)
titulo(s, "A5 · Por que avaliamos com split temporal", "Protocolo alternativo (alvo Withdrawn, dia 30) reproduzido no OULAD.", size=24)
tabela(s, 0.6, 1.95, 12.15, 3.3, ["Cenário", "Modelo", "AUC-ROC", "AUC-PR", "Precisão @ top-20%", "Lift"],
       [["(a) Split aleatório 80/20 estratificado", "Logística L1 balanceada", "0,814", "0,714", "0,780", "2,50×"], ["(a) Split aleatório 80/20 estratificado", "HGB Retena", "0,834", "0,748", "0,807", "2,59×"], ["(b) Split temporal 2013 → 2014", "Logística L1 balanceada", "0,790", "0,700", "0,772", "2,29×"], ["(b) Split temporal 2013 → 2014", "HGB Retena", "0,821", "0,754", "0,828", "2,45×"], ["(c) Temporal, sem quem já se desmatriculou até o dia 30", "Logística L1 balanceada", "0,659", "0,315", "0,334", "1,70×"], ["(c) Temporal, sem quem já se desmatriculou até o dia 30", "HGB Retena", "0,692", "0,336", "0,376", "1,92×"]],
       [4.6, 2.6, 1.2, 1.2, 1.55, 1.0], size=10, alinh_centro_apartir=2)
bullets(s, 0.6, 5.45, 12.1, ["A inflação do split aleatório é real, mas modesta (+0,024 de AUC-ROC para a logística). O ponto decisivo: 15,7% das matrículas já tinham desmatrícula registrada até o dia 30 e são acertadas trivialmente; sem elas, o desempenho cai para AUC-ROC 0,66–0,69.", "É o análogo do subconjunto acionável do Retena — onde o método semanal com recência e regularidade obteve AUC-ROC 0,853 no mesmo dataset e mesmo split. O grão semanal carrega muito mais sinal acionável do que uma fotografia única do dia 30."], size=10.5, gap=0.08)
rodape(s, False, N)
notes(s, N, "A5 Split temporal", "Apoio para perguntas metodológicas e para o debate com abordagens de split aleatório.")

# A6 LGPD e caminho OCI
s = novo(False)
titulo(s, "A6 · LGPD, segurança e caminho OCI", "O dado do aluno não sai da instituição. O caminho para o Autonomous está pronto.", size=24)
card(s, 0.6, 1.95, 5.9, 4.75); text(s, 0.8, 2.08, 5.5, 0.35, "Privacidade e segurança", size=12.5, cor=AZUL, bold=True)
bullets(s, 0.8, 2.55, 5.5, ["Processamento dentro do banco que a IES já controla; nenhum dado em ETL externo, servidor de ML ou nuvem de terceiros.", "Pseudonimização fora do painel (\"Aluno NNNN\"); dados nominais só para tutores autorizados.", "Base legal: execução do contrato educacional e legítimo interesse de apoio acadêmico; opt-in de contato registrado.", "Perfis de acesso por papel (coordenação, tutor, gestão); TDE e auditoria nativos do Autonomous; minimização: só logs de navegação.", "Tom de voz de apoio, nunca de cobrança ou vigilância."], size=10.5, gap=0.1)
card(s, 6.85, 1.95, 5.9, 4.75); text(s, 7.05, 2.08, 5.5, 0.35, "Caminho OCI (06_Oracle/oci) — status", size=12.5, cor=AZUL, bold=True)
tabela(s, 7.05, 2.5, 5.5, 3.3, ["Etapa", "Status"], [["Conexão dual (Free local / Autonomous com wallet)", "Executado local"], ["Exportação de EVENTOS_LMS para CSV gzip (684.723 linhas)", "Executado (dry-run)"], ["MERGE idempotente do snapshot de risco (2× sem duplicar)", "Executado local"], ["Object Storage + DBMS_CLOUD.COPY_DATA", "Runbook (sem conta OCI)"], ["Autonomous Always Free + usuário RETENA", "Runbook"], ["APEX, Select AI, DBMS_SCHEDULER", "Runbook"]], [3.7, 1.8], size=9.5, alinh_centro_apartir=1)
text(s, 7.05, 5.95, 5.5, 0.6, "Runbook estimado em 60 minutos com uma conta OCI; números esperados já documentados para conferência.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A6 LGPD e OCI", "Apoio para perguntas de LGPD, segurança e 'quando vai para a nuvem'.")

# A7 jornada
s = novo(False)
titulo(s, "A7 · Jornada da usuária", "A semana da coordenadora de permanência com a Retena.")
card(s, 0.6, 1.95, 12.15, 4.75); img_fit(s, IMG("02_Diagramas", "03_jornada_usuario.png"), 0.7, 2.02, 11.95, 4.6, trim=True)
rodape(s, False, N)
notes(s, N, "A7 Jornada", "Apoio para perguntas de produto e experiência de uso.")

# A8 riscos
s = novo(False)
titulo(s, "A8 · Riscos e mitigação", "O que pode dar errado e o que já está desenhado.")
tabela(s, 0.6, 1.95, 12.15, 4.2, ["Risco", "Mitigação", "Situação na Fase 6"],
       [["Poucos dados por IES; rótulo é proxy comportamental", "Validação temporal, retreino mensal, faixas lidas como prioridade relativa", "Métricas honestas reportadas; portabilidade provada no OULAD"], ["Coordenação tem dor, mas não orçamento; ciclo de venda longo", "Venda ao diretor de operações com painel de receita em risco; piloto de 90 dias com meta", "Dupla persona, plano Essencial e calculadora de ROI incorporados"], ["Integração vira projeto de TI", "Entrada por CSV padrão do LMS; APEX pronto em dias; primeira fila em 30 dias", "Carga por export padrão validada; runbook OCI pronto"], ["LGPD e percepção de vigilância do aluno", "Processamento in-database, pseudonimização, tom de apoio, opt-in", "Arquitetura in-database executada e evidenciada"], ["Concorrência de BI embarcado; nome confundido com 'retina'", "Ciclo fechado com ROI; canal Oracle; marca sempre com tagline e símbolo; nomes reserva", "Manual de marca e posicionamento definidos"]],
       [3.6, 4.6, 3.95], size=10, alinh_centro_apartir=9)
rodape(s, False, N)
notes(s, N, "A8 Riscos", "Apoio para perguntas sobre riscos do negócio.")

# A9 rich picture + stakeholders
s = novo(False)
titulo(s, "A9 · Rich picture e mapa de stakeholders", "Atualizados na Fase 6 após validação e integração Oracle.")
card(s, 0.6, 1.95, 6.0, 4.75); img_fit(s, IMG("02_Diagramas", "01_rich_picture.png"), 0.7, 2.02, 5.8, 4.6, trim=True)
card(s, 6.75, 1.95, 6.0, 4.75); img_fit(s, IMG("02_Diagramas", "02_mapa_stakeholders.png"), 6.85, 2.02, 5.8, 4.6, trim=True)
rodape(s, False, N)
notes(s, N, "A9 Rich picture", "Apoio para perguntas sobre a Parte 2 (validação e stakeholders).")

# A10 benchmark de modelos (v2)
s = novo(False)
titulo(s, "A10 · Benchmark e portabilidade", "O que o time acrescentou depois da entrega: mais modelos, outro dataset.")
card(s, 0.6, 1.95, 6.4, 4.75); text(s, 0.8, 2.08, 6.0, 0.35, "Benchmark no mesmo split temporal (teste jun–ago/2026)", size=12.5, cor=AZUL, bold=True)
tabela(s, 0.8, 2.5, 6.0, 2.85, ["Modelo", "AUC-ROC", "AUC-PR", "F2"],
       [["HGB · HistGradientBoosting (entregue)", "0,882", "0,839", "0,626"], ["Logística baseline", "0,893", "0,859", "0,696"], ["Logística + balanced", "0,889", "0,855", "0,766"], ["Logística EduRetain (L1)", "0,882", "0,850", "0,759"], ["XGBoost (config EduRetain)", "0,874", "0,818", "0,586"], ["GradientBoosting padrão", "0,811", "0,739", "0,543"]],
       [3.0, 1.0, 1.0, 1.0], size=10, destaque_linha=1)
bullets(s, 0.8, 5.5, 6.0, ["Nenhuma configuração alternativa supera o baseline já existente; a vantagem em F2 dos modelos balanceados é efeito de limiar, não de ordenação.", "HGB permanece o modelo entregue (melhor precisão a 0,5 e rastreabilidade); o limiar 0,30 da faixa Médio recupera o recall."], size=9.5, gap=0.05)
card(s, 7.3, 1.95, 5.45, 4.75); text(s, 7.5, 2.08, 5.1, 0.35, "Portabilidade: mesmo método no OULAD (Open University, UK)", size=12, cor=AZUL, bold=True)
bullets(s, 7.5, 2.55, 5.05, ["32.593 matrículas e 10,66 milhões de cliques; base aluno-semana de 730.673 linhas e 24.392 alunos.", "Mesmo rótulo, mesmas features conceituais e mesmos hiperparâmetros; split temporal: treino 2013 (11.438 alunos), teste 2014 (14.293 alunos).", "AUC-ROC 0,922 e lift 3,51× no top-20% (IES parceira: 0,882 e 3,06×); faixa Alto com 85% de inatividade observada contra 6% na Baixo.", "As mesmas features dominam: dias ativos em 28 dias, recência e regularidade semanal. Módulo nunca visto no treino: AUC 0,93 / 0,91."], size=10, gap=0.08)
rect(s, 7.5, 5.62, 5.05, 0.95, VERDE_CLARO, radius=0.08)
text(s, 7.65, 5.68, 4.8, 0.85, "O mesmo método, sem mudar arquitetura, concentrou 70% dos alunos que ficariam 3 semanas inativos nos 20% de maior risco — em outra instituição, outro país e outro LMS.", size=10.5, cor=AZUL, bold=True)
rodape(s, False, N)
notes(s, N, "A10 Benchmark", "Apoio para 'por que este modelo' e '203 alunos é pouco'. Benchmark do pipeline de um integrante incorporado após a entrega: nenhuma configuração supera o baseline; OULAD confirma o método.")

# A11 diferencial × alternativas
s = novo(False)
titulo(s, "A11 · Diferencial × alternativas", "BI olha o passado, CRM cobra tarde. A Retena fecha o ciclo.")
rows = [("Antecipa o risco semanas antes (recência, tendência, capítulo)", "●", "○", "○", "◐"), ("Diz quem contatar, por quê, quando e o que dizer", "●", "○", "◐", "◐"), ("Mapa de atrito de conteúdo por capítulo", "●", "◐", "○", "◐"), ("Registra o resultado e mede receita preservada em R$", "●", "○", "◐", "○"), ("Roda dentro do banco da IES (LGPD, sem ETL externo)", "●", "◐", "○", "○"), ("Retreina com o resultado das intervenções", "●", "○", "○", "○"), ("Implantação em semanas, sem cientista de dados", "●", "●", "●", "○")]
tbl = s.shapes.add_table(len(rows) + 1, 5, P(0.6), P(1.95), P(12.15), P(4.25)).table
for j, w in enumerate([5.55, 1.65, 1.65, 1.65, 1.65]): tbl.columns[j].width = P(w)
for j, c in enumerate(["", "Retena", "BI do LMS", "CRM de cobrança", "Consultoria"]):
    cell = tbl.cell(0, j); cell.text = c; cell.fill.solid(); cell.fill.fore_color.rgb = AZUL; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER if j else PP_ALIGN.LEFT
    for r in pp.runs: r.font.size = Pt(11.5); r.font.bold = True; r.font.color.rgb = BRANCO; r.font.name = FONT
for i, row in enumerate(rows, start=1):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j); cell.text = v; cell.fill.solid(); cell.fill.fore_color.rgb = BRANCO if i % 2 else OFF; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        for r in pp.runs:
            r.font.size = Pt(11) if j == 0 else Pt(15); r.font.name = FONT; r.font.bold = (j == 1)
            r.font.color.rgb = GRAFITE if j == 0 else (VERDE if j == 1 else (AMBAR if v == "◐" else (AZUL if v == "●" else CINZA)))
text(s, 0.6, 6.3, 12.1, 0.4, "● atende plenamente   ◐ atende em parte   ○ não atende. Por que não foi resolvido assim antes: dado preso em relatórios descritivos; ML exigia pipeline externo e cientista de dados; ninguém fechava o ciclo com ROI — e o EAD só virou maioria em 2024.", size=9.5, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A11 Diferencial", "Apoio para 'isso não é só um BI?' e 'concorrentes?'.")

# A12 validação estruturada
s = novo(False)
titulo(s, "A12 · Validação estruturada", "Dados reais, fontes de mercado e entrevistas com roteiro.")
card(s, 0.6, 1.95, 5.9, 4.75); text(s, 0.8, 2.08, 5.5, 0.35, "Hipóteses H1–H6 · status após a Fase 6", size=12.5, cor=AZUL, bold=True)
hip = [("H1 · A IES descobre a evasão tarde", "6/6 percebem em ≥ 2 semanas", VERDE), ("H2 · Sinais do LMS antecipam a evasão", "AUC 0,88 no teste temporal; 0,92 no OULAD", VERDE), ("H3 · Tutores não conseguem priorizar", "5/6 priorizam de forma intuitiva", VERDE), ("H4 · Conteúdo tem atrito identificável", "4/6 citam capítulos específicos", VERDE), ("H5 · Disposição a pagar por aluno/mês", "coordenação R$ 1–3; sponsor R$ 3–4", AMBAR), ("H6 · Integração por export é aceitável", "6/6 têm export de logs acessível", VERDE)]
for i, (a, b, c) in enumerate(hip):
    y = 2.55 + i * 0.68; oval(s, 0.85, y + 0.06, 0.2, c); text(s, 1.15, y, 3.0, 0.6, a, size=10.5, cor=AZUL, bold=True); text(s, 4.05, y, 2.35, 0.6, b, size=9.5, cor=GRAFITE)
card(s, 6.85, 1.95, 5.9, 4.75); text(s, 7.05, 2.08, 5.5, 0.35, "O que as entrevistas mudaram na proposta", size=12.5, cor=AZUL, bold=True)
bullets(s, 7.05, 2.55, 5.5, ["Venda ao sponsor de operações (receita em risco em R$); uso diário pela coordenação.", "Plano Essencial para IES pequenas: a dor existe, o orçamento é mínimo.", "Template de mensagem, janela 19h–22h e \"kit de retomada\" em cada linha da fila.", "Registro de resultado em um clique; WhatsApp no primeiro trimestre pós-piloto.", "Piloto com meta de rematrícula contratual; argumento LGPD explícito."], size=10.5, gap=0.08)
rect(s, 7.05, 5.72, 5.5, 0.85, AMBAR_CLARO, radius=0.08)
text(s, 7.2, 5.77, 5.2, 0.75, "Nota: as 8 entrevistas foram simuladas com personas sintéticas (perfis-alvo e base real) para calibrar o instrumento; 6 institucionais entram na contagem x/6 e 2 com alunos calibraram H4 e H5. Serão confirmadas em campo antes do piloto.", size=8.8, cor=GRAFITE)
rodape(s, False, N)
notes(s, N, "A12 Validação estruturada", "Se perguntarem sobre as entrevistas: foram simuladas com personas sintéticas para calibrar o roteiro e antecipar objeções; estão rotuladas assim no documento e serão confirmadas em campo antes do piloto. Responder exatamente isso.")

# A13 mapa de atrito
s = novo(False)
titulo(s, "A13 · Onde os alunos travam", "Atrito de conteúdo: conhecido de ouvido, nunca medido.")
card(s, 0.6, 1.95, 7.6, 4.75); img_fit(s, IMG("05_MVP", "outputs", "figs", "fig_atrito_heatmap.png"), 0.75, 2.05, 7.3, 4.55, trim=True)
bullets(s, 8.6, 2.05, 4.15, ["Mapa fase × capítulo: taxa de queda (alunos que chegaram ao capítulo e não avançaram) ponderada pelo esforço relativo.", "Cauda de travamento nos capítulos 1–3 de todas as fases; na F5 (em andamento), 25 alunos parados nos caps 1–2.", "Piores capítulos encerrados: Cap 2 da F4 (\"Estudo de Caso\", esforço 3,4× o típico), Cap 2 da F3 e Cap 11 da F2.", "Conteúdo quase só em HTML (323 mil eventos) contra 18,6 mil em PDF e quase nada em vídeo e áudio.", "Cada célula vira uma recomendação para a coordenação pedagógica: dividir o capítulo, inserir quiz de checagem, oferecer vídeo curto."], size=11.5, gap=0.14)
rodape(s, False, N)
notes(s, N, "A13 Mapa de atrito", "Apoio para perguntas sobre o módulo de conteúdo e a parte pedagógica.")

# A14 evidência na base real
s = novo(True)
titulo(s, "A14 · Evidência na base real (anonimizada)", "O LMS já sabia. Só faltava alguém ouvir.", escuro=True)
stats = [("684.723", "eventos de LMS", "203 alunos · 5 fases · jan–ago/2026"), ("61 alunos", "30% da turma", "há mais de 14 dias sem acesso, em um único dia — sem alerta"), ("12%", "dos ingressantes perdidos", "em 7 meses: funil 94% → 94% → 92% → 88%"), ("19h–22h", "pico de estudo", "de segunda a quinta: o aluno trabalhador")]
for i, (a, b, c) in enumerate(stats):
    y = 1.95 + i * 1.2; card(s, 0.6, y, 5.3, 1.05, True)
    text(s, 0.85, y + 0.18, 2.1, 0.6, a, size=24, cor=VERDE, bold=True)
    text(s, 3.0, y + 0.12, 2.75, 0.35, b, size=12.5, cor=BRANCO, bold=True); text(s, 3.0, y + 0.45, 2.75, 0.55, c, size=10, cor=DIM)
cd = CategoryChartData(); cd.categories = ["Fase 1", "Fase 2", "Fase 3", "Fase 4", "Fase 5"]; cd.add_series("Alunos ativos", (175, 165, 165, 161, 154))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, P(6.4), P(1.95), P(6.4), P(4.75), cd).chart
gf.has_legend = False; gf.has_title = True; gf.chart_title.text_frame.text = "Alunos da Fase 1 que seguem ativos em cada fase"
tt = gf.chart_title.text_frame.paragraphs[0].runs[0].font; tt.size = Pt(12.5); tt.bold = True; tt.color.rgb = BRANCO; tt.name = FONT
pl = gf.plots[0]; pl.gap_width = 60; pl.has_data_labels = True; dl = pl.data_labels; dl.position = XL_LABEL_POSITION.OUTSIDE_END; dl.font.size = Pt(12); dl.font.color.rgb = BRANCO; dl.font.bold = True; dl.number_format = "0"; dl.number_format_is_linked = False
ser = pl.series[0]
for idx in range(5):
    pt = ser.points[idx]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = VERDE if idx < 4 else AMBAR
ca = gf.category_axis; ca.tick_labels.font.size = Pt(11); ca.tick_labels.font.color.rgb = BRANCO; ca.format.line.color.rgb = CARD_ESC_B; ca.has_major_gridlines = False
va = gf.value_axis; va.visible = False; va.has_major_gridlines = False; va.maximum_scale = 200; va.minimum_scale = 0
text(s, 6.4, 6.72, 6.4, 0.3, "Fase 5 em andamento (ago/2026). 9 alunos aparecem só na F1; 8 param após a F4.", size=9.5, cor=DIM)
rodape(s, True, N)
notes(s, N, "A14 Evidência na base real", "Apoio para 'de onde vêm os 30%' e para o funil por fase. O dashboard usa outra definição de ativo por fase (165 → 163 → 165 → 153 → 143), por isso os números diferem.")

# A15 arquitetura Oracle
s = novo(False)
titulo(s, "A15 · Arquitetura Oracle", "ML in-database: do export do LMS ao painel, sem o dado sair do banco.")
card(s, 0.6, 1.95, 8.6, 4.75); img_fit(s, IMG("02_Diagramas", "06_arquitetura_oracle.png"), 0.7, 2.02, 8.4, 4.6, trim=True)
bullets(s, 9.5, 2.0, 3.25, ["Oracle Autonomous AI Database 26ai: eventos, features em SQL, treino e scoring in-database com Oracle Machine Learning (DBMS_DATA_MINING).", "PREDICTION_PROBABILITY e PREDICTION_DETAILS geram score e motivo; views JSON alimentam APEX, Select AI e API.", "APEX para o painel; Select AI para perguntas em português; Object Storage e DBMS_SCHEDULER para ingestão e retreino.", "O dado do aluno não sai da instituição: LGPD por arquitetura, sem servidor de ML nem cientista de dados dedicado."], size=11, gap=0.16)
rodape(s, False, N)
notes(s, N, "A15 Arquitetura Oracle", "Apoio para perguntas de arquitetura: onde cada componente Oracle entra e por que o dado nunca sai do banco.")

prs.save(OUT)
with open(os.path.join(AQUI, "notas_apresentador.json"), "w", encoding="utf-8") as f:
    json.dump(NOTAS, f, ensure_ascii=False, indent=1)
print("OK ->", OUT, "| slides:", len(prs.slides))
