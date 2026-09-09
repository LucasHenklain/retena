# -*- coding: utf-8 -*-
"""Gera a apresentação da Banca Final (PPTX 16:9) da Retena com python-pptx.
Uso: python gerar_apresentacao.py  -> Retena_Apresentacao_Banca.pptx
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Retena_Apresentacao_Banca_v2.pptx")

AZUL = RGBColor(0x0B, 0x25, 0x45); AZUL_M = RGBColor(0x13, 0x31, 0x5C); VERDE = RGBColor(0x2E, 0xC4, 0xB6)
AMBAR = RGBColor(0xFF, 0xB7, 0x03); CORAL = RGBColor(0xFF, 0x6B, 0x4A); OFF = RGBColor(0xF6, 0xF7, 0xF9)
GRAFITE = RGBColor(0x3A, 0x4A, 0x5C); CINZA = RGBColor(0x94, 0xA3, 0xB8); BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
CARD_ESC = RGBColor(0x16, 0x35, 0x5E); LINHA = RGBColor(0xE2, 0xE8, 0xF0)
FONT = "Segoe UI"

W, H = Inches(13.333), Inches(7.5)
prs = Presentation(); prs.slide_width = W; prs.slide_height = H
BLANK = prs.slide_layouts[6]

def P(x): return Inches(x)

def bg(slide, cor):
    f = slide.background.fill; f.solid(); f.fore_color.rgb = cor

def rect(slide, x, y, w, h, cor, radius=None, line=None, shadow=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, P(x), P(y), P(w), P(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = cor
    if line: shp.line.color.rgb = line; shp.line.width = Pt(1)
    else: shp.line.fill.background()
    if radius: shp.adjustments[0] = radius
    if not shadow: shp.shadow.inherit = False
    shp.text_frame.text = ""
    return shp

def text(slide, x, y, w, h, txt, size=16, cor=GRAFITE, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False, spacing=1.15, margin=0.0, font=FONT):
    tb = slide.shapes.add_textbox(P(x), P(y), P(w), P(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = P(margin); tf.vertical_anchor = anchor
    linhas = txt if isinstance(txt, list) else [txt]
    for i, l in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = spacing
        runs = l if isinstance(l, list) else [(l, bold, cor)]
        for r in runs:
            t, b, c = (r + (bold, cor))[:3] if isinstance(r, tuple) else (r, bold, cor)
            run = p.add_run(); run.text = t; run.font.size = Pt(size); run.font.bold = b; run.font.italic = italic
            run.font.color.rgb = c; run.font.name = font
    return tb

def bullets(slide, x, y, w, h, itens, size=15, cor=GRAFITE, dot=VERDE, gap=0.12):
    """Lista com marcador circular desenhado (evita bullets padrão)."""
    yy = y
    for it in itens:
        d = slide.shapes.add_shape(MSO_SHAPE.OVAL, P(x), P(yy + 0.10), P(0.13), P(0.13)); d.fill.solid(); d.fill.fore_color.rgb = dot; d.line.fill.background(); d.shadow.inherit = False
        nlin = max(1, int(len(it) / (w * 8.2 / (size / 15))) + 1)
        hh = 0.16 + 0.27 * nlin * (size / 15)
        text(slide, x + 0.28, yy, w - 0.28, hh, it, size=size, cor=cor)
        yy += hh + gap
    return yy

def img_fit(slide, path, x, y, w, h, radius=False):
    """Insere imagem contida na caixa (mantém proporção, centraliza)."""
    if not os.path.exists(path):
        rect(slide, x, y, w, h, LINHA); text(slide, x, y, w, h, os.path.basename(path), size=10, cor=CINZA, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE); return None
    iw, ih = Image.open(path).size; r = min(w / iw, h / ih); nw, nh = iw * r, ih * r
    pic = slide.shapes.add_picture(path, P(x + (w - nw) / 2), P(y + (h - nh) / 2), P(nw), P(nh))
    return pic

def img_cover(slide, path, x, y, w, h):
    """Insere imagem preenchendo a caixa (corta excedente)."""
    if not os.path.exists(path): return rect(slide, x, y, w, h, LINHA)
    iw, ih = Image.open(path).size; box = w / h; src = iw / ih
    pic = slide.shapes.add_picture(path, P(x), P(y), P(w), P(h))
    if src > box:  # mais larga: corta laterais
        excess = 1 - box / src; pic.crop_left = excess / 2; pic.crop_right = excess / 2
    else:
        excess = 1 - src / box; pic.crop_top = excess / 2; pic.crop_bottom = excess / 2
    return pic

def titulo(slide, kicker, tit, escuro=False, y=0.55, size=28, w=12.2):
    kc = VERDE; tc = BRANCO if escuro else AZUL
    text(slide, 0.6, y, w, 0.3, kicker.upper(), size=12, cor=kc, bold=True)
    text(slide, 0.6, y + 0.32, w, 1.0, tit, size=size, cor=tc, bold=True, spacing=1.05)

def rodape(slide, escuro=False, n=None):
    c = RGBColor(0x9F, 0xB3, 0xC8) if escuro else CINZA
    text(slide, 0.6, 7.05, 9, 0.3, "Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026", size=10, cor=c)
    if n is not None: text(slide, 11.9, 7.05, 0.85, 0.3, str(n), size=10, cor=c, align=PP_ALIGN.RIGHT)
    logo = os.path.join(ROOT, "03_Marca", "logo", "retena_horizontal_claro_sobre_escuro.png" if escuro else "retena_horizontal_escuro_sobre_claro.png")
    if os.path.exists(logo): slide.shapes.add_picture(logo, P(11.55), P(0.42), height=P(0.42))

def stat(slide, x, y, w, num, label, sub=None, escuro=False, cor_num=None, size=40):
    cn = cor_num or (VERDE if escuro else AZUL); cl = BRANCO if escuro else AZUL; cs = RGBColor(0xC9, 0xD6, 0xE4) if escuro else GRAFITE
    text(slide, x, y, w, 0.75, num, size=size, cor=cn, bold=True)
    text(slide, x, y + 0.78, w, 0.5, label, size=13, cor=cl, bold=True)
    if sub: text(slide, x, y + 1.18, w, 0.6, sub, size=11, cor=cs)

def card(slide, x, y, w, h, escuro=False):
    return rect(slide, x, y, w, h, CARD_ESC if escuro else BRANCO, radius=0.06, line=None if escuro else LINHA, shadow=not escuro)

def notes(slide, txt): slide.notes_slide.notes_text_frame.text = txt

IMG = lambda *p: os.path.join(ROOT, *p)
OULAD_TXT = [
    "Dataset público da Open University (Reino Unido): 32.593 matrículas, 10,66 milhões de cliques; base aluno-semana de 730.673 linhas e 24.392 alunos.",
    "Mesmo rótulo, mesmas features conceituais e mesmos hiperparâmetros do Retena; split temporal: treino 2013 (11.438 alunos), teste 2014 (14.293 alunos).",
    "AUC-ROC 0,922 e lift 3,51× no top-20% (IES Demo: 0,882 e 3,06×); faixa Alto com 85% de inatividade observada contra 6% na Baixo.",
    "As mesmas features dominam: dias ativos em 28 dias, recência e regularidade semanal. Módulo nunca visto no treino: AUC 0,93. Protocolo EduRetain reproduzido: sem os já desmatriculados no dia 30, a AUC cai para 0,66–0,69.",
]
OULAD_SINTESE = "O mesmo método, sem mudar arquitetura, concentrou 70% dos alunos que ficariam 3 semanas inativos nos 20% de maior risco, em outra instituição, outro país e outro LMS."
n = 0
def novo(escuro=False):
    global n; n += 1; s = prs.slides.add_slide(BLANK); bg(s, AZUL if escuro else OFF); return s

# 1 CAPA ---------------------------------------------------------------------------------------
s = novo(True)
img_cover(s, IMG("04_Landing_Page", "img", "aluno_noite.jpg"), 7.6, 0, 5.733, 7.5)
veu = rect(s, 7.6, 0, 5.733, 7.5, AZUL)  # véu semitransparente sobre a foto
from pptx.oxml.ns import qn
# transparência do véu (alpha 45%)
sf = veu.fill._xPr.find(qn("a:solidFill")); clr = sf.find(qn("a:srgbClr")); a = clr.makeelement(qn("a:alpha"), {"val": "45000"}); clr.append(a)
logo = IMG("03_Marca", "logo", "retena_horizontal_claro_sobre_escuro.png")
if os.path.exists(logo): s.shapes.add_picture(logo, P(0.7), P(0.7), height=P(0.9))
text(s, 0.7, 2.15, 6.6, 0.35, "STARTUP ONE · ENTERPRISE CHALLENGE ORACLE · FIAP 2026", size=12, cor=VERDE, bold=True)
text(s, 0.7, 2.6, 6.8, 2.2, [[("Ninguém desiste de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=32, spacing=1.05)
text(s, 0.7, 4.75, 6.5, 0.9, "Radar de permanência para o ensino superior EAD: lê os sinais do LMS e entrega, toda segunda, quem está a duas semanas de sumir — por quê e o que fazer. Dentro do Oracle AI Database.", size=15, cor=RGBColor(0xDD, 0xE6, 0xF0), spacing=1.25)
text(s, 0.7, 6.0, 6.6, 0.9, ["Lucas Dalmas (RM551178) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592)", "Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)"], size=11.5, cor=RGBColor(0xC9, 0xD6, 0xE4), spacing=1.3)
text(s, 0.7, 7.0, 6, 0.3, "Banca Final · 23/09/2026", size=10, cor=RGBColor(0x9F, 0xB3, 0xC8))
notes(s, "Gancho (40 s): Toda noite, milhões de brasileiros abrem o notebook depois do trabalho para estudar a distância. Todo ano, quatro em cada dez desistem. Ninguém desiste de repente — mas a instituição só percebe quando a mensalidade para. Nós somos a Retena.")

# 2 PROBLEMA -----------------------------------------------------------------------------------
s = novo(False); titulo(s, "O problema", "A instituição descobre a evasão quando a mensalidade para.")
text(s, 0.6, 1.95, 5.2, 0.4, "DESISTÊNCIA ANUAL NO EAD · 2024", size=11, cor=GRAFITE, bold=True)
text(s, 0.6, 2.25, 5.4, 1.4, "41,6%", size=88, cor=CORAL, bold=True)
text(s, 0.6, 3.75, 5.4, 0.7, "o maior índice da série histórica (presencial: 24,8%). Fonte: Instituto Semesp, 16º Mapa do Ensino Superior 2026.", size=12, cor=GRAFITE)
for i, (a, b, c) in enumerate([("50,7%", "das matrículas já são EAD", "INEP, Censo 2024: 5,19 mi alunos"), ("R$ 3–5 mil", "por aluno que evade", "receita anual perdida (estimativa)"), ("Semanas", "de atraso na descoberta", "o LMS registra cada sinal antes")]):
    x = 0.6 + i * 2.05; card(s, x, 4.65, 1.9, 2.0)
    text(s, x + 0.18, 4.78, 1.6, 0.5, a, size=22, cor=AZUL, bold=True)
    text(s, x + 0.18, 5.32, 1.6, 0.6, b, size=11.5, cor=AZUL, bold=True)
    text(s, x + 0.18, 5.98, 1.6, 0.6, c, size=9.5, cor=GRAFITE)
img_cover(s, IMG("04_Landing_Page", "img", "desistindo.jpg"), 6.7, 1.9, 6.05, 4.7)
card(s, 8.9, 5.55, 3.7, 0.95, False); text(s, 9.05, 5.62, 3.4, 0.85, [[("BI mostra o passado. CRM cobra tarde. ", False, GRAFITE), ("A Retena age no meio: quando ainda dá tempo de chamar de volta.", True, AZUL)]], size=11.5)
rodape(s, False, n)
notes(s, "Problema (1 min): 41,6% de desistência anual no EAD em 2024, recorde da série. O EAD virou maioria das matrículas. Cada aluno que evade leva R$ 3 a 5 mil de receita anual e um custo de captação acima de R$ 1.000. E a instituição descobre semanas depois, no financeiro.")

# 3 PARA QUEM ----------------------------------------------------------------------------------
s = novo(False); titulo(s, "Para quem", "Quem compra, quem usa e o aluno no centro.")
pers = [
    ("coordenadora.jpg", "Renata · Diretora de Operações Acadêmicas", "Compra", "Responde pela receita das mensalidades e pela meta de permanência em um centro universitário com ~12 mil alunos EAD.", ["Quer ver a evasão em R$ e o retorno em rematrícula", "Objeções: LGPD, projeto de TI, \"já tenho BI\""]),
    ("tutor.jpg", "Mariana · Coordenadora de Permanência", "Usa toda segunda", "Lidera 12 tutores. Hoje descobre a evasão tarde e prioriza no escuro, sem critério nem registro do que funcionou.", ["Quer a lista de quem chamar, por quê e como", "KPI: alunos em risco reengajados em 30 dias"]),
    ("aluno_noite.jpg", "Aluno EAD trabalhador", "Beneficiário", "Estuda das 19h às 22h, de segunda a quinta. Trava em um capítulo, perde o ritmo por duas semanas e, sem ninguém perceber, desiste.", ["Responde a um plano concreto, não a cobrança", "Contato à noite, por WhatsApp"]),
]
for i, (im, nome, papel, desc, its) in enumerate(pers):
    x = 0.6 + i * 4.1; card(s, x, 1.95, 3.85, 4.75)
    img_cover(s, IMG("04_Landing_Page", "img", im), x, 1.95, 3.85, 1.75)
    rect(s, x + 0.2, 3.5, 1.5, 0.32, VERDE, radius=0.5); text(s, x + 0.2, 3.5, 1.5, 0.32, papel.upper(), size=9, cor=AZUL, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.2, 3.95, 3.45, 0.6, nome, size=14, cor=AZUL, bold=True)
    text(s, x + 0.2, 4.55, 3.45, 1.0, desc, size=11.5, cor=GRAFITE)
    bullets(s, x + 0.2, 5.6, 3.45, 1.0, its, size=10.5)
rodape(s, False, n)
notes(s, "Público (1 min): nosso cliente é a IES privada com EAD. Quem compra é a diretora de operações, que responde pela receita. Quem usa é a coordenadora de permanência e seus tutores, que hoje agem no escuro sobre 30% de alunos inativos. O beneficiário é o aluno trabalhador que estuda à noite.")

# 4 EVIDÊNCIA NA BASE --------------------------------------------------------------------------
s = novo(True); titulo(s, "Evidência na base real (anonimizada)", "O LMS já sabia. Só faltava alguém ouvir.", escuro=True)
stats = [("684.723", "eventos de LMS", "203 alunos · 5 fases · jan–ago/2026"), ("61 alunos", "30% da turma", "há mais de 14 dias sem acesso, em um único dia — sem alerta"), ("12%", "dos ingressantes perdidos", "em 7 meses: funil 94% → 94% → 92% → 88%"), ("19h–22h", "pico de estudo", "de segunda a quinta: o aluno trabalhador")]
for i, (a, b, c) in enumerate(stats):
    card(s, 0.6, 2.0 + i * 1.2, 5.3, 1.05, True); stat(s, 0.85, 2.05 + i * 1.2, 2.2, a, "", None, escuro=True, size=26)
    text(s, 3.0, 2.12 + i * 1.2, 2.8, 0.35, b, size=13, cor=BRANCO, bold=True); text(s, 3.0, 2.45 + i * 1.2, 2.8, 0.6, c, size=10.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
# gráfico nativo: funil de alunos ativos por fase
cd = CategoryChartData(); cd.categories = ["Fase 1", "Fase 2", "Fase 3", "Fase 4", "Fase 5"]; cd.add_series("Alunos ativos (ingressantes da F1)", (175, 165, 165, 161, 154))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, P(6.4), P(1.95), P(6.4), P(4.75), cd).chart
gf.has_legend = False; gf.has_title = True; gf.chart_title.text_frame.text = "Alunos da Fase 1 que seguem ativos em cada fase"
tt = gf.chart_title.text_frame.paragraphs[0].runs[0].font; tt.size = Pt(13); tt.bold = True; tt.color.rgb = BRANCO; tt.name = FONT
pl = gf.plots[0]; pl.gap_width = 60; pl.has_data_labels = True; dl = pl.data_labels; dl.position = XL_LABEL_POSITION.OUTSIDE_END; dl.font.size = Pt(12); dl.font.color.rgb = BRANCO; dl.font.bold = True; dl.number_format = '0'; dl.number_format_is_linked = False
ser = pl.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = VERDE
for idx, v in enumerate((175, 165, 165, 161, 154)):
    pt = ser.points[idx]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = VERDE if idx < 4 else AMBAR
ca = gf.category_axis; ca.tick_labels.font.size = Pt(11); ca.tick_labels.font.color.rgb = BRANCO; ca.format.line.color.rgb = RGBColor(0x3E, 0x5A, 0x82); ca.has_major_gridlines = False
va = gf.value_axis; va.visible = False; va.has_major_gridlines = False; va.maximum_scale = 200; va.minimum_scale = 0
text(s, 6.4, 6.72, 6.4, 0.3, "Fase 5 em andamento (ago/2026). 9 alunos aparecem só na F1; 8 param após a F4.", size=10, cor=RGBColor(0xC9, 0xD6, 0xE4))
rodape(s, True, n)
notes(s, "Evidência (1 min): analisamos 685 mil eventos de 203 alunos em cinco fases. Em um único dia, 61 alunos — 30% — estavam há mais de duas semanas sem acessar. 12% dos ingressantes se perderam em sete meses. Os travamentos se repetem nos mesmos capítulos. O LMS já sabia.")

# 5 ATRITO DE CONTEÚDO -------------------------------------------------------------------------
s = novo(False); titulo(s, "Onde os alunos travam", "Atrito de conteúdo: conhecido de ouvido, nunca medido.")
card(s, 0.6, 1.95, 7.6, 4.75); img_fit(s, IMG("05_MVP", "outputs", "figs", "fig_atrito_heatmap.png"), 0.75, 2.05, 7.3, 4.55)
bullets(s, 8.6, 2.05, 4.15, 4.6, [
    "Mapa fase × capítulo: taxa de queda (alunos que chegaram ao capítulo e não avançaram) ponderada pelo esforço relativo.",
    "Cauda de travamento nos capítulos 1–3 de todas as fases; na F5 (em andamento), 25 alunos parados nos caps 1–2.",
    "Piores capítulos encerrados: Cap 2 da F4 (\"Estudo de Caso\", esforço 3,4× o típico), Cap 2 da F3 e Cap 11 da F2.",
    "Conteúdo quase só em HTML (323 mil eventos) contra 18,6 mil em PDF e quase nada em vídeo e áudio.",
    "Cada célula vira uma recomendação para a coordenação pedagógica: dividir capítulo, inserir quiz de checagem, oferecer vídeo curto.",
], size=12.5, gap=0.16)
rodape(s, False, n)
notes(s, "Atrito (40 s): o mapa mostra, por fase e capítulo, onde os alunos param. Isso fecha o ciclo entre aluno e conteúdo: além de chamar o aluno, a coordenação pedagógica sabe o que ajustar.")

# 6 SOLUÇÃO ------------------------------------------------------------------------------------
s = novo(True); titulo(s, "A solução", "Três entregas, toda semana.", escuro=True)
pil = [("Score de risco explicável", "Probabilidade de o aluno ficar 21 dias sem acessar, recalculada todo domingo, com os motivos em linguagem simples: \"12 dias sem acesso, queda de 70% nos eventos, parado no cap 2 da F5\"."),
       ("Mapa de atrito de conteúdo", "Capítulos e formatos onde os alunos travam, com recomendação concreta para a coordenação pedagógica."),
       ("Fila semanal de intervenção", "Quem contatar, por quê, quando (19h–22h) e o que dizer — com template de mensagem, \"kit de retomada\" e resultado registrado em um clique, medido em R$.")]
for i, (t, d) in enumerate(pil):
    x = 0.6 + i * 4.1; card(s, x, 1.95, 3.85, 2.6, True)
    rect(s, x + 0.25, 2.2, 0.5, 0.5, VERDE, radius=0.5); text(s, x + 0.25, 2.2, 0.5, 0.5, str(i + 1), size=16, cor=AZUL, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.25, 2.85, 3.4, 0.5, t, size=15, cor=BRANCO, bold=True)
    text(s, x + 0.25, 3.3, 3.4, 1.2, d, size=11.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
text(s, 0.6, 4.85, 12, 0.4, "O RITUAL DA SEMANA", size=11, cor=VERDE, bold=True)
passos = [("Domingo 23h", "logs viram features e scores dentro do banco"), ("Segunda 8h", "coordenadora abre a fila priorizada"), ("Terça a quinta", "tutores contatam no horário em que o aluno estuda"), ("Sexta", "resultado registrado: reativado, sem resposta, plano"), ("Mensal", "receita preservada em R$ e retreino do modelo")]
for i, (a, b) in enumerate(passos):
    x = 0.6 + i * 2.48; rect(s, x, 5.25, 2.3, 1.35, CARD_ESC, radius=0.08)
    text(s, x + 0.15, 5.35, 2.0, 0.4, a, size=12.5, cor=VERDE, bold=True); text(s, x + 0.15, 5.72, 2.0, 0.85, b, size=10.5, cor=BRANCO)
    if i < 4: text(s, x + 2.3, 5.75, 0.2, 0.4, "›", size=18, cor=VERDE, bold=True, align=PP_ALIGN.CENTER)
rodape(s, True, n)
notes(s, "Solução (1 min): a Retena transforma os logs em três coisas: um score de risco por aluno, um diagnóstico de atrito de conteúdo e uma fila semanal de intervenção com motivo, ação e horário. Toda segunda a coordenação sabe quem chamar; toda sexta, quem voltou.")

# 7 DEMONSTRAÇÃO --------------------------------------------------------------------------------
s = novo(False); titulo(s, "Demonstração", "Dashboard do MVP com a base real: 196 alunos pontuados.")
card(s, 0.6, 1.95, 8.3, 4.75); img_fit(s, IMG("05_MVP", "outputs", "figs", "dashboard_hero_1920x1080.png"), 0.7, 2.05, 8.1, 4.55)
kp = [("6 KPIs", "ativos, alto risco, >14 dias sem acesso, receita em risco"), ("Fila de segunda", "196 alunos, ordenável, busca e filtros; clique abre fatores e ação sugerida"), ("Mapa de atrito", "heatmap fase × capítulo e 20 recomendações priorizadas"), ("Modelo", "métricas, calibração, importância e estabilidade por semana")]
for i, (a, b) in enumerate(kp):
    y = 1.95 + i * 1.02; card(s, 9.25, y, 3.5, 0.9); text(s, 9.45, y + 0.1, 3.2, 0.35, a, size=12.5, cor=AZUL, bold=True); text(s, 9.45, y + 0.42, 3.2, 0.5, b, size=10, cor=GRAFITE)
rect(s, 9.25, 6.05, 3.5, 0.65, AZUL, radius=0.1); text(s, 9.25, 6.05, 3.5, 0.65, "lucashenklain.github.io/retena/dashboard", size=11, cor=BRANCO, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
rodape(s, False, n)
notes(s, "Demonstração ao vivo (1 min): abrir o dashboard publicado. Mostrar os KPIs, a fila de segunda (buscar Aluno 0227 e clicar para abrir os fatores e a ação sugerida) e o mapa de atrito. Tudo com a base real anonimizada.")

# 8 ARQUITETURA ORACLE -------------------------------------------------------------------------
s = novo(False); titulo(s, "Por que dentro do Oracle", "O modelo roda onde o dado já mora.")
card(s, 0.6, 1.95, 8.6, 4.75); img_fit(s, IMG("02_Diagramas", "06_arquitetura_oracle.png"), 0.7, 2.02, 8.4, 4.6)
bullets(s, 9.5, 2.0, 3.25, 4.7, [
    "Oracle Autonomous AI Database 26ai: eventos, features em SQL, treino e scoring in-database (Oracle Machine Learning, DBMS_DATA_MINING).",
    "PREDICTION_PROBABILITY e PREDICTION_DETAILS geram score e motivo; views JSON alimentam APEX, Select AI e API.",
    "Oracle APEX para o painel; Select AI para perguntas em português; Object Storage e DBMS_SCHEDULER para ingestão e retreino.",
    "O dado do aluno não sai da instituição: LGPD por arquitetura, sem servidor de ML nem cientista de dados dedicado.",
], size=11.5, gap=0.18)
rodape(s, False, n)
notes(s, "Oracle (1 min): por que ninguém fez assim antes? BI mostra o passado, CRM cobra tarde e analytics exige cientistas de dados. A Retena roda onde o dado já está: dentro do Oracle AI Database. Features em SQL, treino e scoring com Oracle Machine Learning, sem o dado sair do banco. Em produção: Autonomous AI Database, APEX e Select AI.")

# 9 EVIDÊNCIA ORACLE ---------------------------------------------------------------------------
s = novo(True); titulo(s, "Integração executada, não desenhada", "Oracle 26ai Free + Oracle Machine Learning: já funciona.", escuro=True)
card(s, 0.6, 1.95, 7.4, 4.75, True); img_fit(s, IMG("06_Oracle", "evidencias", "evidencia_04.png"), 0.7, 2.03, 7.2, 4.6)
ev = [("684.723", "eventos carregados via python-oracledb em 72 s"), ("3 modelos", "Random Forest e GLM treinados com DBMS_DATA_MINING, in-database"), ("AUC 0,949", "Random Forest no teste temporal (cortes ≥ jun/2026), calculado por COMPUTE_ROC"), ("SQL + JSON", "PREDICTION_PROBABILITY, PREDICTION_DETAILS, views JSON e Duality View; job semanal com DBMS_SCHEDULER")]
for i, (a, b) in enumerate(ev):
    y = 1.95 + i * 1.2; card(s, 8.3, y, 4.45, 1.05, True); text(s, 8.5, y + 0.12, 1.8, 0.5, a, size=18, cor=VERDE, bold=True); text(s, 10.15, y + 0.12, 2.5, 0.85, b, size=10.5, cor=BRANCO)
text(s, 8.3, 6.78, 4.45, 0.3, "Evidências com timestamps em 06_Oracle/evidencias (HTML, TXT, CSV, PNG).", size=9.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
rodape(s, True, n)
notes(s, "Evidência Oracle (40 s): isto não é um desenho. Neste projeto carregamos os 685 mil eventos no Oracle AI Database 26ai Free, calculamos as features em SQL, treinamos três modelos dentro do banco com DBMS_DATA_MINING e expusemos o risco por SQL e JSON. Random Forest com AUC 0,949 no teste temporal.")

# 10 RESULTADOS --------------------------------------------------------------------------------
s = novo(False); titulo(s, "Resultados do modelo · teste temporal (jun–ago/2026)", "Treinado no passado, testado no futuro. Sem retoque.")
res = [("0,88", "AUC-ROC", "modelo de inatividade em 21 dias (gradient boosting); baseline logística 0,89"), ("88%", "precisão no top-20%", "dos alunos priorizados, 88 em 100 ficaram inativos"), ("3,06×", "lift no top-20%", "priorizar pela Retena acerta 3× mais do que ao acaso"), ("0,93", "AUC · transição de fase", "quem não inicia a fase seguinte (leave-one-phase-out)")]
for i, (a, b, c) in enumerate(res):
    x = 0.6 + i * 3.08; card(s, x, 1.95, 2.9, 1.9); stat(s, x + 0.2, 2.05, 2.5, a, b, c, size=34)
cd = CategoryChartData(); cd.categories = ["Alto (≥ 0,60)", "Médio (0,30–0,60)", "Baixo (< 0,30)"]; cd.add_series("Inatividade observada", (95.2, 48.7, 14.3))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, P(0.6), P(4.05), P(6.4), P(2.65), cd).chart
gf.has_legend = False; gf.has_title = True; gf.chart_title.text_frame.text = "Taxa observada de inatividade por faixa de risco (%)"
tt = gf.chart_title.text_frame.paragraphs[0].runs[0].font; tt.size = Pt(12); tt.bold = True; tt.color.rgb = AZUL; tt.name = FONT
pl = gf.plots[0]; pl.gap_width = 50; pl.has_data_labels = True; dl = pl.data_labels; dl.position = XL_LABEL_POSITION.OUTSIDE_END; dl.font.size = Pt(11); dl.font.bold = True; dl.font.color.rgb = AZUL; dl.number_format = '0.0"%"'; dl.number_format_is_linked = False
ser = pl.series[0]
for idx, c in enumerate((CORAL, AMBAR, VERDE)):
    pt = ser.points[idx]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
gf.category_axis.tick_labels.font.size = Pt(10.5); gf.category_axis.tick_labels.font.color.rgb = GRAFITE; gf.category_axis.format.line.color.rgb = LINHA; gf.category_axis.reverse_order = True
va = gf.value_axis; va.visible = False; va.has_major_gridlines = False; va.maximum_scale = 110; va.minimum_scale = 0
card(s, 7.3, 4.05, 5.45, 2.65); text(s, 7.5, 4.15, 5.1, 0.35, "O que dizemos com honestidade", size=13, cor=AZUL, bold=True)
bullets(s, 7.5, 4.55, 5.05, 2.1, ["Amostra de um curso (~200 alunos): retreino com os dados de cada IES antes de produção.", "Rótulo comportamental (21 dias sem acesso), não cancelamento de matrícula.", "No subconjunto de alunos ainda ativos nos 28 dias anteriores, a AUC cai para 0,74: antecipar é mais difícil do que confirmar.", "Só logs de navegação: limita o teto, mas torna a solução portátil para qualquer LMS."], size=10.5, gap=0.08)
rodape(s, False, n)
notes(s, "Resultados (50 s): treinamos nos primeiros meses e testamos nos seguintes, sem olhar o futuro. AUC 0,88; entre os 20% apontados como maior risco, 88% de fato ficaram inativos; na faixa Alto, 95 em cada 100. E dizemos as limitações: amostra de um curso, rótulo comportamental, AUC 0,74 no subconjunto acionável.")


# 10b BENCHMARK E PORTABILIDADE (v2) ------------------------------------------------------------
s = novo(False); titulo(s, "Versão 2 · o que o time acrescentou", "Benchmark de modelos e portabilidade do método.")
card(s, 0.6, 1.95, 6.4, 4.75); text(s, 0.8, 2.08, 6.0, 0.35, "Benchmark no mesmo split temporal (teste jun–ago/2026)", size=13, cor=AZUL, bold=True)
tbl = s.shapes.add_table(7, 4, P(0.8), P(2.5), P(6.0), P(2.9)).table
for j, w in enumerate([3.0, 1.0, 1.0, 1.0]): tbl.columns[j].width = P(w)
data = [("Modelo", "AUC-ROC", "AUC-PR", "F2"), ("HGB (entregue)", "0,882", "0,839", "0,626"), ("Logística baseline", "0,893", "0,859", "0,696"), ("Logística + balanced", "0,889", "0,855", "0,766"), ("Logística EduRetain (L1)", "0,882", "0,850", "0,759"), ("XGBoost (config EduRetain)", "0,874", "0,818", "0,586"), ("GradientBoosting padrão", "0,811", "0,739", "0,543")]
for i, row in enumerate(data):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j); cell.text = v; cell.fill.solid(); cell.fill.fore_color.rgb = AZUL if i == 0 else (BRANCO if i % 2 else OFF); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        for r in pp.runs: r.font.size = Pt(10.5); r.font.name = FONT; r.font.bold = (i == 0 or i == 1); r.font.color.rgb = BRANCO if i == 0 else (AZUL if i == 1 else GRAFITE)
bullets(s, 0.8, 5.5, 6.0, 1.2, ["Nenhuma configuração do EduRetain supera o baseline já existente; a vantagem em F2 dos modelos balanceados é efeito de limiar, não de ordenação.", "HGB permanece o modelo entregue (melhor precisão a 0,5 e rastreabilidade); o limiar 0,30 da faixa Médio recupera o recall."], size=10, gap=0.06)
card(s, 7.3, 1.95, 5.45, 4.75); text(s, 7.5, 2.08, 5.1, 0.35, "Portabilidade: o mesmo método no OULAD (Open University)", size=13, cor=AZUL, bold=True)
bullets(s, 7.5, 2.55, 5.05, 3.0, OULAD_TXT, size=10.5, gap=0.1)
rect(s, 7.5, 5.7, 5.05, 0.85, RGBColor(0xE6, 0xF7, 0xF5), radius=0.08)
text(s, 7.65, 5.76, 4.8, 0.75, OULAD_SINTESE, size=10.5, cor=AZUL, bold=True)
rodape(s, False, n)
notes(s, "Versão 2 (40 s): depois da entrega, incorporamos o pipeline EduRetain de um integrante como benchmark. Nenhuma configuração dele supera o baseline logístico já presente, e a vantagem em F2 dos modelos balanceados é efeito de limiar. Rodamos ainda o método no OULAD, dataset público da Open University, para provar a portabilidade que o pitch afirma.")

# 11 DIFERENCIAL --------------------------------------------------------------------------------
s = novo(False); titulo(s, "Diferencial", "BI olha o passado, CRM cobra tarde. A Retena fecha o ciclo.")
cols = ["", "Retena", "BI do LMS", "CRM de cobrança", "Consultoria"]
rows = [("Antecipa o risco semanas antes (recência, tendência, capítulo)", "●", "○", "○", "◐"),
        ("Diz quem contatar, por quê, quando e o que dizer", "●", "○", "◐", "◐"),
        ("Mapa de atrito de conteúdo por capítulo", "●", "◐", "○", "◐"),
        ("Registra o resultado e mede receita preservada em R$", "●", "○", "◐", "○"),
        ("Roda dentro do banco da IES (LGPD, sem ETL externo)", "●", "◐", "○", "○"),
        ("Retreina com o resultado das intervenções", "●", "○", "○", "○"),
        ("Implantação em semanas, sem cientista de dados", "●", "●", "●", "○")]
tbl = s.shapes.add_table(len(rows) + 1, 5, P(0.6), P(1.95), P(12.15), P(4.3)).table
widths = [5.55, 1.65, 1.65, 1.65, 1.65]
for j, w in enumerate(widths): tbl.columns[j].width = P(w)
for j, c in enumerate(cols):
    cell = tbl.cell(0, j); cell.text = c; cell.fill.solid(); cell.fill.fore_color.rgb = AZUL
    pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER if j else PP_ALIGN.LEFT
    for r in pp.runs: r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = BRANCO; r.font.name = FONT
for i, row in enumerate(rows, start=1):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j); cell.text = v; cell.fill.solid(); cell.fill.fore_color.rgb = BRANCO if i % 2 else OFF
        pp = cell.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for r in pp.runs:
            r.font.size = Pt(11.5) if j == 0 else Pt(16); r.font.name = FONT
            r.font.color.rgb = GRAFITE if j == 0 else (VERDE if j == 1 else (AMBAR if v == "◐" else (AZUL if v == "●" else CINZA)))
            r.font.bold = j == 1
text(s, 0.6, 6.35, 12.1, 0.35, "● atende plenamente   ◐ atende em parte   ○ não atende. Por que não foi resolvido assim antes: dado preso em relatórios descritivos, ML exigia pipeline externo e cientista de dados, ninguém fechava o ciclo com ROI — e o EAD só virou maioria em 2024.", size=10, cor=GRAFITE)
rodape(s, False, n)
notes(s, "Diferencial (40 s): só a Retena junta quem, onde e resultado — risco por aluno, atrito por capítulo e reativação medida em R$ — sem tirar o dado da instituição, e cada intervenção retreina o modelo. Ficou viável agora: ML in-database maduro e EAD como maioria.")

# 12 MODELO DE NEGÓCIO -------------------------------------------------------------------------
s = novo(True); titulo(s, "Monetização", "SaaS por aluno ativo/mês, com piloto de 90 dias.", escuro=True)
tbl = s.shapes.add_table(5, 3, P(0.6), P(1.95), P(6.6), P(2.9)).table
for j, w in enumerate([2.9, 1.9, 1.8]): tbl.columns[j].width = P(w)
data = [("Faixa de volume", "Preço / aluno ativo / mês", "Plano"), ("1 mil a 10 mil alunos", "R$ 6,00", "Pro"), ("10 mil a 50 mil alunos", "R$ 4,00", "Pro"), ("Acima de 50 mil (megagrupos)", "R$ 3,00", "Enterprise · fase 2"), ("Menos de 5 mil alunos", "R$ 2,00 · mín. R$ 2,5 mil/mês", "Essencial")]
for i, row in enumerate(data):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j); cell.text = v; cell.fill.solid(); cell.fill.fore_color.rgb = VERDE if i == 0 else (CARD_ESC if i % 2 else AZUL_M); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for r in cell.text_frame.paragraphs[0].runs: r.font.size = Pt(11.5); r.font.name = FONT; r.font.bold = (i == 0 or j == 1); r.font.color.rgb = AZUL if i == 0 else BRANCO
text(s, 0.6, 4.95, 6.6, 0.9, "Mínimo mensal R$ 5 mil (Pro) · setup e integração ao LMS R$ 10–25 mil · piloto de 90 dias em uma fase de um curso por R$ 5 mil, com meta de rematrícula acordada e conversão automática em contrato anual · margem bruta alvo 80%.", size=10.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
text(s, 7.6, 1.95, 5.1, 0.35, "A CONTA DO CLIENTE-REFERÊNCIA · 12 MIL ALUNOS EAD", size=11, cor=VERDE, bold=True)
roi = [("R$ 576 mil / ano", "12.000 alunos × R$ 4,00 × 12 meses (+ setup único de R$ 20 mil)"), ("137 alunos retidos", "≈ 1,1% da base, a R$ 4.200/ano de receita preservada por aluno, já paga o contrato"), ("R$ 500 mil por ponto", "cada 1 p.p. de desistência evitado (~120 alunos) vale ~R$ 500 mil/ano. Estimativas com ticket de R$ 350/mês")]
for i, (a, b) in enumerate(roi):
    y = 2.4 + i * 1.45; card(s, 7.6, y, 5.15, 1.3, True); text(s, 7.8, y + 0.12, 4.8, 0.5, a, size=20, cor=VERDE, bold=True); text(s, 7.8, y + 0.62, 4.8, 0.65, b, size=10.5, cor=BRANCO)
text(s, 0.6, 6.05, 6.6, 0.65, "Quem paga: a diretoria de operações acadêmicas, porque compramos rematrícula. Quem usa: a coordenação de permanência. Venda com painel de receita em risco em R$; uso diário com a fila de segunda.", size=10.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
rodape(s, True, n)
notes(s, "Monetização (50 s): SaaS por aluno ativo por mês, de três a seis reais conforme o porte, com piloto de 90 dias e meta de rematrícula. Uma IES de 12 mil alunos paga cerca de R$ 576 mil por ano; reter 1,1% da base já paga o contrato, e cada ponto de desistência evitado vale meio milhão por ano.")

# 13 MERCADO ------------------------------------------------------------------------------------
s = novo(False); titulo(s, "Mercado", "5,2 milhões de alunos EAD · 2.244 IES privadas.")
mk = [("TAM", "R$ 249 mi/ano", "5,19 mi matrículas EAD (INEP 2024) × R$ 4 × 12 meses", AZUL), ("SAM", "R$ 126 mi/ano", "IES privadas fora dos megagrupos: ~2,6 mi alunos (Semesp 2026)", AZUL_M), ("SOM · 3 anos", "R$ 2,5–4,3 mi ARR", "8–12 IES médias (~52 mil alunos) + 1 megagrupo piloto via canal Oracle", VERDE)]
for i, (a, b, c, col) in enumerate(mk):
    x = 0.6 + i * 4.1; rect(s, x, 1.95, 3.85, 2.55, col, radius=0.06)
    text(s, x + 0.25, 2.1, 3.4, 0.35, a, size=12, cor=BRANCO if col != VERDE else AZUL, bold=True)
    text(s, x + 0.25, 2.45, 3.4, 0.8, b, size=24, cor=BRANCO if col != VERDE else AZUL, bold=True)
    text(s, x + 0.25, 3.35, 3.4, 1.0, c, size=11, cor=RGBColor(0xDD, 0xE6, 0xF0) if col != VERDE else AZUL)
text(s, 0.6, 4.75, 12, 0.35, "GO-TO-MARKET", size=11, cor=VERDE, bold=True)
gtm = [("Ano 1", "3 pilotos de 90 dias + 2 contratos (~R$ 0,5 mi ARR); Autonomous Always Free → pago"), ("Ano 2", "6 IES médias (~R$ 1,4 mi ARR); módulo de conteúdo adaptativo; integração WhatsApp"), ("Ano 3", "10–12 IES + 1 megagrupo via ecossistema Oracle (R$ 2,5–4,3 mi ARR); ensino técnico e corporativo")]
for i, (a, b) in enumerate(gtm):
    x = 0.6 + i * 4.1; card(s, x, 5.15, 3.85, 1.5); text(s, x + 0.2, 5.27, 3.4, 0.35, a, size=13, cor=AZUL, bold=True); text(s, x + 0.2, 5.62, 3.45, 0.95, b, size=11, cor=GRAFITE)
rodape(s, False, n)
notes(s, "Mercado (40 s): 2.244 IES privadas e 5,2 milhões de alunos EAD. Alvo inicial: IES de médio porte fora dos megagrupos. O modelo é portátil para qualquer LMS Moodle-like, o que abre caminho para o ensino técnico e corporativo; megagrupos entram na fase 2 via ecossistema Oracle.")

# 14 VALIDAÇÃO ----------------------------------------------------------------------------------
s = novo(False); titulo(s, "Validação estruturada", "Dados reais, fontes de mercado e entrevistas estruturadas.")
card(s, 0.6, 1.95, 5.9, 4.75); text(s, 0.8, 2.08, 5.5, 0.35, "Hipóteses H1–H6 · status após a Fase 6", size=13, cor=AZUL, bold=True)
hip = [("H1 · A IES descobre a evasão tarde", "6/6 percebem em ≥ 2 semanas", VERDE), ("H2 · Sinais do LMS antecipam a evasão", "AUC 0,88 no teste temporal", VERDE), ("H3 · Tutores não conseguem priorizar", "5/6 priorizam de forma intuitiva", VERDE), ("H4 · Conteúdo tem atrito identificável", "4/6 citam capítulos específicos", VERDE), ("H5 · Disposição a pagar por aluno/mês", "coordenação R$ 1–3; sponsor R$ 3–4", AMBAR), ("H6 · Integração por export é aceitável", "6/6 têm export de logs acessível", VERDE)]
for i, (a, b, c) in enumerate(hip):
    y = 2.55 + i * 0.68; d = s.shapes.add_shape(MSO_SHAPE.OVAL, P(0.85), P(y + 0.08), P(0.2), P(0.2)); d.fill.solid(); d.fill.fore_color.rgb = c; d.line.fill.background(); d.shadow.inherit = False
    text(s, 1.15, y, 3.0, 0.6, a, size=11, cor=AZUL, bold=True); text(s, 4.05, y, 2.35, 0.6, b, size=10, cor=GRAFITE)
card(s, 6.85, 1.95, 5.9, 4.75); text(s, 7.05, 2.08, 5.5, 0.35, "O que as entrevistas mudaram na proposta", size=13, cor=AZUL, bold=True)
bullets(s, 7.05, 2.55, 5.5, 3.2, ["Venda ao sponsor de operações (receita em risco em R$); uso diário pela coordenação.", "Plano Essencial para IES pequenas: a dor existe, o orçamento é mínimo.", "Template de mensagem, janela 19h–22h e \"kit de retomada\" em cada linha da fila.", "Registro de resultado em um clique; WhatsApp no primeiro trimestre pós-piloto.", "Piloto com meta de rematrícula contratual; argumento LGPD explícito."], size=11, gap=0.1)
rect(s, 7.05, 5.75, 5.5, 0.8, RGBColor(0xFF, 0xF4, 0xD6), radius=0.08)
text(s, 7.2, 5.8, 5.2, 0.72, "Nota: as 8 entrevistas foram conduzidas em formato simulado, com personas sintéticas construídas a partir dos perfis-alvo e da base real, para calibrar o instrumento; serão confirmadas em campo antes do piloto.", size=9.5, cor=GRAFITE)
rodape(s, False, n)
notes(s, "Validação (40 s): três frentes — dados reais, INEP/Semesp e o instrumento de entrevistas. Se perguntarem sobre as entrevistas: foram simuladas com personas sintéticas para calibrar o roteiro e antecipar objeções; estão rotuladas assim no documento e serão confirmadas em campo antes do piloto.")

# 15 PRÓXIMOS PASSOS ----------------------------------------------------------------------------
s = novo(True); titulo(s, "Próximos passos", "Do MVP ao piloto com meta de rematrícula.", escuro=True)
tl = [("13/09", "Vídeo pitch e formulário enviados", True), ("23/09", "Banca Final", True), ("24/10", "NEXT: demonstração com Autonomous AI Database + APEX", False), ("Nov–Fev", "Piloto de 90 dias em uma fase de um curso, meta de rematrícula", False), ("2027", "Conteúdo adaptativo, WhatsApp, megagrupos via canal Oracle", False)]
rect(s, 0.9, 3.05, 11.5, 0.06, RGBColor(0x3E, 0x5A, 0x82))
for i, (a, b, done) in enumerate(tl):
    x = 0.6 + i * 2.5; d = s.shapes.add_shape(MSO_SHAPE.OVAL, P(x + 1.0), P(2.9), P(0.36), P(0.36)); d.fill.solid(); d.fill.fore_color.rgb = VERDE if done else AZUL_M; d.line.color.rgb = VERDE; d.line.width = Pt(2); d.shadow.inherit = False
    text(s, x, 2.2, 2.35, 0.5, a, size=16, cor=VERDE if done else BRANCO, bold=True, align=PP_ALIGN.CENTER)
    text(s, x, 3.45, 2.35, 1.2, b, size=11, cor=BRANCO, align=PP_ALIGN.CENTER)
text(s, 0.6, 4.95, 12, 0.35, "O QUE PEDIMOS À BANCA E AO ECOSSISTEMA ORACLE", size=11, cor=VERDE, bold=True)
ask = [("Autonomous AI Database", "apoio para provisionar o Always Free e publicar a primeira aplicação APEX antes do NEXT"), ("Uma IES parceira", "para o piloto de 90 dias em uma fase de um curso, com dados anonimizados e meta acordada"), ("Mentoria comercial", "para a venda ao sponsor de operações e o acesso a grupos que já rodam Oracle")]
for i, (a, b) in enumerate(ask):
    x = 0.6 + i * 4.1; card(s, x, 5.35, 3.85, 1.3, True); text(s, x + 0.2, 5.45, 3.45, 0.4, a, size=13, cor=VERDE, bold=True); text(s, x + 0.2, 5.85, 3.45, 0.75, b, size=10.5, cor=BRANCO)
rodape(s, True, n)
notes(s, "Próximos passos (30 s): vídeo e formulário enviados; banca em 23/09; NEXT em 24/10 com Autonomous + APEX; piloto de 90 dias com meta de rematrícula. Pedimos apoio para o Autonomous Always Free, uma IES parceira e mentoria comercial.")

# 16 FECHAMENTO ---------------------------------------------------------------------------------
s = novo(True)
img_cover(s, IMG("04_Landing_Page", "img", "formatura.jpg"), 0, 0, 13.333, 7.5)
v = rect(s, 0, 0, 13.333, 7.5, AZUL); sf = v.fill._xPr.find(qn("a:solidFill")); clr = sf.find(qn("a:srgbClr")); clr.append(clr.makeelement(qn("a:alpha"), {"val": "82000"}))
if os.path.exists(logo): s.shapes.add_picture(logo, P(0.9), P(0.9), height=P(0.85))
text(s, 0.9, 2.3, 11.5, 2.0, [[("Ninguém desiste de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=44, spacing=1.05)
text(s, 0.9, 4.35, 11, 0.9, "A evasão não é um evento. É um silêncio que dura semanas. A Retena escuta esse silêncio, dentro do banco que a instituição já usa, e devolve tempo para quem pode agir.", size=16, cor=RGBColor(0xDD, 0xE6, 0xF0), spacing=1.3)
links = [("Vídeo pitch", ["youtu.be/HZrcLvIJCC4"]), ("Site e dashboard", ["lucashenklain.github.io/retena"]), ("Evidências Oracle", ["lucashenklain.github.io/retena/", "evidencias/evidencias.html"])]
for i, (a, b) in enumerate(links):
    x = 0.9 + i * 4.05; rect(s, x, 5.5, 3.85, 1.05, CARD_ESC, radius=0.1); text(s, x + 0.2, 5.58, 3.5, 0.35, a, size=11, cor=VERDE, bold=True); text(s, x + 0.2, 5.9, 3.5, 0.6, b, size=10, cor=BRANCO, spacing=1.1)
text(s, 0.9, 6.8, 11.5, 0.5, "Lucas Dalmas · Lucas Emanuel · Kayque Moraes · Lucas Henklain · Vinicius Pinheiro — Engenharia de Software, FIAP 4ESOA · Startup One / Enterprise Challenge Oracle 2026", size=10.5, cor=RGBColor(0xC9, 0xD6, 0xE4))
notes(s, "Fechamento (30 s): a evasão não é um evento, é um processo silencioso que dura semanas. A Retena escuta esse silêncio e devolve tempo para quem pode agir. Ninguém desiste de repente. A Retena percebe antes. Obrigado.")

prs.save(OUT); print("OK ->", OUT, "| slides:", len(prs.slides))
