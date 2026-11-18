# -*- coding: utf-8 -*-
"""Gera img/projecao.png a partir de modelo_financeiro.json (cores da marca)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

AQUI = Path(__file__).resolve().parent
FONTES = AQUI.parent.parent / "03_Marca" / "fontes"
for f in ("Inter-Variable.ttf", "Sora-Variable.ttf"):
    if (FONTES / f).exists():
        fm.fontManager.addfont(str(FONTES / f))
plt.rcParams["font.family"] = "Inter"
r = json.loads((AQUI / "modelo_financeiro.json").read_text(encoding="utf-8"))
anos = ["Ano 1\n2027", "Ano 2\n2028", "Ano 3\n2029"]
arr = [x / 1e6 for x in r["arr_fim"]]
ebitda = [x / 1e6 for x in r["ebitda"]]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=180)
for ax in (a1, a2):
    ax.spines[["top", "right"]].set_visible(False); ax.spines[["left", "bottom"]].set_color("#94A3B8")
    ax.tick_params(colors="#3A4A5C"); ax.yaxis.grid(True, color="#E2E7EE"); ax.set_axisbelow(True)
b = a1.bar(anos, arr, color="#2EC4B6", width=0.55, label="Cenário base")
a1.bar([anos[2]], [r["arr_ano3_otimista"] / 1e6 - arr[2]], bottom=[arr[2]], color="#2EC4B6", alpha=0.35, width=0.55,
       hatch="//", edgecolor="#0F6F68", label="+1 megagrupo (otimista)")
for i, v in enumerate(arr):
    a1.text(i, v + 0.06, f"R$ {v:.2f} mi".replace(".", ","), ha="center", color="#0B2545", fontweight="bold", fontsize=10)
a1.text(2, r["arr_ano3_otimista"] / 1e6 + 0.06, f"R$ {r['arr_ano3_otimista']/1e6:.1f} mi".replace(".", ","), ha="center", color="#0F6F68", fontsize=9)
a1.set_title("ARR no fim do ano (R$ mi)", loc="left", color="#0B2545", fontweight="bold", fontsize=12)
a1.set_ylim(0, 4.9); a1.legend(frameon=False, fontsize=8.5, loc="upper left")
cores = ["#FF6B4A" if v < 0 else "#2EC4B6" for v in ebitda]
a2.bar(anos, ebitda, color=cores, width=0.55)
a2.axhline(0, color="#3A4A5C", lw=0.8)
a2.bar([anos[2]], [r["ebitda_ano3_otimista"] / 1e6], color="#2EC4B6", alpha=0.35, width=0.25, hatch="//", edgecolor="#0F6F68")
for i, v in enumerate(ebitda):
    a2.text(i, v - 0.05, f"{v*1000:,.0f} mil".replace(",", "."), ha="center", va="top", color="#0B2545", fontsize=9.5, fontweight="bold")
a2.text(2.18, r["ebitda_ano3_otimista"] / 1e6 + 0.02, "otimista\n+" + f"{r['ebitda_ano3_otimista']/1e3:,.0f} mil".replace(",", "."),
        fontsize=8.5, color="#0F6F68", va="bottom")
a2.set_title("EBITDA (R$ mi) — estimativas", loc="left", color="#0B2545", fontweight="bold", fontsize=12)
a2.set_ylim(-0.4, 0.6)
fig.tight_layout()
(AQUI / "img").mkdir(exist_ok=True)
fig.savefig(AQUI / "img" / "projecao.png", facecolor="white")
print("ok")
