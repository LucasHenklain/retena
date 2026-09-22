# -*- coding: utf-8 -*-
"""
Materiais de apoio do kit da Banca Final (PDF via Edge headless, com as fontes da marca Sora/Inter):
  Retena_Guia_do_Apresentador.pdf  — roteiro cronometrado, notas por slide, perguntas prováveis, checklist do dia
  Retena_OnePager_Banca.pdf        — folha A4 de apoio para a banca (problema, solução, números, Oracle, negócio, equipe, QR codes)
Uso: python gerar_materiais_apoio.py   (após gerar_kit_banca.py)
"""
import os, json, re, subprocess, html
import markdown

AQUI = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(AQUI)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONTES = "file:///" + os.path.join(ROOT, "03_Marca", "fontes").replace("\\", "/")
LOGO_ESC = "file:///" + os.path.join(ROOT, "03_Marca", "logo", "retena_horizontal_escuro_sobre_claro.svg").replace("\\", "/")
LOGO_CLA = "file:///" + os.path.join(ROOT, "03_Marca", "logo", "retena_horizontal_claro_sobre_escuro.svg").replace("\\", "/")
QR = lambda n: "file:///" + os.path.join(AQUI, "qr", f"{n}.png").replace("\\", "/")

CSS = f"""
@font-face{{font-family:'Sora';src:url('{FONTES}/Sora-Variable.ttf');font-weight:100 800}}
@font-face{{font-family:'Inter';src:url('{FONTES}/Inter-Variable.ttf');font-weight:100 900}}
@page{{size:A4;margin:14mm 16mm 16mm}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,'Segoe UI',sans-serif;color:#3A4A5C;background:#fff;font-size:10pt;line-height:1.4}}
h1,h2,h3,h4{{font-family:Sora,Inter,sans-serif;color:#0B2545;margin:0}}
.pagina{{page-break-after:always;position:relative}}
.pagina:last-child{{page-break-after:auto}}
.onepage{{width:210mm;height:297mm;padding:11mm 13mm 8mm;overflow:hidden;font-size:8.4pt;line-height:1.32}}
.onepage .cabecalho{{padding-bottom:2.5mm;margin-bottom:3.5mm}} .onepage .cabecalho img{{height:9mm}} .onepage h1{{font-size:15.5pt;margin-bottom:2mm}} .onepage h3{{font-size:9.5pt;margin:0 0 1.2mm}}
.onepage .card{{padding:2.6mm 3.5mm;margin:0 0 2.5mm}} .onepage .grid2,.onepage .grid3,.onepage .grid4{{gap:2.5mm}} .onepage .stat{{padding:2.2mm 2.8mm}} .onepage .stat .n{{font-size:14pt}} .onepage .stat .l{{font-size:8pt}} .onepage .stat .s{{font-size:7.2pt}}
.onepage p{{margin:0 0 1.8mm}} .onepage li{{margin-bottom:0.6mm}} .onepage ul{{margin-left:4mm}} .onepage .escuro{{padding:3mm 4mm}} .onepage .qr img{{width:18mm;height:18mm}} .onepage .rodape{{position:static;margin-top:2.5mm;padding-top:1.5mm}}
.cabecalho{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #2EC4B6;padding-bottom:5mm;margin-bottom:7mm}}
h2{{page-break-after:avoid}} table,tr{{page-break-inside:avoid}} .card{{page-break-inside:avoid}}
.cabecalho img{{height:11mm}} .cabecalho .meta{{text-align:right;font-size:9pt;color:#94A3B8}}
.eyebrow{{font-size:8.5pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#2EC4B6;margin-bottom:2mm}}
h1{{font-size:22pt;line-height:1.1;margin-bottom:4mm}} h2{{font-size:14pt;margin:7mm 0 3mm}} h3{{font-size:11.5pt;margin:5mm 0 2mm}}
p{{margin:0 0 2.5mm}} ul,ol{{margin:0 0 3mm 5mm;padding:0}} li{{margin-bottom:1.2mm}}
table{{width:100%;border-collapse:collapse;font-size:9.2pt;margin:2mm 0 4mm}} th{{background:#0B2545;color:#fff;text-align:left;padding:2mm 2.5mm;font-weight:700}}
td{{padding:1.8mm 2.5mm;border-bottom:1px solid #E2E8F0;vertical-align:top}} tr:nth-child(even) td{{background:#F6F7F9}}
.card{{background:#F6F7F9;border:1px solid #E2E8F0;border-radius:3mm;padding:4mm 5mm;margin:0 0 4mm}}
.escuro{{background:#0B2545;color:#fff;border-radius:3mm;padding:5mm 6mm}} .escuro h2,.escuro h3{{color:#fff}} .escuro .eyebrow{{color:#2EC4B6}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:4mm}} .grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4mm}} .grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm}}
.stat{{background:#fff;border:1px solid #E2E8F0;border-radius:3mm;padding:3.5mm 4mm}} .stat .n{{font-family:Sora,sans-serif;font-size:19pt;font-weight:800;color:#0B2545;line-height:1}} .stat .l{{font-size:9pt;font-weight:700;color:#0B2545;margin-top:1.5mm}} .stat .s{{font-size:8pt;color:#3A4A5C;margin-top:1mm}}
.coral{{color:#FF6B4A}} .verde{{color:#2EC4B6}} .badge{{display:inline-block;background:#2EC4B6;color:#0B2545;font-weight:700;font-size:8pt;border-radius:999px;padding:1mm 3mm}}
.rodape{{margin-top:8mm;border-top:1px solid #E2E8F0;padding-top:2mm;font-size:8pt;color:#94A3B8;display:flex;justify-content:space-between}}
.nota{{background:#FFF4D6;border-radius:2.5mm;padding:3mm 4mm;font-size:9pt}}
.qr{{display:flex;gap:3mm;align-items:center}} .qr img{{width:22mm;height:22mm}} .qr .t{{font-size:8.5pt}} .qr .t b{{display:block;color:#0B2545}}
blockquote{{margin:2mm 0 3mm;padding:2.5mm 4mm;border-left:3px solid #2EC4B6;background:#F6F7F9;font-style:italic}}
"""

