# -*- coding: utf-8 -*-
"""Converte os relatórios desta pasta (Markdown) em PDF com a identidade da Retena (Edge headless + fontes Sora/Inter).
Uso: python gerar_pdfs.py            (gera ao lado de cada .md listado em DOCS)
"""
import os, re, subprocess, html, sys
import markdown

AQUI = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(AQUI)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONTES = "file:///" + os.path.join(ROOT, "03_Marca", "fontes").replace("\\", "/")
LOGO = "file:///" + os.path.join(ROOT, "03_Marca", "logo", "retena_horizontal_escuro_sobre_claro.svg").replace("\\", "/")
DOCS = ["README.md", "01_Prototipo/prototipo_fluxo.md", "02_PoC/poc_evidencia.md", "03_Validacao_Tecnica/relatorio_validacao_tecnica.md",
        "04_Arquitetura/arquitetura_evolucao.md", "05_Usabilidade/protocolo_teste_usabilidade.md", "05_Usabilidade/formulario_feedback.md",
        "05_Usabilidade/consolidacao_feedback.md", "06_Roadmap/roadmap.md"]

CSS = f"""
@font-face{{font-family:'Sora';src:url('{FONTES}/Sora-Variable.ttf');font-weight:100 800}}
@font-face{{font-family:'Inter';src:url('{FONTES}/Inter-Variable.ttf');font-weight:100 900}}
@page{{size:A4;margin:14mm 15mm 16mm}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,'Segoe UI',sans-serif;color:#3A4A5C;background:#fff;font-size:9.8pt;line-height:1.45}}
h1,h2,h3,h4{{font-family:Sora,Inter,sans-serif;color:#0B2545;margin:0}}
h1{{font-size:19pt;line-height:1.15;margin:0 0 4mm;padding-bottom:3mm;border-bottom:2px solid #2EC4B6}} h2{{font-size:13.5pt;margin:7mm 0 2.5mm;page-break-after:avoid}} h3{{font-size:11pt;margin:5mm 0 2mm;page-break-after:avoid}}
p{{margin:0 0 2.5mm}} ul,ol{{margin:0 0 3mm 5mm;padding:0}} li{{margin-bottom:1.2mm}}
table{{width:100%;border-collapse:collapse;font-size:8.6pt;margin:2mm 0 4mm}} th{{background:#0B2545;color:#fff;text-align:left;padding:1.8mm 2.3mm;font-weight:700;vertical-align:top}}
td{{padding:1.6mm 2.3mm;border-bottom:1px solid #E2E8F0;vertical-align:top}} tr:nth-child(even) td{{background:#F6F7F9}} tr{{page-break-inside:avoid}}
code{{font-family:Consolas,'Courier New',monospace;font-size:8.6pt;background:#F1F4F8;padding:0 1mm;border-radius:1mm}} pre{{background:#0B2545;color:#E6ECF5;padding:3mm 4mm;border-radius:2.5mm;font-size:8.4pt;white-space:pre-wrap;page-break-inside:avoid}} pre code{{background:none;color:inherit;padding:0}}
blockquote{{margin:2mm 0 3mm;padding:2.5mm 4mm;border-left:3px solid #FFB703;background:#FFF4D6;border-radius:0 2mm 2mm 0}}
strong{{color:#0B2545}} a{{color:#13315C}} img{{max-width:100%;border:1px solid #E2E8F0;border-radius:2mm}}
.cab{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6mm}} .cab img{{height:9mm;border:none}} .cab .meta{{text-align:right;font-size:8.3pt;color:#94A3B8}}
.rod{{margin-top:8mm;border-top:1px solid #E2E8F0;padding-top:2mm;font-size:8pt;color:#94A3B8;display:flex;justify-content:space-between}}
"""

def to_pdf(html_path, pdf_path):
    tag = re.sub(r"\W", "_", os.path.basename(pdf_path))
    # Edge herda do app desktop (Electron) a variável CHROME_CRASHPAD_PIPE_NAME e encerra sem renderizar: ambiente filtrado.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CHROME_", "ELECTRON_"))}
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
                    f"--user-data-dir={os.environ.get('TEMP')}\\edge_pdf_{tag}", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "file:///" + html_path.replace("\\", "/")], capture_output=True, timeout=180, env=env)
    return os.path.exists(pdf_path)

for rel in DOCS:
    md_path = os.path.join(AQUI, *rel.split("/"))
    if not os.path.exists(md_path): print("ausente:", rel); continue
    md = open(md_path, encoding="utf-8").read()
    corpo = markdown.markdown(md, extensions=["tables", "fenced_code"])
    # imagens relativas ao .md
    base = "file:///" + os.path.dirname(md_path).replace("\\", "/") + "/"
    corpo = re.sub(r'src="(?!file:|http)([^"]+)"', lambda m: f'src="{base}{m.group(1)}"', corpo)
    titulo = re.search(r"^# (.+)$", md, re.M); titulo = html.escape(titulo.group(1)) if titulo else rel
    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{titulo}</title><style>{CSS}</style></head><body>
<div class="cab"><img src="{LOGO}" alt="Retena"/><div class="meta">Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026<br/>Prototipação e PoC · 10/10/2026</div></div>
{corpo}
<div class="rod"><span>Retena · {html.escape(rel)}</span><span>Lucas Dalmas · Lucas Emanuel · Kayque Moraes · Lucas Henklain · Vinicius Pinheiro</span></div>
</body></html>"""
    hp = md_path[:-3] + ".html"; open(hp, "w", encoding="utf-8").write(doc)
    pp = md_path[:-3] + ".pdf"
    if "--so-html" in sys.argv:          # só gera o HTML; a conversão é feita por fora (PowerShell: converter_pdfs.ps1)
        print(rel, "-> html"); continue
    if os.path.exists(pp): os.remove(pp)
    print(rel, "->", "pdf ok" if to_pdf(hp, pp) else "PDF FALHOU")
    try: os.remove(hp)
    except OSError: pass
