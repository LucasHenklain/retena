# -*- coding: utf-8 -*-
"""Gera os diagramas da Retena (SVG + PNG 2x via Edge headless).

Uso:  python gerar_diagramas.py [nome_do_diagrama ...]
Sem argumentos gera todos. Saída na própria pasta 02_Diagramas.
"""
import os, sys, subprocess, html, math

AQUI = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONT_FAMILY = "Sora, Inter, 'Segoe UI', sans-serif"
RODAPE = "Retena · Startup One / Enterprise Challenge Oracle · FIAP 2026"

# Paleta
AZUL = "#0B2545"; AZUL2 = "#13315C"; VERDE = "#2EC4B6"; AMBAR = "#FFB703"
CORAL = "#FF6B4A"; FUNDO = "#F6F7F9"; GRAFITE = "#3A4A5C"; CINZA = "#94A3B8"
BRANCO = "#FFFFFF"; VERDE_CLARO = "#E3F8F5"; AMBAR_CLARO = "#FFF3D6"
CORAL_CLARO = "#FFE4DC"; AZUL_CLARO = "#E6ECF5"; CINZA_CLARO = "#EEF1F5"

def esc(s):
    return html.escape(str(s), quote=True)

# ---------- medição e quebra de texto (estimativa por caractere) ----------
_NARROW = set("iljtfr.,:;'!|()[] -")
_WIDE = set("mwMW@%")
def text_width(s, size, bold=False):
    w = 0.0
    for ch in s:
        if ch in _NARROW: w += 0.31
        elif ch in _WIDE: w += 0.82
        elif ch.isupper(): w += 0.66
        elif ch.isdigit(): w += 0.58
        else: w += 0.54
    return w * size * (1.07 if bold else 1.0)

WRAP_SAFETY = 1.0  # fator de segurança da estimativa de largura (ajustável por diagrama)
def wrap(text, max_w, size, bold=False):
    lines = []
    for par in str(text).split("\n"):
        words = par.split(" ")
        cur = ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if cur and text_width(t, size, bold) * WRAP_SAFETY > max_w:
                lines.append(cur); cur = wd
            else:
                cur = t
        lines.append(cur)
    return lines

# ---------- documento SVG ----------
class SVG:
    def __init__(self, w, h, bg=FUNDO):
        self.w, self.h = w, h
        self.parts = []
        self.defs = set()
        self.bg = bg
    def add(self, s): self.parts.append(s)
    def marker(self, color):
        mid = "m" + color.lstrip("#").lower()
        self.defs.add(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')
        return mid
    def text(self, x, y, s, size=13, color=GRAFITE, bold=False, anchor="start", italic=False, family=None, opacity=1.0, rotate=None):
        fw = ' font-weight="600"' if bold else ''
        fs = ' font-style="italic"' if italic else ''
        fam = f' font-family="{family}"' if family else ''
        op = f' opacity="{opacity}"' if opacity < 1 else ''
        rt = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ''
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}"{fw}{fs}{fam}{op}{rt}>{esc(s)}</text>')
    def lines(self, x, y, lines, size=13, color=GRAFITE, bold=False, anchor="start", lh=None):
        lh = lh or size * 1.35
        for i, ln in enumerate(lines):
            self.text(x, y + i * lh, ln, size, color, bold, anchor)
        return y + len(lines) * lh
    def para(self, x, y, text, max_w, size=13, color=GRAFITE, bold=False, anchor="start", lh=None):
        return self.lines(x, y, wrap(text, max_w, size, bold), size, color, bold, anchor, lh)
    def render(self):
        defs = "".join(sorted(self.defs))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="{FONT_FAMILY}">\n<defs>{defs}</defs>\n'
                f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>\n' + "\n".join(self.parts) + "\n</svg>\n")

# ---------- primitivas ----------
def rect(svg, x, y, w, h, fill=BRANCO, stroke=AZUL, sw=1.5, r=12, dash=None, opacity=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    op = f' opacity="{opacity}"' if opacity < 1 else ''
    svg.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{op}/>')

def box(svg, x, y, w, h, title=None, lines=None, fill=BRANCO, stroke=AZUL, title_color=AZUL,
        text_color=GRAFITE, title_size=15, text_size=12.5, r=12, sw=1.5, dash=None, align="left",
        pad=14, title_bg=None, title_fg=None, center_v=False):
    """Caixa arredondada com título opcional e linhas com quebra automática. Retorna y final do texto."""
    rect(svg, x, y, w, h, fill, stroke, sw, r, dash)
    tx = x + w / 2 if align == "center" else x + pad
    anchor = "middle" if align == "center" else "start"
    cy = y + pad + title_size * 0.85
    if title_bg:
        th = title_size + 18
        svg.add(f'<path d="M{x},{y+r} a{r},{r} 0 0 1 {r},-{r} h{w-2*r} a{r},{r} 0 0 1 {r},{r} v{th-r} h-{w} z" fill="{title_bg}"/>')
        svg.text(tx, y + th / 2 + title_size * 0.36, title, title_size, title_fg or BRANCO, True, anchor)
        cy = y + th + pad * 0.8 + text_size * 0.8
    elif title:
        tl = wrap(title, w - 2 * pad, title_size, True)
        cy = svg.lines(tx, cy, tl, title_size, title_color, True, anchor, lh=title_size * 1.25)
        cy += text_size * 0.55
    if lines:
        body = []
        for ln in ([lines] if isinstance(lines, str) else lines):
            body += wrap(ln, w - 2 * pad, text_size)
        if center_v and not title:
            total = len(body) * text_size * 1.35
            cy = y + (h - total) / 2 + text_size * 0.95
        cy = svg.lines(tx, cy, body, text_size, text_color, False, anchor)
    return cy

def arrow(svg, x1, y1, x2, y2, color=AZUL2, sw=2, dash=None, label=None, label_size=11.5, label_color=None,
          via=None, head=True, label_dy=-6, label_pos=None, halo=False, start_head=False):
    """Seta reta ou com pontos intermediários (via=[(x,y),...]); rótulo no meio (ou em label_pos)."""
    mid = svg.marker(color) if head or start_head else None
    pts = [(x1, y1)] + (via or []) + [(x2, y2)]
    d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    me = f' marker-end="url(#{mid})"' if head else ''
    ms = f' marker-start="url(#{mid})"' if start_head else ''
    if halo:
        svg.add(f'<path d="{d}" fill="none" stroke="{svg.bg}" stroke-width="{sw+7}" stroke-linejoin="round"/>')
    svg.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{me}{ms} stroke-linejoin="round"/>')
    if label:
        # ponto médio do trajeto
        n = len(pts) // 2
        if label_pos:
            lx, ly = label_pos
        elif len(pts) % 2 == 0:
            lx = (pts[n-1][0] + pts[n][0]) / 2; ly = (pts[n-1][1] + pts[n][1]) / 2
        else:
            lx, ly = pts[n]
        tw = text_width(label, label_size) + 10
        svg.add(f'<rect x="{lx-tw/2:.1f}" y="{ly+label_dy-label_size*0.95:.1f}" width="{tw:.1f}" height="{label_size+6:.1f}" rx="4" fill="{FUNDO}" opacity="0.92"/>')
        svg.text(lx, ly + label_dy, label, label_size, label_color or color, False, "middle")

def person(svg, cx, cy, color=AZUL, label=None, sub=None, size=1.0, label_color=None, sub_color=GRAFITE, max_w=150):
    """Ícone-pessoa centrado em (cx, cy) (topo da cabeça em cy). Rótulo abaixo."""
    r = 13 * size
    svg.add(f'<circle cx="{cx}" cy="{cy + r}" r="{r}" fill="{color}"/>')
    bw, bh = 44 * size, 30 * size
    svg.add(f'<path d="M{cx-bw/2},{cy+2*r+bh+4*size} v-{bh*0.55} a{bw/2},{bw/2} 0 0 1 {bw},0 v{bh*0.55} z" fill="{color}"/>')
    y = cy + 2 * r + bh + 4 * size + 18
    if label:
        y = svg.lines(cx, y, wrap(label, max_w, 12.5, True), 12.5, label_color or color, True, "middle")
    if sub:
        svg.lines(cx, y + 1, wrap(sub, max_w, 11), 11, sub_color, False, "middle", lh=13.5)
    return y

def cylinder(svg, x, y, w, h, fill=BRANCO, stroke=AZUL, label=None, sub=None, sw=1.5, dash=None, label_color=None, text_size=12):
    ry = min(14, h * 0.16)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    svg.add(f'<path d="M{x},{y+ry} v{h-2*ry} a{w/2},{ry} 0 0 0 {w},0 v-{h-2*ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>')
    svg.add(f'<ellipse cx="{x+w/2}" cy="{y+ry}" rx="{w/2}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>')
    ty = y + ry * 2 + 20
    if label:
        ty = svg.lines(x + w / 2, ty, wrap(label, w - 16, 13, True), 13, label_color or stroke, True, "middle")
    if sub:
        svg.lines(x + w / 2, ty + 2, wrap(sub, w - 16, text_size), text_size, GRAFITE, False, "middle", lh=text_size * 1.3)

def cloud(svg, cx, cy, w, h, fill=BRANCO, stroke=AZUL, label=None, sub=None, sw=1.5, dash=None, label_color=None):
    da = f' stroke-dasharray="{dash}"' if dash else ''
    # nuvem composta por círculos + base
    rs = [(cx - w*0.28, cy + h*0.05, h*0.32), (cx - w*0.05, cy - h*0.12, h*0.42), (cx + w*0.22, cy + h*0.0, h*0.36), (cx + w*0.36, cy + h*0.15, h*0.26)]
    d = ""
    for (px, py, r) in rs:
        d += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>'
    svg.add(d)
    svg.add(f'<rect x="{cx-w*0.42:.1f}" y="{cy+h*0.05:.1f}" width="{w*0.84:.1f}" height="{h*0.32:.1f}" rx="{h*0.16:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>')
    # apaga traços internos
    for (px, py, r) in rs:
        svg.add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r-sw:.1f}" fill="{fill}"/>')
    svg.add(f'<rect x="{cx-w*0.42+sw:.1f}" y="{cy+h*0.05+sw:.1f}" width="{w*0.84-2*sw:.1f}" height="{h*0.32-2*sw:.1f}" rx="{h*0.16:.1f}" fill="{fill}"/>')
    ty = cy - 2
    if label:
        ty = svg.lines(cx, ty, wrap(label, w * 0.7, 13, True), 13, label_color or stroke, True, "middle")
    if sub:
        svg.lines(cx, ty + 1, wrap(sub, w * 0.7, 11.5), 11.5, GRAFITE, False, "middle", lh=14)

def monitor(svg, x, y, w, h, fill=BRANCO, stroke=AZUL, label=None, sub=None, screen=AZUL_CLARO, dash=None, label_color=None):
    da = f' stroke-dasharray="{dash}"' if dash else ''
    sh = h - 22
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{sh}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{da}/>')
    svg.add(f'<rect x="{x+6}" y="{y+6}" width="{w-12}" height="{sh-12}" rx="4" fill="{screen}"/>')
    svg.add(f'<rect x="{x+w/2-18}" y="{y+sh}" width="36" height="10" fill="{stroke}"/>')
    svg.add(f'<rect x="{x+w/2-40}" y="{y+sh+10}" width="80" height="5" rx="2" fill="{stroke}"/>')
    ty = y + 16 + 12
    if label:
        ty = svg.lines(x + w / 2, ty, wrap(label, w - 28, 13, True), 13, label_color or stroke, True, "middle")
    if sub:
        svg.lines(x + w / 2, ty + 2, wrap(sub, w - 28, 11.5), 11.5, GRAFITE, False, "middle", lh=14)

def bolt(svg, cx, cy, color=CORAL, s=1.0):
    """Raio (conflito)."""
    pts = [(-6, -18), (3, -18), (-2, -4), (7, -4), (-6, 18), (-2, 2), (-9, 2)]
    d = " ".join(f"{cx+px*s:.1f},{cy+py*s:.1f}" for px, py in pts)
    svg.add(f'<polygon points="{d}" fill="{color}" stroke="{BRANCO}" stroke-width="1.5"/>')