def pagina(conteudo, titulo_doc, n, total, classe="pagina"):
    return f"""<section class="{classe}"><div class="cabecalho"><img src="{LOGO_ESC}" alt="Retena"/><div class="meta">{titulo_doc}<br/>Banca Final · 23/09/2026</div></div>{conteudo}
<div class="rodape"><span>Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026</span><span>Seção {n}/{total}</span></div></section>"""

def to_pdf(html_path, pdf_path):
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
                    f"--user-data-dir={os.environ.get('TEMP')}\\edge_kit", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "file:///" + html_path.replace("\\", "/")], capture_output=True, timeout=180)
    return os.path.exists(pdf_path)

# ------------------------------------------------------------------ GUIA DO APRESENTADOR
notas = json.load(open(os.path.join(AQUI, "notas_apresentador.json"), encoding="utf-8"))
resumo_md = open(os.path.join(ROOT, "01_Documento", "Resumo_para_Banca.md"), encoding="utf-8").read()
# recorta as seções úteis do resumo (perguntas prováveis, riscos, frase de fechamento)
def secao(md, titulo_ini, titulo_fim=None):
    i = md.find(titulo_ini); j = md.find(titulo_fim, i + 1) if titulo_fim else -1
    return md[i:j] if i >= 0 else ""
perguntas_md = secao(resumo_md, "## 4. Perguntas prováveis", "## 5.")
riscos_md = secao(resumo_md, "## 6. Riscos", "## 7.")
fechamento_md = secao(resumo_md, "## 7. Frase de fechamento")
md2html = lambda t: markdown.markdown(t, extensions=["tables"])

