# -*- coding: utf-8 -*-
"""
Monta a pasta `site/` (estática, pronta para GitHub Pages) a partir da entrega:
  /              -> landing page (index.html, fontes/, img/)
  /dashboard/    -> dashboard do MVP
  /evidencias/   -> evidências da integração Oracle (HTML + PNG + TXT/CSV/JSON)
  /diagramas/    -> índice + diagramas (PNG/SVG)
Os links relativos "../05_MVP/..." e "../06_Oracle/..." da landing são reescritos para os caminhos do site.

Uso: python montar_site_publicacao.py <pasta_destino>
"""
import shutil, sys, re
from pathlib import Path

ENTREGA = Path(__file__).resolve().parents[1]
dest = Path(sys.argv[1]).resolve()
if dest.exists():
    shutil.rmtree(dest)
dest.mkdir(parents=True)

# landing
land = ENTREGA / "04_Landing_Page"
shutil.copytree(land / "fontes", dest / "fontes")
shutil.copytree(land / "img", dest / "img")
html = (land / "index.html").read_text(encoding="utf-8")
html = html.replace("../05_MVP/dashboard/index.html", "dashboard/index.html")
html = html.replace("../06_Oracle/evidencias/evidencias.html", "evidencias/evidencias.html")
(dest / "index.html").write_text(html, encoding="utf-8")

# dashboard (autocontido)
(dest / "dashboard").mkdir()
shutil.copy(ENTREGA / "05_MVP" / "dashboard" / "index.html", dest / "dashboard" / "index.html")

# evidências Oracle
ev_src = ENTREGA / "06_Oracle" / "evidencias"
(dest / "evidencias").mkdir()
for f in ev_src.iterdir():
    if f.is_file() and f.suffix.lower() in {".html", ".png", ".txt", ".csv", ".json"}:
        shutil.copy(f, dest / "evidencias" / f.name)

# diagramas
dg_src = ENTREGA / "02_Diagramas"
(dest / "diagramas").mkdir()
for f in dg_src.iterdir():
    if f.is_file() and (f.suffix.lower() in {".png", ".svg"} or f.name == "00_indice_diagramas.html"):
        shutil.copy(f, dest / "diagramas" / f.name)
idx = dest / "diagramas" / "00_indice_diagramas.html"
if idx.exists():
    t = idx.read_text(encoding="utf-8")
    t = t.replace("../03_Marca/logo/", "../img/").replace("../03_Marca/fontes/", "../img/")
    idx.write_text(t, encoding="utf-8")
    # logo usado pelo índice
    logo = ENTREGA / "03_Marca" / "logo" / "retena_horizontal_escuro_sobre_claro.svg"
    if logo.exists() and not (dest / "img" / logo.name).exists():
        shutil.copy(logo, dest / "img" / logo.name)

# evidencias.html e dashboard podem referenciar a marca por caminho relativo à entrega
for f in [dest / "evidencias" / "evidencias.html", dest / "dashboard" / "index.html"]:
    if f.exists():
        t = f.read_text(encoding="utf-8")
        t2 = re.sub(r"\.\./\.\./03_Marca/(logo|fontes)/", r"../img/", t)
        t2 = re.sub(r"\.\./03_Marca/(logo|fontes)/", r"../img/", t2)
        if t2 != t:
            f.write_text(t2, encoding="utf-8")
for extra in (ENTREGA / "03_Marca" / "logo").glob("retena_horizontal_*sobre_*.svg"):
    if not (dest / "img" / extra.name).exists():
        shutil.copy(extra, dest / "img" / extra.name)
for fnt in (ENTREGA / "03_Marca" / "fontes").glob("*.ttf"):
    if not (dest / "img" / fnt.name).exists():
        shutil.copy(fnt, dest / "img" / fnt.name)

(dest / ".nojekyll").write_text("", encoding="utf-8")
total = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
print(f"site montado em {dest} — {sum(1 for _ in dest.rglob('*') if _.is_file())} arquivos, {total/1e6:.1f} MB")