def balloon(svg, x, y, w, text, tail=(0, 0), fill=BRANCO, stroke=CINZA, color=AZUL, size=12, italic=True):
    """Balão de fala; tail = ponto (absoluto) para onde a cauda aponta."""
    lines = wrap(text, w - 24, size)
    h = len(lines) * size * 1.35 + 20
    tx, ty = tail
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h:.1f}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
    if tail != (0, 0):
        if tx < x or tx > x + w:  # cauda lateral
            bx = x if tx < x else x + w
            by = min(max(ty, y + 16), y + h - 16)
            svg.add(f'<polygon points="{bx},{by-8:.1f} {bx},{by+8:.1f} {tx},{ty}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
            svg.add(f'<line x1="{bx}" y1="{by-7:.1f}" x2="{bx}" y2="{by+7:.1f}" stroke="{fill}" stroke-width="2.2"/>')
        else:
            bx = min(max(tx, x + 18), x + w - 18)
            by = y + h if ty > y + h else y
            svg.add(f'<polygon points="{bx-8},{by} {bx+8},{by} {tx},{ty}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
            svg.add(f'<line x1="{bx-7}" y1="{by}" x2="{bx+7}" y2="{by}" stroke="{fill}" stroke-width="2.2"/>')
    for i, ln in enumerate(lines):
        svg.text(x + 12, y + 14 + size * 0.85 + i * size * 1.35 - 4, ln, size, color, False, "start", italic)
    return h

def header(svg, title, subtitle=None, tag=None):
    svg.add(f'<rect width="{svg.w}" height="6" fill="{VERDE}"/>')
    svg.text(56, 58, title, 28, AZUL, True)
    if subtitle:
        svg.text(56, 86, subtitle, 15, GRAFITE)
    if tag:
        tw = text_width(tag, 12, True) + 26
        svg.add(f'<rect x="{svg.w-56-tw}" y="36" width="{tw:.1f}" height="28" rx="14" fill="{AZUL}"/>')
        svg.text(svg.w - 56 - tw / 2, 55, tag, 12, BRANCO, True, "middle")
    # marca discreta
    svg.text(svg.w - 56, 90, "Retena", 13, AZUL, True, "end")

def footer(svg, extra=None):
    y = svg.h - 26
    svg.add(f'<line x1="56" y1="{y-18}" x2="{svg.w-56}" y2="{y-18}" stroke="{CINZA}" stroke-width="1"/>')
    svg.text(56, y, RODAPE, 12, GRAFITE)
    if extra:
        svg.text(svg.w - 56, y, extra, 12, GRAFITE, False, "end")

def legend(svg, x, y, items, title="Legenda", cols=1, col_w=300, row_h=22, box_w=None):
    """items: lista de (tipo, cor, texto, dash) — tipo em {'fill','line','dashed','person','bolt','dot'}."""
    rows = math.ceil(len(items) / cols)
    bw = box_w or cols * col_w + 24
    bh = rows * row_h + (34 if title else 16)
    rect(svg, x, y, bw, bh, BRANCO, CINZA, 1, 10)
    oy = y + 14
    if title:
        svg.text(x + 14, y + 20, title, 12.5, AZUL, True); oy = y + 34
    for i, it in enumerate(items):
        tipo, cor, txt = it[0], it[1], it[2]
        dash = it[3] if len(it) > 3 else None
        c, r = divmod(i, rows)
        ix, iy = x + 14 + c * col_w, oy + r * row_h
        if tipo == "fill":
            rect(svg, ix, iy, 26, 14, cor, cor, 1, 3)
        elif tipo == "stroke":
            rect(svg, ix, iy, 26, 14, BRANCO, cor, 2, 3, dash)
        elif tipo == "line":
            d = f' stroke-dasharray="{dash}"' if dash else ''
            svg.add(f'<line x1="{ix}" y1="{iy+7}" x2="{ix+26}" y2="{iy+7}" stroke="{cor}" stroke-width="2.5"{d} marker-end="url(#{svg.marker(cor)})"/>')
        elif tipo == "bolt":
            bolt(svg, ix + 13, iy + 7, cor, 0.45)
        elif tipo == "dot":
            svg.add(f'<circle cx="{ix+13}" cy="{iy+7}" r="7" fill="{cor}"/>')
        elif tipo == "diamond":
            svg.add(f'<polygon points="{ix+13},{iy-2} {ix+26},{iy+7} {ix+13},{iy+16} {ix},{iy+7}" fill="{BRANCO}" stroke="{cor}" stroke-width="2"/>')
        elif tipo == "pill":
            rect(svg, ix, iy, 26, 14, cor, cor, 1, 7)
        svg.text(ix + 36, iy + 12, txt, 11.5, GRAFITE)
    return bh

# ---------- exportação ----------
def salvar(svg, nome):
    svg_path = os.path.join(AQUI, nome + ".svg")
    html_path = os.path.join(AQUI, nome + ".html")
    png_path = os.path.join(AQUI, nome + ".png")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg.render())
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{nome}</title>
<style>
@font-face{{font-family:'Sora';src:url('../03_Marca/fontes/Sora-Variable.ttf') format('truetype');font-weight:100 800;}}
@font-face{{font-family:'Inter';src:url('../03_Marca/fontes/Inter-Variable.ttf') format('truetype');font-weight:100 900;}}
html,body{{margin:0;padding:0;background:{FUNDO};width:{svg.w}px;height:{svg.h}px;overflow:hidden;}}
svg{{display:block;font-family:{FONT_FAMILY};}}
</style></head><body>
{svg.render()}
</body></html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page)
    udd = os.path.join(os.environ.get("TEMP", AQUI), "edge_diag")
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
           f"--user-data-dir={udd}", "--force-device-scale-factor=2", f"--window-size={svg.w},{svg.h}",
           "--virtual-time-budget=4000", f"--screenshot={png_path}", "file:///" + html_path.replace("\\", "/")]
    if os.path.exists(png_path):
        os.remove(png_path)
    import time
    def _espera_png(limite=60):
        """O launcher do Edge pode retornar antes de o PNG ser gravado; espera o arquivo estabilizar."""
        t0 = time.time(); ult = -1
        while time.time() - t0 < limite:
            if os.path.exists(png_path):
                sz = os.path.getsize(png_path)
                if sz > 0 and sz == ult:
                    return True
                ult = sz
            time.sleep(0.5)
        return os.path.exists(png_path)
    for tentativa in range(2):
        try:
            subprocess.run(cmd, timeout=120, capture_output=True)
        except subprocess.TimeoutExpired:
            print("  [aviso] Edge excedeu 120 s em", nome)
        if _espera_png(60 if tentativa == 0 else 90):
            break
        print(f"  [aviso] tentativa {tentativa+1} sem PNG; repetindo")
    ok = os.path.exists(png_path)
    print(f"{nome}: svg ok, png {'ok' if ok else 'FALHOU'}")
    return ok