tempos = {1: "0:30", 2: "0:15", 3: "1:00", 4: "0:40", 5: "1:00", 6: "0:40", 7: "1:00", 8: "1:00", 9: "(reserva)", 10: "1:00", 11: "0:40", 12: "0:50", 13: "0:40", 14: "0:40", 15: "0:40", 16: "0:50", 17: "0:40", 18: "0:30", 19: "0:20", 20: "0:30"}
linhas = ""
for n in notas:
    if n["slide"] > 20: break
    linhas += f"<tr><td style='white-space:nowrap'><b>{n['slide']:02d}</b></td><td><b>{html.escape(n['titulo'])}</b></td><td style='white-space:nowrap'>{tempos.get(n['slide'], '')}</td><td>{html.escape(n['notas'])}</td></tr>"
apend = "".join(f"<li><b>{html.escape(n['titulo'])}</b> — {html.escape(n['notas'])}</li>" for n in notas if n["slide"] > 20)

p1 = f"""<div class="eyebrow">Guia do apresentador</div><h1>Retena na Banca Final: roteiro, notas e respostas.</h1>
<p>Deck: <b>Retena_Banca_Final.pptx / .pdf</b> (20 slides principais + apêndice A1–A8). Tempo-alvo de apresentação: <b>8 minutos</b> (slides 1–20, com a demonstração ao vivo no slide 8). O slide 9 é reserva caso a internet falhe. Perguntas: usar o apêndice sob demanda.</p>
<div class="grid3">
<div class="stat"><div class="n">8 min</div><div class="l">apresentação</div><div class="s">20 slides · demonstração ao vivo no slide 8</div></div>
<div class="stat"><div class="n">8 slides</div><div class="l">de apêndice</div><div class="s">métricas, OULAD, split temporal, LGPD/OCI, jornada, riscos, rich picture</div></div>
<div class="stat"><div class="n">3 QR</div><div class="l">no fechamento</div><div class="s">vídeo · site e dashboard · repositório</div></div>
</div>
<h2>Checklist antes de entrar</h2>
<div class="grid2"><div class="card"><h3>Tecnologia</h3><ul>
<li>Abrir <b>https://lucashenklain.github.io/retena/dashboard/</b> em uma aba (deixar a busca em “Aluno 0227” pronta) e a landing em outra.</li>
<li>Abrir o PDF do deck como plano B (fontes embutidas); o PPTX usa Segoe UI e abre em qualquer Windows.</li>
<li>Testar o link do vídeo em janela anônima: https://youtu.be/HZrcLvIJCC4.</li>
<li>Modo apresentador com notas ligado; transições em <i>fade</i> já configuradas.</li></ul></div>
<div class="card"><h3>Papéis sugeridos</h3><ul>
<li><b>Abertura, problema e público</b> (slides 1–4): 1 pessoa.</li>
<li><b>Evidência, solução e demonstração</b> (5–9): 1 pessoa, com o dashboard aberto.</li>
<li><b>Oracle e resultados</b> (10–13): 1 pessoa.</li>
<li><b>Negócio, mercado e fechamento</b> (14–20): 1 pessoa. Todos respondem às perguntas; quem lidera decide quem responde.</li></ul></div></div>
<h2>Ordem e mensagem central</h2>
<table><tr><th>#</th><th>Bloco</th><th>Tempo</th><th>O que dizer</th></tr>{linhas}</table>"""

