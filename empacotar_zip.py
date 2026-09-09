# -*- coding: utf-8 -*-
"""Gera o pacote ZIP final da entrega (exclui arquivos de trabalho)."""
import zipfile, os, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ.parent / "Retena_Fase6_Entrega.zip"
EXCLUIR_DIRS = {"_work", "_preview", "__pycache__", ".git"}
EXCLUIR_ARQ = {"empacotar_zip.py", "dashboard_tall.png", "_tall_small.png", "_contato.jpg", "_contato2.jpg", "_contato_slides.jpg"}
EXCLUIR_EXT = {".pyc", ".log.tmp"}

def incluir(p: Path) -> bool:
    if any(part in EXCLUIR_DIRS for part in p.parts): return False
    if p.name in EXCLUIR_ARQ or p.suffix in EXCLUIR_EXT: return False
    if p.name.startswith("_") and p.suffix in {".png", ".jpg", ".html"}: return False
    return True

n = 0; total = 0
with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(RAIZ.rglob("*")):
        if p.is_file() and incluir(p):
            z.write(p, Path("Retena_Fase6_Entrega") / p.relative_to(RAIZ)); n += 1; total += p.stat().st_size
print(f"{n} arquivos, {total/1e6:.1f} MB descompactados -> {DESTINO} ({DESTINO.stat().st_size/1e6:.1f} MB)")