# =====================================================================
# 06 — Arquitetura Oracle
# =====================================================================
def d06_arquitetura_oracle():
    W, H = 1800, 1100
    s = SVG(W, H)
    header(s, "Arquitetura Oracle da Retena — ML in-database",
           "Do log do LMS à fila de intervenção sem o dado de aluno sair do banco: Autonomous AI Database 26ai + OML + APEX + Select AI",
           "Diagrama 06 · Arquitetura final")
    top, bottom = 150, 900
    # ---- faixas de camada ----
    cols = [("Fontes da IES", 56, 260), ("Ingestão (OCI)", 350, 250), ("Oracle Autonomous AI Database 26ai", 640, 560),
            ("Entrega e canais", 1240, 260), ("Usuários", 1540, 204)]
    for nome, x, w in cols:
        s.text(x + w / 2, top - 14, nome.upper(), 11.5, CINZA, True, "middle")
        s.add(f'<line x1="{x}" y1="{top-4}" x2="{x+w}" y2="{top-4}" stroke="{CINZA}" stroke-width="1" stroke-dasharray="3 4"/>')

    PROV = dict(stroke=VERDE, sw=2.2)          # provado neste projeto
    ROAD = dict(stroke=CINZA, sw=1.6, dash="6 5")  # roadmap

    # ---- 1. Fontes ----
    monitor(s, 90, 230, 190, 130, label="LMS Moodle / FIAP ON", sub="logs de eventos, progresso, quizzes", stroke=AZUL)
    s.text(185, 385, "684.723 eventos · 203 alunos (base do projeto)", 10.5, GRAFITE, False, "middle")
    cylinder(s, 105, 470, 160, 120, label="ERP acadêmico", sub="matrícula, mensalidade, ticket médio", stroke=AZUL, dash="6 5")
    s.text(185, 612, "roadmap: receita em R$ por coorte", 10.5, CINZA, False, "middle")

    # ---- 2. Ingestão ----
    cloud(s, 475, 290, 210, 120, label="OCI Object Storage", sub="landing dos CSVs · DBMS_CLOUD", stroke=CINZA, dash="6 5")
    box(s, 380, 400, 190, 70, "python-oracledb", ["carga direta do logs.csv (dev/piloto)"], stroke=VERDE, sw=2.2, align="center", title_size=13.5, text_size=11.5)
    box(s, 380, 500, 190, 78, "API / webhooks do LMS", ["OCI Functions + API Gateway"], stroke=CINZA, dash="6 5", align="center", title_size=13.5, text_size=11.5, title_color=GRAFITE)

    # ---- 3. Oracle DB (grande) ----
    ox, oy, ow, oh = 640, 175, 560, 640
    rect(s, ox, oy, ow, oh, AZUL_CLARO, AZUL, 2.5, 18)
    s.text(ox + 20, oy + 32, "Oracle Autonomous AI Database 26ai", 17, AZUL, True)
    s.text(ox + 20, oy + 51, "dev: Oracle Database Free 26ai em Docker (gvenzl/oracle-free)", 10.5, GRAFITE)
    s.text(ox + 20, oy + 65, "piloto: Autonomous Always Free (OCI) · produção: um schema por IES, auto-scaling", 10.5, GRAFITE)
    # faixa LGPD
    s.add(f'<path d="M{ox},{oy+oh-40} h{ow} v22 a18,18 0 0 1 -18,18 h-{ow-36} a18,18 0 0 1 -18,-18 z" fill="{VERDE}"/>')
    s.text(ox + ow / 2, oy + oh - 15, "O DADO NÃO SAI DO BANCO (LGPD) — features, treino, scoring e explicação acontecem onde o dado mora", 12.5, AZUL, True, "middle")
    # componentes internos — linha 1
    r1, h1 = oy + 82, 110
    cylinder(s, ox + 30, r1, 150, h1, fill=BRANCO, label="EVENTOS_LMS", sub="log bruto: hora, aluno, contexto, componente, evento", text_size=10.5, **PROV)
    box(s, ox + 210, r1, 150, h1, "Features em SQL", ["ALUNO_SEMANA: eventos 7/14/28 d, recência, capítulos, quizzes, faixa horária"],
        fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, **PROV)
    box(s, ox + 390, r1, 140, h1, "Rótulo histórico", ["inativo 21 d ou não avançou de fase"], fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, **PROV)
    # linha 2
    r2, h2 = r1 + h1 + 32, 122
    box(s, ox + 30, r2, 330, h2, "Oracle Machine Learning — DBMS_DATA_MINING", ["CREATE_MODEL2 (GLM / XGBoost), treino no schema", "PREDICTION_PROBABILITY → score semanal", "PREDICTION_DETAILS → motivo explicável"],
        fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, **PROV)
    box(s, ox + 390, r2, 140, h2, "SCORE_ALUNO", ["p(risco), faixa Alto / Médio / Baixo, motivo, janela 19h–22h"], fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, **PROV)
    # linha 3
    r3, h3 = r2 + h2 + 30, 96
    box(s, ox + 30, r3, 240, h3, "DBMS_SCHEDULER", ["job domingo 23h: features + scoring + fila", "retreino mensal com resultado das intervenções"],
        fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, title_color=GRAFITE, **ROAD)
    box(s, ox + 300, r3, 230, h3, "INTERVENCOES", ["registro de contato e resultado (reativado / não / sem resposta) — realimenta o modelo"],
        fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, title_color=GRAFITE, **ROAD)
    # linha 4
    r4, h4 = r3 + h3 + 30, 92
    box(s, ox + 30, r4, 500, h4, "Views de negócio (JSON / Duality Views)", ["V_FILA_SEMANAL · V_MAPA_ATRITO (fase × capítulo) · V_RECEITA_EM_RISCO (coorte × ticket médio)", "expostas ao APEX, ao Select AI e à API — sem cópia de dados"],
        fill=BRANCO, align="left", title_size=13, text_size=10.5, pad=10, title_color=GRAFITE, **ROAD)
    # setas internas
    arrow(s, ox + 180, r1 + 50, ox + 210, r1 + 50, VERDE, 2)
    arrow(s, ox + 360, r1 + 50, ox + 390, r1 + 50, VERDE, 2)
    arrow(s, ox + 285, r1 + h1, ox + 285, r2, VERDE, 2)
    arrow(s, ox + 460, r1 + h1, ox + 460, r2, VERDE, 2)
    arrow(s, ox + 360, r2 + 60, ox + 390, r2 + 60, VERDE, 2)
    arrow(s, ox + 460, r2 + h2, ox + 460, r4, VERDE, 2, via=[(ox + 460, r2 + h2 + 14), (ox + 545, r2 + h2 + 14), (ox + 545, r4 - 14), (ox + 460, r4 - 14)])
    arrow(s, ox + 150, r2 + h2, ox + 150, r3, CINZA, 1.6, dash="5 4")
    arrow(s, ox + 415, r3 + h3, ox + 415, r4, CINZA, 1.6, dash="5 4")
    arrow(s, ox + 300, r3 + 70, ox + 270, r3 + 70, CINZA, 1.6, dash="5 4", label="retreino", label_pos=(ox + 285, r3 + 92))

    # ---- 4. Entrega ----
    ex, ew = 1290, 210
    monitor(s, ex, 200, ew, 150, label="Oracle APEX", sub="painel da coordenadora: fila, mapa de atrito, registro · dashboard executivo em R$", stroke=CINZA, dash="6 5", screen=CINZA_CLARO)
    box(s, ex, 400, ew, 84, "Select AI", ["perguntas em português sobre as views: \"quem parou no cap 2 da F5?\""], stroke=CINZA, dash="6 5", title_size=13.5, text_size=11, title_color=GRAFITE)
    box(s, ex, 520, ew, 96, "OCI API Gateway + Functions", ["mensagem automática no horário do aluno: WhatsApp / e-mail (roadmap)"], stroke=CINZA, dash="6 5", title_size=13.5, text_size=11, title_color=GRAFITE)
    box(s, ex, 650, ew, 84, "Notebook / relatório do projeto", ["python-oracledb + SQL: AUC 0,88, precisão@top-20% 88%, lift 3×"], stroke=VERDE, sw=2.2, title_size=13, text_size=11)

    # ---- 5. Usuários ----
    ux = 1660
    person(s, ux, 215, AZUL, "Mariana — coordenadora de permanência", "fila toda segunda", max_w=165)
    person(s, ux, 380, AZUL2, "Tutores (12)", "contato ter/qua, 19h–22h", max_w=165)
    person(s, ux, 545, VERDE, "Aluno EAD trabalhador", "chamado antes de desistir", max_w=165)
    person(s, ux, 720, AZUL, "Renata — diretora de operações", "receita em risco e preservada (R$)", max_w=165)

    # ---- setas entre camadas ----
    arrow(s, 280, 300, 400, 300, AZUL2, 2, label="export CSV semanal")
    arrow(s, 280, 300, 380, 435, AZUL2, 2, via=[(320, 300), (320, 435)])
    arrow(s, 265, 530, 380, 540, CINZA, 1.6, dash="5 4", label="API / eventos")
    arrow(s, 565, 315, 640, 315, CINZA, 1.6, dash="5 4", label="DBMS_CLOUD", label_dy=16)
    arrow(s, 570, 435, 640, 380, VERDE, 2.2, via=[(600, 435), (600, 380)])
    arrow(s, 570, 540, 640, 560, CINZA, 1.6, dash="5 4")
    # barramento SQL/REST (banco → entrega)
    bus = 1228
    arrow(s, 1200, r4 + 30, ex, 280, AZUL2, 2, via=[(bus, r4 + 30), (bus, 280)], label="SQL / REST", label_pos=(bus + 12, 262), label_size=10.5)
    arrow(s, bus, 442, ex, 442, AZUL2, 2)
    arrow(s, bus, 568, ex, 568, AZUL2, 2)
    arrow(s, 1200, r4 + 60, ex, 692, VERDE, 2.2, via=[(1214, r4 + 60), (1214, 692)])
    # retorno: registro do contato (APEX) volta para INTERVENCOES
    fb = 1262
    arrow(s, ex, 330, 1200, r3 + 40, CINZA, 1.6, dash="5 4", via=[(fb, 330), (fb, r3 + 40)])
    s.add(f'<rect x="{fb-8}" y="{300}" width="16" height="128" rx="3" fill="{FUNDO}"/>')
    s.text(fb + 4, 364, "registro → INTERVENCOES", 10, CINZA, False, "middle", rotate=-90)
    # entrega → usuários
    arrow(s, ex + ew, 260, ux - 32, 260, VERDE, 2.2, label="fila + motivo")
    arrow(s, ex + ew, 300, ux - 32, 410, VERDE, 2.2, via=[(1532, 300), (1532, 410)])
    arrow(s, ex + ew, 335, ux - 32, 750, AZUL2, 2, via=[(1514, 335), (1514, 750)], label="dashboard em R$", label_pos=(1578, 742), label_size=10.5)
    arrow(s, ex + ew, 575, ux - 32, 575, CINZA, 1.6, dash="5 4", label="WhatsApp / e-mail", halo=True)
    arrow(s, ux, 478, ux, 540, VERDE, 2.2)
    s.text(ux - 14, 514, "liga 19h–22h", 10.5, VERDE, False, "end")

    # ---- legenda ----
    legend(s, 56, 880, [
        ("stroke", VERDE, "Provado neste projeto: Oracle Database Free 26ai em Docker + OML (DBMS_DATA_MINING) + python-oracledb + SQL de features e scoring"),
        ("stroke", CINZA, "Roadmap (piloto/produção): Autonomous Always Free, APEX, Select AI, OCI Object Storage, DBMS_SCHEDULER, API Gateway/Functions", "6 5"),
        ("line", AZUL2, "Fluxo de dados / consulta"),
        ("line", VERDE, "Fluxo positivo: do score à ação da equipe"),
        ("fill", VERDE, "Faixa LGPD: nenhum dado de aluno em ETL externo, servidor de ML ou nuvem de terceiros"),
    ], title="Legenda", cols=1, col_w=900, row_h=22)
    box(s, 1010, 880, 734, 144, "Por que in-database é decisão estratégica", [
        "1. LGPD e venda: elimina a objeção nº 1 da diretora e do jurídico (\"os dados dos alunos não saem da instituição\").",
        "2. Custo e time-to-value: Always Free + APEX = MVP em semanas, sem cientista de dados dedicado nem servidor de ML.",
        "3. Distribuição: ERPs acadêmicos e grupos já rodam Oracle; a Retena entra como extensão do que a IES já tem.",
        "4. Defensibilidade: o retreino com resultados das intervenções cria dado proprietário dentro do banco de cada cliente.",
    ], fill=BRANCO, stroke=AZUL, title_size=14, text_size=11.5, pad=14)
    footer(s, "Mesmo dialeto SQL do dev ao Autonomous: migração por Data Pump / scripts, zero reescrita")
    return s, "06_arquitetura_oracle"

def badge(svg, cx, cy, num, fill=AMBAR, color=AZUL, r=11):
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{BRANCO}" stroke-width="2"/>')
    svg.text(cx, cy + 4.5, str(num), 12, color, True, "middle")