p2 = f"""<div class="eyebrow">Perguntas prováveis</div><h1>O que a banca deve perguntar, e a resposta curta.</h1>{md2html(perguntas_md.replace('## 4. Perguntas prováveis da banca e respostas curtas', ''))}"""
p3 = f"""<div class="eyebrow">Riscos, apêndice e fechamento</div><h1>Riscos reconhecidos, apêndice e a frase final.</h1>
{md2html(riscos_md.replace('## 6. Riscos que a própria equipe reconhece', '<h2>Riscos que a própria equipe reconhece</h2>'))}
<h2>Apêndice (slides 21–29) — quando usar</h2><ul>{apend}</ul>
{md2html(fechamento_md.replace('## 7. Frase de fechamento', '<h2>Frase de fechamento</h2>'))}
<div class="nota"><b>Regra de honestidade:</b> se perguntarem sobre as entrevistas, responder que foram simuladas com personas sintéticas para calibrar o instrumento (6 institucionais entram na contagem x/6; 2 com alunos calibraram H4 e H5), rotuladas assim no documento, e que serão confirmadas em campo antes do piloto. Se perguntarem sobre a diferença entre AUC 0,88 (Python) e 0,95 (Oracle), explicar que são duas implementações independentes do mesmo problema, ambas com teste temporal; o ponto é que o sinal existe e roda dentro do banco. Sobre o funil do slide 5 (175 → 165 → 165 → 161 → 154): são os alunos ativos na Fase 1 que seguem ativos em cada fase seguinte (definição do brief); o dashboard usa outra definição (alunos com ação própria por fase: 165 → 163 → 165 → 153 → 143), por isso os números diferem.</div>"""

guia_html = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Retena · Guia do Apresentador</title><style>{CSS}</style></head><body>" + pagina(p1, "Guia do Apresentador", 1, 3) + pagina(p2, "Guia do Apresentador", 2, 3) + pagina(p3, "Guia do Apresentador", 3, 3) + "</body></html>"
gpath = os.path.join(AQUI, "Retena_Guia_do_Apresentador.html"); open(gpath, "w", encoding="utf-8").write(guia_html)
print("guia pdf:", to_pdf(gpath, os.path.join(AQUI, "Retena_Guia_do_Apresentador.pdf")))

