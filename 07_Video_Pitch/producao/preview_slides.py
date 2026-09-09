# -*- coding: utf-8 -*-
"""Renderiza todos os slides HTML em PNG e monta uma folha de contato para revisão."""
import subprocess, os, sys
from pathlib import Path
from PIL import Image

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = Path(__file__).resolve().parent
src = BASE / "slides"; out = BASE / "_preview"; out.mkdir(exist_ok=True)
profile = Path(os.environ.get("TEMP", ".")) / "retena_edge_profile"
for f in sorted(src.glob("*.html")):
    png = out / (f.stem + ".png")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
                    f"--user-data-dir={profile}", "--window-size=1920,1080", f"--screenshot={png}",
                    "file:///" + str(f).replace("\\", "/")], capture_output=True, timeout=120)
files = sorted(out.glob("s*.png"))
ims = [Image.open(f).convert("RGB").resize((640, 360)) for f in files]
cols = 3; rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (640 * cols, 360 * rows), "white")
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
sheet.save(out / "_contato_slides.jpg", quality=80)
print(len(files), "slides renderizados ->", out / "_contato_slides.jpg")