# =====================================================================
# 05 — Arquitetura inicial (antes da decisão Oracle)
# =====================================================================
def d05_arquitetura_inicial():
    W, H = 1600, 1000
    s = SVG(W, H)
    header(s, "Arquitetura inicial — pipeline de ML fora da IES",
           "Primeira proposta (Fases 1–4): exportar logs do LMS, processar em Python e servir um dashboard próprio. Substituída pelo desenho in-database após a validação.",
           "Diagrama 05 · Antes da decisão Oracle")
    top = 172
    # fronteiras
    rect(s, 40, top, 276, 490, BRANCO, CORAL, 1.8, 14, dash="8 6")
    s.text(178, top + 22, "DENTRO DA IES", 11.5, CORAL, True, "middle")
    rect(s, 336, top, 1224, 490, AMBAR_CLARO, AMBAR, 1.8, 14, dash="8 6")
    s.text(948, top + 22, "INFRAESTRUTURA DA RETENA (NUVEM DE TERCEIROS) — O DADO NOMINAL DO ALUNO SAI DA IES", 11.5, "#B07A00", True, "middle")
    cols = [("Fontes", 56, 244), ("Ingestão / ETL", 356, 200), ("Processamento de ML", 596, 320), ("Armazenamento e API", 966, 260), ("Apresentação", 1276, 268)]
    for nome, x, w in cols:
        s.text(x + w / 2, top - 12, nome.upper(), 11.5, CINZA, True, "middle")
        s.add(f'<line x1="{x}" y1="{top-4}" x2="{x+w}" y2="{top-4}" stroke="{CINZA}" stroke-width="1" stroke-dasharray="3 4"/>')

    # fontes
    monitor(s, 86, 240, 190, 130, label="LMS Moodle", sub="logs de eventos, notas, progresso", stroke=AZUL)
    cylinder(s, 100, 440, 160, 120, label="ERP acadêmico", sub="matrícula, mensalidade (roda Oracle)", stroke=AZUL, dash="6 5")
    # ingestão
    box(s, 366, 250, 180, 80, "Export CSV / API do LMS", ["extração semanal manual ou por script"], align="center", title_size=13, text_size=11)
    box(s, 366, 390, 180, 96, "ETL — scripts Python", ["cron: extrai, limpa e carrega; sem monitoramento; reprocesso manual"], align="center", title_size=13, text_size=11)
    badge(s, 546, 390, 1)
    # servidor de ML
    rect(s, 596, 212, 320, 380, BRANCO, AZUL2, 2, 14)
    s.text(616, 240, "Servidor de ML (VM / contêiner próprio)", 14.5, AZUL, True)
    badge(s, 916, 212, 3)
    box(s, 616, 262, 130, 96, "pandas", ["limpeza e features aluno-semana"], fill=AZUL_CLARO, stroke=AZUL2, align="center", title_size=13, text_size=11, pad=10)
    box(s, 766, 262, 130, 96, "scikit-learn", ["HistGradientBoosting + regressão logística"], fill=AZUL_CLARO, stroke=AZUL2, align="center", title_size=13, text_size=11, pad=10)
    box(s, 616, 384, 130, 78, "modelo.pkl", ["artefato versionado à mão"], fill=AZUL_CLARO, stroke=AZUL2, align="center", title_size=13, text_size=11, pad=10)
    box(s, 766, 384, 130, 78, "Scoring em lote", ["script semanal gera scores.csv"], fill=AZUL_CLARO, stroke=AZUL2, align="center", title_size=13, text_size=11, pad=10)
    box(s, 616, 488, 280, 84, "Jupyter Notebook", ["exploração, retreino e ajuste de faixas feitos manualmente por um cientista de dados"], fill=AZUL_CLARO, stroke=AZUL2, align="center", title_size=13, text_size=11, pad=10)
    badge(s, 896, 488, 4)
    arrow(s, 746, 310, 766, 310, AZUL2, 2)
    arrow(s, 831, 358, 831, 384, AZUL2, 2)
    arrow(s, 766, 423, 746, 423, AZUL2, 2)
    arrow(s, 681, 384, 681, 358, AZUL2, 2, dash="4 3")
    arrow(s, 756, 488, 756, 462, AZUL2, 2, dash="4 3", label="retreino manual", label_size=10, label_pos=(756, 480))
    # banco e API
    cylinder(s, 996, 250, 200, 170, label="Banco relacional genérico", sub="PostgreSQL / MySQL: alunos, features, scores, intervenções", stroke=AZUL)
    badge(s, 1196, 262, 5)
    box(s, 996, 480, 200, 90, "API REST (FastAPI)", ["autenticação, endpoints de fila, relatório e registro de contato"], align="center", title_size=13, text_size=11)
    arrow(s, 1096, 420, 1096, 480, AZUL2, 2)
    # apresentação
    monitor(s, 1300, 240, 220, 150, label="Dashboard web próprio", sub="React / Streamlit: fila, filtros, relatório em R$ — front-end do zero", stroke=AZUL)
    badge(s, 1520, 240, 6)
    person(s, 1350, 460, AZUL, "Coordenadora", max_w=110)
    person(s, 1470, 460, AZUL2, "Tutores", max_w=110)
    arrow(s, 1410, 412, 1410, 455, AZUL2, 2)
    # fluxo entre camadas
    arrow(s, 276, 300, 366, 290, AZUL2, 2, label="CSV nominal", label_dy=-8)
    badge(s, 326, 262, 2)
    arrow(s, 456, 330, 456, 390, AZUL2, 2)
    arrow(s, 546, 438, 616, 300, AZUL2, 2, via=[(576, 438), (576, 300)], label="logs brutos", label_size=10, label_pos=(576, 372), label_dy=0)
    arrow(s, 896, 423, 996, 423, AZUL2, 2, via=[(946, 423)], label="scores.csv", label_size=10, label_dy=-8)
    arrow(s, 1196, 525, 1300, 525, AZUL2, 2, via=[(1250, 525), (1250, 330), (1300, 330)], head=True, label="JSON", label_size=10, label_pos=(1250, 425))
    arrow(s, 260, 500, 456, 488, CINZA, 1.6, dash="5 4", via=[(456, 500)], head=True)
    s.text(356, 516, "ticket médio (planilha)", 10, CINZA, False, "middle")

    # legenda
    legend(s, 56, 676, [
        ("stroke", AZUL, "Componente a construir e operar pela Retena"),
        ("dot", AMBAR, "Limitação identificada na validação (numerada abaixo)"),
        ("stroke", CORAL, "Fronteira da IES (onde o dado nasce)", "8 6"),
        ("line", AZUL2, "Fluxo de dados (cópias sucessivas)"),
    ], title=None, cols=4, col_w=370, row_h=22)

    # painel de limitações
    lx, ly, lw, lh = 56, 728, 1000, 192
    rect(s, lx, ly, lw, lh, BRANCO, AMBAR, 1.8, 12)
    s.text(lx + 16, ly + 24, "Limitações anotadas na validação (Fase 5) — por que este desenho não fecha a venda", 13.5, AZUL, True)
    lim = [
        (1, "ETL externo", "cópia semanal dos logs; falha silenciosa; reprocessamento manual; latência de dias."),
        (2, "O dado sai da IES", "logs nominais de alunos em servidor de terceiros — objeção nº 1 da diretora e do jurídico (LGPD)."),
        (3, "Servidor de ML dedicado", "VM, dependências, deploy do .pkl e monitoramento: custo fixo antes do primeiro cliente."),
        (4, "Exige cientista de dados", "notebook → produção e retreino manuais; a IES não consegue operar sozinha."),
        (5, "Dado em dois lugares", "banco da Retena duplica o que já está no Oracle do ERP; sincronização e divergência."),
        (6, "Front-end do zero", "meses de desenvolvimento para painel, relatório em R$ e formulários de contato."),
    ]
    for i, (n, t, d) in enumerate(lim):
        c, r = divmod(i, 3)
        bx, by = lx + 16 + c * 495, ly + 50 + r * 48
        badge(s, bx + 11, by + 4, n)
        s.text(bx + 30, by + 2, t + ":", 12, AZUL, True)
        s.lines(bx + 30, by + 17, wrap(d, 400, 11), 11, GRAFITE, lh=13.5)
    # decisão
    box(s, 1080, 728, 464, 192, "Decisão (Fase 6): levar o ML para dentro do banco", [
        "A validação mostrou que \"o dado não sai da IES\" é condição de compra, que o ERP acadêmico já roda Oracle e que a equipe não terá cientista de dados dedicado.",
        "Resposta: Oracle Autonomous AI Database com OML (treino e scoring em SQL), APEX no lugar do front-end próprio e Select AI para perguntas em português — ver Diagrama 06.",
    ], fill=VERDE_CLARO, stroke=VERDE, sw=2, title_size=14, text_size=11.5)
    footer(s, "Componentes 1–6 desaparecem ou viram serviço gerenciado na arquitetura Oracle")
    return s, "05_arquitetura_inicial"