# ------------------------------------------------------------------ ONE-PAGER
one = f"""<div class="eyebrow">One-pager · Banca Final · Startup One / Enterprise Challenge Oracle</div>
<h1>Retena — <span class="verde">Ninguém desiste de repente. A Retena percebe antes.</span></h1>
<p><b>Radar de permanência para o ensino superior EAD.</b> Lê os sinais que o LMS já registra, pontua o risco de evasão de cada aluno dentro do Oracle AI Database com Oracle Machine Learning e entrega, toda segunda, quem contatar, por quê e o que ajustar. Vendemos proteção de receita à diretoria de operações; quem usa é a coordenação de permanência.</p>
<div class="grid4">
<div class="stat"><div class="n coral">41,6%</div><div class="l">desistência EAD em 2024</div><div class="s">recorde da série (Semesp, Mapa 2026)</div></div>
<div class="stat"><div class="n">50,7%</div><div class="l">das matrículas são EAD</div><div class="s">5,19 mi alunos (INEP, Censo 2024)</div></div>
<div class="stat"><div class="n">30%</div><div class="l">da turma em silêncio</div><div class="s">61 de 203 alunos há mais de 14 dias sem acesso, sem alerta (base real)</div></div>
<div class="stat"><div class="n">684.723</div><div class="l">eventos analisados</div><div class="s">203 alunos · 5 fases · jan–ago/2026</div></div>
</div>
<div class="grid2" style="margin-top:4mm">
<div class="card"><h3>Três entregas, toda semana</h3><ul>
<li><b>Score de risco explicável:</b> probabilidade de 21 dias sem acesso, com motivos em linguagem simples.</li>
<li><b>Mapa de atrito de conteúdo:</b> capítulos e formatos onde os alunos travam, com recomendação.</li>
<li><b>Fila semanal de intervenção:</b> quem, por quê, quando (19h–22h), o que dizer; resultado registrado e medido em R$.</li></ul></div>
<div class="card"><h3>Por que dentro do Oracle</h3><ul>
<li>Features em SQL; treino e scoring com <b>DBMS_DATA_MINING</b> (PREDICTION_PROBABILITY / DETAILS); views JSON para APEX, Select AI e API.</li>
<li><b>O dado do aluno não sai da instituição</b> (LGPD); sem servidor de ML nem cientista de dados dedicado.</li>
<li>Executado: 684.723 eventos carregados, 3 modelos treinados in-database, Random Forest com AUC 0,949; runbook para Autonomous + Object Storage pronto.</li></ul></div></div>
<div class="grid4">
<div class="stat"><div class="n">0,88</div><div class="l">AUC-ROC</div><div class="s">teste temporal jun–ago/2026 (gradient boosting)</div></div>
<div class="stat"><div class="n">88%</div><div class="l">precisão no top-20%</div><div class="s">lift 3,06×; faixa Alto com 95% de inatividade observada</div></div>
<div class="stat"><div class="n">0,92</div><div class="l">AUC no OULAD</div><div class="s">mesmo método em 14.293 alunos da Open University; lift 3,51×</div></div>
<div class="stat"><div class="n">0,95</div><div class="l">AUC in-database</div><div class="s">Random Forest treinado no Oracle 26ai, teste temporal</div></div>
</div>
<div class="grid2" style="margin-top:4mm">
<div class="escuro"><div class="eyebrow">Negócio</div><h3>SaaS por aluno ativo/mês</h3>
<p style="font-size:9.5pt;margin-top:2mm">R$ 6 (até 10 mil alunos) · R$ 4 (10–50 mil) · R$ 3 (megagrupos) · Essencial R$ 2 para IES pequenas. Mínimo R$ 5 mil/mês; setup R$ 10–25 mil; piloto de 90 dias com meta de rematrícula.</p>
<p style="font-size:9.5pt"><b>Cliente-referência (12 mil alunos):</b> R$ 576 mil/ano; reter 137 alunos (1,1% da base) paga o contrato; cada ponto de desistência evitado vale ~R$ 500 mil/ano (estimativa, ticket R$ 350/mês).</p>
<p style="font-size:9.5pt;margin:0"><b>Mercado:</b> TAM R$ 249 mi/ano · SAM R$ 126 mi/ano · SOM R$ 2,5–4,3 mi ARR em 3 anos.</p></div>
<div class="card"><h3>Diferencial</h3><p style="font-size:9.5pt">BI mostra o passado e CRM cobra tarde. A Retena antecipa (recência, tendência, capítulo travado), prioriza (quem, por quê, quando, o que dizer) e fecha o ciclo (resultado registrado, receita preservada em R$, retreino). Ficou viável agora: ML in-database maduro e EAD como maioria desde 2024.</p>
<h3 style="margin-top:3mm">Próximos passos</h3><p style="font-size:9.5pt;margin:0">NEXT 24/10 com Autonomous AI Database + APEX; piloto de 90 dias em uma fase de um curso com meta de rematrícula. Pedimos: apoio ao Always Free, uma IES parceira e mentoria comercial.</p></div></div>
<div class="grid3" style="margin-top:3mm;align-items:center">
<div class="qr"><img src="{QR('video')}"/><div class="t"><b>Vídeo pitch (4:48)</b>youtu.be/HZrcLvIJCC4</div></div>
<div class="qr"><img src="{QR('site')}"/><div class="t"><b>Site, dashboard e evidências</b>lucashenklain.github.io/retena</div></div>
<div class="qr"><img src="{QR('repo')}"/><div class="t"><b>Repositório completo</b>github.com/LucasHenklain/retena</div></div></div>
<p style="margin-top:2.5mm;font-size:8.3pt"><b>Equipe:</b> Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198) — Engenharia de Software, FIAP 4ESOA.</p>"""
one_html = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Retena · One-pager</title><style>{CSS}\n@page{{margin:0}}</style></head><body>" + pagina(one, "One-pager para a banca", 1, 1, classe="onepage") + "</body></html>"
opath = os.path.join(AQUI, "Retena_OnePager_Banca.html"); open(opath, "w", encoding="utf-8").write(one_html)
print("one-pager pdf:", to_pdf(opath, os.path.join(AQUI, "Retena_OnePager_Banca.pdf")))
