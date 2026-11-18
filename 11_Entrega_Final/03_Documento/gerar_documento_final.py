# -*- coding: utf-8 -*-
"""
gerar_documento_final.py - Retena_Documento_Final.md -> .html (marca) -> .pdf (Edge headless) + .docx (python-docx).
Uso: python gerar_documento_final.py [--sem-pdf] [--sem-docx]
"""
import argparse, base64, os, re, subprocess, tempfile
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
ENTREGA = AQUI.parent.parent
MARCA = ENTREGA / "03_Marca"
FONTE_MD = AQUI / "Retena_Documento_Final.md"
SAIDA = AQUI / "Retena_Documento_Final"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def ler_md():
    txt = FONTE_MD.read_text(encoding="utf-8")
    meta = {}
    if txt.startswith("---"):
        cab, txt = txt[3:].split("---", 1)
        for l in cab.strip().splitlines():
            k, v = l.split(":", 1); meta[k.strip()] = v.strip()
    return meta, txt


def data_uri(p: Path, mime):
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


CSS = """
@font-face{font-family:Sora;src:url(%(sora)s) format('truetype');font-weight:100 800}
@font-face{font-family:Inter;src:url(%(inter)s) format('truetype');font-weight:100 900}
@page{size:A4;margin:18mm 16mm 18mm 16mm}
*{box-sizing:border-box}
body{font:10.2pt/1.5 Inter,sans-serif;color:#3A4A5C;margin:0;font-feature-settings:"tnum" 1}
.capa{height:261mm;background:#0B2545;color:#fff;margin:-0mm;padding:30mm 22mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;border-radius:6px}
.capa img{width:70mm}
.capa h1{font:700 30pt/1.15 Sora,sans-serif;color:#fff;margin:0 0 6mm;border:0;padding:0;page-break-before:avoid!important}
.capa .sub{font-size:12.5pt;color:#C9D6E6}
.capa .tag{font:600 13pt Sora,sans-serif;color:#2EC4B6;margin-top:10mm}
.capa .eq{font-size:10pt;color:#C9D6E6;line-height:1.7}
.capa .pulso{height:3px;background:linear-gradient(90deg,#2EC4B6,#2EC4B6 60%%,transparent);margin:8mm 0}
h1{font:700 19pt/1.2 Sora,sans-serif;color:#0B2545;margin:0 0 4mm;padding-bottom:2mm;border-bottom:3px solid #2EC4B6;page-break-before:always}
h1.primeiro{page-break-before:avoid}
h2{font:600 13pt/1.25 Sora,sans-serif;color:#0B2545;margin:6mm 0 2mm;page-break-after:avoid}
h3,h4{font:600 11pt Sora,sans-serif;color:#13315C;margin:4mm 0 1.5mm}
p{margin:0 0 2.6mm}
ul,ol{margin:0 0 3mm;padding-left:6mm}
li{margin:0.8mm 0}
b,strong{color:#0B2545}
code{font:8.6pt Consolas,monospace;background:#EEF2F6;padding:0 3px;border-radius:3px;color:#0B2545}
pre{background:#0B2545;color:#D8F3F0;padding:3mm 4mm;border-radius:4px;font:8.6pt Consolas,monospace;white-space:pre-wrap}
pre code{background:none;color:inherit}
table{border-collapse:collapse;width:100%%;margin:2mm 0 4mm;font-size:8.6pt;page-break-inside:auto}
tr{page-break-inside:avoid}
th{background:#0B2545;color:#fff;text-align:left;padding:1.8mm 2.2mm;font-weight:600}
td{padding:1.6mm 2.2mm;border-bottom:1px solid #E2E7EE;vertical-align:top}
tr:nth-child(even) td{background:#F6F7F9}
img{max-width:100%%;display:block;margin:2mm auto 1mm;border:1px solid #E2E7EE;border-radius:4px}
p.legenda{text-align:center;font-size:8.4pt;color:#94A3B8;margin-bottom:4mm}
hr{display:none}
.fluxo{display:grid;grid-template-columns:repeat(6,1fr);gap:2mm;margin:3mm 0 4mm}
.fluxo div{background:#F1F6FB;border-top:3px solid #2EC4B6;border-radius:4px;padding:2mm;font-size:8.2pt}
.fluxo b{display:block;font-family:Sora;color:#0B2545;margin-bottom:1mm}
.pendente{background:#FFF4D6;border-left:4px solid #FFB703;padding:3mm 4mm;margin:2mm 0 4mm;border-radius:3px;font-size:9.4pt}
.bmc{display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:auto auto auto;gap:1.6mm;font-size:7.8pt;margin:2mm 0 4mm}
.bmc>div{border:1px solid #CBD3DE;border-radius:4px;padding:2mm;background:#fff}
.bmc h4{margin:0 0 1mm;font-size:8.6pt;color:#0B2545}
.bmc ul{padding-left:3.5mm;margin:0}
.bmc-pk{grid-column:1;grid-row:1/3}.bmc-ka{grid-column:2;grid-row:1}.bmc-kr{grid-column:2;grid-row:2}
.bmc-vp{grid-column:3;grid-row:1/3;background:#EAFAF8!important;border-color:#2EC4B6!important}
.bmc-cr{grid-column:4;grid-row:1}.bmc-ch{grid-column:4;grid-row:2}.bmc-cs{grid-column:5;grid-row:1/3}
.bmc-co{grid-column:1/3;grid-row:3}.bmc-rs{grid-column:3/6;grid-row:3}
.rodape-doc{font-size:8pt;color:#94A3B8;text-align:center;margin-top:8mm}
"""