def pill(svg, x, y, text, fill=AMBAR, color=AZUL, size=11, bold=True, prefix=None):
    """Pílula de destaque (insight). Retorna largura."""
    t = (prefix + "  " if prefix else "") + text
    w = text_width(t, size, bold) + 22
    svg.add(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{size+12}" rx="{(size+12)/2}" fill="{fill}"/>')
    svg.text(x + 11, y + size + 2, t, size, color, bold)
    return w

def antenna(svg, cx, cy, r=60):
    """Símbolo da Retena: círculo com antena e ondas de radar."""
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{VERDE_CLARO}" stroke="{VERDE}" stroke-width="3"/>')
    svg.add(f'<line x1="{cx}" y1="{cy+r*0.55}" x2="{cx}" y2="{cy-r*0.1}" stroke="{AZUL}" stroke-width="3" stroke-linecap="round"/>')
    svg.add(f'<circle cx="{cx}" cy="{cy-r*0.15}" r="{r*0.09}" fill="{AZUL}"/>')
    svg.add(f'<line x1="{cx-r*0.35}" y1="{cy+r*0.55}" x2="{cx+r*0.35}" y2="{cy+r*0.55}" stroke="{AZUL}" stroke-width="3" stroke-linecap="round"/>')
    for k, rr in enumerate([0.3, 0.5, 0.7]):
        svg.add(f'<path d="M{cx-r*rr*0.87},{cy-r*0.15-r*rr*0.5} a{r*rr},{r*rr} 0 0 1 {2*r*rr*0.87},0" fill="none" stroke="{VERDE if k<2 else AZUL}" stroke-width="{3-k*0.5}" stroke-linecap="round"/>')

# =====================================================================
# 01 — Rich picture
# =====================================================================
def d01_rich_picture():
    W, H = 1600, 1000
    s = SVG(W, H)
    header(s, "Rich picture — o sistema da evasão silenciosa no EAD",
           "Atores, preocupações, fluxos e conflitos em torno do aluno que some sem aviso; a Retena entra como antena que lê os logs e avisa quem deve agir",
           "Diagrama 01 · Visão sistêmica")
    # contexto externo
    cloud(s, 228, 205, 330, 170, label="Contexto: INEP / Semesp / Abmes", sub="desistência anual EAD ≈ 41% · mensalidade = receita recorrente · ERPs das IES já rodam Oracle", stroke=CINZA, label_color=GRAFITE)
    # sistemas
    monitor(s, 700, 150, 200, 130, label="LMS (Moodle / FIAP ON)", sub="eventos por aluno: acesso, capítulo, quiz, PDF/HTML", stroke=AZUL)
    cylinder(s, 990, 165, 120, 100, label="ERP acadêmico", sub="matrícula, notas, mensalidade", stroke=AZUL, dash="6 5")
    # Retena
    antenna(s, 800, 470, 60)
    s.text(800, 556, "Retena — radar de permanência", 15, AZUL, True, "middle")
    s.para(800, 575, "lê os logs no próprio banco, pontua o risco e diz quem chamar, quando e por quê", 240, 11, GRAFITE, anchor="middle")
    # atores
    person(s, 470, 380, AZUL, "Mariana, coordenadora de permanência", "usa o painel toda segunda", max_w=150)
    person(s, 330, 640, AZUL2, "Tutor sobrecarregado", "200 alunos por pessoa", max_w=130)
    person(s, 800, 690, VERDE, "Aluno EAD trabalhador", "estuda 19h–22h, seg–qui", max_w=150)
    person(s, 1240, 165, AZUL, "Renata, diretora de operações", "compra: protege receita", max_w=150)
    person(s, 1300, 470, GRAFITE, "TI + Jurídico (LGPD)", "aprova integração e dados", max_w=140)
    person(s, 1180, 650, AZUL2, "Coordenação pedagógica", "dona do conteúdo", max_w=140)
    # balões
    balloon(s, 200, 290, 230, "Descubro tarde. Quando vejo, o aluno já sumiu há um mês — e não tenho critério de quem chamar primeiro.", tail=(455, 392), stroke=CORAL)
    balloon(s, 80, 560, 220, "Quem eu ligo primeiro? São 200 alunos, ligo no escuro e ninguém registra o que funcionou.", tail=(318, 652), stroke=CORAL)
    balloon(s, 880, 720, 250, "Estudo das 19h às 22h depois do trabalho. Travei no capítulo 2, perdi o ritmo por 3 semanas e ninguém percebeu.", tail=(830, 708), stroke=CORAL)
    balloon(s, 1330, 300, 240, "Só vejo a evasão quando a receita cai. Quanto isso devolve em rematrícula?", tail=(1262, 262), stroke=CORAL)
    balloon(s, 1340, 385, 220, "Dados dos alunos não podem sair da IES. E integração não pode virar projeto de TI.", tail=(1322, 485), stroke=CORAL)
    balloon(s, 1260, 700, 280, "O capítulo 2 da F5 trava todo mundo — mas só descubro pela reclamação, meses depois.", tail=(1202, 680), stroke=CORAL)
    # fluxos
    arrow(s, 800, 285, 800, 405, AZUL2, 2.2, label="logs do LMS: 684.723 eventos", label_pos=(895, 345), label_size=10.5)
    arrow(s, 1050, 268, 830, 418, CINZA, 1.6, dash="5 4", via=[(1050, 340)], label="ERP: mensalidade (roadmap)", label_pos=(1050, 300), label_size=10)
    arrow(s, 775, 700, 698, 252, CINZA, 1.6, dash="5 4", via=[(660, 700), (660, 252)])
    s.add(f'<rect x="652" y="478" width="16" height="124" rx="3" fill="{FUNDO}"/>')
    s.text(656, 540, "acessa à noite, seg–qui", 10, CINZA, False, "middle", rotate=-90)
    arrow(s, 742, 455, 496, 425, VERDE, 2.4, label="fila toda segunda + motivo", label_pos=(640, 420), label_size=10.5)
    arrow(s, 455, 508, 350, 640, AZUL2, 2, label="distribui contatos", label_pos=(392, 570), label_size=10.5)
    arrow(s, 365, 702, 770, 714, VERDE, 2.4, label="liga 19h–22h com um caminho concreto", label_pos=(565, 690), label_size=10.5)
    arrow(s, 860, 450, 1216, 215, AZUL2, 2, via=[(1140, 450), (1140, 215)], label="receita em risco e preservada (R$)", label_pos=(1000, 442), label_size=10.5)
    arrow(s, 860, 480, 1268, 480, VERDE, 2.4, label="modelo roda no Oracle da IES: o dado não sai", label_pos=(1060, 497), label_size=10.5)
    arrow(s, 850, 500, 1150, 660, AZUL2, 2, label="mapa de atrito por fase × capítulo", label_pos=(990, 548), label_size=10.5)
    # conflitos
    bolt(s, 565, 712, CORAL, 0.8)
    s.text(565, 748, "hoje: ligação aleatória, no horário errado, soa como cobrança", 10.5, CORAL, True, "middle")
    bolt(s, 560, 330, CORAL, 0.8)
    s.text(560, 366, "BI do LMS mostra só o passado", 10.5, CORAL, True, "middle")
    bolt(s, 1010, 640, CORAL, 0.8)
    s.text(1010, 676, "atrito nos capítulos iniciais", 10.5, CORAL, True, "middle")
    # insights da validação
    pill(s, 440, 612, "30% dos alunos inativos há mais de 14 dias", prefix="A")
    pill(s, 880, 812, "pico de atividade 19h–22h, seg–qui: a hora certa de chamar", prefix="B")
    pill(s, 1250, 785, "atrito concentrado nos caps. 1–2 (F5: 25 alunos)", prefix="C")
    pill(s, 1120, 118, "dupla persona: quem usa (Mariana) ≠ quem compra (Renata)", prefix="D")
    pill(s, 1200, 605, "LGPD: \"o dado não sai da IES\" é condição de compra", prefix="E")
    # legenda
    legend(s, 56, 888, [
        ("dot", AZUL, "Ator (pessoa) · balão = preocupação a confirmar nas entrevistas (Anexo A)"),
        ("bolt", CORAL, "Conflito / dor do processo atual"),
        ("line", AZUL2, "Fluxo de dados ou de trabalho hoje"),
        ("line", VERDE, "Fluxo que a Retena introduz"),
        ("line", CINZA, "Fluxo secundário / roadmap", "5 4"),
        ("fill", AMBAR, "Insight A–E da validação com dados (base real) e fontes secundárias"),
    ], title=None, cols=3, col_w=490, row_h=22)
    footer(s, "Base: 684.723 eventos de 203 alunos (FIAP ON) · hipóteses a confirmar nas entrevistas (instrumento no Anexo A)")
    return s, "01_rich_picture"

# =====================================================================
# 02 — Mapa de stakeholders (poder × interesse)
# =====================================================================
def d02_mapa_stakeholders():
    W, H = 1600, 1000
    s = SVG(W, H)
    header(s, "Mapa de stakeholders — poder × interesse",
           "Quem decide, quem usa e quem precisa ser convencido; as setas mostram como a validação (Fase 5) mudou a posição de três atores",
           "Diagrama 02 · Stakeholders")
    MX, MY, MW, MH = 120, 150, 940, 690
    hx, hy = MX + MW / 2, MY + MH / 2
    # quadrantes
    quads = [
        (MX, MY, AMBAR_CLARO, "MANTER SATISFEITO", "alto poder, baixo interesse: mostrar que LGPD, TI e caixa estão cobertos", "#B07A00"),
        (hx, MY, VERDE_CLARO, "GERENCIAR DE PERTO", "alto poder, alto interesse: envolver na decisão e no piloto de 90 dias", "#1C8C82"),
        (MX, hy, CINZA_CLARO, "MONITORAR", "baixo poder, baixo interesse: acompanhar; comunicação mínima", GRAFITE),
        (hx, hy, AZUL_CLARO, "MANTER INFORMADO", "baixo poder, alto interesse: treinar, ouvir e devolver resultado", AZUL2),
    ]
    for qx, qy, fill, t, d, c in quads:
        rect(s, qx, qy, MW / 2, MH / 2, fill, fill, 0, 0)
        s.text(qx + 16, qy + 24, t, 12.5, c, True)
        s.text(qx + 16, qy + 42, d, 10.5, GRAFITE)
    rect(s, MX, MY, MW, MH, "none", CINZA, 1.2, 0)
    s.add(f'<line x1="{hx}" y1="{MY}" x2="{hx}" y2="{MY+MH}" stroke="{BRANCO}" stroke-width="3"/>')
    s.add(f'<line x1="{MX}" y1="{hy}" x2="{MX+MW}" y2="{hy}" stroke="{BRANCO}" stroke-width="3"/>')
    # eixos
    arrow(s, MX, MY + MH + 14, MX + MW, MY + MH + 14, GRAFITE, 1.5)
    s.text(MX + MW / 2, MY + MH + 40, "INTERESSE no problema da evasão (quanto a dor pesa no dia a dia)  →", 12, GRAFITE, True, "middle")
    arrow(s, MX - 14, MY + MH, MX - 14, MY, GRAFITE, 1.5)
    s.text(MX - 28, MY + MH / 2, "PODER / influência na decisão de compra  →", 12, GRAFITE, True, "middle", rotate=-90)

    def P(ix, py): return MX + ix * MW, MY + (1 - py) * MH
    def pt(ix, py, name, sub, color, ghost=False, lpos="r", r=10, max_w=170):
        x, y = P(ix, py)
        if ghost:
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{BRANCO}" stroke="{color}" stroke-width="2" stroke-dasharray="3 3" opacity="0.9"/>')
        else:
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="{BRANCO}" stroke-width="2.5"/>')
        if lpos == "b":
            tx, anchor, ty = x, "middle", y + r + 16
        else:
            tx = x + r + 8 if lpos == "r" else x - r - 8
            anchor = "start" if lpos == "r" else "end"
            ty = y - 2
        col = CINZA if ghost else color
        ny = s.lines(tx, ty, wrap(name, max_w, 12.5, True), 12.5, col, True, anchor, lh=15)
        if sub:
            s.lines(tx, ny + 1, wrap(sub, max_w, 10.5), 10.5, GRAFITE if not ghost else CINZA, False, anchor, lh=13)
        return x, y

    # posições "depois da validação"
    pt(0.13, 0.86, "Reitoria / mantenedora", "aprova o contrato", AZUL)
    pt(0.44, 0.62, "Financeiro", "quer ver R$ preservado × assinatura", AZUL)
    pt(0.28, 0.56, "TI da IES", "integração leve: CSV do Moodle", GRAFITE)
    pt(0.90, 0.76, "Renata — diretora de operações", "SPONSOR: compra proteção de receita", AZUL, lpos="l", r=13, max_w=180)
    pt(0.66, 0.82, "FIAP / banca", "avalia solução, pitch e uso Oracle", AMBAR, lpos="l", max_w=150)
    pt(0.76, 0.66, "Oracle / parceiro", "canal e crédito; caso OML + APEX", AMBAR, lpos="r", max_w=200)
    pt(0.62, 0.74, "Jurídico / LGPD", "veto se o dado sair da IES; aprova in-database", GRAFITE, lpos="b", max_w=170)
    pt(0.92, 0.60, "Mariana — coordenadora de permanência", "USUÁRIA e campeã interna; usa a fila toda segunda", VERDE, lpos="l", r=13, max_w=240)
    pt(0.66, 0.40, "Coordenação pedagógica", "recebe o mapa de atrito por capítulo", VERDE, lpos="r", max_w=190)
    pt(0.78, 0.24, "Tutores", "executam o contato 19h–22h; registram resultado", VERDE, lpos="r", max_w=170)
    pt(0.55, 0.10, "Alunos EAD trabalhadores", "beneficiários; tom de apoio, não cobrança", VERDE, lpos="r", max_w=220)
    # posições "antes" (fantasmas) + setas de movimento
    ax, ay = pt(0.33, 0.80, "Diretora (antes)", "só via a evasão na receita", AZUL, ghost=True, lpos="b", max_w=130)
    jx, jy = pt(0.12, 0.66, "Jurídico (antes)", "fora do radar da venda", GRAFITE, ghost=True, lpos="b", max_w=120)
    cx_, cy_ = pt(0.22, 0.36, "Coord. pedagógica (antes)", "sem dado sobre onde o aluno trava", VERDE, ghost=True, lpos="l", max_w=160)
    v = P(0.62, 0.90); dx, dy = P(0.90, 0.76)
    arrow(s, ax + 12, ay - 4, dx - 4, dy - 16, CORAL, 2.4, via=[v], label="vira sponsor: dashboard de R$ em risco", label_size=10.5, label_pos=(v[0], v[1] - 10), label_dy=0)
    v = P(0.36, 0.72); dx, dy = P(0.62, 0.74)
    arrow(s, jx + 12, jy - 3, dx - 14, dy + 1, CORAL, 2.4, via=[v], label="entra na decisão: \"o dado não sai da IES\"", label_size=10.5, label_pos=(v[0] - 10, v[1] + 22), label_dy=0)
    v = P(0.45, 0.32); dx, dy = P(0.66, 0.40)
    arrow(s, cx_ + 12, cy_ + 2, dx - 14, dy + 2, CORAL, 2.4, via=[v], label="ganha interesse: mapa de atrito", label_size=10.5, label_pos=(v[0], v[1] + 22), label_dy=0)

    # painel lateral
    px, py, pw = 1100, 150, 444
    rect(s, px, py, pw, 690, BRANCO, CINZA, 1.2, 12)
    s.text(px + 18, py + 30, "O que a validação mudou no mapa", 15, AZUL, True)
    mud = [
        ("Diretora de operações vira sponsor", "Tinha poder, mas via a evasão só na queda de receita. O dashboard de R$ em risco e o relatório mensal a transformam em compradora e patrocinadora do piloto."),
        ("Jurídico / LGPD entra na decisão", "Antes ausente da conversa; \"o dado não sai da IES\" virou condição de compra e levou o ML para dentro do Oracle da IES (Diagrama 06)."),
        ("Coordenação pedagógica ganha interesse", "O mapa de atrito por fase × capítulo dá a ela um dado que nunca teve: onde o aluno trava, antes da reclamação."),
    ]
    yy = py + 54
    for i, (t, d) in enumerate(mud):
        arrow(s, px + 18, yy + 6, px + 46, yy + 6, CORAL, 2.4)
        s.text(px + 54, yy + 10, t, 12.5, AZUL, True)
        yy = s.lines(px + 54, yy + 26, wrap(d, pw - 76, 11), 11, GRAFITE, lh=14) + 12
    s.add(f'<line x1="{px+18}" y1="{yy}" x2="{px+pw-18}" y2="{yy}" stroke="{CINZA_CLARO}" stroke-width="2"/>')
    yy += 26
    s.text(px + 18, yy, "Mensagem e canal por stakeholder", 15, AZUL, True)
    yy += 16
    tab = [
        ("Diretora / financeiro", "receita preservada em R$ vs. assinatura", "relatório mensal APEX"),
        ("Coordenadora", "fila priorizada com motivo explicável", "painel APEX, segunda 8h"),
        ("Tutores", "quem ligar, quando (19h–22h) e o que dizer", "e-mail-resumo + painel"),
        ("Jurídico e TI", "in-database, CSV do Moodle, pseudonimização", "reunião de arquitetura"),
        ("Coord. pedagógica", "capítulos que travam a turma", "ticket na quinta"),
        ("Oracle / parceiro", "caso de uso OML + APEX + Select AI", "programa de parceria"),
    ]
    cw = [118, 178, 112]
    s.text(px + 18, yy + 14, "Quem", 10.5, CINZA, True); s.text(px + 18 + cw[0], yy + 14, "Mensagem-chave", 10.5, CINZA, True); s.text(px + 18 + cw[0] + cw[1], yy + 14, "Canal", 10.5, CINZA, True)
    yy += 22
    for q, m, c in tab:
        s.add(f'<line x1="{px+18}" y1="{yy}" x2="{px+pw-18}" y2="{yy}" stroke="{CINZA_CLARO}" stroke-width="1"/>')
        l1 = wrap(q, cw[0] - 8, 11, True); l2 = wrap(m, cw[1] - 8, 11); l3 = wrap(c, cw[2] - 8, 11)
        s.lines(px + 18, yy + 15, l1, 11, AZUL, True, lh=13)
        s.lines(px + 18 + cw[0], yy + 15, l2, 11, GRAFITE, lh=13)
        s.lines(px + 18 + cw[0] + cw[1], yy + 15, l3, 11, GRAFITE, lh=13)
        yy += 8 + 13 * max(len(l1), len(l2), len(l3)) + 4
    # legenda
    legend(s, 120, 900, [
        ("dot", AZUL, "Decisores e compradores"),
        ("dot", VERDE, "Usuários e beneficiários"),
        ("dot", GRAFITE, "Controle e tecnologia (TI, jurídico)"),
        ("dot", AMBAR, "Externos: Oracle, FIAP/banca"),
        ("stroke", CINZA, "Posição antes da validação", "3 3"),
        ("line", CORAL, "Movimento após a validação (Fase 5)"),
    ], title=None, cols=6, col_w=236, row_h=22, box_w=1424)
    footer(s, "Fonte: análise da base real + brief Enterprise Challenge Oracle · posições a confirmar nas entrevistas (Anexo A)")
    return s, "02_mapa_stakeholders"

def smooth_path(pts):
    """Curva suave (Catmull-Rom → Bézier) passando pelos pontos."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d

# =====================================================================
# 03 — Jornada da usuária (Mariana)
# =====================================================================
def d03_jornada_usuario():
    global WRAP_SAFETY; WRAP_SAFETY = 1.08
    W, H = 1800, 1000
    s = SVG(W, H)
    header(s, "Jornada da usuária — a semana de Mariana com a Retena",
           "Coordenadora de permanência: do job de domingo ao retreino mensal. A curva compara a emoção com a Retena e como é hoje, sem ela",
           "Diagrama 03 · Jornada do usuário")
    X0, CW, GAP = 200, 150, 4.4
    def cx(i): return X0 + i * (CW + GAP)
    def cm(i): return cx(i) + CW / 2
    # fases
    fases = [("Automático", 0, 0, GRAFITE), ("Segunda: priorizar e distribuir", 1, 3, AZUL),
             ("Contato e registro", 4, 5, "#1C8C82"), ("Aprender e ajustar", 6, 7, AZUL2), ("Provar valor e evoluir", 8, 9, "#B07A00")]
    for t, a, b, c in fases:
        x = cx(a); w = cx(b) + CW - x
        rect(s, x, 118, w, 26, c, c, 0, 6)
        s.text(x + w / 2, 136, t.upper(), 11, BRANCO, True, "middle")
    # faixas
    rows = [("ETAPA", 156, 96), ("AÇÃO", 262, 122), ("PONTO DE CONTATO", 394, 52), ("EMOÇÃO", 456, 196), ("MÉTRICA", 662, 84)]
    for i, (t, y, h) in enumerate(rows):
        fill = BRANCO if i % 2 == 0 else CINZA_CLARO
        rect(s, 56, y, W - 112, h, fill, fill, 0, 8)
        s.lines(64, y + 22, wrap(t, 120, 11, True), 11, CINZA, True, lh=13)
    etapas = [
        ("Dom 23h", "Job semanal roda sozinho", "sistema", "Recalcula features e scores no Autonomous DB (OML); gera a fila e dispara o e-mail-resumo para Mariana e tutores.", [("job OML", GRAFITE, BRANCO), ("e-mail", AZUL_CLARO, AZUL)], 0.15, "tranquila: roda sem ninguém", None, "203 alunos pontuados em minutos"),
        ("Seg 8h", "Abre o Pulso da turma", "Mariana", "Painel APEX: 203 alunos, 31 vermelhos, 44 amarelos e a receita em risco desta semana, em R$.", [("APEX", AZUL, BRANCO)], -0.3, "apreensiva: 31 vermelhos", (-0.8, "descobre tarde, na mensalidade"), "31 vermelhos · 44 amarelos · R$ em risco"),
        ("Seg 8h30", "Prioriza a fila", "Mariana", "Ordena por probabilidade × valor; cada linha traz o motivo: \"12 dias sem acesso, tendência −65%, parado no cap 2 da F5\".", [("APEX", AZUL, BRANCO)], 0.35, "no controle: sabe por quê", None, "top-20% da fila: precisão 88%"),
        ("Seg 9h", "Distribui aos tutores", "Mariana", "Atribui responsáveis em dois cliques; o sistema sugere modelo de mensagem e janela de contato (19h–22h, terça ou quarta).", [("APEX", AZUL, BRANCO), ("e-mail", AZUL_CLARO, AZUL)], 0.5, "ágil: dois cliques", None, "100% da fila com tutor em 10 min"),
        ("Ter–Qua 19h–22h", "Tutor contata o aluno", "tutor", "Liga ou manda mensagem no horário sugerido, com ação concreta: \"vamos retomar o cap 2 juntos; segue o resumo em PDF\".", [("WhatsApp / telefone", VERDE, AZUL)], 0.25, "expectativa: momento da verdade", (-0.6, "liga no escuro; soa cobrança"), "taxa de resposta por horário"),
        ("Ter–Qui", "Registra o resultado", "tutor", "Marca respondeu / não respondeu / voltou; a reativação é marcada sozinha quando o LMS registra novo acesso em 7 dias.", [("APEX", AZUL, BRANCO)], 0.65, "alívio: o aluno voltou", None, "reativação em 7 dias (novo acesso)"),
        ("Qui", "Confere o mapa de atrito", "Mariana", "Vê que os caps. 1–2 da F5 concentram travamentos; abre ticket para a coordenação pedagógica (dividir capítulo, vídeo curto).", [("APEX", AZUL, BRANCO)], -0.15, "preocupada: o cap 2 trava", (-0.7, "só sabe pela reclamação"), "caps. 1–2: 25 alunos travados"),
        ("Sob demanda", "Pergunta em português", "Mariana", "Select AI: \"quantos amarelos da F4 não fizeram quiz nas últimas 2 semanas?\" — e ajusta a fila sem pedir SQL a ninguém.", [("Select AI", AMBAR, AZUL)], 0.5, "autônoma: sem depender de TI", None, "resposta em segundos, sem SQL"),
        ("Fim do mês", "Relatório para Renata", "Mariana → diretora", "Relatório executivo: alunos reativados, resposta por horário e receita preservada em R$ vs. custo da assinatura.", [("APEX (PDF)", AZUL, BRANCO)], 0.85, "orgulhosa: R$ na mesa", (-0.9, "só via a receita cair"), "R$ preservado ÷ assinatura"),
        ("Mensal", "Retreino do modelo", "sistema", "Resultados registrados realimentam o OML; o score da próxima segunda já incorpora o que funcionou naquela IES.", [("job OML", GRAFITE, BRANCO)], 0.7, "confiante: o modelo aprende", None, "AUC e lift recalculados; faixas ajustadas"),
    ]
    ymid, amp = 554, 75
    pts, ghost = [], []
    for i, (quando, titulo, ator, acao, canais, emo, emo_txt, hoje, metrica) in enumerate(etapas):
        x = cx(i)
        # etapa
        badge(s, x + 16, 176, i + 1, AZUL, BRANCO, 12)
        s.text(x + 34, 180, quando, 11, AZUL, True)
        ty = s.lines(x + 6, 204, wrap(titulo, CW - 12, 12.5, True), 12.5, AZUL, True, lh=15)
        s.text(x + 6, 244, "quem: " + ator, 10, CINZA, False)
        # ação
        s.lines(x + 6, 280, wrap(acao, CW - 20, 10.5), 10.5, GRAFITE, lh=13)
        # canais
        px = x + 6
        for txt, f, c in canais:
            px += pill(s, px, 408, txt, f, c, 10.5) + 4
        # emoção
        py = ymid - emo * amp
        pts.append((cm(i), py))
        lab = wrap(emo_txt, CW - 8, 10)
        if emo >= 0:
            s.lines(cm(i), py - 12 - (len(lab) - 1) * 12, lab, 10, "#1C8C82", True, "middle", lh=12)
        else:
            s.lines(cm(i), py + 20, lab, 10, "#1C8C82", True, "middle", lh=12)
        if hoje:
            gy = ymid - hoje[0] * amp
            ghost.append((cm(i), gy, hoje[1]))
        # métrica
        s.lines(x + 6, 684, wrap(metrica, CW - 12, 11, True), 11, AZUL, True, lh=13.5)
        # separador de coluna
        if i:
            s.add(f'<line x1="{x-GAP/2:.1f}" y1="156" x2="{x-GAP/2:.1f}" y2="746" stroke="{CINZA}" stroke-width="0.8" stroke-dasharray="2 4"/>')
    # curva de emoção
    s.add(f'<line x1="{cx(0)}" y1="{ymid}" x2="{cx(9)+CW}" y2="{ymid}" stroke="{CINZA}" stroke-width="1" stroke-dasharray="4 4"/>')
    s.text(cx(0) - 6, ymid + 4, "neutro", 9.5, CINZA, False, "end")
    s.text(cx(0) - 6, ymid - amp + 4, "+", 12, CINZA, True, "end")
    s.text(cx(0) - 6, ymid + amp + 4, "−", 12, CINZA, True, "end")
    gp = [(g[0], g[1]) for g in ghost]
    s.add(f'<path d="{smooth_path(gp)}" fill="none" stroke="{CINZA}" stroke-width="2" stroke-dasharray="6 5"/>')
    for gx, gy, gt in ghost:
        s.add(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="5" fill="{BRANCO}" stroke="{CINZA}" stroke-width="2"/>')
        s.lines(gx, gy + 16, wrap("hoje: " + gt, CW - 8, 9.5), 9.5, GRAFITE, False, "middle", lh=11.5)
    s.add(f'<path d="{smooth_path(pts)}" fill="none" stroke="{VERDE}" stroke-width="3.5" stroke-linecap="round"/>')
    for px_, py_ in pts:
        s.add(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="6.5" fill="{VERDE}" stroke="{BRANCO}" stroke-width="2.5"/>')
    # laço de retorno
    arrow(s, cm(9), 746, cm(0), 746, AZUL2, 2, dash="6 4", via=[(cm(9), 762), (cm(0), 762)],
          label="o resultado registrado realimenta o modelo — a próxima segunda começa com uma fila melhor", label_size=10.5, label_pos=(W / 2, 762), label_dy=0)
    # destaques
    bw = (W - 112 - 32) / 3
    box(s, 56, 790, bw, 104, "Momento da verdade (etapa 5)", ["O tutor liga entre 19h e 22h, na janela em que o aluno de fato estuda, com um caminho concreto — não uma cobrança. É aqui que a probabilidade vira permanência."], fill=VERDE_CLARO, stroke=VERDE, sw=1.8, title_size=13, text_size=10.5, pad=26)
    box(s, 56 + bw + 16, 790, bw, 104, "O que muda em relação a hoje", ["Hoje Mariana descobre a evasão na mensalidade, o tutor liga no escuro e o capítulo que trava só aparece pela reclamação. Com a Retena, a semana começa com fila, motivo e janela de contato."], fill=AMBAR_CLARO, stroke=AMBAR, sw=1.8, title_size=13, text_size=10.5, pad=26)
    box(s, 56 + 2 * (bw + 16), 790, bw, 104, "Ciclo fechado (etapas 6 → 10)", ["Cada contato registrado vira rótulo para o retreino mensal: o modelo aprende o que funcionou naquela IES, sem cientista de dados e sem o dado sair do banco."], fill=AZUL_CLARO, stroke=AZUL2, sw=1.8, title_size=13, text_size=10.5, pad=26)
    legend(s, 56, 908, [
        ("line", VERDE, "Emoção de Mariana com a Retena"),
        ("line", CINZA, "Como é hoje, sem a Retena", "6 5"),
        ("fill", AZUL, "APEX (painel / relatório)"),
        ("fill", VERDE, "Contato com o aluno"),
        ("fill", AMBAR, "Select AI (pergunta em português)"),
        ("fill", GRAFITE, "Automático (job OML)"),
    ], title=None, cols=6, col_w=276, row_h=22, box_w=W - 112)
    footer(s, "Jornada validada com a persona usuária (conceito final, seção 7)")
    WRAP_SAFETY = 1.0
    return s, "03_jornada_usuario"

# ---------- formas de fluxograma ----------
def diamond(svg, cx, cy, w, h, text, fill=BRANCO, stroke=AZUL, size=12.5):
    svg.add(f'<polygon points="{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}" fill="{fill}" stroke="{stroke}" stroke-width="1.8" stroke-linejoin="round"/>')
    ls = wrap(text, w * 0.62, size, True)
    y0 = cy - (len(ls) - 1) * size * 1.3 / 2 + size * 0.36
    svg.lines(cx, y0, ls, size, AZUL, True, "middle", lh=size * 1.3)

def terminal(svg, cx, cy, w, h, text, fill=AZUL, color=BRANCO):
    rect(svg, cx - w / 2, cy - h / 2, w, h, fill, fill, 0, h / 2)
    svg.text(cx, cy + 4.5, text, 13, color, True, "middle")

def proc(svg, cx, cy, w, h, title, sub=None, fill=BRANCO, stroke=AZUL, title_color=AZUL, skew=0, sw=1.8):
    if skew:
        svg.add(f'<polygon points="{cx-w/2+skew},{cy-h/2} {cx+w/2},{cy-h/2} {cx+w/2-skew},{cy+h/2} {cx-w/2},{cy+h/2}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')
    else:
        rect(svg, cx - w / 2, cy - h / 2, w, h, fill, stroke, sw, 10)
    tl = wrap(title, w - 2 * skew - 28, 12.5, True)
    sl = wrap(sub, w - 2 * skew - 44, 10.5) if sub else []
    total = len(tl) * 15 + (len(sl) * 13 + 3 if sl else 0)
    y0 = cy - total / 2 + 11
    y = svg.lines(cx, y0, tl, 12.5, title_color, True, "middle", lh=15)
    if sl:
        svg.lines(cx, y + 2, sl, 10.5, GRAFITE, False, "middle", lh=13)

# =====================================================================
# 04 — Fluxograma do MVP
# =====================================================================
def d04_fluxograma_mvp():
    W, H = 1400, 1300
    s = SVG(W, H)
    header(s, "Fluxograma do MVP — do log ao aluno reativado",
           "Ciclo semanal de scoring e intervenção, com retorno mensal de resultados para o modelo. Tudo roda dentro do Oracle da IES; as pessoas agem pelo APEX",
           "Diagrama 04 · Fluxo do MVP")
    MX, AX, BX, RX = 700, 350, 1050, 1330
    BW, BH = 300, 64
    # raias (anotação lateral)
    lanes = [(204, 650, "AUTOMÁTICO — job semanal dentro do Oracle da IES (OML)", VERDE),
             (672, 953, "PESSOAS — Mariana e tutores no APEX", AZUL),
             (988, 1052, "GESTÃO", GRAFITE)]
    for y1, y2, t, c in lanes:
        s.add(f'<line x1="176" y1="{y1}" x2="176" y2="{y2}" stroke="{c}" stroke-width="3" stroke-linecap="round"/>')
        s.text(160, (y1 + y2) / 2, t, 11, c, True, "middle", rotate=-90)
    # fluxo principal
    terminal(s, MX, 150, 320, 44, "INÍCIO — domingo 23h, job semanal")
    proc(s, MX, 232, BW, BH, "Logs do LMS (Moodle / FIAP ON)", "684.723 eventos · CSV exportado ou API", fill=AZUL_CLARO, skew=16)
    proc(s, MX, 318, BW, BH, "Normalização", "eventos → aluno-semana; pseudonimização (Aluno NNNN)")
    proc(s, MX, 404, BW, BH, "Features semanais", "acessos 7/14/28 dias, tendência, capítulo atual, quiz, PDF/HTML")
    proc(s, MX, 490, BW, BH, "Scoring OML no Autonomous DB", "probabilidade de inatividade em 21 dias · AUC-ROC 0,88", fill=VERDE_CLARO, stroke=VERDE, sw=2.2)
    diamond(s, MX, 600, 230, 100, "Faixa de risco?")
    # nota de faixas
    rect(s, 880, 452, 290, 58, AMBAR_CLARO, AMBAR, 1.4, 10, dash="5 4")
    s.text(895, 472, "Faixas calibradas na validação", 11.5, "#B07A00", True)
    s.lines(895, 488, wrap("Alto ≥ 0,60 (95% de fato ficam inativos) · Médio 0,30–0,60 · Baixo < 0,30", 260, 10.5), 10.5, GRAFITE, lh=13)
    # ramos
    proc(s, AX, 705, BW, 66, "ALTO → contato do tutor", "19h–22h, terça ou quarta, com ação concreta e o motivo do alerta", fill=CORAL_CLARO, stroke=CORAL, title_color="#B3401F")
    proc(s, MX, 705, BW, 66, "MÉDIO → mensagem automática", "e-mail / WhatsApp com convite de retomada; segue monitorado", fill=AMBAR_CLARO, stroke=AMBAR, title_color="#B07A00")
    proc(s, BX, 705, BW, 66, "BAIXO → nenhuma ação", "segue monitorado na próxima rodada semanal", fill=VERDE_CLARO, stroke=VERDE, title_color="#1C8C82")
    proc(s, AX, 805, BW, BH, "Registrar resultado no APEX", "respondeu / não respondeu / voltou a acessar (automático em 7 dias)")
    diamond(s, AX, 905, 230, 96, "Reativado em 7 dias?")
    proc(s, MX, 905, BW, BH, "Plano de retomada", "2º contato, ajuste de conteúdo com a coordenação, acompanhamento")
    proc(s, AX, 1020, BW, BH, "Receita preservada", "aluno permanece; mensalidade contabilizada em R$", fill=VERDE_CLARO, stroke=VERDE, sw=2.2)
    proc(s, MX, 1020, BW, BH, "Relatório mensal para a diretora", "R$ preservado vs. assinatura; resposta por horário")
    proc(s, BX, 1020, BW, BH, "Retreino mensal (OML)", "resultados registrados viram rótulos; faixas reajustadas", fill=VERDE_CLARO, stroke=VERDE, sw=2.2)
    # setas do fluxo
    A = lambda *a, **k: arrow(s, *a, **k)
    A(MX, 172, MX, 200, AZUL2, 2)
    A(MX, 264, MX, 286, AZUL2, 2)
    A(MX, 350, MX, 372, AZUL2, 2)
    A(MX, 436, MX, 458, AZUL2, 2)
    A(MX, 522, MX, 550, AZUL2, 2)
    A(MX - 115, 600, AX, 672, CORAL, 2.2, via=[(AX, 600)], label="Alto", label_pos=(470, 600), label_dy=-8)
    A(MX, 650, MX, 672, "#B07A00", 2.2, label="Médio", label_pos=(740, 664), label_dy=0)
    A(MX + 115, 600, BX, 672, VERDE, 2.2, via=[(BX, 600)], label="Baixo", label_pos=(930, 600), label_dy=-8)
    A(AX, 738, AX, 773, AZUL2, 2)
    A(MX, 738, AX + BW / 2, 805, AZUL2, 2, via=[(MX, 805)], label="resultado da mensagem", label_size=10, label_pos=(600, 805), label_dy=-8)
    A(BX + BW / 2, 705, RX, 705, VERDE, 2, head=False)
    s.add(f'<circle cx="{RX}" cy="705" r="5" fill="{VERDE}"/>')
    A(AX, 837, AX, 857, AZUL2, 2)
    A(AX, 953, AX, 988, VERDE, 2.2, label="Sim", label_pos=(AX + 24, 973), label_dy=0)
    A(AX + 115, 905, MX - BW / 2, 905, CORAL, 2.2, label="Não", label_pos=(508, 905), label_dy=-8)
    A(MX, 937, MX, 988, AZUL2, 2)
    A(AX + BW / 2, 1020, MX - BW / 2, 1020, AZUL2, 2)
    A(MX + BW / 2, 1020, BX - BW / 2, 1020, AZUL2, 2)
    A(BX + BW / 2, 1020, MX + 160, 150, VERDE, 2.2, dash="8 5", via=[(RX, 1020), (RX, 150)])
    s.add(f'<rect x="{RX-9}" y="240" width="18" height="430" rx="3" fill="{FUNDO}"/>')
    s.text(RX + 4, 455, "volta ao início: próximo domingo (fila) · próximo mês (retreino)", 10.5, "#1C8C82", True, "middle", rotate=-90)
    # legenda
    legend(s, 56, 1176, [
        ("pill", AZUL, "Início / fim do ciclo"),
        ("stroke", AZUL, "Processo"),
        ("stroke", VERDE, "Processo in-database (OML) — o dado não sai da IES"),
        ("diamond", AZUL, "Decisão"),
        ("line", AZUL2, "Fluxo semanal"),
        ("line", VERDE, "Retorno do ciclo", "8 5"),
    ], title=None, cols=3, col_w=420, row_h=22, box_w=W - 112)
    footer(s, "Faixas e métricas: base FIAP ON, split temporal (teste ≥ jun/2026)")
    return s, "04_fluxograma_mvp"

# =====================================================================
# 07 — Fluxo de dados e ML
# =====================================================================
def d07_fluxo_dados_ml():
    global WRAP_SAFETY; WRAP_SAFETY = 1.08
    W, H = 1600, 900
    s = SVG(W, H)
    header(s, "Fluxo de dados e ML — de 684.723 eventos à fila semanal",
           "Como os logs do LMS viram probabilidade de evasão, faixa de risco e ação. Métricas do teste temporal (Fase 4) e equivalentes in-database no OML (Fase 6)",
           "Diagrama 07 · Dados e modelo")
    NW, GAP, X0, NY, NH = 160, 30, 56, 206, 96
    def nx(i): return X0 + i * (NW + GAP)
    for a, b, t, c in [(0, 2, "DADOS", AZUL), (3, 5, "MODELO", "#1C8C82"), (6, 7, "DECISÃO E AÇÃO", "#B07A00")]:
        x = nx(a); w = nx(b) + NW - x
        rect(s, x, 124, w, 24, c, c, 0, 6)
        s.text(x + w / 2, 141, t, 11, BRANCO, True, "middle")
    titles = ["Logs brutos do LMS", "Normalização", "Base aluno-semana", "Split temporal", "Treino dos modelos", "Avaliação (teste)", "Faixas de risco", "Fila + mapa de atrito"]
    for i, t in enumerate(titles):
        s.text(nx(i) + NW / 2, 176, f"{i+1}. {t}", 12, AZUL, True, "middle")
    # nós
    cylinder(s, nx(0), NY, NW, NH, AZUL_CLARO, AZUL, "684.723 eventos", "203 alunos · FIAP ON", text_size=10.5)
    proc(s, nx(1) + NW / 2, NY + NH / 2, NW, NH, "Limpar e padronizar", "pseudonimizar · semana ISO")
    cylinder(s, nx(2), NY, NW, NH, AZUL_CLARO, AZUL, "aluno × semana", "features + rótulo", text_size=10.5)
    x = nx(3); rect(s, x, NY, NW, NH, BRANCO, AZUL, 1.8, 10)
    wt = (NW - 16) * 0.6; wv = (NW - 16) * 0.4 - 4
    rect(s, x + 6, NY + 6, wt, NH - 12, AZUL_CLARO, AZUL_CLARO, 0, 6)
    rect(s, x + 6 + wt + 4, NY + 6, wv, NH - 12, AMBAR_CLARO, AMBAR_CLARO, 0, 6)
    s.text(x + 6 + wt / 2, NY + NH / 2 - 3, "treino", 11.5, AZUL, True, "middle"); s.text(x + 6 + wt / 2, NY + NH / 2 + 12, "< jun/2026", 10, GRAFITE, False, "middle")
    s.text(x + 6 + wt + 4 + wv / 2, NY + NH / 2 - 3, "teste", 11.5, "#B07A00", True, "middle"); s.text(x + 6 + wt + 4 + wv / 2, NY + NH / 2 + 12, "≥ jun/26", 10, GRAFITE, False, "middle")
    proc(s, nx(4) + NW / 2, NY + NH / 2, NW, NH, "Gradient boosting", "+ regressão logística (baseline)", fill=VERDE_CLARO, stroke=VERDE, sw=2.2)
    proc(s, nx(5) + NW / 2, NY + NH / 2, NW, NH, "AUC-ROC 0,88", "precisão@top-20% 88% · lift 3×", fill=VERDE_CLARO, stroke=VERDE, sw=2.2)
    x = nx(6); rect(s, x, NY, NW, NH, BRANCO, AZUL, 1.8, 10)
    bh = (NH - 16) / 3
    for k, (t, f, c) in enumerate([("Alto ≥ 0,60", CORAL_CLARO, "#B3401F"), ("Médio 0,30–0,60", AMBAR_CLARO, "#B07A00"), ("Baixo < 0,30", VERDE_CLARO, "#1C8C82")]):
        rect(s, x + 6, NY + 6 + k * (bh + 2), NW - 12, bh, f, f, 0, 4)
        s.text(x + NW / 2, NY + 6 + k * (bh + 2) + bh / 2 + 4, t, 11, c, True, "middle")
    monitor(s, nx(7), NY - 4, NW, NH + 8, label="Fila semanal", sub="APEX · segunda 8h", stroke=AZUL)
    for i in range(7):
        arrow(s, nx(i) + NW + 1, NY + NH / 2, nx(i + 1) - 1, NY + NH / 2, AZUL2, 2)
    # cartões de detalhe
    CY, CH = 328, 246
    cards = [
        ["203 alunos, fases F1–F5 (FIAP ON)", "eventos: acesso, capítulo visto, quiz, download PDF/HTML, horário", "extração: CSV exportado (padrão Moodle) ou API — sem projeto de TI", "dado nominal fica no banco da IES"],
        ["limpeza e deduplicação de eventos", "pseudonimização: Aluno NNNN fora do painel", "calendário semanal (seg–dom) e fase/capítulo por evento", "tabela EVENTO(aluno, semana, tipo, fase, capítulo)"],
        ["1 linha = aluno × semana", "features em janelas de 7 / 14 / 28 dias: nº de acessos, dias ativos, tendência (Δ%), capítulo atual, quizzes, PDFs, horário típico", "rótulo inativo_21d: nenhum acesso nos 21 dias seguintes"],
        ["treino: semanas anteriores a jun/2026", "teste: semanas a partir de jun/2026", "sem vazamento temporal — o modelo só vê o passado", "reproduz a produção: pontuar hoje o que acontece daqui a 3 semanas"],
        ["HistGradientBoosting (principal): melhor ranking", "regressão logística (baseline): coeficientes explicam o motivo", "equivalentes OML in-database: XGBoost / GLM", "saída: probabilidade 0–1 por aluno-semana"],
        None,
        ["Alto ≥ 0,60 → contato do tutor (19h–22h)", "Médio 0,30–0,60 → mensagem automática", "Baixo < 0,30 → apenas monitorar", "limiares recalibrados no retreino mensal, por IES"],
        ["fila ordenada por probabilidade × valor, com motivo explicável", "mapa de atrito: fase × capítulo em que o aluno trava", "e-mail-resumo para Mariana e tutores", "Select AI para perguntas em português"],
    ]
    for i, c in enumerate(cards):
        x = nx(i)
        rect(s, x, CY, NW, CH, BRANCO, CINZA, 1, 10)
        arrow(s, x + NW / 2, NY + NH + 4, x + NW / 2, CY - 2, CINZA, 1.2, dash="3 3")
        if c is None:
            mets = [("0,88", "AUC-ROC no teste temporal"), ("88%", "precisão no top-20% da fila"), ("3×", "lift vs. escolha aleatória"), ("95%", "da faixa Alto de fato inativos")]
            yy = CY + 30
            for v, l in mets:
                s.text(x + 12, yy, v, 19, "#1C8C82", True)
                s.lines(x + 12, yy + 14, wrap(l, NW - 24, 9.5), 9.5, GRAFITE, lh=11)
                yy += 52
            s.text(x + 12, CY + CH - 12, "preliminares: F5 em curso", 9, CINZA, False, italic=True)
            continue
        yy = CY + 22
        for ln in c:
            ls = wrap(ln, NW - 40, 10.5)
            s.text(x + 10, yy, "•", 10.5, VERDE, True)
            yy = s.lines(x + 20, yy, ls, 10.5, GRAFITE, lh=12.5) + 5
    # retorno do retreino
    arrow(s, nx(7) + NW / 2, CY + CH, nx(4) + NW / 2, CY + CH + 2, VERDE, 2.2, dash="8 5",
          via=[(nx(7) + NW / 2, CY + CH + 24), (nx(4) + NW / 2, CY + CH + 24)],
          label="retreino mensal: resultados dos contatos viram novos rótulos e recalibram limiares", label_size=10.5, label_pos=((nx(4) + nx(7)) / 2 + NW / 2, CY + CH + 24), label_dy=-9)
    # decisões de modelagem
    bw = (W - 112 - 32) / 3; by = 640
    box(s, 56, by, bw, 168, "Por que split temporal, e não aleatório", ["Evasão é um fenômeno no tempo: misturar semanas futuras no treino infla as métricas. O corte em jun/2026 reproduz a produção — o modelo só conhece o passado quando pontua a semana corrente."], fill=AZUL_CLARO, stroke=AZUL2, sw=1.8, title_size=13, text_size=10.5, pad=26)
    box(s, 56 + bw + 16, by, bw, 168, "Por que duas famílias de modelo", ["O gradient boosting entrega o melhor ranking (AUC 0,88); a regressão logística traduz o motivo em linguagem simples para a coordenadora. No Oracle, OML oferece os equivalentes (XGBoost / GLM) treinados e pontuados em SQL, sem o dado sair do banco."], fill=VERDE_CLARO, stroke=VERDE, sw=1.8, title_size=13, text_size=10.5, pad=26)
    box(s, 56 + 2 * (bw + 16), by, bw, 168, "Rótulo preliminar e retreino", ["Com 203 alunos e a F5 em andamento, inativo_21d é um rótulo proxy e as métricas são preliminares. O retreino mensal incorpora o resultado dos contatos (respondeu / voltou) e recalibra os limiares para cada IES."], fill=AMBAR_CLARO, stroke=AMBAR, sw=1.8, title_size=13, text_size=10.5, pad=26)
    footer(s, "Base FIAP ON: 684.723 eventos · 203 alunos · teste temporal ≥ jun/2026")
    WRAP_SAFETY = 1.0
    return s, "07_fluxo_dados_ml"

# =====================================================================
# 00 — Índice HTML
# =====================================================================
INDICE = [
    ("01_rich_picture", "Rich picture — o sistema da evasão silenciosa no EAD", "Atores, preocupações, fluxos e conflitos em torno do aluno que some; a Retena como radar que lê os logs e devolve a fila semanal."),
    ("02_mapa_stakeholders", "Mapa de stakeholders — poder × interesse", "Quatro quadrantes com estratégia de engajamento e as três mudanças de posição trazidas pela validação."),
    ("03_jornada_usuario", "Jornada da usuária — a semana de Mariana", "Dez etapas, do job de domingo ao retreino mensal, com ação, ponto de contato, curva de emoção e métrica."),
    ("04_fluxograma_mvp", "Fluxograma do MVP — do log ao aluno reativado", "Scoring semanal, faixas Alto / Médio / Baixo, contato, registro, receita preservada e retorno ao ciclo."),
    ("05_arquitetura_inicial", "Arquitetura inicial — pipeline de ML fora da IES", "Primeira proposta (Fases 1–4) e as seis limitações apontadas na validação."),
    ("06_arquitetura_oracle", "Arquitetura Oracle — ML dentro do banco da IES", "Autonomous AI Database com OML, APEX e Select AI: o dado não sai da IES."),
    ("07_fluxo_dados_ml", "Fluxo de dados e ML — de 684.723 eventos à fila semanal", "Normalização, base aluno-semana, split temporal, modelos, métricas, faixas e saídas."),
]

def gerar_indice():
    cards = "\n".join(f"""
    <article class="card">
      <a href="{n}.png" target="_blank"><img src="{n}.png" alt="{esc(t)}" loading="lazy"></a>
      <div class="corpo">
        <span class="num">Diagrama {n[:2]}</span>
        <h2>{esc(t)}</h2>
        <p>{esc(d)}</p>
        <p class="links"><a href="{n}.svg" target="_blank">SVG</a> · <a href="{n}.png" target="_blank">PNG</a> · <a href="{n}.html" target="_blank">HTML</a></p>
      </div>
    </article>""" for n, t, d in INDICE)
    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Retena — Diagramas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
@font-face{{font-family:'Sora';src:url('../03_Marca/fontes/Sora-Variable.ttf') format('truetype');font-weight:100 800;}}
@font-face{{font-family:'Inter';src:url('../03_Marca/fontes/Inter-Variable.ttf') format('truetype');font-weight:100 900;}}
*{{box-sizing:border-box}} body{{margin:0;background:{FUNDO};color:{GRAFITE};font-family:Inter,'Segoe UI',sans-serif;}}
header{{background:#fff;border-top:6px solid {VERDE};padding:28px 48px 22px;display:flex;align-items:center;gap:28px;flex-wrap:wrap}}
header img{{height:56px}} header h1{{font-family:Sora,Inter,sans-serif;color:{AZUL};font-size:26px;margin:0}} header p{{margin:4px 0 0;font-size:14px}}
.nota{{margin:20px 48px 0;padding:12px 16px;background:{VERDE_CLARO};border-left:4px solid {VERDE};border-radius:8px;font-size:14px;color:{AZUL}}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:22px;padding:24px 48px 40px}}
.card{{background:#fff;border:1px solid #DDE3EA;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}}
.card img{{width:100%;display:block;aspect-ratio:16/10;object-fit:cover;object-position:top;border-bottom:1px solid #EEF1F5;background:{FUNDO}}}
.corpo{{padding:16px 18px 18px}} .num{{font-size:11px;font-weight:600;letter-spacing:.06em;color:{VERDE};text-transform:uppercase}}
h2{{font-family:Sora,Inter,sans-serif;font-size:17px;color:{AZUL};margin:6px 0 8px;line-height:1.3}} .corpo p{{font-size:13.5px;line-height:1.45;margin:0 0 10px}}
.links a{{color:{AZUL2};font-weight:600;text-decoration:none}} .links a:hover{{text-decoration:underline}}
footer{{padding:16px 48px 28px;font-size:12.5px;color:{GRAFITE};border-top:1px solid #DDE3EA;margin:0 48px}}
</style></head><body>
<header><img src="../03_Marca/logo/retena_horizontal_escuro_sobre_claro.svg" alt="Retena"><div><h1>Diagramas — Fase 6</h1><p>Sete diagramas do conceito, da jornada e da arquitetura da Retena, em SVG e PNG (2x).</p></div></header>
<div class="nota">Diagramas atualizados na Fase 6 após a validação e a integração Oracle.</div>
<main>{cards}
</main>
<footer>{esc(RODAPE)}</footer>
</body></html>"""
    with open(os.path.join(AQUI, "00_indice_diagramas.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("00_indice_diagramas.html: ok")

DIAGRAMAS = {
    "01_rich_picture": d01_rich_picture,
    "02_mapa_stakeholders": d02_mapa_stakeholders,
    "03_jornada_usuario": d03_jornada_usuario,
    "04_fluxograma_mvp": d04_fluxograma_mvp,
    "05_arquitetura_inicial": d05_arquitetura_inicial,
    "06_arquitetura_oracle": d06_arquitetura_oracle,
    "07_fluxo_dados_ml": d07_fluxo_dados_ml,
}

if __name__ == "__main__":
    nomes = sys.argv[1:] or list(DIAGRAMAS.keys()) + ["indice"]
    for n in nomes:
        if n == "indice":
            gerar_indice(); continue
        svg, nome = DIAGRAMAS[n]()
        salvar(svg, nome)