def montar_html(meta, corpo_md):
    html = markdown.markdown(corpo_md, extensions=["tables", "fenced_code", "md_in_html", "sane_lists"])
    # imagens: legenda a partir do alt e embed base64 (HTML autocontido)
    def img(m):
        alt, src = m.group(2), m.group(1)
        p = (AQUI / src).resolve()
        uri = data_uri(p, "image/png") if p.exists() else src
        return f'<img src="{uri}" alt="{alt}"><p class="legenda">{alt}</p>'
    html = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', lambda m: img(type("M", (), {"group": lambda s, i: (m.group(2) if i == 1 else m.group(1))})()), html)
    html = html.replace("<h1>", '<h1 class="primeiro">', 1)
    css = CSS % {"sora": data_uri(MARCA / "fontes" / "Sora-Variable.ttf", "font/ttf"),
                 "inter": data_uri(MARCA / "fontes" / "Inter-Variable.ttf", "font/ttf")}
    logo = data_uri(MARCA / "logo" / "retena_horizontal_claro_sobre_escuro.svg", "image/svg+xml")
    capa = f"""<section class="capa"><div><img src="{logo}" alt="Retena" style="border:0"></div>
<div><h1>{meta.get('titulo','')}</h1><div class="sub">{meta.get('subtitulo','')}</div><div class="pulso"></div>
<div class="tag">Ninguém desiste de repente. A Retena percebe antes.</div></div>
<div class="eq">Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592)<br>
Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)<br>Engenharia de Software · FIAP · {meta.get('data','')}</div></section>"""
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{meta.get('titulo','Retena')}</title>
<style>{css}</style></head><body>{capa}{html}
<p class="rodape-doc">Retena · Startup One · Enterprise Challenge Oracle · FIAP 2026 · documento gerado de Retena_Documento_Final.md</p></body></html>"""


def pdf(html_path: Path, pdf_path: Path):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CHROME_", "CLAUDE", "ELECTRON_"))}
    perfil = Path(tempfile.gettempdir()) / f"retena_edge_{pdf_path.stem}"
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
                    f"--user-data-dir={perfil}", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "file:///" + str(html_path).replace("\\", "/")], env=env, timeout=180, capture_output=True)
    if not pdf_path.exists():
        raise SystemExit("PDF nao gerado")


# --------------------------------------------------------------------------- DOCX (fonte editavel)
def docx(corpo_md, meta, caminho):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    AZUL = RGBColor(0x0B, 0x25, 0x45)
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2); s.top_margin = s.bottom_margin = Cm(2)
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    for n in ("Heading 1", "Heading 2", "Heading 3"):
        d.styles[n].font.color.rgb = AZUL
    t = d.add_paragraph(); r = t.add_run(meta.get("titulo", "")); r.bold = True; r.font.size = Pt(24); r.font.color.rgb = AZUL
    d.add_paragraph(meta.get("subtitulo", ""))
    d.add_paragraph("Ninguém desiste de repente. A Retena percebe antes.").runs[0].italic = True
    d.add_paragraph("Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · "
                    "Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198) — " + meta.get("data", ""))
    d.add_page_break()

    def inline(par, texto):
        texto = re.sub(r"<[^>]+>", "", texto)
        for parte in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", texto):
            if not parte:
                continue
            if parte.startswith("**"):
                par.add_run(parte[2:-2]).bold = True
            elif parte.startswith("`"):
                rr = par.add_run(parte[1:-1]); rr.font.name = "Consolas"; rr.font.size = Pt(9)
            else:
                par.add_run(parte.replace("*", ""))

    def sombrear(cell, cor):
        tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), cor); tcPr.append(shd)

    linhas = corpo_md.splitlines()
    i = 0
    primeiro_h1 = True
    while i < len(linhas):
        l = linhas[i]
        if l.startswith("|") and i + 1 < len(linhas) and re.match(r"^\|[-| :]+\|$", linhas[i + 1].strip()):
            cab = [c.strip() for c in l.strip().strip("|").split("|")]
            i += 2; dados = []
            while i < len(linhas) and linhas[i].startswith("|"):
                dados.append([c.strip() for c in linhas[i].strip().strip("|").split("|")]); i += 1
            tb = d.add_table(rows=1, cols=len(cab)); tb.style = "Table Grid"
            for j, c in enumerate(cab):
                cell = tb.rows[0].cells[j]; cell.text = ""; p = cell.paragraphs[0]; inline(p, c)
                for rr in p.runs: rr.bold = True; rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); rr.font.size = Pt(9)
                sombrear(cell, "0B2545")
            for row in dados:
                cells = tb.add_row().cells
                for j in range(len(cab)):
                    cells[j].text = ""; p = cells[j].paragraphs[0]; inline(p, row[j] if j < len(row) else "")
                    for rr in p.runs: rr.font.size = Pt(9)
            d.add_paragraph()
            continue
        if l.startswith("<div class=\"bmc\">"):
            blocos = []
            i += 1
            while i < len(linhas) and not linhas[i].startswith("</div>"):
                m = re.match(r'<div class="bmc-\w+"><h4>(.*?)</h4><ul>(.*)</ul></div>', linhas[i])
                if m:
                    blocos.append((m.group(1), re.findall(r"<li>(.*?)</li>", m.group(2))))
                i += 1
            for tit, itens in blocos:
                d.add_heading(tit, level=3)
                for it in itens:
                    inline(d.add_paragraph(style="List Bullet"), it)
            i += 1; continue
        if l.startswith("<div class=\"fluxo\">"):
            i += 1
            while i < len(linhas) and not linhas[i].startswith("</div>"):
                m = re.match(r"<div><b>(.*?)</b><span>(.*?)</span></div>", linhas[i])
                if m:
                    p = d.add_paragraph(style="List Number"); inline(p, f"**{m.group(1)}** — {m.group(2)}")
                i += 1
            i += 1; continue
        if l.startswith("<div class=\"pendente\">"):
            p = d.add_paragraph(); inline(p, l); p.runs[0].font.color.rgb = RGBColor(0x8A, 0x5A, 0x00)
            i += 1; continue
        m = re.match(r"!\[(.*?)\]\((.*?)\)", l)
        if m:
            p = AQUI / m.group(2)
            if p.exists():
                d.add_picture(str(p), width=Cm(16.5))
                cap = d.add_paragraph(m.group(1)); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap.runs[0].italic = True; cap.runs[0].font.size = Pt(8.5)
            i += 1; continue
        if l.startswith("```"):
            i += 1; bloco = []
            while i < len(linhas) and not linhas[i].startswith("```"):
                bloco.append(linhas[i]); i += 1
            p = d.add_paragraph(); rr = p.add_run("\n".join(bloco)); rr.font.name = "Consolas"; rr.font.size = Pt(9)
            i += 1; continue
        if l.startswith("# "):
            if not primeiro_h1:
                d.add_page_break()
            primeiro_h1 = False
            d.add_heading(l[2:], level=1)
        elif l.startswith("## "):
            d.add_heading(l[3:], level=2)
        elif l.startswith("### "):
            d.add_heading(l[4:], level=3)
        elif re.match(r"^\s*[-*] ", l):
            inline(d.add_paragraph(style="List Bullet"), re.sub(r"^\s*[-*] ", "", l))
        elif re.match(r"^\d+\. ", l):
            inline(d.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", l))
        elif l.strip() and l.strip() != "---":
            inline(d.add_paragraph(), l)
        i += 1
    d.save(caminho)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--sem-pdf", action="store_true"); ap.add_argument("--sem-docx", action="store_true")
    a = ap.parse_args()
    meta, corpo = ler_md()
    html = montar_html(meta, corpo)
    hp = SAIDA.with_suffix(".html"); hp.write_text(html, encoding="utf-8")
    print("HTML:", hp)
    if not a.sem_pdf:
        pdf(hp, SAIDA.with_suffix(".pdf")); print("PDF:", SAIDA.with_suffix(".pdf"))
    if not a.sem_docx:
        docx(corpo, meta, SAIDA.with_suffix(".docx")); print("DOCX:", SAIDA.with_suffix(".docx"))
