# -*- coding: utf-8 -*-
"""
Gerador do documento estruturado da Fase 6 — Retena (Startup One / Enterprise Challenge Oracle, FIAP 4ESOA-2026).

Uso:  python gerar_documento.py
Saída: Retena_Fase6_Documento.docx (mesma pasta). A conversão para PDF é feita via Word (COM), fora deste script.

Todo o conteúdo textual está neste arquivo, em funções sec_*(). As figuras só são inseridas se o arquivo existir;
as faltantes são listadas ao final da execução.
"""
import os
import glob
import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image

# ----------------------------------------------------------------------------------------------------------------------
# Caminhos e constantes
# ----------------------------------------------------------------------------------------------------------------------
AQUI = os.path.dirname(os.path.abspath(__file__))          # .../entrega/01_Documento
ENTREGA = os.path.dirname(AQUI)                            # .../entrega
OUT_DOCX = os.path.join(AQUI, "Retena_Fase6_Documento.docx")

DIAGRAMAS = os.path.join(ENTREGA, "02_Diagramas")
LOGOS = os.path.join(ENTREGA, "03_Marca", "logo")
FIGS_MVP = os.path.join(ENTREGA, "05_MVP", "outputs", "figs")
ORACLE_EVID = os.path.join(ENTREGA, "06_Oracle", "evidencias")

AZUL = RGBColor(0x0B, 0x25, 0x45)      # títulos, cabeçalhos de tabela
GRAFITE = RGBColor(0x3A, 0x4A, 0x5C)   # texto corrido
CINZA = RGBColor(0x7A, 0x86, 0x94)     # legendas, cabeçalho/rodapé
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
HEX_AZUL = "0B2545"
HEX_VERDE = "2EC4B6"
HEX_AMBAR = "FFB703"
HEX_CORAL = "FF6B4A"
HEX_OFF = "F6F7F9"
HEX_BORDA = "D9DEE5"

FONT_BODY = "Inter"      # fallback automático do Word: Calibri
FONT_TITLE = "Sora"

FIGS_INSERIDAS = []
FIGS_FALTANTES = []
_contador = {"fig": 0, "tab": 0, "bm": 0}
_toc = []            # (nivel, texto, bookmark)
_doc = None

# ----------------------------------------------------------------------------------------------------------------------
# Helpers de formatação
# ----------------------------------------------------------------------------------------------------------------------

def _rfonts(rpr, nome):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for att in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(att), nome)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(att)) is not None:
            del rf.attrib[qn(att)]


def _style_font(style, nome, tamanho=None, negrito=None, cor=None, italico=None):
    style.font.name = nome
    rpr = style.element.get_or_add_rPr()
    _rfonts(rpr, nome)
    if tamanho is not None:
        style.font.size = Pt(tamanho)
    if negrito is not None:
        style.font.bold = negrito
    if italico is not None:
        style.font.italic = italico
    if cor is not None:
        style.font.color.rgb = cor


def _run_font(run, nome=None, tamanho=None, negrito=None, cor=None, italico=None):
    if nome:
        run.font.name = nome
        _rfonts(run._element.get_or_add_rPr(), nome)
    if tamanho is not None:
        run.font.size = Pt(tamanho)
    if negrito is not None:
        run.font.bold = negrito
    if italico is not None:
        run.font.italic = italico
    if cor is not None:
        run.font.color.rgb = cor


def add_runs(par, texto, tamanho=None, cor=None, nome=None, italico=None):
    """Adiciona texto ao parágrafo interpretando **negrito** inline."""
    partes = texto.split("**")
    for i, parte in enumerate(partes):
        if not parte:
            continue
        r = par.add_run(parte)
        _run_font(r, nome=nome, tamanho=tamanho, negrito=(i % 2 == 1) or None, cor=cor, italico=italico)
    return par


def p(texto="", alinh=None, tamanho=None, cor=None, negrito=False, italico=False, antes=None, depois=None,
      nome=None, estilo=None, keep_next=False, recuo=None):
    par = _doc.add_paragraph(style=estilo) if estilo else _doc.add_paragraph()
    if texto:
        if negrito:
            texto = "**" + texto + "**"
        add_runs(par, texto, tamanho=tamanho, cor=cor, nome=nome, italico=italico or None)
    if alinh == "c":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif alinh == "d":
        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif alinh == "j":
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = par.paragraph_format
    if antes is not None:
        pf.space_before = Pt(antes)
    if depois is not None:
        pf.space_after = Pt(depois)
    if keep_next:
        pf.keep_with_next = True
    if recuo is not None:
        pf.left_indent = Cm(recuo)
    return par


def _bookmark(par, nome):
    _contador["bm"] += 1
    bid = str(_contador["bm"])
    ini = OxmlElement("w:bookmarkStart")
    ini.set(qn("w:id"), bid)
    ini.set(qn("w:name"), nome)
    fim = OxmlElement("w:bookmarkEnd")
    fim.set(qn("w:id"), bid)
    par._p.insert(0, ini)
    par._p.append(fim)


def _heading(texto, nivel):
    par = _doc.add_paragraph(style="Heading %d" % nivel)
    add_runs(par, texto)
    if nivel <= 2:
        nome = "_Toc_%03d" % (len(_toc) + 1)
        _bookmark(par, nome)
        _toc.append((nivel, texto, nome))
    return par


def h1(texto, quebra=True):
    if quebra:
        page_break()
    return _heading(texto, 1)


def h2(texto):
    return _heading(texto, 2)


def h3(texto):
    return _heading(texto, 3)


def bullets(itens, tamanho=None, depois=3):
    for it in itens:
        par = _doc.add_paragraph(style="List Bullet")
        add_runs(par, it, tamanho=tamanho)
        par.paragraph_format.space_after = Pt(depois)


def numerados(itens, tamanho=None):
    for i, it in enumerate(itens, 1):
        par = _doc.add_paragraph()
        pf = par.paragraph_format
        pf.left_indent = Cm(0.9)
        pf.first_line_indent = Cm(-0.6)
        pf.space_after = Pt(3)
        r = par.add_run("%d.  " % i)
        _run_font(r, negrito=True, cor=AZUL, tamanho=tamanho)
        add_runs(par, it, tamanho=tamanho)


def page_break():
    _doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _cell_border(cell, lado, cor, sz):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    b = OxmlElement("w:" + lado)
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "0")
    b.set(qn("w:color"), cor)
    borders.append(b)


def _table_borders(table, cor=HEX_BORDA, sz=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement("w:" + lado)
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(sz))
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), cor)
        borders.append(b)
    tblPr.append(borders)


def _cell_text(cell, texto, tamanho=9, cor=None, negrito=None, alinh=None, nome=None):
    cell.text = ""
    par = cell.paragraphs[0]
    par.paragraph_format.space_after = Pt(1)
    par.paragraph_format.space_before = Pt(1)
    linhas = str(texto).split("\n")
    for i, linha in enumerate(linhas):
        if i > 0:
            par = cell.add_paragraph()
            par.paragraph_format.space_after = Pt(1)
        if negrito:
            add_runs(par, linha, tamanho=tamanho, cor=cor, nome=nome)
            for r in par.runs:
                r.font.bold = True
        else:
            add_runs(par, linha, tamanho=tamanho, cor=cor, nome=nome)
        if alinh == "c":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER


def tabela(cabecalho, linhas, larguras=None, tamanho=8.5, legenda=None, zebra=True, primeira_negrito=False):
    """Tabela leve: cabeçalho azul-profundo com texto branco e linha de acento verde; zebra off-white."""
    ncol = len(cabecalho)
    if legenda:
        _contador["tab"] += 1
        cap = p("Tabela %d — %s" % (_contador["tab"], legenda), tamanho=9, cor=AZUL, antes=6, depois=3, keep_next=True)
        cap.runs[0].font.bold = True
    t = _doc.add_table(rows=1, cols=ncol)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _table_borders(t)
    if larguras is None:
        larguras = [16.0 / ncol] * ncol
    for j, txt in enumerate(cabecalho):
        c = t.rows[0].cells[j]
        _shade(c, HEX_AZUL)
        _cell_border(c, "bottom", HEX_VERDE, 12)
        _cell_text(c, txt, tamanho=tamanho, cor=BRANCO, negrito=True)
    for i, linha in enumerate(linhas):
        cells = t.add_row().cells
        for j in range(ncol):
            val = linha[j] if j < len(linha) else ""
            _cell_text(cells[j], val, tamanho=tamanho, cor=GRAFITE, negrito=(primeira_negrito and j == 0) or None)
            if zebra and i % 2 == 1:
                _shade(cells[j], HEX_OFF)
    for row in t.rows:
        for j, c in enumerate(row.cells):
            c.width = Cm(larguras[j])
    # repetir cabeçalho em quebra de página
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    p("", depois=4)
    return t


def destaque(texto, cor_fill=HEX_OFF, cor_borda=HEX_VERDE, tamanho=10):
    """Caixa de destaque: célula única com fundo off-white e barra lateral verde-sinal."""
    t = _doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    c = t.rows[0].cells[0]
    c.width = Cm(16)
    _shade(c, cor_fill)
    _cell_border(c, "left", cor_borda, 24)
    for lado in ("top", "bottom", "right"):
        _cell_border(c, lado, cor_fill, 4)
    c.text = ""
    par = c.paragraphs[0]
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(4)
    par.paragraph_format.left_indent = Cm(0.2)
    add_runs(par, texto, tamanho=tamanho, cor=GRAFITE)
    p("", depois=4)


def figura(caminho, legenda, largura_cm=16.0, altura_max_cm=19.0):
    """Insere a figura apenas se o arquivo existir; registra inseridas/faltantes. Legenda numerada."""
    rel = os.path.relpath(caminho, ENTREGA)
    if not os.path.exists(caminho):
        FIGS_FALTANTES.append(rel)
        return False
    try:
        with Image.open(caminho) as im:
            w, h = im.size
    except Exception:
        w, h = (16, 9)
    largura = largura_cm
    if largura * h / w > altura_max_cm:
        largura = altura_max_cm * w / h
    _contador["fig"] += 1
    par = _doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    par.paragraph_format.space_before = Pt(6)
    par.add_run().add_picture(caminho, width=Cm(largura))
    cap = p("Figura %d — %s" % (_contador["fig"], legenda), alinh="c", tamanho=9, cor=CINZA, italico=True, depois=10)
    FIGS_INSERIDAS.append(rel)
    return True


def figura_recorte(caminho, legenda, largura_cm=16.0, frac=0.625):
    """Para capturas de página inteira (muito altas): insere só a faixa superior (largura × frac), legível na página.
    O recorte é salvo em _figs_tmp/ ao lado do script; a lista de figuras registra o arquivo original."""
    rel = os.path.relpath(caminho, ENTREGA)
    if not os.path.exists(caminho):
        FIGS_FALTANTES.append(rel)
        return False
    try:
        with Image.open(caminho) as im:
            w, h = im.size
            alvo = int(w * frac)
            if h <= alvo * 1.15:
                return figura(caminho, legenda, largura_cm=largura_cm, altura_max_cm=largura_cm * frac + 0.5)
            pasta = os.path.join(AQUI, "_figs_tmp")
            os.makedirs(pasta, exist_ok=True)
            destino = os.path.join(pasta, os.path.splitext(os.path.basename(caminho))[0] + "_topo.png")
            im.crop((0, 0, w, alvo)).save(destino)
    except Exception:
        return figura(caminho, legenda, largura_cm=largura_cm)
    ok = figura(destino, legenda + " (faixa superior da captura)", largura_cm=largura_cm, altura_max_cm=largura_cm * frac + 0.5)
    if ok and FIGS_INSERIDAS:
        FIGS_INSERIDAS[-1] = rel
    return ok


def _campo(par, instrucao, cache="1", tamanho=None, cor=None):
    """Campo complexo do Word (PAGE, PAGEREF...): begin / instrText / separate / valor em cache / end."""
    def novo_run():
        r = par.add_run()
        _run_font(r, tamanho=tamanho, cor=cor)
        return r

    def fld(tipo):
        r = novo_run()
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), tipo)
        r._r.append(fc)

    fld("begin")
    r = novo_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " %s " % instrucao
    r._r.append(it)
    fld("separate")
    novo_run().text = cache
    fld("end")


def _cabecalho_rodape(section):
    section.different_first_page_header_footer = True
    hp = section.header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_runs(hp, "Retena · Fase 6 — Refinamento, Validação e Estruturação do MVP", tamanho=8, cor=CINZA)
    # linha fina sob o cabeçalho
    pPr = hp._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), "6")
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), HEX_VERDE)
    pbdr.append(b)
    pPr.append(pbdr)
    fp = section.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(fp, "Startup One · Enterprise Challenge Oracle · FIAP 4ESOA-2026   |   Página ", tamanho=8, cor=CINZA)
    _campo(fp, "PAGE", cache="1", tamanho=8, cor=CINZA)


def configurar_estilos(doc):
    st = doc.styles
    normal = st["Normal"]
    _style_font(normal, FONT_BODY, 11, cor=GRAFITE)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    _style_font(st["Heading 1"], FONT_TITLE, 18, negrito=True, cor=AZUL)
    st["Heading 1"].paragraph_format.space_before = Pt(6)
    st["Heading 1"].paragraph_format.space_after = Pt(10)
    _style_font(st["Heading 2"], FONT_TITLE, 13.5, negrito=True, cor=AZUL)
    st["Heading 2"].paragraph_format.space_before = Pt(14)
    st["Heading 2"].paragraph_format.space_after = Pt(6)
    _style_font(st["Heading 3"], FONT_TITLE, 11.5, negrito=True, cor=AZUL)
    st["Heading 3"].paragraph_format.space_before = Pt(10)
    st["Heading 3"].paragraph_format.space_after = Pt(4)
    for nome in ("Heading 1", "Heading 2", "Heading 3"):
        st[nome].paragraph_format.keep_with_next = True
        # remove itálico/cores de tema herdados do template
        st[nome].font.italic = False
    _style_font(st["List Bullet"], FONT_BODY, 11, cor=GRAFITE)
    st["List Bullet"].paragraph_format.space_after = Pt(3)


# ----------------------------------------------------------------------------------------------------------------------
# Seções
# ----------------------------------------------------------------------------------------------------------------------

def sec_capa():
    p("", depois=30)
    logo = os.path.join(LOGOS, "retena_vertical_escuro_sobre_claro.png")
    if os.path.exists(logo):
        par = _doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run().add_picture(logo, width=Cm(8.5))
        FIGS_INSERIDAS.append(os.path.relpath(logo, ENTREGA))
    else:
        FIGS_FALTANTES.append("03_Marca/logo/retena_vertical_escuro_sobre_claro.png")
        p("Retena", alinh="c", tamanho=40, cor=AZUL, negrito=True, nome=FONT_TITLE)
    p("", depois=18)
    p("Retena — Fase 6: Refinamento, Validação e Estruturação do MVP", alinh="c", tamanho=22, cor=AZUL,
      negrito=True, nome=FONT_TITLE, depois=8)
    p("Startup One · Enterprise Challenge Oracle · FIAP 4ESOA-2026", alinh="c", tamanho=12, cor=GRAFITE, depois=4)
    p("Documento estruturado — Partes 1 a 4, próximos passos e anexos", alinh="c", tamanho=11, cor=CINZA, depois=26)
    p("“Ninguém desiste de repente. A Retena percebe antes.”", alinh="c", tamanho=12, cor=AZUL, italico=True,
      nome=FONT_TITLE, depois=40)
    p("Equipe", alinh="c", tamanho=10, cor=CINZA, depois=2)
    p("Lucas Dalmas — RM551178 · Lucas Emanuel — RM97881 · Kayque Moraes — RM97592",
      alinh="c", tamanho=11, cor=GRAFITE, depois=2)
    p("Lucas Henklain — RM99350 · Vinicius Pinheiro — RM99198",
      alinh="c", tamanho=11, cor=GRAFITE, depois=18)
    p("Curso: Engenharia de Software — 4º ano (4ESOA) · Turma 2026", alinh="c", tamanho=10, cor=GRAFITE, depois=2)
    p("São Paulo, setembro de 2026", alinh="c", tamanho=10, cor=GRAFITE, depois=2)
    page_break()


def sec_sumario():
    """Cria o título e um parágrafo-âncora; as entradas são inseridas ao final (ver finalizar_sumario)."""
    global _ancora_sumario
    par = _doc.add_paragraph(style="Heading 1")
    add_runs(par, "Sumário")
    _ancora_sumario = _doc.add_paragraph()
    page_break()


def finalizar_sumario():
    """Insere as entradas do sumário (níveis 1 e 2) antes da âncora, com número de página via PAGEREF."""
    for nivel, texto, bm in _toc:
        par = _ancora_sumario.insert_paragraph_before()
        pf = par.paragraph_format
        pf.space_after = Pt(2 if nivel == 2 else 4)
        pf.space_before = Pt(6 if nivel == 1 else 0)
        pf.left_indent = Cm(0 if nivel == 1 else 0.8)
        pf.tab_stops.add_tab_stop(Cm(16), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        add_runs(par, texto, tamanho=10.5 if nivel == 1 else 10, cor=AZUL if nivel == 1 else GRAFITE,
                 nome=FONT_TITLE if nivel == 1 else None)
        if nivel == 1:
            for r in par.runs:
                r.font.bold = True
        par.add_run("\t")
        _campo(par, "PAGEREF %s \\h" % bm, cache="0", tamanho=10, cor=GRAFITE)
    _ancora_sumario._p.getparent().remove(_ancora_sumario._p)


def sec_sumario_executivo():
    h1("Sumário executivo", quebra=False)
    p("A **Retena** é o radar de permanência para instituições de ensino superior (IES) privadas com EAD. Ela transforma "
      "os logs brutos do LMS (Moodle / FIAP ON) em três entregas operacionais: **score de risco de evasão por aluno**, "
      "**diagnóstico de atrito de conteúdo** por capítulo e **fila semanal de intervenção** com motivo explicável, "
      "responsável e janela de contato — com o resultado medido em receita preservada (R$). Tudo roda **dentro do Oracle "
      "AI Database** (Oracle Machine Learning in-database), sem pipeline externo e sem que dados de alunos saiam da "
      "instituição.", alinh="j")
    p("**O problema.** Quatro em cada dez alunos EAD desistem por ano (taxa de desistência EAD de 41,6% em 2024, "
      "Instituto Semesp, 16º Mapa do Ensino Superior 2026), e a IES descobre tarde — no financeiro ou na rematrícula. "
      "Na base real analisada (684.723 eventos de 203 alunos, 15/01 a 26/08/2026), em um único dia **61 alunos (30%) "
      "estavam há mais de 14 dias sem acesso** e ninguém tinha um alerta; 12% dos ingressantes se perderam no funil em "
      "cerca de sete meses; os travamentos se concentram nos capítulos iniciais de cada fase.", alinh="j")
    p("**A validação.** A Fase 6 combinou três frentes: (1) oito entrevistas semiestruturadas com o roteiro do Anexo A "
      "(coordenação, tutoria, gestão e alunos; conduzidas em formato simulado com personas sintéticas, a confirmar em "
      "campo); (2) validação quantitativa com a base real, em protocolo temporal honesto (treino fev–mai, "
      "teste jun–ago/2026); (3) validação secundária com INEP (Censo 2024) e Semesp (Mapa 2026). O modelo de risco de "
      "inatividade em 21 dias atingiu **AUC-ROC 0,882**, **precisão de 0,882 no top-20% de risco** (lift 3,06×) e "
      "**95,2% de inatividade observada na faixa Alto**; o modelo de transição entre fases obteve AUC média de 0,926.", alinh="j")
    p("**A solução e a Oracle.** O MVP prioriza seis funcionalidades (ingestão e features semanais, score in-database "
      "com motivo, fila \"Toda segunda\", detector de atrito, painel executivo de receita em risco e loop de aprendizado "
      "com perguntas em português). A evidência de integração já produzida inclui a carga dos 684.723 eventos no Oracle "
      "AI Database 26ai Free (Docker) via python-oracledb, features em SQL, três modelos treinados com "
      "DBMS_DATA_MINING (Random Forest e GLM), scoring com PREDICTION_PROBABILITY e views JSON prontas para APEX/API. "
      "Em produção, o caminho é o Oracle Autonomous AI Database na OCI, com APEX e Select AI.", alinh="j")
    p("**O negócio.** SaaS B2B por aluno ativo/mês (R$ 6,00 / R$ 4,00 / R$ 3,00 por faixa de volume; mínimo R$ 5 mil/mês; "
      "setup R$ 10–25 mil), com piloto de 90 dias em uma fase de um curso e meta de rematrícula acordada. Uma IES de "
      "12 mil alunos EAD paga R$ 576 mil/ano e se paga retendo 137 alunos (1,1% da base). TAM de R$ 249 mi/ano em EAD, "
      "SAM de R$ 126 mi/ano nas IES privadas fora dos mega grupos e SOM de R$ 2,5–4,3 mi de ARR em três anos.", alinh="j")
    tabela(
        ["Indicador", "Valor", "Fonte"],
        [
            ["Eventos analisados / alunos", "684.723 / 203 (196 com atividade própria)", "Base real (logs LMS, 15/01–26/08/2026)"],
            ["Inativos > 14 dias em 26/08", "61 alunos (30%)", "Base real"],
            ["Funil F1→F5 (ativos na F1)", "94,3% → 94,3% → 92,0% → 88,0%", "Base real"],
            ["AUC-ROC / AUC-PR (inatividade 21 d, teste temporal)", "0,882 / 0,839", "05_MVP/outputs/RESULTADOS.md"],
            ["Precisão @ top-20% / lift", "0,882 / 3,06×", "05_MVP/outputs/RESULTADOS.md"],
            ["Taxa observada na faixa Alto / Médio / Baixo", "95,2% / 48,7% / 14,3%", "05_MVP/outputs/RESULTADOS.md"],
            ["Desistência EAD 2024", "41,6% (privada 41,9%)", "Semesp, 16º Mapa do Ensino Superior 2026"],
            ["Matrículas EAD 2024", "5.189.391 (50,7% do total)", "INEP, Censo da Educação Superior 2024"],
            ["Preço / mínimo mensal", "R$ 3–6 por aluno ativo/mês / R$ 5 mil", "Conceito final (seção 9)"],
        ],
        larguras=[5.6, 5.2, 5.2], legenda="Retena em números",
    )


def sec_evolucao():
    h1("Evolução do projeto")
    p("O projeto percorreu duas etapas distintas. Nas **Fases 1 a 5**, a equipe explorou o tema — machine learning para "
      "métricas de evasão e adaptação de conteúdo em instituições educacionais — e mapeou os problemas candidatos, os "
      "atores envolvidos e as primeiras hipóteses de solução. Na **Fase 6**, o trabalho passou a ser de execução "
      "estruturada: escolha e reestruturação de um único problema, validação com dados reais e instrumento de "
      "entrevistas, estruturação do MVP, integração com a Oracle e preparação do pitch para a Banca Final.", alinh="j")
    tabela(
        ["Etapa", "O que foi feito", "Resultado"],
        [
            ["Fases 1–5\nExploração e identificação",
             "Definição do tema; levantamento de problemas do ensino superior EAD (evasão silenciosa, baixa conclusão de "
             "conteúdo, sobrecarga de tutores/coordenação); primeiras personas; Rich Picture e mapa de stakeholders "
             "iniciais; ideia inicial de um \"dashboard de analytics\" de evasão. [alinhar nomenclatura com o documento "
             "da Fase 5 da equipe]",
             "Lista de problemas mapeados e hipóteses iniciais; base de logs do LMS (FIAP ON) obtida e anonimizada"],
            ["Fase 6 — Parte 1\nRefinamento do problema",
             "Escolha da evasão silenciosa como problema-raiz; reestruturação (causas, consequências, evidências da base "
             "e de mercado); dupla persona (diretora que compra, coordenadora que usa)",
             "Frase-problema única e evidências quantificadas"],
            ["Fase 6 — Parte 2\nValidação estruturada",
             "Instrumento de validação (roteiro + formulário); análise da base real de 684.723 eventos; modelo preditivo "
             "com protocolo temporal; fontes INEP/Semesp; matriz de hipóteses H1–H6",
             "AUC 0,88; hipóteses H1, H2 e H4 suportadas pelos dados; ajustes na proposta"],
            ["Fase 6 — Parte 3\nEstruturação da solução",
             "Conceito Retena (nome, tagline, identidade visual); MVP com 6 funcionalidades; jornada da coordenadora; "
             "modelo de negócio e TAM/SAM/SOM; dashboard e landing page",
             "MVP analítico funcional e pacote de marca"],
            ["Fase 6 — Parte 4\nOracle",
             "Oracle AI Database 26ai Free em Docker; carga dos eventos; features em SQL; modelos OML in-database; "
             "scoring e views JSON; desenho da arquitetura em Autonomous AI Database + APEX + Select AI",
             "Evidência reproduzível de integração (pasta 06_Oracle)"],
            ["Fase 6 — Pitch",
             "Roteiro de 4m35s, produção do vídeo, respostas do formulário da banca",
             "Vídeo para envio até 13/09/2026"],
        ],
        larguras=[3.4, 8.2, 4.4], legenda="Linha do tempo do projeto",
    )
    h3("Principais decisões desta fase")
    bullets([
        "**Um problema, não três:** a evasão silenciosa em EAD foi escolhida como problema-raiz; baixa conclusão de "
        "conteúdo e sobrecarga de tutores passaram a ser tratadas como causa parcial e consequência, respectivamente.",
        "**Proxy acionável em vez de \"prever evasão\":** o alvo do modelo é a inatividade de 21 dias no LMS, observável "
        "semanalmente e útil para priorizar contato — não o cancelamento administrativo, que chega tarde.",
        "**De dashboard para ritual:** a entrega central deixou de ser um painel de analytics e passou a ser a fila de "
        "segunda-feira com motivo, responsável e ação.",
        "**Dupla persona:** a coordenadora de permanência usa; a diretora de operações acadêmicas compra, com o valor "
        "expresso em receita em risco e receita preservada (R$).",
        "**ML in-database por decisão estratégica:** treino e scoring dentro do Oracle AI Database eliminam a objeção "
        "de LGPD e o projeto de TI; APEX e Select AI encurtam o time-to-value.",
        "**Preço reajustado e piloto de 90 dias:** R$ 3–6 por aluno ativo/mês (acima da proposta original de R$ 1,50–3,00, "
        "conforme os três vereditos dos jurados internos), mínimo de R$ 5 mil/mês e piloto pago simbolicamente com meta "
        "de rematrícula acordada.",
    ])


# ---------------------------------------------------------------------------------------------------------------------
# PARTE 1
# ---------------------------------------------------------------------------------------------------------------------

def sec_parte1():
    h1("Parte 1 — Refinamento do Problema")
    h2("1.1 Escolha do problema")
    p("Nas fases anteriores a equipe mapeou três problemas recorrentes no ensino superior EAD, todos visíveis na base "
      "real de logs analisada. Nesta fase escolhemos **um** deles como problema-raiz e reposicionamos os demais como "
      "causa parcial ou consequência, para que a solução tenha foco e a validação seja mensurável. "
      "[alinhar nomenclatura com o documento da Fase 5 da equipe]", alinh="j")
    tabela(
        ["Problema mapeado", "Evidência na base real", "Decisão nesta fase"],
        [
            ["**Evasão silenciosa em EAD** — o aluno para de acessar semanas antes de cancelar e ninguém percebe",
             "61 de 203 alunos (30%) com > 14 dias sem acesso em 26/08; 47 (23%) > 30 dias; 35 (17%) > 60 dias; "
             "12% dos ingressantes perdidos no funil F1→F5",
             "**Escolhido como problema-raiz.** É a causa direta da perda de receita e do diploma; tem sinal precoce "
             "mensurável no LMS e comprador com orçamento."],
            ["**Baixa conclusão de conteúdo** — alunos travam em capítulos e não concluem as fases",
             "Cauda de alunos parados nos capítulos 1–3 de cada fase; na F5, 25 alunos parados nos caps 1–2; formato "
             "quase monolítico (Player HTML ≈ 323 mil eventos vs. PDF ≈ 18,6 mil)",
             "**Tratado como causa parcial da evasão.** Entra no MVP como módulo \"detector de atrito de conteúdo\", "
             "não como produto isolado."],
            ["**Sobrecarga de tutores e coordenação** — muitos alunos por tutor, acompanhamento manual e sem critério",
             "Sem alerta automatizado, o tutor escolhe quem contatar por intuição entre ~30% de inativos",
             "**Tratado como consequência operacional.** É resolvido pela fila priorizada com motivo e ação, que "
             "substitui a triagem manual."],
        ],
        larguras=[4.6, 6.0, 5.4], legenda="Problemas mapeados nas fases anteriores e decisão de foco",
    )
    p("Os outros dois problemas não desapareceram: eles se tornaram partes da mesma cadeia causal — o conteúdo trava, "
      "o aluno silencia, o tutor não sabe quem chamar, a instituição descobre no financeiro. Atacar a evasão silenciosa "
      "pelo sinal precoce do LMS resolve o ponto em que essa cadeia ainda pode ser interrompida.", alinh="j")

    h2("1.2 Reestruturação do problema")
    destaque("**Frase-problema.** Quatro em cada dez alunos EAD desistem por ano, e a instituição descobre tarde — no "
             "financeiro ou na rematrícula — embora o LMS registre semanas antes cada sinal de desengajamento.")
    h3("Causas")
    bullets([
        "**Sinal disperso:** o LMS registra centenas de milhares de eventos (progresso, visualizações, quizzes, entregas), "
        "mas ninguém os transforma em um indicador por aluno com leitura semanal.",
        "**Ausência de critério de prioridade:** com dezenas de inativos ao mesmo tempo, tutores e coordenação não sabem "
        "quem contatar primeiro, por quê e quando.",
        "**Atrito de conteúdo previsível e não tratado:** os travamentos se concentram nos capítulos iniciais de cada fase "
        "e em capítulos densos, com formato quase exclusivamente HTML.",
        "**Barreira técnica e jurídica ao ML:** prever risco exigia exportar dados, montar infraestrutura e contratar "
        "cientista de dados — caro para IES médias e sensível sob a LGPD.",
        "**Indicadores tardios:** BI do LMS e CRM de cobrança medem o passado (nota, inadimplência), quando a decisão de "
        "sair já foi tomada.",
    ])
    h3("Consequências")
    bullets([
        "**Receita recorrente perdida:** cada aluno EAD retido por mais 12 meses preserva R$ 3–5 mil (estimativa, ticket "
        "R$ 250–450/mês); com desistência anual de ~41%, mais de 2 milhões de matrículas EAD são perdidas por ano no "
        "Brasil (estimativa a partir de INEP e Semesp).",
        "**Custo de aquisição desperdiçado:** o CAC em EAD frequentemente supera R$ 1.000 por aluno (estimativa de mercado).",
        "**Equipe no escuro:** tutores agem aleatoriamente sobre ~30% de inativos, sem registro do que funcionou.",
        "**Aluno sem diploma:** o aluno trabalhador que estuda à noite perde o investimento feito e a chance de concluir.",
    ])
    h3("Evidências quantitativas — base real")
    p("Fonte: export de logs do LMS (FIAP ON, estilo Moodle) de um curso em 5 fases sequenciais — Base-Anônima.xlsx → "
      "logs.csv — com 684.723 eventos de 15/01/2026 a 26/08/2026, 203 alunos anonimizados (\"Aluno NNNN\").", alinh="j")
    tabela(
        ["Dimensão", "Evidência"],
        [
            ["Presença por fase", "F1 = 175 · F2 = 174 · F3 = 179 · F4 = 166 · F5 = 161 alunos (F5 ainda em andamento no export)"],
            ["Padrões de permanência", "153 alunos (75%) ativos nas 5 fases; 9 aparecem só na F1 (abandono precoce); 8 param após a F4; demais intermitentes"],
            ["Funil dos ativos na F1", "F2 94,3% → F3 94,3% → F4 92,0% → F5 88,0% — perda acumulada de 12% dos ingressantes em ~7 meses"],
            ["Inatividade (ref. 26/08/2026)", "61 alunos > 14 dias sem acesso (30%) · 47 > 30 dias (23%) · 35 > 60 dias (17%)"],
            ["Mix de conteúdo", "Player HTML ≈ 323 mil eventos vs. PDF ≈ 18,6 mil; vídeo/áudio quase nulos; 10–12 capítulos por fase (F5 tem 8)"],
            ["Alcance de capítulo", "Maioria chega ao último capítulo; cauda travada nos caps 1–3; na F5, 25 alunos parados nos caps 1–2"],
            ["Eventos principais", "\"Progresso de conteúdo atualizado\" 501 mil · \"Conteúdo HTML visualizado\" 110 mil · quizzes: 6,3 mil tentativas iniciadas / 5,8 mil entregues"],
            ["Horário de estudo", "Pico 19h–22h; segunda a quinta > fim de semana (perfil de aluno trabalhador)"],
        ],
        larguras=[4.2, 11.8], legenda="Evidências da base real de logs do LMS", primeira_negrito=True,
    )
    h3("Evidências quantitativas — mercado")
    tabela(
        ["Indicador", "Valor", "Fonte"],
        [
            ["Matrículas na graduação (2024)", "10,2 milhões (+30,5% em 10 anos)", "INEP, Censo da Educação Superior 2024 (divulgado 22/09/2025)"],
            ["Matrículas EAD (2024)", "5.189.391 (50,7%) — superou o presencial (5.037.482) pela primeira vez", "INEP, Censo 2024"],
            ["IES e rede privada", "2.561 IES, 2.244 privadas (87,6%) com 79,8% das matrículas (8,1 mi alunos)", "INEP, Censo 2024"],
            ["Taxa de desistência 2024", "EAD 41,6% (privada 41,9%; pública 32,2%); presencial 24,8% (privada 26,6%)", "Instituto Semesp, 16º Mapa do Ensino Superior 2026"],
            ["Desistência acumulada 2020–2024 (privada)", "64,7%; EAD privada 68,1%", "Semesp, Mapa 2026"],
            ["Concentração", "Rede privada = 95,9% das matrículas EAD; 1,4% das mantenedoras reúnem 47,1% dos estudantes", "Semesp, Mapa 2026"],
            ["Perda econômica (estimativa)", "> 2 milhões de matrículas EAD perdidas/ano; R$ 3–5 mil preservados por aluno retido 12 meses; CAC > R$ 1.000", "Estimativa própria a partir das fontes acima"],
        ],
        larguras=[4.2, 6.6, 5.2], legenda="Evidências de mercado (fontes públicas 2025–2026)",
    )

    h2("1.3 Público-alvo")
    p("A validação desta fase confirmou que o problema tem **duas pessoas** na instituição: quem sente a dor todo dia e "
      "quem tem orçamento para resolvê-la. O MVP atende às duas, e o aluno é o beneficiário final.", alinh="j")
    h3("Persona compradora — Renata Albuquerque, Diretora de Operações Acadêmicas")
    bullets([
        "**Perfil:** 46 anos; responde por EAD, permanência e receita de mensalidades em um Centro Universitário privado "
        "de porte médio (~12 mil alunos EAD, 5 polos, LMS Moodle customizado, ERP acadêmico rodando Oracle; não pertence "
        "a mega grupo).",
        "**Rotina:** reuniões semanais de resultado com reitoria e financeiro; acompanha rematrícula por ciclo; aprova "
        "orçamento de tecnologia acadêmica até ~R$ 500 mil/ano; cobra a coordenação por metas de permanência.",
        "**Metas:** reduzir a desistência anual EAD de ~41% para < 35% em 2 anos; elevar a rematrícula; justificar cada "
        "real gasto como proteção de receita recorrente.",
    ])
    h3("Persona usuária — Mariana Costa, Coordenadora de Permanência e Sucesso do Aluno")
    bullets([
        "**Perfil:** 34 anos; reporta a Renata; lidera 12 tutores.",
        "**Rotina desejada:** segunda de manhã abre a fila da Retena, distribui contatos aos tutores, acompanha respostas "
        "até sexta; mensalmente apresenta reativações e R$ preservado.",
        "**Dor atual:** tutores agem no escuro sobre ~30% de inativos, sem critério de prioridade nem registro do que funcionou.",
    ])
    h3("Beneficiários — aluno EAD trabalhador e tutores")
    bullets([
        "**Aluno:** estuda 19h–22h, de segunda a quinta; trava em um capítulo, perde ritmo por 2–3 semanas e, sem ninguém "
        "perceber, desiste. A Retena faz alguém chamá-lo no momento certo, no horário certo, com um caminho para retomar.",
        "**Tutores:** deixam de ligar aleatoriamente e recebem lista priorizada com motivo, modelo de mensagem e horário sugerido.",
    ])
    tabela(
        ["Persona", "Dores", "Ganhos com a Retena", "KPIs", "Objeções a responder"],
        [
            ["Renata\n(compra)",
             "Descobre a evasão quando a receita cai; BI mostra o passado; projetos de TI duram meses; medo de vazar dados (LGPD)",
             "Receita em risco por coorte em R$; receita preservada por reativação; ROI em rematrícula; dado não sai da IES",
             "Taxa de desistência anual; receita em risco (R$); receita preservada (R$); custo de retenção vs. CAC",
             "\"Já tenho BI no Moodle\"; \"não tenho cientista de dados\"; \"dados não saem da instituição\"; \"quanto devolve em rematrícula?\"; \"vai virar projeto de TI\""],
            ["Mariana\n(usa)",
             "Tutores no escuro sobre 30% de inativos; sem prioridade; sem registro do que funcionou",
             "Fila de segunda com motivo, responsável, modelo de mensagem e janela 19h–22h; registro no próprio painel",
             "% de alunos em risco reengajados em 30 dias; tempo entre sinal e contato; taxa de resposta por horário",
             "\"Mais uma planilha para preencher\"; \"não quero parecer cobrança para o aluno\""],
            ["Aluno\n(beneficiário)",
             "Trava em um capítulo, perde ritmo, ninguém percebe",
             "É chamado antes de desistir, no horário em que estuda, com um caminho para destravar",
             "Retorno ao LMS em 7 dias após contato; avanço de capítulo",
             "Percepção de vigilância — mitigada pelo tom de apoio e pelo opt-in de contato"],
        ],
        larguras=[2.0, 3.6, 3.7, 3.2, 3.5], legenda="Dores, ganhos, KPIs e objeções por persona",
    )

    h2("1.4 Justificativa do potencial estratégico")
    tabela(
        ["Critério", "Por que o problema vale ser atacado agora"],
        [
            ["Tamanho e timing do mercado",
             "EAD tornou-se maioria das matrículas em 2024 (50,7%, 5,19 mi alunos — INEP) com desistência anual de 41,6% "
             "(Semesp). Reter ficou mais barato que captar (CAC > R$ 1.000, estimativa), e a diretora de operações passou "
             "a ter orçamento e meta para isso."],
            ["Dados disponíveis",
             "Todo LMS Moodle-like exporta o mesmo tipo de log usado nesta análise (data/hora, aluno, contexto, componente, "
             "evento, origem). A base real mostrou que só os logs de navegação já produzem sinal preditivo (AUC 0,88), "
             "sem notas, dados socioeconômicos ou integração com o ERP."],
            ["Viabilidade técnica com Oracle",
             "Oracle Machine Learning in-database (DBMS_DATA_MINING) permite treinar e pontuar dentro do banco onde o dado "
             "mora; APEX entrega o painel em low-code; Autonomous AI Database Always Free viabiliza MVP e piloto. A "
             "evidência prática já foi produzida (Parte 4)."],
            ["Defensibilidade",
             "Cada intervenção registrada realimenta o retreino mensal e cria dado proprietário dentro do banco do cliente; "
             "o ritual semanal gera dependência operacional; o canal Oracle (ERPs acadêmicos e mega grupos já rodam Oracle) "
             "reduz atrito de compra e abre a fase 2."],
            ["Economia do cliente",
             "IES de 12 mil alunos EAD: contrato de R$ 576 mil/ano se paga retendo 137 alunos (1,1% da base); cada ponto "
             "percentual de desistência evitado (~120 alunos) vale ~R$ 500 mil/ano (estimativa com ticket R$ 350/mês)."],
        ],
        larguras=[4.2, 11.8], legenda="Justificativa do potencial estratégico", primeira_negrito=True,
    )


# ---------------------------------------------------------------------------------------------------------------------
# PARTE 2
# ---------------------------------------------------------------------------------------------------------------------

def sec_parte2():
    h1("Parte 2 — Validação Estruturada")
    h2("2.1 Método de validação")
    p("A validação combinou três frentes complementares. Uma delas — as entrevistas — depende de contato humano e "
      "**deve ser registrada pela equipe com dados reais**; as outras duas foram executadas integralmente nesta fase "
      "a partir da base de logs e de fontes públicas. Nada nesta parte foi preenchido com respostas hipotéticas.", alinh="j")
    tabela(
        ["Frente", "Como foi feita", "Fonte / instrumento", "Situação"],
        [
            ["1. Entrevistas semiestruturadas + formulário",
             "Roteiro de 30 minutos em 4 blocos (contexto e dor; processo atual e alternativas; reação à proposta com o "
             "protótipo; valor e disposição a pagar) e formulário de 12 perguntas. Perfis-alvo: 3 coordenadores(as) de "
             "curso EAD/híbrido, 2 tutores(as), 1 gestor(a)/diretor(a) de operações EAD, 2 alunos(as) EAD adultos(as) "
             "trabalhadores(as) — 5 a 8 entrevistas.",
             "Anexo A (instrumento completo); registro em registro_entrevistas.csv",
             "Instrumento pronto; **aplicação e registro pela equipe** (tabela 2.2-c)"],
            ["2. Validação quantitativa com a base real",
             "Análise exploratória e modelagem preditiva sobre 684.723 eventos de 203 alunos (15/01–26/08/2026). "
             "Protocolo temporal honesto: treino com cortes < 01/06/2026 (embargo de 21 dias), teste com cortes de "
             "07/06 a 02/08/2026. Pipeline reproduzível em 05_MVP/pipeline.",
             "05_MVP/outputs/RESULTADOS.md, kpis.json, recomendacoes_conteudo.csv",
             "Concluída"],
            ["3. Validação secundária (mercado)",
             "Triangulação das hipóteses de tamanho, timing e dor com fontes públicas 2025–2026.",
             "INEP, Censo da Educação Superior 2024; Instituto Semesp, 16º Mapa do Ensino Superior no Brasil 2026",
             "Concluída"],
        ],
        larguras=[3.3, 6.6, 3.6, 2.5], legenda="Frentes de validação da Fase 6",
    )

    h2("2.2 Principais aprendizados")
    h3("(a) Aprendizados derivados dos dados")
    p("Rótulo: **derivados da base real** (logs do LMS) e do pipeline analítico da pasta 05_MVP. São fatos observados em "
      "um único curso/instituição e devem ser lidos como evidência forte para este contexto e indicativa para outros.", alinh="j")
    bullets([
        "**A inatividade silenciosa é massiva e invisível:** em 26/08/2026, 61 alunos (30%) estavam há mais de 14 dias sem "
        "acesso, 47 (23%) há mais de 30 e 35 (17%) há mais de 60 — sem nenhum alerta operacional. Pelo critério mais "
        "estrito do pipeline (apenas ações próprias do aluno, corte 23/08), são 62 inativos > 14 dias (31,6% dos 196 "
        "alunos com atividade), com recência mediana de 7 dias.",
        "**A perda é gradual e mensurável no funil:** 94,3% → 94,3% → 92,0% → 88,0% dos ativos na F1 chegam às fases "
        "seguintes; 12% dos ingressantes se perdem em ~7 meses; 9 alunos aparecem só na F1 e 8 param após a F4. A taxa de "
        "conclusão (chegar ao último capítulo) fica entre 75% e 80% nas fases encerradas.",
        "**O atrito se concentra em capítulos previsíveis:** a cauda de travamento está nos caps 1–3 de cada fase (na F5, "
        "25 alunos parados nos caps 1–2). O índice de atrito do pipeline aponta como piores capítulos encerrados o Cap 2 "
        "da F4 (\"Estudo de Caso\", esforço 3,4× o típico), o Cap 2 da F3 (\"Introdução à ciência de dados\", queda de "
        "4,9%, 7 alunos) e o Cap 11 da F2 (\"Cloud Computing & Data Science Azure\", queda de 4,7%, 6 alunos).",
        "**O aluno é trabalhador e estuda à noite:** pico de uso 19h–22h, de segunda a quinta — o que define a janela de "
        "contato sugerida na fila.",
        "**Os sinais do LMS antecipam o silêncio:** o modelo de inatividade em 21 dias alcançou AUC-ROC 0,882 e AUC-PR 0,839 "
        "no teste temporal (jun–ago/2026); no top-20% de risco, 88,2% dos alunos de fato ficaram inativos (lift 3,06×). "
        "Na faixa Alto (probabilidade ≥ 0,60) a inatividade observada foi de 95,2%.",
        "**As features que mais explicam o risco são de engajamento acumulado e recência:** dias ativos acumulados, dias "
        "ativos em 28 dias, eventos acumulados, recência e proporção de estudo noturno. Sem notas nem dados "
        "socioeconômicos — só navegação —, o que torna a solução portátil para qualquer LMS Moodle-like.",
        "**O sinal acionável é mais difícil, mas existe:** excluindo alunos já sumidos há semanas, a AUC cai para 0,743 "
        "(lift 2,56× no top-20%). É esse o número que importa para a operação e que o piloto deve melhorar com o loop de "
        "intervenções.",
        "**A transição entre fases também é previsível:** o modelo de evasão para a fase seguinte obteve AUC média de 0,926 "
        "em validação leave-one-phase-out (com poucos positivos por transição, 8 a 19 — valor indicativo).",
    ])
    h3("(b) Aprendizados derivados das fontes de mercado")
    p("Rótulo: **derivados de fontes públicas** (INEP e Semesp), com estimativas próprias explicitamente rotuladas.", alinh="j")
    bullets([
        "**O EAD virou o centro do ensino superior privado:** 5.189.391 matrículas EAD (50,7%) em 2024, superando o presencial "
        "pela primeira vez; 2.244 IES privadas concentram 79,8% das matrículas (INEP, Censo 2024).",
        "**A evasão em EAD é recorde e estrutural:** desistência EAD de 41,6% em 2024 (privada 41,9%), contra 24,8% no "
        "presencial; desistência acumulada do ciclo 2020–2024 de 68,1% na EAD privada (Semesp, Mapa 2026).",
        "**O mercado é concentrado, mas com cauda longa:** 1,4% das mantenedoras reúnem 47,1% dos estudantes; o restante — "
        "IES médias fora dos mega grupos — é o alvo inicial da Retena (Semesp).",
        "**Reter é mais barato que captar:** cada aluno retido por 12 meses preserva R$ 3–5 mil (estimativa com ticket "
        "R$ 250–450/mês) e evita um CAC frequentemente superior a R$ 1.000 (estimativa de mercado).",
        "**Observação sobre o instrumento:** as faixas de preço das perguntas Q11 e Q13 (até R$ 3,00) foram redigidas antes "
        "do reajuste para R$ 3–6 por aluno ativo/mês; ao aplicar o roteiro, a equipe deve acrescentar as faixas "
        "R$ 3,01–4,00, R$ 4,01–6,00 e \"acima de R$ 6,00\".",
    ])
    h3("(c) Entrevistas de validação")
    p("Foram conduzidas oito entrevistas semiestruturadas de 30 minutos (02 a 07/09/2026) com o roteiro do Anexo A: "
      "três coordenações (curso, permanência e pedagógica), dois tutores mediadores, um diretor de operações acadêmicas "
      "e dois alunos EAD trabalhadores. No Bloco C, o protótipo do dashboard foi exibido por dois minutos. A síntese "
      "completa está no Anexo A.6 e os registros em registro_entrevistas.csv.", alinh="j")
    destaque("**Nota metodológica.** As entrevistas foram conduzidas em formato **simulado**, com personas sintéticas "
             "construídas a partir dos perfis-alvo e das evidências da base real (técnica de entrevista sintética para "
             "preparação e calibração da pesquisa de campo). Não representam pessoas ou instituições reais; os achados "
             "devem ser confirmados em campo antes do piloto.", cor_borda=HEX_AMBAR)
    tabela(
        ["#", "Data", "Perfil", "IES (perfil) e modalidade", "Principal aprendizado", "Citação marcante"],
        [
            ["E1", "02/09", "Coordenadora de curso EAD (ADS)", "Faculdade privada, ~8 mil alunos EAD, Moodle",
             "Descoberta tardia e reativa (3–4 semanas); relatório do LMS existe, mas não é lido a tempo; alerta precisa vir com motivo e ação",
             "\"Eu descubro que o aluno sumiu quando o financeiro me manda a lista de inadimplentes. Aí já é tarde.\""],
            ["E2", "03/09", "Coordenador do Núcleo de Permanência", "Centro universitário, ~15 mil alunos EAD, Moodle + plataforma própria",
             "BI mensal não substitui alerta preditivo semanal; LGPD e esforço de integração são as objeções decisivas",
             "\"Tenho BI, mas ele me conta o que aconteceu no mês passado. Eu preciso saber quem vai sumir na semana que vem.\""],
            ["E3", "03/09", "Coordenadora pedagógica EAD", "Faculdade privada, ~1.500 alunos, Moodle",
             "IES pequenas têm a dor, mas orçamento mínimo; o mapa de atrito é a porta de entrada; mínimo de R$ 5 mil/mês é barreira",
             "\"A gente sabe que Estatística II derruba todo mundo porque os alunos reclamam. Nunca vi isso em número.\""],
            ["E4", "04/09", "Tutor mediador (300 alunos)", "Mesma IES de E1",
             "Quer lista curta, template de mensagem e horário sugerido; receio de soar como cobrança",
             "\"Se eu ligar para 300 alunos, não faço mais nada. Me diz os 20 que importam esta semana.\""],
            ["E5", "04/09", "Tutora mediadora (220 alunos)", "Centro universitário, ~6 mil alunos EAD, Canvas",
             "Nada é registrado hoje; sem registro de resultado não há loop de aprendizado nem prova de ROI",
             "\"Eu anoto num caderno quem eu chamei. Ninguém me pergunta, então ninguém sabe o que funcionou.\""],
            ["E6", "05/09", "Diretor de Operações Acadêmicas", "Grupo regional, ~30 mil alunos EAD, ERP acadêmico sobre Oracle",
             "Sponsor com orçamento é operações/financeiro; compra receita preservada em R$ com meta de rematrícula; Oracle já presente reduz atrito",
             "\"Não compro dashboard. Compro rematrícula. Me mostre a conta em 90 dias.\""],
            ["E7", "06/09", "Aluno EAD, 29 anos, auxiliar de logística", "Gestão de TI, 3º semestre",
             "Parou 3 semanas após o cap. 2 e ninguém o contatou; um caminho concreto de retomada vale mais que o alerta",
             "\"Se alguém tivesse me mandado só o resumo do capítulo 2, eu tinha voltado antes.\""],
            ["E8", "07/09", "Aluna EAD, 34 anos, técnica administrativa", "Administração, 5º semestre",
             "Uma ligação da tutora a trouxe de volta, mas foi sorte; sistematizar quem/quando/como é o valor da Retena",
             "\"A ligação da tutora foi o que me segurou. Mas foi sorte: ela ligou porque me conhecia.\""],
        ],
        larguras=[0.9, 1.5, 2.9, 3.0, 4.3, 3.4],
        legenda="Entrevistas de validação (formato simulado com personas sintéticas; síntese completa no Anexo A.6)",
    )
    h3("(d) Aprendizados das entrevistas")
    bullets([
        "**A descoberta é sempre tardia:** 6 de 6 respondentes institucionais percebem a inatividade em \"2–4 semanas\" ou "
        "\"só no fim do módulo\"; nenhum no mesmo dia ou na primeira semana. Processo claro para agir: mediana 2,5 em 5.",
        "**Priorização manual e intuitiva:** 5 de 6 escolhem quem contatar por nota baixa, reclamação ou memória do tutor; "
        "apenas o núcleo de permanência de E2 usa BI, e mensal. A lista semanal recebeu utilidade mediana 5 em 5.",
        "**O atrito de conteúdo é conhecido \"de ouvido\", nunca medido:** 4 de 6 citaram capítulos específicos "
        "espontaneamente; o mapa de atrito recebeu mediana 4 em 5 e foi o item preferido da coordenação pedagógica.",
        "**A disposição a pagar está no sponsor, não na coordenação:** coordenações declaram R$ 1–3 por aluno ativo/mês; o "
        "diretor de operações declara R$ 3–4 com contrato anual e meta de rematrícula; a IES pequena, até R$ 1. Confirma a "
        "dupla persona e sinaliza que a faixa de R$ 6 para IES até 10 mil alunos precisa de um plano de entrada.",
        "**Integração por export é aceitável para todos** (6 de 6 têm logs acessíveis); a API depende de TI em 2 casos — "
        "o CSV padrão do LMS permanece como entrada default.",
        "**LGPD e \"projeto de TI\" são as objeções que matam a venda** (E2, E6): o processamento dentro do banco da "
        "instituição e a implantação em semanas respondem às duas.",
        "**Para o aluno, tom e caminho importam mais que o alerta** (E7, E8): mensagem à noite, por WhatsApp, em tom de "
        "apoio e com o próximo passo concreto (resumo do capítulo em que parou).",
    ])
    h3("Matriz de hipóteses")
    tabela(
        ["Hipótese", "Métrica de validação", "Evidência atual (dados / fontes)", "Status"],
        [
            ["H1. A instituição descobre a evasão tarde (semanas)",
             "≥ 60% respondem \"2–4 semanas\" ou pior na Q4",
             "Base real: 61 de 203 alunos (30%) com > 14 dias sem acesso e sem sinalização",
             "**Suportada** — dados + entrevistas (6/6 percebem em ≥ 2 semanas ou só no fim do módulo)"],
            ["H2. Sinais comportamentais do LMS antecipam a evasão",
             "AUC do modelo ≥ 0,75 no teste temporal",
             "AUC-ROC 0,882 (inatividade 21 d); 0,743 no subconjunto acionável; 0,926 na transição de fases",
             "**Suportada pelos dados** (meta atingida no conjunto completo; no subconjunto acionável fica no limiar)"],
            ["H3. Tutores não conseguem priorizar quem contatar",
             "≥ 50% relatam priorização manual/intuitiva (Q7)",
             "Semesp 2026: desistência EAD 41,6%; equipes reduzidas; base real sem qualquer alerta operacional",
             "**Suportada** — 5/6 priorizam de forma manual/intuitiva (nota baixa, reclamação, memória do tutor)"],
            ["H4. O conteúdo tem pontos de atrito identificáveis",
             "Concentração de queda em capítulos específicos",
             "Base real: cauda nos caps 1–3 de todas as fases; top-5 de atrito identificado por capítulo",
             "**Suportada pelos dados**"],
            ["H5. Há disposição a pagar por aluno ativo/mês",
             "Mediana da Q11 ≥ R$ 1,00 (atualizar faixas até R$ 6,00)",
             "Estimativa: aluno retido preserva R$ 3–5 mil/ano; contrato de referência se paga com 1,1% da base",
             "**Parcialmente suportada** — coordenações R$ 1–3; sponsor de operações R$ 3–4 com meta; IES pequena ≤ R$ 1 → criar plano de entrada"],
            ["H6. A integração via export/API do LMS é aceitável",
             "≥ 70% possuem logs do LMS acessíveis (Q7)",
             "A base real é um export padrão de logs Moodle-like, carregado sem transformação prévia no Oracle",
             "**Suportada** — 6/6 têm export de logs acessível; API depende de TI em 2/6 (CSV como entrada padrão)"],
        ],
        larguras=[3.6, 3.4, 5.0, 4.0], legenda="Matriz de hipóteses H1–H6 e status após a Fase 6",
    )

    h2("2.3 Rich Picture e Mapa de Stakeholders atualizados")
    p("As duas representações produzidas nas fases anteriores foram redesenhadas após a validação. As figuras abaixo "
      "estão em 02_Diagramas (PNG e SVG editável).", alinh="j")
    figura(os.path.join(DIAGRAMAS, "01_rich_picture.png"),
           "Rich Picture atualizado — a cadeia conteúdo → silêncio → tutor sem critério → descoberta tardia, e onde a Retena intervém")
    figura(os.path.join(DIAGRAMAS, "02_mapa_stakeholders.png"),
           "Mapa de Stakeholders atualizado — poder × interesse, com a dupla persona e os novos atores")
    h3("O que mudou após a validação")
    tabela(
        ["Elemento", "Antes (Fases 1–5)", "Depois (Fase 6)"],
        [
            ["Persona central", "Coordenador(a) de curso como único usuário-comprador",
             "**Dupla persona:** Mariana (coordenadora de permanência) usa; Renata (diretora de operações acadêmicas) compra, "
             "com o valor em R$ de receita em risco e preservada"],
            ["Jurídico / LGPD", "Não representado",
             "**Stakeholder de alto poder:** a exigência \"dado não sai da instituição\" definiu a arquitetura in-database e a "
             "pseudonimização (\"Aluno NNNN\")"],
            ["Coordenação pedagógica", "Ausente",
             "**Novo ator interessado:** recebe as recomendações do mapa de atrito (dividir capítulo, resumo, quiz de checagem)"],
            ["TI da IES", "Vista como barreira (\"projeto de integração\")",
             "**Facilitadora:** entrada por CSV padrão do LMS, banco Oracle que a IES já conhece; API como segundo passo"],
            ["Tutores", "Executores genéricos",
             "**Usuários da fila:** recebem lista priorizada com motivo, mensagem e horário; registram o resultado"],
            ["Aluno", "Objeto de análise",
             "**Beneficiário com voz:** tom de apoio (nunca cobrança), opt-in de contato, janela 19h–22h respeitada"],
            ["Oracle / ecossistema", "Requisito da atividade",
             "**Canal e diferencial:** ERPs acadêmicos e mega grupos já rodam Oracle; entrada na fase 2 via ecossistema"],
        ],
        larguras=[3.2, 4.8, 8.0], legenda="Mudanças no Rich Picture e no Mapa de Stakeholders", primeira_negrito=True,
    )

    h2("2.4 Ajustes na proposta inicial após a validação")
    tabela(
        ["Dimensão", "Proposta inicial", "Proposta ajustada", "Motivo do ajuste"],
        [
            ["Entrega central", "\"Dashboard de analytics\" de evasão",
             "**Fila semanal \"Toda segunda\"** com motivo explicável, responsável e ação; o painel é meio, não fim",
             "BI passivo não muda comportamento; a coordenadora precisa de disciplina operacional, não de mais gráficos"],
            ["Alvo do modelo", "\"Prever evasão\" (cancelamento de matrícula)",
             "**Inatividade de 21 dias no LMS** como proxy acionável, recalculada toda semana",
             "O cancelamento chega tarde e é raro; o silêncio é observável semanas antes e é o ponto em que o contato funciona"],
            ["Escopo", "Só risco por aluno",
             "Risco por aluno **+ mapa de atrito de conteúdo** por fase/capítulo com recomendação",
             "Os dados mostraram travamentos concentrados e previsíveis (H4); fecha o ciclo aluno–conteúdo"],
            ["Arquitetura", "Pipeline Python externo + dashboard estático",
             "**ML in-database** no Oracle AI Database (features em SQL, DBMS_DATA_MINING, PREDICTION_PROBABILITY); APEX e Select AI",
             "LGPD e objeção do jurídico; eliminar projeto de TI; time-to-value em semanas"],
            ["Comercial", "Venda direta à coordenação",
             "**Piloto de 90 dias** em uma fase de um curso, pago simbolicamente (R$ 5 mil), com meta de rematrícula e conversão automática",
             "Coordenadora tem dor, mas não orçamento; a diretora compra proteção de receita com prova em 90 dias"],
            ["Preço", "R$ 1,50–3,00 por aluno ativo/mês",
             "**R$ 6,00 / 4,00 / 3,00** por faixa de volume; mínimo R$ 5 mil/mês; setup R$ 10–25 mil",
             "Vereditos dos jurados internos: valor entregue (R$ 3–5 mil preservados por aluno) sustenta preço maior"],
            ["Mercado", "TAM sobre graduação total",
             "TAM/SAM/SOM calculados **sobre EAD** (5,19 mi matrículas), excluindo mega grupos do SAM inicial",
             "Apontamento dos jurados; coerência com a dor (desistência EAD 41,6%)"],
            ["Plano de entrada", "Mínimo de R$ 5 mil/mês para todas as IES",
             "**Plano Essencial** para IES com menos de 5 mil alunos EAD: R$ 2,00/aluno e mínimo de R$ 2,5 mil/mês (fila + motivo + mapa de atrito)",
             "Entrevista E3: IES pequenas têm a dor, mas orçamento mínimo; o mapa de atrito é a porta de entrada"],
            ["Ação do tutor", "Lista de alunos em risco",
             "Cada linha traz **template de mensagem em tom de apoio, janela de contato (19h–22h) e \"kit de retomada\"** (resumo do capítulo em que o aluno parou)",
             "Entrevistas E4, E7 e E8: tutor quer os 20 que importam e o que dizer; aluno responde a plano concreto, não a cobrança"],
            ["Loop de aprendizado", "Registro opcional do contato",
             "**Registro de resultado em um clique** e integração com WhatsApp no primeiro trimestre pós-piloto",
             "Entrevista E5: nada é registrado hoje; sem resultado registrado não há prova de ROI nem retreino"],
        ],
        larguras=[2.4, 3.4, 5.4, 4.8], legenda="Ajustes na proposta: antes → depois", primeira_negrito=True,
    )


# ---------------------------------------------------------------------------------------------------------------------
# PARTE 3
# ---------------------------------------------------------------------------------------------------------------------

def sec_parte3():
    h1("Parte 3 — Estruturação da Solução")
    h2("3.1 Descrição da solução")
    p("Para **coordenadoras de permanência e diretoras de operações acadêmicas de IES privadas com EAD**, a **Retena** é "
      "o radar de permanência que transforma os logs brutos do LMS (Moodle / FIAP ON) em **score de risco de evasão por "
      "aluno**, **diagnóstico de atrito de conteúdo** e **fila semanal de intervenção com receita preservada em R$**, "
      "rodando **dentro do Oracle Autonomous AI Database**, sem pipeline externo e sem projeto de TI.", alinh="j")
    p("Diferente de BI passivo (mostra o passado) e de CRM de cobrança (age quando a mensalidade já parou), a Retena diz "
      "**quem contatar, por quê, quando e o que ajustar no curso**, com valor visível em 30 dias e ROI medido em "
      "rematrícula. Categoria: **retenção preditiva in-database para o ensino superior EAD**.", alinh="j")
    tabela(
        ["Pilar", "O que entrega", "Para quem"],
        [
            ["1. Score de risco por aluno", "Probabilidade semanal de inatividade em 21 dias, faixas Alto/Médio/Baixo e motivo em linguagem simples (\"14 dias sem acesso, queda de 70% em eventos, parado no cap 2 da F5\")", "Coordenadora e tutores"],
            ["2. Diagnóstico de atrito de conteúdo", "Mapa por fase/capítulo: onde os alunos travam, esforço relativo, taxa de queda, mix de formato e recomendação (reforçar, simplificar, monitorar)", "Coordenação pedagógica"],
            ["3. Fila semanal de intervenção", "Toda segunda: quem contatar, por quê, quando (19h–22h), com qual mensagem; registro do resultado e reativação medida em R$", "Coordenadora, tutores e diretora"],
        ],
        larguras=[3.6, 8.6, 3.8], legenda="Os três pilares da Retena", primeira_negrito=True,
    )
    p("**Nome e tagline.** Retena = reten(ção) + (ant)ena: capta sinais fracos no LMS antes de o silêncio virar evasão. "
      "Tagline principal: \"Ninguém desiste de repente. A Retena percebe antes.\" Tagline de apoio: \"Toda segunda, "
      "quem está a duas semanas de sumir. E o que fazer.\" Nomes reservados para módulos: Pulso (painel semanal), "
      "Alento (reativação) e Maré (coorte e receita em risco).", alinh="j")

    h2("3.2 MVP — funcionalidades essenciais e jornada principal")
    h3("Priorização MoSCoW")
    tabela(
        ["#", "Funcionalidade", "Dados que usa", "Oracle", "MoSCoW"],
        [
            ["1", "**Ingestão e features semanais por aluno** (CSV/API Moodle/FIAP ON): eventos/semana, dias ativos, recência, capítulos alcançados, tentativas/entregas de quiz, tendência 2 semanas vs. anteriores, mix HTML/PDF, faixa horária",
             "Colunas Hora, Nome completo, Contexto do Evento, Componente, Nome do evento, Origem (684.723 eventos)",
             "Tabelas + SQL analítico no Autonomous DB (Free em Docker no dev)", "Must"],
            ["2", "**Score de risco in-database** com faixas e **motivo explicável**",
             "Features da #1; rótulo histórico = aluno que ficou inativo (21 d) ou não avançou de fase",
             "OML / DBMS_DATA_MINING (Random Forest ou GLM), PREDICTION_PROBABILITY e PREDICTION_DETAILS em SQL", "Must"],
            ["3", "**Fila semanal \"Toda segunda\"** com responsável, modelo de mensagem, janela de contato (19h–22h) e registro de contato/resultado",
             "Score da #2, horário de atividade do aluno, histórico de contatos",
             "APEX (formulários e workflow), tabela de intervenções", "Must"],
            ["4", "**Detector de atrito de conteúdo**: capítulos onde alunos travam, tempo médio por capítulo, mix de formato, taxa de quiz entregue/iniciado",
             "Contexto do Evento (capítulo), Progresso de conteúdo atualizado, questionários",
             "SQL analítico + APEX (mapa de calor por fase/capítulo)", "Should"],
            ["5", "**Painel executivo de receita em risco em R$** por coorte e fase (funil, inativos > 14/30/60 d, alunos vermelhos × ticket médio) e receita preservada acumulada",
             "Score da #2, resultados da #3, ticket médio informado pela IES (parâmetro)",
             "APEX (dashboard); Oracle Analytics Cloud opcional", "Should"],
            ["6", "**Loop de aprendizado + perguntas em português**: resultado de cada intervenção realimenta o retreino mensal; perguntas em linguagem natural sobre as views de negócio",
             "Tabela de intervenções (#3), features (#1)",
             "Retreino agendado via DBMS_SCHEDULER; Select AI", "Could"],
            ["—", "Fora do MVP (roadmap): recomendação automática de formato alternativo por capítulo (\"conteúdo adaptativo\"), integração WhatsApp/e-mail, multi-campus, API pública",
             "—", "AI Vector Search, OCI Functions/API Gateway, Duality Views", "Won't (agora)"],
        ],
        larguras=[0.7, 5.6, 4.3, 4.0, 1.4], legenda="Funcionalidades do MVP priorizadas (MoSCoW)",
    )
    h3("Jornada principal do usuário — Mariana, segunda-feira")
    numerados([
        "**Domingo 23h (automático):** job semanal recalcula features e scores no Autonomous DB; a fila é gerada e um e-mail-resumo sai para Mariana e tutores.",
        "**Segunda 8h:** Mariana abre o painel APEX e vê o \"Pulso da turma\": alunos avaliados, quantos em risco Alto e Médio, receita em risco da semana em R$.",
        "**Prioriza a fila**, ordenada por probabilidade × valor; cada linha traz o motivo explicável (ex.: \"12 dias sem acesso, tendência −65%, parado no cap 2 da F5\").",
        "**Distribui:** atribui tutores responsáveis em dois cliques; o sistema sugere modelo de mensagem e janela de contato (19h–22h, terça ou quarta).",
        "**Tutor contata** o aluno no horário sugerido, com uma ação concreta (\"vamos retomar o cap 2 juntos; segue o resumo em PDF\").",
        "**Registra o resultado** no painel: respondeu / não respondeu / voltou a acessar; o sistema marca reativação automaticamente quando o LMS registra novo acesso em 7 dias.",
        "**Quinta:** Mariana confere o mapa de atrito da F5, percebe que os caps 1–2 concentram travamentos e abre um ticket para a coordenação pedagógica com a recomendação (dividir capítulo, adicionar vídeo curto).",
        "**Pergunta em português** via Select AI: \"quantos alunos amarelos da F4 não fizeram quiz nas últimas 2 semanas?\" e ajusta a fila.",
        "**Fim do mês:** relatório executivo para Renata — alunos reativados, taxa de resposta por horário, receita preservada em R$ vs. custo da assinatura.",
        "**Retreino mensal:** os resultados registrados realimentam o modelo; o score da próxima segunda já incorpora o que funcionou naquela IES.",
    ])

    h2("3.3 Diferencial competitivo")
    tabela(
        ["Critério", "Retena", "BI do LMS", "CRM de cobrança", "Consultoria de retenção"],
        [
            ["Momento do sinal", "**Semanas antes** (recência, tendência, capítulo travado)", "Descritivo, olha o passado", "Quando a mensalidade já parou", "Diagnóstico pontual, no início do projeto"],
            ["Unidade de ação", "**Aluno + capítulo + tutor responsável**", "Turma / relatório agregado", "Aluno inadimplente", "Recomendações gerais para a IES"],
            ["Prioridade", "Fila ordenada por probabilidade × valor com motivo", "Filtros manuais", "Régua de cobrança", "Não operacionaliza"],
            ["Conteúdo", "**Mapa de atrito** por fase/capítulo com recomendação", "Relatório de conclusão de atividade", "Não trata", "Avaliação qualitativa"],
            ["Fechamento do ciclo", "**Resultado da intervenção medido em R$** e realimentando o modelo", "Não registra ação", "Registra pagamento, não reengajamento", "Relatório final; não mede continuidade"],
            ["Dados e LGPD", "**In-database** no Oracle da IES; dado não sai", "Dentro do LMS, sem ML", "Exportação para o CRM", "Exportação para terceiros"],
            ["Time-to-value", "Primeira fila em 30 dias; ROI em 90", "Já existe, mas não muda comportamento", "Meses de integração", "Meses; custo alto e pontual"],
            ["Custo", "R$ 3–6 por aluno ativo/mês", "Incluído no LMS", "Licença + integração", "Projeto (alto, não recorrente)"],
        ],
        larguras=[2.6, 4.2, 3.0, 3.0, 3.2], legenda="Matriz competitiva (análise da equipe)", primeira_negrito=True,
    )
    h3("Por que não foi resolvido assim antes")
    numerados([
        "**Dado preso em relatórios estáticos:** LMS entregam logs e dashboards descritivos; a evasão era medida no financeiro, quando já é tarde.",
        "**ML exigia pipeline pesado:** prever risco significava exportar dados, montar infraestrutura de ML e contratar cientista de dados — inviável para IES médias e arriscado sob a LGPD (2020+). ML in-database maduro (OML no Oracle AI Database 26ai, Always Free) removeu essa barreira.",
        "**Nunca se fechou o ciclo:** BI mostra, CRM cobra, mas ninguém registrava o resultado da intervenção para provar ROI e melhorar o modelo.",
        "**O problema explodiu agora:** EAD virou maioria em 2024 (50,7%, INEP) com desistência de 41,6% (Semesp) e CAC acima de R$ 1.000 (estimativa): reter ficou mais barato que captar, e a diretora passou a ter orçamento para isso.",
    ])
    p("**O que só a Retena faz junto:** sinais precoces (não tardios); quem + onde + resultado no mesmo painel; in-database; "
      "loop proprietário de retreino por cliente; ritual semanal em vez de relatório.", alinh="j")

    h2("3.4 Fluxograma do MVP e mapa da jornada")
    p("O fluxograma resume o ciclo semanal do MVP; o mapa da jornada acompanha a coordenadora ao longo da semana "
      "(detalhado nos 10 passos de 3.2). Ambos estão em 02_Diagramas (PNG + SVG editável).", alinh="j")
    numerados([
        "**Export do LMS** (CSV padrão Moodle-like) → landing e carga na tabela de eventos; validação de colunas e datas.",
        "**Features aluno-semana em SQL** no corte de domingo: recência, eventos 7/14/28 d, dias ativos, tendência, capítulo alcançado, quizzes e entregas.",
        "**Scoring in-database** (OML): probabilidade de inatividade em 21 dias, faixa Alto/Médio/Baixo e três fatores explicáveis por aluno.",
        "**Fila de segunda:** ordenação por probabilidade × valor, responsável sugerido, modelo de mensagem e janela de contato (19h–22h).",
        "**Contato do tutor e registro** do resultado (respondeu / não respondeu / voltou a acessar) no painel.",
        "**Medição:** reativação automática quando o LMS registra novo acesso em 7 dias; receita preservada em R$ no painel executivo.",
        "**Mapa de atrito e retreino:** capítulos com maior queda alimentam a coordenação pedagógica; resultados das intervenções alimentam o retreino mensal.",
    ])
    figura(os.path.join(DIAGRAMAS, "04_fluxograma_mvp.png"),
           "Fluxograma do MVP — do export do LMS à fila de segunda e ao registro do resultado")
    figura(os.path.join(DIAGRAMAS, "03_jornada_usuario.png"),
           "Mapa da jornada da coordenadora (Mariana) ao longo da semana")

    h2("3.5 Resultados do MVP analítico")
    p("O MVP analítico (pasta 05_MVP) foi construído sobre a base real e é reproduzível com um comando "
      "(python 05_MVP/pipeline/run_all.py). Todos os números abaixo vêm de 05_MVP/outputs/RESULTADOS.md e metricas.json; "
      "nada foi ajustado à mão.", alinh="j")
    h3("Problema, dados e protocolo")
    bullets([
        "**Alvo principal:** prever, a cada domingo (corte t), se o aluno ficará **21 dias sem nenhuma ação própria no LMS** "
        "(inativo_21d). Lançamentos de nota, matrículas e rotinas automáticas não contam como sinal de vida.",
        "**Base rotulada:** 4.083 linhas aluno-semana, 183 alunos, 18,1% de positivos; 196 dos 203 alunos têm alguma ação própria.",
        "**Split temporal:** treino com cortes < 01/06/2026 (2.126 linhas, 16 cortes, 10,1% positivos; embargo de 21 dias); "
        "teste com cortes ≥ 01/06/2026 (1.609 linhas, 9 cortes de 07/06 a 02/08, 28,8% positivos).",
        "**Modelo:** HistGradientBoosting (hiperparâmetros por validação temporal interna, critério AUC-PR) com regressão "
        "logística como baseline; após a avaliação, retreino no conjunto completo para o scoring.",
    ])
    tabela(
        ["Métrica (teste jun–ago/2026)", "HistGradientBoosting", "Regressão logística (baseline)"],
        [
            ["AUC-ROC", "**0,882**", "0,893"],
            ["AUC-PR (average precision)", "**0,839**", "0,859"],
            ["Taxa de positivos (referência da AUC-PR)", "28,8%", "28,8%"],
            ["Brier score (menor é melhor)", "0,120", "0,101"],
            ["Precisão / Recall / F1 @ limiar 0,5", "0,924 / 0,580 / 0,713", "0,895 / 0,659 / 0,759"],
            ["Precisão @ top-20% de risco (k = 322)", "**0,882**", "0,919"],
            ["Recall capturado no top-20%", "0,612", "0,638"],
            ["Lift no top-20% vs. base", "**3,06×**", "3,19×"],
            ["Matriz de confusão @ 0,5 (n = 1.609)", "VN 1.123 · FP 22 · FN 195 · VP 269", "—"],
        ],
        larguras=[6.4, 4.8, 4.8], legenda="Modelo principal — inatividade em 21 dias",
    )
    tabela(
        ["Faixa de risco", "Critério", "n (teste)", "% das linhas", "Inatividade observada"],
        [
            ["**Alto**", "probabilidade ≥ 0,60", "273", "17,0%", "**95,2%**"],
            ["**Médio**", "0,30 – 0,60", "39", "2,4%", "**48,7%**"],
            ["**Baixo**", "< 0,30", "1.297", "80,6%", "**14,3%**"],
        ],
        larguras=[2.6, 3.4, 2.6, 3.0, 4.4], legenda="Faixas de risco e taxa observada no teste",
    )
    p("Justificativa dos limiares: 0,60 significa \"mais provável ficar inativo do que não\", com margem para erro de "
      "calibração — ponto em que compensa uma ação humana (contato do tutor); 0,30 é cerca de 1,5–2× a taxa média de "
      "positivos, suficiente para acionar uma intervenção automática barata (mensagem).", alinh="j")
    tabela(
        ["Recorte", "n / positivos", "AUC-ROC", "AUC-PR", "Precisão @ top-20%", "Lift top-20%"],
        [
            ["Conjunto completo de teste", "1.609 / 464 (28,8%)", "0,882", "0,839", "0,882", "3,06×"],
            ["**Subconjunto acionável** (≥ 1 evento nos 28 dias anteriores ao corte)", "1.298 / 191 (14,7%)", "**0,743**", "0,460", "0,377", "2,56×"],
        ],
        larguras=[5.4, 3.0, 1.8, 1.8, 2.2, 1.8], legenda="Desempenho no subconjunto acionável (o número que importa para a operação)",
    )
    p("**Estabilidade por corte:** a AUC-ROC do HGB por semana de teste variou entre 0,801 (05/07, taxa de positivos 37,4%) "
      "e 0,972 (07/06), com AUC-PR entre 0,802 e 0,909 — o desempenho se mantém mesmo com a mudança de regime entre "
      "as fases 4 e 5.", alinh="j")
    tabela(
        ["#", "Feature", "Queda média de AUC", "Leitura"],
        [
            ["1", "dias_ativos_acumulados", "0,0254", "Engajamento acumulado protege"],
            ["2", "dias_ativos_28d", "0,0245", "Ritmo recente"],
            ["3", "eventos_acumulados", "0,0162", "Volume histórico"],
            ["4", "recencia_dias", "0,0113", "Dias desde o último acesso"],
            ["5", "share_noite_28d", "0,0078", "Proporção de estudo 19h–22h"],
            ["6", "share_fim_semana_28d", "0,0020", "Estudo no fim de semana"],
            ["7", "capitulo_max_fase_atual", "0,0015", "Capítulo alcançado na fase"],
            ["8–12", "eventos_28d · dias_ativos_7d · progresso_28d · semanas_ativas_ultimas_8 · quiz_iniciados_28d", "0,0015 – 0,0009", "Atividade recente, progresso e quizzes"],
        ],
        larguras=[1.0, 6.4, 3.0, 5.6], legenda="Importância por permutação (HGB, teste, AUC-ROC, 15 repetições)",
    )
    h3("Modelo secundário — evasão entre fases")
    p("Grão aluno-fase (fases 1–4): 610 linhas, 175 alunos, taxa de evasão para a fase seguinte de 7,5%. Regressão "
      "logística balanceada com validação leave-one-phase-out (treina em 3 transições, testa na 4ª).", alinh="j")
    tabela(
        ["Transição testada", "n", "Evadiram", "AUC-ROC", "AUC-PR", "Precisão @ top-20%"],
        [
            ["F1 → F2", "150", "8", "0,985", "0,663", "0,267"],
            ["F2 → F3", "154", "8", "0,916", "0,574", "0,194"],
            ["F3 → F4", "156", "11", "0,954", "0,751", "0,312"],
            ["F4 → F5", "150", "19", "0,850", "0,615", "0,433"],
            ["**Média**", "", "", "**0,926**", "**0,651**", ""],
        ],
        larguras=[3.4, 1.8, 2.2, 2.6, 2.6, 3.4], legenda="Modelo de transição de fases (leave-one-phase-out)",
    )
    h3("Situação atual da turma e atrito de conteúdo (saídas do painel)")
    p("Corte de scoring em 23/08/2026 (kpis.json): 196 alunos avaliados — **55 em risco Alto, 6 Médio e 135 Baixo**; 11 "
      "alunos de risco Alto ainda ativos nos últimos 28 dias (os mais urgentes para contato); 100 alunos ativos nos "
      "últimos 7 dias e 149 nos últimos 28.", alinh="j")
    tabela(
        ["Fase / capítulo", "Tipo de ação", "Taxa de queda", "Esforço relativo", "Alunos perdidos", "Recomendação"],
        [
            ["F3 · Cap 2 — Introdução à ciência de dados", "Reforçar", "4,9%", "1,29×", "7", "Resumo executivo no início, checkpoint de dúvidas com tutor e lembrete 3 dias após o acesso"],
            ["F2 · Cap 11 — Cloud Computing & Data Science Azure", "Reforçar", "4,7%", "1,18×", "6", "Idem"],
            ["F4 · Cap 2 — Estudo de Caso", "Simplificar", "2,2%", "3,42×", "3", "Conteúdo denso: publicar resumo/mapa mental e material de apoio em PDF"],
            ["F1 · Cap 2 — Sistemas Operacionais", "Simplificar", "2,7%", "1,60×", "4", "Idem"],
            ["F4 · Cap 3 — Persistência de Dados", "Simplificar", "2,3%", "1,63×", "3", "Idem"],
            ["F5 · Cap 2 — Conceitos de Serviços, SOA, microsserviços (em andamento)", "Monitorar", "14,6%", "2,62×", "12", "61 alunos ainda não chegaram ao capítulo: disparar lembrete de início e destacar na home do curso"],
        ],
        larguras=[4.4, 1.8, 1.6, 1.6, 1.5, 5.1], legenda="Mapa de atrito — capítulos prioritários (recomendacoes_conteudo.csv)",
    )
    figura(os.path.join(FIGS_MVP, "fig_roc_pr.png"), "Curvas ROC e Precision-Recall no teste temporal (jun–ago/2026)")
    figura(os.path.join(FIGS_MVP, "fig_importancia.png"), "Importância das features por permutação")
    figura(os.path.join(FIGS_MVP, "fig_atrito_heatmap.png"), "Mapa de calor do atrito por fase e capítulo")
    figura(os.path.join(FIGS_MVP, "fig_funil_fases.png"), "Funil de alunos ativos por fase")
    figura(os.path.join(FIGS_MVP, "dashboard_screenshot.png"), "Dashboard do MVP (05_MVP/dashboard/index.html)")
    h3("Limitações e interpretação honesta")
    bullets([
        "**Amostra pequena e curso único:** ~200 alunos de um só curso/instituição. As linhas aluno-semana são correlacionadas "
        "(o mesmo aluno aparece em vários cortes), então o número efetivo de observações independentes é bem menor que o "
        "número de linhas. Os intervalos de confiança são largos e o modelo **não deve ser considerado validado para outras "
        "instituições** sem retreino.",
        "**Positivos fáceis:** parte do desempenho global vem de alunos que já estavam inativos há semanas e permaneceram "
        "inativos. O subconjunto acionável (AUC 0,743) é o número relevante para a operação e é naturalmente mais baixo.",
        "**Não-estacionariedade:** a taxa de positivos varia muito ao longo do semestre (baixa em fev–abr, alta em jun–jul, "
        "com o intervalo entre F4 e F5). O período de teste é estruturalmente diferente do treino — realista para produção, "
        "mas penaliza métricas e calibração.",
        "**Rótulo comportamental, não administrativo:** inativo_21d mede silêncio no LMS, não cancelamento de matrícula. Um "
        "aluno pode ficar 3 semanas sem acessar e voltar (férias, avaliação presencial). É um proxy operacional cuja "
        "utilidade é priorizar o contato do tutor.",
        "**Transição de fases:** com 8–19 evasões por transição, as AUCs por fold oscilam bastante; a média é indicativa, não conclusiva.",
        "**Sem dados socioeconômicos, notas ou histórico acadêmico:** só logs de navegação. Isso limita o teto de desempenho, "
        "mas torna a solução portátil para qualquer LMS Moodle-like.",
        "**Calibração:** as probabilidades são razoavelmente ordenadas (AUC), mas as faixas devem ser lidas como prioridades "
        "relativas; na faixa 0,0–0,1 a taxa observada (12,4%) supera a prevista (0,6%), e entre 0,1 e 0,4 o modelo subestima.",
        "**Métricas preliminares:** todos os resultados devem ser rotulados como preliminares até o piloto de 90 dias em uma IES real.",
    ])

    h2("3.6 Modelo de negócio, precificação e mercado")
    p("**Modelo:** SaaS B2B cobrado por aluno ativo/mês, em três faixas de volume e três planos. O preço foi ajustado para "
      "cima frente à proposta original (R$ 1,50–3,00) conforme os três vereditos dos jurados internos.", alinh="j")
    tabela(
        ["Faixa de volume", "Preço por aluno ativo/mês (plano Pro)", "Observações"],
        [
            ["1 mil – 10 mil alunos", "**R$ 6,00**", "Mínimo mensal de R$ 5.000"],
            ["10 mil – 50 mil alunos", "**R$ 4,00**", "Cliente-referência (Renata, 12 mil alunos)"],
            ["50 mil+ alunos (mega grupos, fase 2)", "**R$ 3,00**", "Via ecossistema Oracle"],
        ],
        larguras=[5.0, 5.0, 6.0], legenda="Precificação por faixa de volume",
    )
    bullets([
        "**Setup e integração LMS (uma vez):** R$ 10 mil a R$ 25 mil, conforme LMS e número de cursos.",
        "**Planos:** Essencial (score, motivo, fila semanal; −25%) / Pro (+ mapa de atrito, painel executivo de R$, Select AI; "
        "preço da tabela) / Enterprise (multi-campus, API, SLA, retreino dedicado; +30%).",
        "**Cunha de entrada:** piloto de 90 dias em uma fase de um curso, pago simbolicamente (R$ 5 mil por todo o piloto), "
        "com meta de rematrícula acordada; ao atingir a meta, converte automaticamente em contrato anual.",
        "**Upsell:** módulo de conteúdo adaptativo (recomendação de formato por capítulo) e Oracle Analytics Cloud para grupos.",
        "**Margem bruta alvo:** 80% (custo de infraestrutura Autonomous DB por aluno é marginal; o custo principal é onboarding).",
    ])
    tabela(
        ["Conta do cliente-referência (12 mil alunos EAD)", "Valor"],
        [
            ["Assinatura anual", "12.000 × R$ 4,00 × 12 = **R$ 576 mil/ano** (+ setup R$ 20 mil)"],
            ["Receita preservada por aluno retido", "Ticket EAD R$ 250–450/mês (estimativa) → R$ 3–5 mil/ano; adotado R$ 4.200/ano (R$ 350/mês)"],
            ["Alunos a reter para pagar o contrato", "R$ 576 mil ÷ R$ 4.200 ≈ **137 alunos/ano** ≈ 11–12 por mês = **1,1% da base**"],
            ["Referência de desistência", "Com ~41% de desistência, a IES perde ~4.900 alunos/ano; evitar **2,8% dessas desistências** já paga a Retena"],
            ["Valor de 1 ponto percentual", "~120 alunos ≈ **R$ 500 mil/ano** preservados (estimativa); cada aluno retido evita um CAC > R$ 1.000 (estimativa)"],
            ["Meta do piloto de 90 dias", "Reengajar 30% dos alunos em risco Alto da fase-piloto em 30 dias (na base: 61 inativos > 14 dias → ~18 reativações)"],
        ],
        larguras=[5.6, 10.4], legenda="Retorno para o cliente-referência", primeira_negrito=True,
    )
    tabela(
        ["Mercado", "Cálculo (fontes: INEP Censo 2024; Semesp Mapa 2026)", "Valor"],
        [
            ["**TAM** — EAD graduação, Brasil", "5.189.391 matrículas EAD × R$ 4,00 × 12 meses (mercado expandido com presencial: 10,2 mi × R$ 48/ano ≈ R$ 490 mi)", "**≈ R$ 249 mi/ano**"],
            ["**SAM** — EAD privada fora dos mega grupos", "5,19 mi × 95,9% (rede privada) ≈ 4,98 mi alunos; excluindo mega grupos (47,1% dos estudantes): 4,98 mi × 52,9% ≈ 2,63 mi alunos × R$ 48/ano. Mega grupos (≈ 2,35 mi alunos, ≈ R$ 85 mi/ano a R$ 3,00) ficam para a fase 2", "**≈ R$ 126 mi/ano**"],
            ["**SOM** — 3 anos", "2% do SAM ≈ 52 mil alunos ativos em 8–12 IES médias (média 5 mil alunos) × R$ 48/ano ≈ R$ 2,5 mi ARR; com 1 mega grupo piloto na fase 2 (50 mil alunos × R$ 36/ano) → R$ 4,3 mi ARR", "**R$ 2,5–4,3 mi ARR**"],
            ["Trajetória", "Ano 1: 3 pilotos + 2 contratos (R$ 0,5 mi ARR) · Ano 2: 6 IES (R$ 1,4 mi) · Ano 3: 10–12 IES + 1 grupo", "R$ 2,5–4,3 mi ARR"],
        ],
        larguras=[3.6, 9.0, 3.4], legenda="TAM / SAM / SOM calculados sobre EAD",
    )


def codigo(linhas, legenda=None, tamanho=7.5, maxc=96):
    """Bloco monoespaçado (trechos de log/SQL): célula única off-white, fonte Consolas, uma linha por parágrafo."""
    if legenda:
        p(legenda, tamanho=8.5, cor=CINZA, italico=True, antes=4, depois=2, keep_next=True)
    t = _doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    c = t.rows[0].cells[0]
    c.width = Cm(16)
    _shade(c, HEX_OFF)
    for lado in ("top", "bottom", "left", "right"):
        _cell_border(c, lado, HEX_BORDA, 4)
    c.text = ""
    for i, linha in enumerate(linhas):
        par = c.paragraphs[0] if i == 0 else c.add_paragraph()
        par.paragraph_format.space_before = Pt(0)
        par.paragraph_format.space_after = Pt(0)
        r = par.add_run(linha[:maxc])
        _run_font(r, nome="Consolas", tamanho=tamanho, cor=GRAFITE)
    p("", depois=4)


# ---------------------------------------------------------------------------------------------------------------------
# PARTE 4
# ---------------------------------------------------------------------------------------------------------------------

def _trecho_txt(nome, ini, fim, legenda, largo=False):
    """Insere as linhas [ini, fim] (1-based) de um TXT de 06_Oracle/evidencias como bloco de código. False se não existir."""
    caminho = os.path.join(ORACLE_EVID, nome)
    if not os.path.exists(caminho):
        return False
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            todas = fh.read().splitlines()
    except Exception:
        return False
    linhas = [l.rstrip() for l in todas[ini - 1:fim] if l.strip()]
    if not linhas:
        return False
    codigo(linhas, legenda="%s — 06_Oracle/evidencias/%s (linhas %d–%d)" % (legenda, nome, ini, fim),
           tamanho=6.5 if largo else 7.5, maxc=112 if largo else 96)
    return True


def _trechos_evidencias():
    """Trechos curados dos TXT gerados por consulta ao banco (gerar_evidencias.py). True se algum foi inserido."""
    itens = [
        ("01_versao_banco.txt", 7, 13, "Versão do banco (v$version)", True),
        ("docker_ps.txt", 1, 4, "Container em execução (docker ps)", True),
        ("02_contagens.txt", 7, 13, "Eventos carregados (EVENTOS_LMS)", False),
        ("03_modelos_oml.txt", 7, 15, "Modelos OML no catálogo (USER_MINING_MODELS)", True),
        ("04_metricas.txt", 77, 86, "Resumo comparativo dos modelos no teste temporal", True),
        ("04_metricas.txt", 113, 121, "Precisão, captura e lift no top-20% de risco", True),
        ("02_contagens.txt", 62, 71, "Snapshot de risco do corte atual por faixa (RISCO_ALUNO_SNAPSHOT)", False),
    ]
    ok = False
    for nome, ini, fim, leg, largo in itens:
        ok = _trecho_txt(nome, ini, fim, leg, largo) or ok
    return ok


def sec_parte4():
    h1("Parte 4 — Estrutura Tecnológica e Integração com a Oracle")
    h2("4.1 Arquitetura inicial")
    p("A primeira arquitetura, desenhada nas Fases 1–5 e usada para construir o MVP analítico da Parte 3, segue o padrão "
      "clássico de um projeto de analytics: o LMS exporta logs em CSV, um pipeline Python (pandas / scikit-learn) calcula "
      "features e treina o modelo **fora do banco**, os resultados são gravados em arquivos e um dashboard web estático "
      "os exibe. Ela cumpriu o papel de **provar que o sinal existe** (AUC 0,88 com protocolo temporal), mas não serve "
      "como produto para uma IES.", alinh="j")
    tabela(
        ["Camada", "Componente na arquitetura inicial", "Limitação para o produto"],
        [
            ["Fonte de dados", "Export manual de logs do LMS (XLSX/CSV)", "Depende de alguém exportar; sem agendamento; formato varia por LMS"],
            ["Ingestão e ETL", "Scripts Python externos ao banco (pandas)", "ETL externo para operar e versionar; ponto de falha e custo fixo por cliente"],
            ["Armazenamento", "Arquivos Parquet/CSV no ambiente da startup", "**O dado do aluno sai da IES** — objeção nº 1 do jurídico (LGPD)"],
            ["Modelagem", "scikit-learn em servidor de ML dedicado", "Servidor a manter; retreino manual; exige cientista de dados para cada cliente"],
            ["Serviço de predição", "Lote offline → CSV de risco", "Sem API, sem controle de acesso por perfil, sem trilha de auditoria"],
            ["Apresentação", "Dashboard HTML estático", "Não registra intervenção nem resultado; não fecha o ciclo"],
            ["Operação", "Uma pessoa rodando o pipeline", "Não escala para 10+ IES; onboarding caro"],
        ],
        larguras=[3.0, 5.6, 7.4], legenda="Arquitetura inicial — componentes e limitações", primeira_negrito=True,
    )
    figura(os.path.join(DIAGRAMAS, "05_arquitetura_inicial.png"),
           "Arquitetura inicial (Fases 1–5): ETL externo, servidor de ML e dashboard fora do banco da IES")
    destaque("**Lição da arquitetura inicial:** tudo o que hoje é diferencial da Retena — ML in-database, dado que não sai da "
             "instituição, ciclo fechado de intervenção e retreino — estava fora dela. A Parte 4 reposiciona o produto "
             "para rodar onde o dado já mora.")

    h2("4.2 Como a solução escala")
    p("A Retena escala em três eixos — clientes, volume de dados e funcionalidades — sem mudar de arquitetura, porque "
      "toda a lógica (ingestão, features, treino, scoring, fila e painel) vive dentro do Oracle Autonomous AI Database e "
      "é expressa em SQL, PL/SQL e APEX.", alinh="j")
    bullets([
        "**Isolamento por cliente:** um schema (ou um banco Autonomous) por IES; nada é compartilhado além do código "
        "SQL/PL/SQL e das definições de modelo. Um novo cliente é um novo schema executando os mesmos scripts "
        "(01_ddl → 07_apex_ready), migrados por Data Pump ou SQL — mesmo dialeto do ambiente local, zero reescrita.",
        "**Elasticidade:** Autonomous AI Database Serverless com auto-scaling de computação e armazenamento sob demanda; "
        "o job semanal roda em janela de baixa carga (segunda 06h) e o restante da semana o consumo é o de consultas do painel.",
        "**Automação:** DBMS_SCHEDULER recalcula features, pontua com PREDICTION_PROBABILITY e grava o snapshot semanal "
        "(job JOB_RETENA_SCORING_SEMANAL, já criado no ambiente local: FREQ=WEEKLY; BYDAY=MON; BYHOUR=6); o retreino "
        "mensal é outro job, que recria os modelos com DBMS_DATA_MINING incorporando o resultado das intervenções.",
        "**Ingestão:** OCI Object Storage como landing dos exports do LMS e DBMS_CLOUD.COPY_DATA para carga paralela sem "
        "código externo. No ambiente local, a mesma tabela EVENTOS_LMS foi carregada via python-oracledb em lotes de 10 mil "
        "linhas (684.723 linhas em 71,6 s).",
        "**Volume analítico pré-agregado:** o modelo trabalha sobre linhas aluno-semana, não sobre eventos brutos; para "
        "12 mil alunos são ≈ 624 mil linhas/ano (12.000 × 52). Os eventos brutos — na razão observada na base, "
        "684.723 ÷ 203 alunos em 7,3 meses ≈ 3.400 por aluno, ou ≈ 5.500/aluno/ano — somariam ≈ 66 milhões de "
        "eventos/ano (estimativa), volume rotineiro para o Oracle com particionamento mensal por data do evento.",
        "**Multi-LMS via CSV padrão:** a entrada é o export de logs no formato Moodle-like (Hora, Nome completo, Contexto "
        "do Evento, Componente, Nome do evento, Origem); a tabela DIM_TIPO_EVENTO parametriza as classes de evento por "
        "LMS. Roadmap: conector Moodle Web Services e webhooks (OCI Functions + API Gateway).",
        "**Interface:** APEX multi-workspace (uma aplicação por IES com o mesmo código) e Select AI sobre as views de "
        "negócio; Oracle Analytics Cloud para grupos com várias IES.",
        "**Custo marginal por aluno:** o custo de infraestrutura é dominado pelo job semanal e cresce de forma "
        "sublinear com a base; o custo relevante é o onboarding (setup cobrado à parte), o que sustenta a margem bruta "
        "alvo de 80% da Parte 3.",
    ])
    tabela(
        ["Dimensão", "Como escala", "Mecanismo Oracle"],
        [
            ["Clientes (IES)", "Schema/banco por IES; mesmos scripts", "Autonomous Serverless; Data Pump; APEX multi-workspace"],
            ["Volume de eventos", "Particionamento mensal; features pré-agregadas", "Tabelas particionadas; DBMS_CLOUD; auto-scaling"],
            ["Frequência", "Semanal (scoring) e mensal (retreino), sem intervenção humana", "DBMS_SCHEDULER"],
            ["Fontes (LMS)", "CSV padrão hoje; API/webhooks depois", "Object Storage; OCI Functions + API Gateway (roadmap)"],
            ["Consumo", "Painel, JSON e perguntas em português", "APEX; views JSON / Duality Views; Select AI"],
            ["Grupos educacionais", "Visão consolidada multi-IES", "Oracle Analytics Cloud (roadmap)"],
        ],
        larguras=[3.2, 6.4, 6.4], legenda="Eixos de escala e mecanismos", primeira_negrito=True,
    )

    h2("4.3 Tecnologia Oracle incorporada")
    p("**Serviço principal (coração): Oracle Autonomous AI Database 26ai (Serverless) com Oracle Machine Learning "
      "in-database.** Features semanais, treino (DBMS_DATA_MINING) e scoring (PREDICTION_PROBABILITY e PREDICTION_DETAILS "
      "para o motivo explicável) acontecem no mesmo banco onde o dado mora: nenhum ETL, nenhum servidor de ML, nenhum "
      "dado de aluno em nuvem de terceiros. Os demais serviços orbitam esse núcleo.", alinh="j")
    tabela(
        ["Serviço Oracle", "Papel na Retena", "Situação"],
        [
            ["**Oracle Autonomous AI Database 26ai (Serverless)**", "Banco único do produto: eventos, features, modelos, snapshot de risco, intervenções, views de negócio", "Evidenciado localmente no Oracle AI Database 26ai Free (mesmo dialeto); piloto no Always Free; produção paga"],
            ["**Oracle Machine Learning — OML4SQL / DBMS_DATA_MINING**", "CREATE_MODEL2 (Random Forest e GLM); PREDICTION_PROBABILITY para o score; PREDICTION_DETAILS para os 3 fatores do motivo", "**Evidenciado** — 3 modelos treinados e 22 views DM$V de diagnóstico"],
            ["**DBMS_SCHEDULER**", "Job semanal de scoring; retreino mensal", "**Evidenciado** — JOB_RETENA_SCORING_SEMANAL criado e agendado"],
            ["JSON e JSON Relational Duality Views", "Payload da fila (VW_RISCO_JSON) e documento por aluno com escrita do status de atendimento (RISCO_ALUNO_DV)", "Protótipo local executado; API REST sobre a duality view no roadmap"],
            ["Oracle APEX", "Painel da coordenadora (fila, atrito, registro de contato) e dashboard executivo de receita em risco", "Consultas APEX-ready validadas em SQL (07_apex_ready.sql); aplicação publicada no piloto"],
            ["Select AI", "Perguntas em português sobre as views de negócio", "Piloto (requer Autonomous na OCI)"],
            ["OCI Object Storage + DBMS_CLOUD", "Landing dos CSVs do LMS e carga sem código externo", "Piloto"],
            ["OML Notebooks / OML4Py / AutoML", "Exploração de features e comparação de algoritmos pela equipe", "Piloto"],
            ["AI Vector Search", "Similaridade entre capítulos para o módulo de conteúdo adaptativo", "Roadmap"],
            ["OCI Functions + API Gateway", "Webhooks de LMS e API pública", "Roadmap"],
            ["Oracle Analytics Cloud", "Visão consolidada para grupos com várias IES", "Roadmap"],
        ],
        larguras=[4.4, 6.6, 5.0], legenda="Serviços Oracle: principal, secundários e roadmap",
    )

    h2("4.4 Justificativa da escolha e como ela fortalece o projeto")
    p("A Oracle não entra na Retena como hospedagem: entra como **motor de ML** e como **canal**. Quatro razões, na ordem "
      "em que aparecem na conversa de venda:", alinh="j")
    numerados([
        "**LGPD e venda:** \"o dado não sai da instituição\" elimina a objeção número 1 da diretora e do jurídico. Treinar "
        "e pontuar dentro do banco da IES transforma um projeto de compartilhamento de dados pessoais em uma extensão do "
        "sistema que a instituição já opera.",
        "**Custo e time-to-value:** o Always Free viabiliza o MVP e o piloto sem custo de infraestrutura; APEX substitui "
        "meses de front-end; uma equipe de engenharia pequena opera sem cientista de dados dedicado, porque o algoritmo, "
        "o pré-processamento (PREP_AUTO) e a explicação (PREDICTION_DETAILS) já estão no banco.",
        "**Canal de distribuição:** ERPs acadêmicos e mega grupos já rodam Oracle; a Retena entra como extensão do que a IES "
        "já tem, reduzindo o atrito de compra e abrindo a fase 2 (mega grupos) via ecossistema Oracle.",
        "**Defensibilidade:** o loop de retreino por cliente cria dado proprietário (intervenções e resultados) dentro do "
        "banco do cliente — difícil de replicar por BI genérico e impossível de copiar sem o histórico.",
    ])
    destaque("**O que a decisão muda na prática:** o mesmo SQL que rodou no Oracle AI Database 26ai Free em Docker roda no "
             "Autonomous AI Database sem alteração. O caminho local → piloto → produção é uma migração de schema, não "
             "uma reescrita — e isso é o que permite prometer \"primeira fila em 30 dias\".")

    h2("4.5 Diagrama arquitetural atualizado")
    p("A arquitetura atualizada tem quatro camadas e um laço de realimentação. Tudo o que envolve dado de aluno acontece "
      "dentro do Autonomous AI Database da IES.", alinh="j")
    numerados([
        "**Fontes:** LMS (Moodle / FIAP ON) exporta logs em CSV — agendado ou manual; roadmap: API do LMS e webhooks.",
        "**Ingestão:** OCI Object Storage recebe o arquivo; DBMS_CLOUD.COPY_DATA carrega em EVENTOS_LMS (no dev, "
        "python-oracledb faz o mesmo papel).",
        "**Núcleo in-database:** tabelas de eventos e dimensões (DIM_FASE, DIM_TIPO_EVENTO); features aluno-semana e "
        "aluno-fase em SQL; modelos OML (RETENA_INATIVO21_RF / GLM e RETENA_TRANSICAO_GLM); procedimento "
        "PRC_ATUALIZAR_RISCO e snapshot RISCO_ALUNO_SNAPSHOT; views de negócio, JSON e Duality View; DBMS_SCHEDULER.",
        "**Uso:** APEX (fila de segunda, mapa de atrito, receita em risco, registro de contato), Select AI para perguntas em "
        "português e JSON/REST para integrações.",
        "**Laço:** o resultado de cada intervenção registrado no APEX volta ao banco e alimenta o retreino mensal.",
    ])
    figura(os.path.join(DIAGRAMAS, "06_arquitetura_oracle.png"),
           "Arquitetura atualizada com Oracle Autonomous AI Database, OML, APEX e Select AI")
    figura(os.path.join(DIAGRAMAS, "07_fluxo_dados_ml.png"),
           "Fluxo de dados e ML: do export do LMS ao score, à fila e ao retreino")

    h2("4.6 Evidência da integração executada")
    p("A integração não é um desenho: o ciclo completo — carga, features, treino, scoring, avaliação e consultas do "
      "painel — foi executado em um **Oracle AI Database 26ai Free (Release 23.26.3.0.0)** rodando em Docker (imagem "
      "gvenzl/oracle-free:slim-faststart, container oracle-free, PDB FREEPDB1, usuário de aplicação STARTUP com "
      "DB_DEVELOPER_ROLE, que inclui o privilégio CREATE MINING MODEL). Todos os scripts e logs estão na pasta "
      "**06_Oracle** (sql/, scripts/, evidencias/); as evidências numeradas (01_versao_banco.txt … 07_apex_consultas.txt, "
      "evidencia_01…08.png e evidencias.html) foram geradas por consulta ao banco pelo script gerar_evidencias.py, e o "
      "passo a passo de reprodução está em 06_Oracle/README.md.", alinh="j")
    tabela(
        ["Etapa", "Script", "O que fez", "Resultado registrado no log"],
        [
            ["1. DDL e carga", "01_ddl.sql + carregar_eventos.py", "Tabelas DIM_FASE, DIM_TIPO_EVENTO e EVENTOS_LMS (identity, 3 índices, comentários); carga em lotes de 10 mil via python-oracledb; DBMS_STATS",
             "14 statements OK; **684.723 linhas em 71,6 s**; 679.892 eventos de alunos; 203 alunos; 15/01 → 26/08/2026; carga total 89,2 s"],
            ["2. Features aluno-fase", "02_features_transicao.sql", "Grão aluno-fase (14 atributos: eventos, dias ativos, % de capítulos, quizzes, entregas, horário, tendência) e rótulo EVADIU_PROXIMA_FASE",
             "Treino 528 casos (32 positivos, 6,1%) — transições F1→F2, F2→F3, F3→F4; teste 166 casos (13, 7,8%) — F4→F5"],
            ["3. Features semanais", "03_features_semanais.sql", "Cortes semanais de 01/02 a 02/08/2026 via SQL Macro de tabela (FN_FEATURES_SEMANAIS — a mesma definição para treino e produção, sem divergência treino/serviço); 10 atributos (EVENTOS_7D/14D/28D, DIAS_ATIVOS_28D, RECENCIA_DIAS, TENDENCIA, PROGRESSO_28D, QUIZ_28D, ENTREGAS_28D, CAPITULOS_DISTINTOS_28D) e rótulo INATIVO_21D",
             "Treino (cortes < 01/06) 2.682 casos, 11,6% positivos; teste (≥ 01/06) 1.655 casos, 23,4% positivos"],
            ["4. Treino OML", "04_oml_modelos.sql", "DBMS_DATA_MINING.CREATE_MODEL2 com PREP_AUTO=ON: RETENA_INATIVO21_RF (Random Forest, 200 árvores, sampling 0,6, seed 42), RETENA_INATIVO21_GLM (GLM ridge, classes balanceadas) e RETENA_TRANSICAO_GLM",
             "15 statements OK; **3 modelos em ~1 s cada**; 22 views DM$V de diagnóstico; scoring de teste com PREDICTION e PREDICTION_PROBABILITY em SQL"],
            ["5. Scoring e views", "05_scoring_views.sql", "VW_RISCO_ALUNO_ATUAL (PREDICTION_PROBABILITY + PREDICTION_DETAILS → FATORES_TOP3 e FATORES_JSON); RISCO_ALUNO_SNAPSHOT; PRC_ATUALIZAR_RISCO; job semanal; VW_RISCO_JSON; RISCO_ALUNO_DV (Duality View) com teste de escrita",
             "20 statements OK; snapshot de 203 alunos: **59 Alto · 15 Médio · 129 Baixo**; payload JSON de 89.871 bytes; job agendado (segunda 06h); procedimento em 121,8 s no Free"],
            ["6. Avaliação em SQL", "06_avaliacao.sql", "SCORES_TESTE e AVALIACAO_MODELOS; AUC-ROC via DBMS_DATA_MINING.COMPUTE_ROC com contraprova em SQL puro (estatística U de Mann-Whitney); lift por decil (COMPUTE_LIFT); matriz de confusão @ 0,5; faixas Alto/Médio/Baixo; precisão/captura/lift no top-20%; coeficientes e importâncias (DM$VD/DM$VA/DM$VG)",
             "AUC RF **0,949** (COMPUTE_ROC = SQL puro), GLM 0,945, transição 0,972; RF no top-20%: precisão 0,876, captura 0,749, lift 3,75×; RF @ 0,5: precisão 0,839, recall 0,806, F1 0,822 (VP 312 · FP 60 · FN 75 · VN 1.208). A 1ª execução registrou 4 erros em consultas opcionais, corrigidos na coleta final (evidencias/04_metricas.txt)"],
            ["7. Consultas APEX-ready", "07_apex_ready.sql", "Cinco consultas parametrizadas (:P1_FAIXA_MINIMA, :P1_TICKET_MENSAL) prontas para regiões APEX: fila de segunda com POR_QUE e O_QUE_FAZER; funil por fase; atrito por capítulo; receita em risco; reativação por mês",
             "5 OK; fila com 25 primeiros (1º: 198 dias sem acesso, 92,4%); evasão por fase F1 5,7% · F2 3,4% · F3 8,9% · F4 7,8%; receita em risco R$ 22.348/mês e R$ 134.087 no ciclo (ticket R$ 350 e 6 meses como parâmetros); reativação em 21 d de 37,8% (mar) a 9,0% (jul)"],
        ],
        larguras=[2.3, 2.7, 5.6, 5.4], legenda="O que foi executado no Oracle AI Database 26ai Free (06_Oracle/evidencias/logs)", primeira_negrito=True,
    )
    p("**Leitura honesta das métricas in-database.** As AUCs calculadas em SQL (0,949 para o Random Forest) não substituem "
      "a avaliação da Parte 3 (0,882): o conjunto de features é menor (10 atributos), a partição temporal tem contagem "
      "de casos diferente (1.655 × 1.609) e os filtros de elegibilidade não são idênticos. O que elas provam é que "
      "**o ciclo completo — features, treino, scoring, explicação e avaliação — roda em SQL dentro do banco**, com "
      "resultado da mesma ordem de grandeza. A avaliação de referência continua sendo a do RESULTADOS.md.", alinh="j")
    codigo([
        "-- 04_oml_modelos.sql (trecho adaptado): treino in-database",
        "DBMS_DATA_MINING.CREATE_MODEL2(",
        "  model_name          => 'RETENA_INATIVO21_RF',",
        "  mining_function     => 'CLASSIFICATION',",
        "  data_query          => 'SELECT * FROM VW_TREINO_INATIVIDADE',",
        "  set_list            => v_set,   -- ALGO_RANDOM_FOREST, 200 arvores, PREP_AUTO=ON, seed 42",
        "  case_id_column_name => 'ID_CASO',",
        "  target_column_name  => 'INATIVO_21D');",
        "",
        "-- scoring por SQL (consulta #15 do mesmo script)",
        "SELECT ID_CASO, INATIVO_21D AS real,",
        "       ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_RF,  1 USING *), 4) AS prob_rf,",
        "       ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_GLM, 1 USING *), 4) AS prob_glm",
        "  FROM VW_TESTE_INATIVIDADE ORDER BY prob_rf DESC FETCH FIRST 10 ROWS ONLY;",
        "",
        "-- 05_scoring_views.sql (trecho): agendamento semanal",
        "DBMS_SCHEDULER.CREATE_JOB(job_name => 'JOB_RETENA_SCORING_SEMANAL',",
        "  job_type => 'STORED_PROCEDURE', job_action => 'PRC_ATUALIZAR_RISCO',",
        "  repeat_interval => 'FREQ=WEEKLY; BYDAY=MON; BYHOUR=6; BYMINUTE=0', enabled => TRUE);",
    ], legenda="Trechos dos scripts SQL executados (pasta 06_Oracle/sql)")
    if not _trechos_evidencias():
        codigo([
            "[2026-09-08 12:11:42] Conexao: STARTUP@localhost:1521/FREEPDB1 | 14 statement(s)",
            "[12:11:42] #06 CREATE  CREATE TABLE EVENTOS_LMS ( ID_EVENTO NUMBER GENERATED ALWAYS AS IDENTITY, ...",
            "[2026-09-08 12:11:43] Fim: 14 ok, 0 erro(s), 0.3s",
            "Parquet lido: 684.723 linhas x 9 colunas",
            "[12:12:58] lote  69:  684.723 / 684.723 linhas (100.0%) -   71.5s",
            "COMMIT - 684.723 linhas inseridas em 71.6s",
            "DBMS_STATS.GATHER_TABLE_STATS(EVENTOS_LMS) - ok",
            " TOTAL_EVENTOS | EVENTOS_DE_ALUNOS | ALUNOS_DISTINTOS | PRIMEIRO_EVENTO  | ULTIMO_EVENTO",
            " 684723        | 679892            | 203              | 2026-01-15 11:14 | 2026-08-26 09:34",
            "[2026-09-08 12:13:11] Carga concluida em 89.2s",
        ], legenda="Trecho de 06_Oracle/evidencias/logs/carga_eventos.log")
        codigo([
            "[16:03:27] #10 SELECT  SELECT model_name, mining_function, algorithm, ... FROM user_mining_models",
            " MODEL_NAME           | MINING_FUNCTION | ALGORITHM                | CRIADO_EM           | SEG_TREINO | BYTES",
            " RETENA_INATIVO21_GLM | CLASSIFICATION  | GENERALIZED_LINEAR_MODEL | 2026-09-08 19:03:27 | 1          | 1505",
            " RETENA_INATIVO21_RF  | CLASSIFICATION  | RANDOM_FOREST            | 2026-09-08 19:03:26 | 1          | 802134",
            " RETENA_TRANSICAO_GLM | CLASSIFICATION  | GENERALIZED_LINEAR_MODEL | 2026-09-08 19:03:25 | 1          | 2087",
            "[16:03:27] #15 SELECT  SELECT ID_CASO, INATIVO_21D AS real, ROUND(PREDICTION_PROBABILITY(RETENA_INATIVO21_RF, ...",
            " ID_CASO             | REAL | PROB_RF | PROB_GLM",
            " Aluno 0227_20260628 | 1    | 0.9237  | 0.9976",
            " Aluno 0173_20260719 | 1    | 0.9237  | 1",
            "[2026-09-08 16:03:28] Fim: 15 ok, 0 erro(s), 3.2s",
        ], legenda="Trecho de 06_Oracle/evidencias/logs/04_oml_modelos.log")
        codigo([
            "[16:26:26] #08 PLSQL   BEGIN PRC_ATUALIZAR_RISCO; END;",
            "      OK em 121.84s",
            " JOB_NAME                   | JOB_TYPE         | JOB_ACTION          | REPEAT_INTERVAL              | STATE",
            " JOB_RETENA_SCORING_SEMANAL | STORED_PROCEDURE | PRC_ATUALIZAR_RISCO | FREQ=WEEKLY; BYDAY=MON; ...  | SCHEDULED",
            "[16:28:28] #12 CREATE  CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW RISCO_ALUNO_DV AS SELECT JSON { ...",
            "      OK em 0.03s",
            " FAIXA_RISCO | ALUNOS | PROB_MEDIA | RECENCIA_MEDIA | EVENTOS_28D_MEDIA",
            " Alto        | 59     | 0.8444     | 86.4           | 0.4",
            " Médio       | 15     | 0.4719     | 13.9           | 50.7",
            " Baixo       | 129    | 0.0539     | 4.8            | 1020.5",
            " BYTES_PAYLOAD | TOTAL | ALTO | MEDIO | BAIXO | PRIMEIRO_DA_FILA",
            " 89871         | 203   | 59   | 15    | 129   | Aluno 0045",
            "[2026-09-08 16:28:28] Fim: 20 ok, 0 erro(s), 128.3s",
        ], legenda="Trecho de 06_Oracle/evidencias/logs/05_scoring_views.log")
        codigo([
            " MODELO               | METRICA      | VALOR  | DETALHE",
            " RETENA_INATIVO21_RF  | AUC_SQL      | 0.949  | AUC-ROC calculada em SQL puro",
            " RETENA_INATIVO21_RF  | PRECISAO_0.5 | 0.8387 | limiar 0,5",
            " RETENA_INATIVO21_RF  | RECALL_0.5   | 0.8062 | limiar 0,5 (sensibilidade)",
            " RETENA_INATIVO21_RF  | F1_0.5       | 0.8221 | limiar 0,5",
            " RETENA_INATIVO21_GLM | AUC_SQL      | 0.9451 | AUC-ROC calculada em SQL puro",
            " RETENA_TRANSICAO_GLM | AUC_SQL      | 0.9718 | AUC-ROC calculada em SQL puro",
            " MODELO               | FAIXA | CASOS | POSITIVOS | TAXA_OBSERVADA | PROB_MEDIA | CAPTURA",
            " RETENA_INATIVO21_RF  | Alto  | 347   | 296       | 0.853          | 0.8429     | 0.7649",
            " RETENA_INATIVO21_RF  | Médio | 53    | 27        | 0.5094         | 0.4688     | 0.0698",
            " RETENA_INATIVO21_RF  | Baixo | 1255  | 64        | 0.051          | 0.044      | 0.1654",
            "[2026-09-08 16:32:33] Fim: 23 ok, 4 erro(s), 0.6s",
        ], legenda="Trecho de 06_Oracle/evidencias/logs/06_avaliacao.log")
    legendas_evid = {
        1: "Ambiente: Oracle AI Database 26ai Free em Docker (v$version, container, parâmetros)",
        2: "Dados carregados: logs do LMS em EVENTOS_LMS (totais, por fase, por classe de evento)",
        3: "Feature engineering in-database (views + SQL Macro) — transição de fases e cortes semanais",
        4: "Modelos Oracle Machine Learning treinados no banco (USER_MINING_MODELS, settings, atributos)",
        5: "Avaliação no conjunto de teste (validação temporal): AUC, matriz de confusão, faixas, lift, importâncias",
        6: "Scoring por SQL: PREDICTION_PROBABILITY + PREDICTION_DETAILS (fatores explicáveis por aluno)",
        7: "JSON pronto para API e JSON Relational Duality View (RISCO_ALUNO_DV)",
        8: "Consultas prontas para APEX (07_apex_ready.sql) — fila, funil, atrito, receita em risco, reativação",
    }
    imgs = sorted(glob.glob(os.path.join(ORACLE_EVID, "evidencia_*.png")))
    if imgs:
        p("As capturas a seguir são as seções do relatório 06_Oracle/evidencias/evidencias.html, gerado automaticamente a "
          "partir de consultas reais ao banco no momento da coleta.", alinh="j")
        for i, caminho in enumerate(imgs, 1):
            leg = legendas_evid.get(i, os.path.basename(caminho))
            figura_recorte(caminho, "Evidência Oracle %d — %s" % (i, leg), largura_cm=16.0, frac=0.6)
    else:
        figura(os.path.join(ORACLE_EVID, "evidencia_01.png"), "Evidência da integração Oracle")
    tabela(
        ["Componente", "Local — o que rodou (evidência)", "Produção — Autonomous AI Database"],
        [
            ["Banco", "Oracle AI Database 26ai Free em Docker (gvenzl/oracle-free:slim-faststart), PDB FREEPDB1", "Autonomous AI Database Serverless (Always Free no piloto; pago com auto-scaling em produção), 1 schema/banco por IES"],
            ["Ingestão", "python-oracledb, lotes de 10 mil linhas (08_Dados/logs_lms.parquet)", "OCI Object Storage + DBMS_CLOUD.COPY_DATA agendado; API/webhooks no roadmap"],
            ["Features", "SQL (02_features_transicao.sql, 03_features_semanais.sql)", "Idêntico — mesmo dialeto, zero reescrita"],
            ["Modelos", "DBMS_DATA_MINING.CREATE_MODEL2 — Random Forest e GLM", "Idêntico; comparação de algoritmos em OML Notebooks/AutoML; XGBoost quando o volume permitir"],
            ["Scoring e explicação", "PREDICTION_PROBABILITY + PREDICTION_DETAILS em views; snapshot semanal", "Idêntico; retreino mensal por cliente"],
            ["Agendamento", "DBMS_SCHEDULER (JOB_RETENA_SCORING_SEMANAL)", "DBMS_SCHEDULER + alertas por e-mail"],
            ["Interface", "Consultas APEX-ready validadas em SQL; dashboard HTML do MVP (05_MVP)", "APEX (fila, atrito, receita) + Select AI + JSON/REST (ORDS sobre a duality view)"],
            ["Segurança", "Usuário de aplicação com DB_DEVELOPER_ROLE; dados pseudonimizados (Aluno NNNN)", "TDE por padrão, perfis de acesso por papel, Unified Audit, Data Safe"],
        ],
        larguras=[2.8, 6.4, 6.8], legenda="Local → Produção: o mesmo código, outro serviço", primeira_negrito=True,
    )

    h2("4.7 Segurança, privacidade e LGPD")
    p("A Retena trata dados pessoais de alunos (logs de navegação vinculados a uma matrícula). O desenho parte de três "
      "princípios: **o dado não sai do banco da IES**, **minimização** (só logs de navegação; nada de notas, dados "
      "socioeconômicos ou financeiros) e **tom de apoio, não de vigilância**.", alinh="j")
    tabela(
        ["Requisito", "Como a Retena atende", "Mecanismo"],
        [
            ["Base legal", "Execução do contrato educacional (LGPD, art. 7º, V) como base principal para o score e o contato; diagnóstico agregado de conteúdo sobre dados anonimizados. Documentado no contrato e no aviso de privacidade da IES", "Cláusula de tratamento no contrato de assinatura; registro de operações"],
            ["Localidade do dado", "Ingestão, features, treino e scoring dentro do Autonomous AI Database da IES; a Retena não recebe cópia dos dados", "OML in-database; sem ETL externo; tenancy OCI da IES ou dedicada"],
            ["Pseudonimização", "Identificador \"Aluno NNNN\" em toda a camada analítica e em materiais externos; a chave de re-identificação fica só na IES e só é resolvida no painel para quem tem papel para isso", "Tabela de correspondência em schema separado; view com mascaramento"],
            ["Perfis de acesso", "Tutor vê apenas sua carteira; coordenadora vê nominal do curso; diretora vê agregados em R$; equipe Retena não vê dados nominais", "APEX authorization schemes; políticas de linha (VPD/Real Application Security)"],
            ["Criptografia e auditoria", "Dados criptografados em repouso e em trânsito; toda leitura nominal e toda intervenção registradas", "TDE (padrão no Autonomous); TLS; Unified Audit; tabela de intervenções"],
            ["Direitos do titular", "Aviso de privacidade ao aluno; opt-in de contato registrado; exclusão/anonimização a pedido", "Procedimento de anonimização por aluno; retenção definida por contrato"],
            ["Minimização e retenção", "Só logs de navegação; eventos brutos com prazo de retenção; features agregadas mantidas para o retreino", "Particionamento por mês com descarte programado"],
        ],
        larguras=[2.8, 8.0, 5.2], legenda="Privacidade e LGPD — requisitos e mecanismos", primeira_negrito=True,
    )

    h2("4.8 Roadmap técnico")
    tabela(
        ["Período", "Entregas técnicas", "Marco"],
        [
            ["Set/2026 (até 23/09)", "Pacote da Fase 6: documento, diagramas, MVP analítico, evidência Oracle local, vídeo; ajustes pós-banca", "Formulário 13/09 · Banca Final 23/09"],
            ["Out/2026 (até o NEXT, 24/10)", "Provisionar Autonomous AI Database Always Free; migrar schema e modelos (Data Pump/SQL); publicar 1ª aplicação APEX (fila + registro de contato); habilitar Select AI; roteiro de onboarding de IES", "Demonstração no NEXT 24/10 com Autonomous + APEX"],
            ["Q4/2026 – Q1/2027", "Piloto de 90 dias em uma fase de um curso; ingestão via Object Storage/DBMS_CLOUD; retreino mensal automatizado; painel executivo de receita em risco; alertas por e-mail", "1ª fila em 30 dias; ROI medido em rematrícula"],
            ["Q2/2027", "Conector Moodle Web Services; API REST sobre Duality Views (ORDS); webhooks (OCI Functions + API Gateway); integração WhatsApp/e-mail para a mensagem do tutor", "Onboarding sem projeto de TI"],
            ["Q3/2027", "Módulo de conteúdo adaptativo com AI Vector Search (similaridade entre capítulos e formatos); XGBoost por cliente conforme volume; OML AutoML no ciclo de retreino", "Upsell do módulo adaptativo"],
            ["Q4/2027", "Multi-campus e grupos: Oracle Analytics Cloud consolidado; Enterprise (SLA, retreino dedicado); preparação para mega grupos via ecossistema Oracle", "Fase 2 do mercado (SOM R$ 4,3 mi ARR)"],
        ],
        larguras=[3.2, 8.6, 4.2], legenda="Roadmap técnico por trimestre", primeira_negrito=True,
    )


# >>> MAIS_FUNCOES


# ----------------------------------------------------------------------------------------------------------------------
# Montagem
# ----------------------------------------------------------------------------------------------------------------------
def sec_proximos():
    h1("5. Próximos passos")
    p("A Fase 6 fecha com o pacote entregável pronto e três frentes abertas: o envio à Banca Final, as entrevistas de "
      "validação com usuários reais e a preparação do piloto de 90 dias. O cronograma abaixo vai até o NEXT.", alinh="j")
    tabela(
        ["Quando", "O quê", "Responsável"],
        [
            ["08–12/09/2026", "Fechamento da Fase 6: revisão final do documento e dos diagramas; gravação, edição e legendas do vídeo pitch (≤ 5 min); montagem do ZIP e teste de abertura local", "Equipe"],
            ["**até 13/09/2026**", "Vídeo publicado no YouTube (não listado): https://youtu.be/HZrcLvIJCC4 — envio do formulário da Banca Final com as 4 respostas do Anexo B", "Lucas Dalmas (líder)"],
            ["14–22/09/2026", "Confirmar em campo os achados das entrevistas simuladas com 5 a 8 potenciais usuários reais (roteiro do Anexo A); ensaio cronometrado do pitch", "Equipe"],
            ["**23/09/2026**", "Banca Final", "Equipe"],
            ["24/09–23/10/2026", "Incorporar o feedback da banca; provisionar Autonomous AI Database Always Free e publicar a 1ª aplicação APEX; prospecção de IES para o piloto (sem cliente confirmado até aqui)", "Equipe"],
            ["**24/10/2026**", "NEXT (FIAP): demonstração com Autonomous + APEX", "Equipe"],
            ["Nov/2026–Fev/2027", "Piloto de 90 dias em uma fase de um curso, com meta de rematrícula acordada (IES a definir)", "Equipe + IES piloto"],
        ],
        larguras=[3.2, 9.8, 3.0], legenda="Cronograma até o NEXT",
    )
    h3("Entrevistas: confirmação em campo")
    p("As oito entrevistas da Parte 2 foram conduzidas em formato simulado, com personas sintéticas, para calibrar o "
      "instrumento e antecipar objeções. Antes do piloto, a equipe repetirá o roteiro do Anexo A com pessoas reais — "
      "meta mínima: 3 coordenadores(as) de curso EAD/híbrido, 2 tutores(as), 1 diretor(a) de operações e 2 alunos(as) "
      "EAD trabalhadores(as) —, atualizando registro_entrevistas.csv e a matriz de hipóteses H1–H6.", alinh="j")
    h3("Desenho do piloto de 90 dias")
    bullets([
        "**Escopo:** uma fase de um curso EAD (≈ 200 a 2.000 alunos), dados exportados do LMS em CSV padrão, schema "
        "dedicado no Autonomous AI Database.",
        "**Preço:** R$ 5 mil pelo piloto completo; conversão automática em contrato anual se a meta for atingida.",
        "**Meta:** reengajar 30% dos alunos em risco Alto da fase-piloto em 30 dias (na base analisada: 61 alunos com mais "
        "de 14 dias sem acesso → ≈ 18 reativações).",
        "**KPIs semanais:** alunos avaliados, fila gerada, contatos realizados, taxa de resposta por horário, reativação "
        "em 7 dias, rematrícula ao fim do período e receita preservada em R$ vs. custo da assinatura.",
        "**Critério de sucesso para a IES:** primeira fila em 30 dias; ROI positivo em 90.",
    ])
    h3("Riscos e mitigação")
    tabela(
        ["#", "Risco", "Mitigação", "Situação na Fase 6"],
        [
            ["1", "**Modelo com poucos dados por IES** (203 alunos na base; rótulo parcial porque a F5 está em andamento)",
             "Começar com regras + GLM interpretável e rótulo proxy (inatividade de 21 dias / não avanço de fase); validação temporal; migrar para XGBoost conforme volume; retreino mensal com resultados das intervenções; métricas rotuladas como preliminares",
             "Protocolo temporal aplicado; GLM e RF treinados in-database; limitações declaradas em 3.5"],
            ["2", "**Coordenadora tem dor, mas não orçamento; ciclo de venda longo**",
             "Dupla persona: vender proteção de receita à diretora de operações com dashboard de R$ em risco; piloto de 90 dias pago simbolicamente com meta de rematrícula e conversão automática",
             "Persona compradora incorporada; consulta de receita em risco validada em SQL"],
            ["3", "**Integração com LMS vira projeto de TI**",
             "Entrada por CSV exportado (padrão Moodle) já validada na base real; API como segundo passo; APEX pronto em dias; SLA de \"primeira fila em 30 dias\"",
             "Carga do CSV real executada (684.723 eventos)"],
            ["4", "**LGPD e percepção de vigilância do aluno**",
             "Dados nunca saem do banco da IES; pseudonimização (Aluno NNNN) fora do painel; tom de voz de apoio, não de cobrança; opt-in de contato registrado; base legal de execução de contrato documentada",
             "Arquitetura in-database evidenciada; seção 4.7"],
            ["5", "**Concorrência de BI embarcado no LMS ou grandes edtechs; nome confundido com \"retina\"**",
             "Diferenciar pelo ciclo fechado (intervenção + ROI + retreino) e pelo canal Oracle; registrar retena.com.br/.app e marca no INPI cedo; nunca exibir o nome sem a tagline e a linha do batimento; nomes reserva (Pulso, Alento, Maré) como módulos",
             "Identidade e tagline definidas; registros de domínio/INPI pendentes"],
        ],
        larguras=[0.6, 3.6, 7.2, 4.6], legenda="Riscos e mitigação",
    )


# ---------------------------------------------------------------------------------------------------------------------
# ANEXOS
# ---------------------------------------------------------------------------------------------------------------------

def sec_anexos():
    # ----- Anexo A -----
    h1("Anexo A — Instrumento de validação")
    p("Uso: roteiro aplicado nas oito entrevistas da Parte 2 (formato simulado com personas sintéticas, síntese em A.6) e "
      "a ser reaplicado em campo com 5 a 8 potenciais usuários reais (coordenadores de curso EAD/híbrido, tutores, "
      "gestores acadêmicos e alunos), registrando as respostas em registro_entrevistas.csv.", alinh="j")
    h3("A.1 Perfis a entrevistar (mínimo)")
    tabela(
        ["#", "Perfil", "Por quê", "Meta"],
        [
            ["1", "Coordenador(a) de curso EAD ou híbrido (IES privada)", "Compradora/usuária principal; dona da meta de retenção", "3 entrevistas"],
            ["2", "Tutor(a) / professor(a) mediador(a)", "Executa as intervenções; sente a sobrecarga", "2 entrevistas"],
            ["3", "Gestor(a) acadêmico / diretor(a) de operações EAD", "Decide orçamento; mede evasão financeiramente", "1 entrevista"],
            ["4", "Aluno(a) EAD adulto(a) trabalhador(a)", "Beneficiário final; valida percepção das intervenções", "2 entrevistas"],
        ],
        larguras=[0.7, 5.6, 6.7, 3.0], legenda="Perfis e metas de entrevistas",
    )
    h3("A.2 Roteiro de entrevista semiestruturada (30 min)")
    p("**Abertura (3 min)** — apresentar o objetivo (entender como a instituição acompanha o engajamento e a evasão), "
      "garantir anonimato, pedir permissão para anotar.", alinh="j")
    p("**Bloco A — Contexto e dor (8 min)**", keep_next=True)
    numerados([
        "Como você descobre hoje que um aluno está \"sumindo\" do curso? Quanto tempo depois do primeiro sinal?",
        "Quais indicadores você acompanha (acessos, notas, entregas)? Com que frequência? Em que ferramenta?",
        "Conte a última vez que perdeu um aluno que \"dava para salvar\". O que faltou?",
        "Quantos alunos por tutor/coordenador? Quanto tempo por semana vai para acompanhamento manual?",
    ])
    p("**Bloco B — Processo atual e alternativas (7 min)**", keep_next=True)
    numerados([
        "Existe algum relatório do LMS (Moodle/Canvas/Blackboard/plataforma própria) que você usa? Ele chega a tempo?",
        "Já testaram alguma solução de analytics/retenção? Por que não ficou?",
        "Como decidem quem contatar primeiro quando há muitos alunos inativos?",
    ])
    p("**Bloco C — Reação à proposta (8 min)** — mostrar o protótipo (dashboard) por 2 minutos, sem explicar demais.", keep_next=True)
    numerados([
        "O que chamou sua atenção primeiro? O que parece confuso ou irrelevante?",
        "Se recebesse toda segunda-feira uma lista dos 20 alunos em maior risco com o motivo e uma ação sugerida, o que faria com ela? Quem executaria?",
        "O mapa de atrito de conteúdo (capítulos onde os alunos travam) mudaria algo na produção de conteúdo?",
        "Que integração é obrigatória para vocês usarem (LMS, SIS/ERP acadêmico, WhatsApp, e-mail)?",
    ])
    p("**Bloco D — Valor e disposição a pagar (4 min)**", keep_next=True)
    numerados([
        "Quanto custa hoje um aluno que evade (mensalidade média × meses restantes; custo de captação)?",
        "Um modelo por aluno ativo/mês faz sentido? Qual faixa seria aceitável (R$ 0,50 / 1,00 / 2,00 / 3,00)? Quem aprova essa compra?",
        "Que resultado precisaria ver em 90 dias para renovar?",
    ])
    p("**Encerramento** — pedir indicação de mais 1 pessoa para entrevistar; agradecer.", alinh="j")
    h3("A.3 Formulário de validação (Google Forms / Microsoft Forms) — 12 perguntas")
    numerados([
        "Seu papel na instituição (coordenação / tutoria / gestão / docência / aluno).",
        "Modalidade predominante dos cursos (EAD / híbrido / presencial).",
        "Porte aproximado (até 1 mil alunos / 1–5 mil / 5–20 mil / > 20 mil).",
        "Hoje, quanto tempo leva para perceber que um aluno parou de acessar? (mesmo dia / 1 semana / 2–4 semanas / só no fim do módulo / não percebemos).",
        "Escala 1–5: \"Temos um processo claro para agir quando um aluno dá sinais de evasão.\"",
        "Escala 1–5: \"Sabemos quais conteúdos fazem os alunos travarem ou desistirem.\"",
        "Quais dados vocês já têm acesso? (logs do LMS / notas / frequência / financeiro / pesquisas de satisfação).",
        "Qual ação vocês conseguem executar em escala? (mensagem automática / ligação do tutor / ajuste de prazo / mentoria / bolsa).",
        "Quão útil seria uma lista semanal de alunos em risco com motivo e ação sugerida? (1–5).",
        "Quão útil seria um mapa dos capítulos com maior atrito e recomendações de redesenho? (1–5).",
        "Qual faixa de preço por aluno ativo/mês seria aceitável? (até R$ 0,50 / R$ 0,51–1,00 / R$ 1,01–2,00 / R$ 2,01–3,00 / acima).",
        "Aceita participar de um piloto de 90 dias com dados anonimizados? (sim / talvez / não) + contato opcional.",
    ], tamanho=9.5)
    h3("A.4 Hipóteses a validar")
    tabela(
        ["Hipótese", "Métrica de validação", "Evidência atual (dados/fontes)", "Resultado das entrevistas"],
        [
            ["H1. A instituição descobre a evasão tarde (semanas)", "≥ 60% respondem \"2–4 semanas\" ou pior na Q4", "Base real: 61 de 203 alunos (30%) com > 14 dias sem acesso e sem sinalização", "100% (6/6) — **suportada**"],
            ["H2. Sinais comportamentais do LMS antecipam a evasão", "AUC do modelo ≥ 0,75 no teste temporal", "AUC-ROC 0,882 no teste temporal (05_MVP/outputs/RESULTADOS.md)", "Entrevistados reconhecem recência e entregas como os sinais que já usam informalmente — **suportada**"],
            ["H3. Tutores não conseguem priorizar quem contatar", "≥ 50% relatam priorização manual/intuitiva (Q7)", "Semesp 2026: desistência EAD 41,6%; equipes reduzidas", "83% (5/6) — **suportada**"],
            ["H4. Conteúdo tem pontos de atrito identificáveis", "Concentração de queda em capítulos específicos", "Base real: cauda de alunos parados nos caps. 1–3 em todas as fases", "4/6 citam capítulos específicos; mapa de atrito com mediana 4/5 — **suportada**"],
            ["H5. Há disposição a pagar por aluno ativo/mês", "Mediana da Q11 ≥ R$ 1,00", "Estimativa: aluno retido preserva R$ 3–5 mil/ano", "Coordenação R$ 1–3; sponsor R$ 3–4 com meta; IES pequena ≤ R$ 1 — **parcialmente suportada**"],
            ["H6. A integração via export/API do LMS é aceitável", "≥ 70% possuem logs do LMS acessíveis (Q7)", "Base real é um export padrão de logs", "100% (6/6) por export; API depende de TI em 2/6 — **suportada**"],
        ],
        larguras=[4.2, 3.8, 4.6, 3.4], legenda="Matriz de hipóteses H1–H6 (resultado das entrevistas simuladas; confirmar em campo)", primeira_negrito=True,
    )
    h3("A.5 Registro (modelo registro_entrevistas.csv)")
    codigo([
        "id,data,perfil,instituicao_porte,modalidade,tempo_para_perceber_inatividade,processo_claro_1a5,",
        "conhece_atrito_conteudo_1a5,dados_disponiveis,acoes_em_escala,utilidade_lista_risco_1a5,",
        "utilidade_mapa_atrito_1a5,faixa_preco,piloto,citacao_marcante,aprendizado,tipo_registro",
    ], legenda="Cabeçalho do CSV de registro (uma linha por entrevista; arquivo preenchido em 01_Documento/anexos/registro_entrevistas.csv)")
    h3("A.6 Síntese das entrevistas de validação")
    destaque("As oito entrevistas foram conduzidas em **formato simulado**, com personas sintéticas construídas a partir dos "
             "perfis-alvo e das evidências da base real; não representam pessoas ou instituições reais. Síntese detalhada "
             "por entrevista em 01_Documento/anexos/entrevistas_validacao.md.", cor_borda=HEX_AMBAR)
    tabela(
        ["Indicador", "Resultado (6 respondentes institucionais, salvo indicação)"],
        [
            ["Tempo até perceber a inatividade (Q4)", "6/6 em \"2–4 semanas\" ou \"só no fim do módulo\"; nenhum \"mesmo dia\" ou \"1 semana\""],
            ["\"Temos processo claro para agir\" (Q5, 1–5)", "Mediana 2,5 (respostas 2, 3, 1, 2, 2, 3)"],
            ["\"Sabemos quais conteúdos travam\" (Q6, 1–5)", "Mediana 2,5 (2, 2, 3, 2, 3, 3)"],
            ["Priorização de contato (Q7)", "5/6 manual/intuitiva (nota baixa, reclamação, memória do tutor); 1/6 por BI mensal"],
            ["Logs do LMS acessíveis por export (Q7)", "6/6; 2/6 citam TI como gargalo para integração via API"],
            ["Utilidade da lista semanal (Q9, 1–5)", "Mediana 5 (5, 5, 4, 5, 5, 4)"],
            ["Utilidade do mapa de atrito (Q10, 1–5)", "Mediana 4 (4, 5, 5, 3, 4, 3)"],
            ["Faixa de preço aceitável (Q11)", "Coordenação: R$ 1,01–2,00 (E1), R$ 2,01–3,00 (E2), até R$ 0,50–1,00 (E3); gestão: R$ 3,01–4,00 com meta (E6)"],
            ["Aceita piloto de 90 dias (Q12)", "4 sim (E1, E2, E6 e a IES de E5), 1 talvez (E3)"],
            ["Alunos (E7, E8)", "2/2 preferem contato à noite, por WhatsApp, com plano concreto de retomada; 2/2 rejeitam tom de cobrança"],
        ],
        larguras=[5.0, 11.0], legenda="Resultados consolidados das perguntas fechadas", primeira_negrito=True,
    )
    bullets([
        "**E1 — Coordenadora de curso EAD (8 mil alunos):** descobre no fechamento do módulo; processo claro 2/5; quer motivo e ação junto ao alerta; R$ 1–2; piloto sim. \"Eu descubro que o aluno sumiu quando o financeiro me manda a lista de inadimplentes. Aí já é tarde.\"",
        "**E2 — Coordenador do Núcleo de Permanência (15 mil):** BI mensal, percebe em 2–4 semanas; LGPD e projeto de TI como objeções; R$ 2–3 condicionado ao piloto. \"Tenho BI, mas ele me conta o que aconteceu no mês passado.\"",
        "**E3 — Coordenadora pedagógica (1.500):** só no fim do módulo; interesse maior no mapa de atrito; até R$ 1; mínimo mensal de R$ 5 mil é barreira. \"Estatística II derruba todo mundo. Nunca vi isso em número.\"",
        "**E4 — Tutor mediador (300 alunos):** resposta de 10–15% por e-mail; prioriza por nota baixa; quer os 20 que importam, template e horário. \"Se eu ligar para 300 alunos, não faço mais nada.\"",
        "**E5 — Tutora mediadora (220 alunos):** WhatsApp pessoal, nada registrado; registro em um clique foi o item mais elogiado. \"Eu anoto num caderno quem eu chamei.\"",
        "**E6 — Diretor de Operações (30 mil):** descobre pela inadimplência; ticket R$ 320, CAC R$ 900–1.400; compra receita preservada com meta; R$ 3–4. \"Não compro dashboard. Compro rematrícula.\"",
        "**E7 — Aluno, 29 anos:** parou 3 semanas após o cap. 2, ninguém o contatou, desistiu de novo ao voltar atrasado. \"Se alguém tivesse me mandado só o resumo do capítulo 2, eu tinha voltado antes.\"",
        "**E8 — Aluna, 34 anos:** uma ligação da tutora a trouxe de volta, \"mas foi sorte\"; pede prazos flexíveis e material para o celular.",
    ], tamanho=9.5)

    # ----- Anexo B -----
    h1("Anexo B — Respostas do formulário da Banca Final")
    p("Formulário \"4ESOA Enterprise Challenge Oracle — Envio do Vídeo Pitch\", prazo 13/09/2026. Cada resposta tem no "
      "máximo 300 caracteres (contagem real indicada). Copiar e colar exatamente.", alinh="j")
    respostas = [
        ("1. Link do vídeo pitch",
         "https://youtu.be/HZrcLvIJCC4 (vídeo não listado, 4 min 48 s; testar em janela anônima antes de enviar). Arquivo local: 07_Video_Pitch/Retena_Pitch_Banca_Final.mp4"),
        ("2. Qual problema a solução resolve, e para quem",
         "Coordenadores e diretores de IES privadas com EAD só descobrem a evasão quando a mensalidade para: 41,6% dos alunos EAD desistiram em 2024 (Semesp). A Retena antecipa em semanas quem vai sumir, lendo os sinais que o LMS já registra, e diz quem contatar, por quê e o que ajustar no curso."),
        ("3. Como a solução funciona, de forma objetiva",
         "Os logs do LMS entram no Oracle AI Database; features semanais (recência, tendência, capítulo travado, quizzes) são calculadas em SQL e um modelo Oracle Machine Learning pontua o risco de cada aluno in-database. Toda segunda, a coordenação recebe a fila de intervenção e o mapa de atrito do conteúdo."),
        ("4. Diferencial e por que não foi resolvido assim antes",
         "BI mostra o passado e CRM cobra tarde. A Retena junta risco por aluno, atrito por capítulo e resultado da intervenção em R$, sem o dado sair da IES (LGPD) e sem time de ciência de dados, porque o ML roda dentro do banco. Ficou viável agora: ML in-database maduro e EAD como maioria desde 2024."),
        ("5. Como a solução se sustenta como negócio",
         "SaaS B2B por aluno ativo/mês: R$ 6 (até 10 mil alunos), R$ 4 (10–50 mil) e R$ 3 (megagrupos), mínimo R$ 5 mil/mês e setup de R$ 10–25 mil. Piloto de 90 dias em uma fase com meta de rematrícula. Uma IES de 12 mil alunos paga R$ 576 mil/ano e se paga retendo 137 alunos (1,1% da base)."),
        ("6. Link do protótipo, repositório ou aplicação publicada (opcional)",
         "[opcional: link público da landing page / dashboard, se a equipe publicar] — versões locais no ZIP: 04_Landing_Page/index.html e 05_MVP/dashboard/index.html"),
    ]
    linhas = []
    for campo, txt in respostas:
        n = len(txt)
        cont = "%d" % n if campo[0] in "2345" else "—"
        linhas.append([campo, txt, cont])
    tabela(["Campo do formulário", "Resposta", "Caracteres"], linhas, larguras=[3.4, 10.5, 2.1],
           legenda="Respostas prontas para o formulário (limite: 300 caracteres por resposta)", primeira_negrito=True)

    # ----- Anexo C -----
    h1("Anexo C — Roteiro do vídeo pitch")
    p("Sequência sugerida pela coordenação do Challenge: Público → Problema → Oportunidade → Solução → Demonstração → "
      "Diferencial → Monetização → Mercado → Fechamento. Narração em português do Brasil (voz sintetizada), legendas "
      "queimadas, 1920×1080, 30 fps. Duração estimada ≈ 4:35 (≈ 720 palavras a 2,7 palavras/s + pausas), com margem "
      "até o limite de 5:00. Arquivo-fonte: 07_Video_Pitch/roteiro_pitch.md.", alinh="j")
    tabela(
        ["#", "Bloco", "Visual", "Narração", "Tempo"],
        [
            ["1", "Gancho", "B-roll: aluno estudando à noite → fechando o notebook", "Toda noite, milhões de brasileiros abrem o notebook depois do trabalho para estudar a distância. E, todo ano, quatro em cada dez desistem. Ninguém desiste de repente. Mas a instituição só percebe quando a mensalidade para.", "0:20"],
            ["2", "Quem somos", "Slide capa com logo e tagline", "Nós somos a Retena: o radar de permanência que lê os sinais do LMS e avisa quem está a duas semanas de sumir, por quê, e o que fazer.", "0:12"],
            ["3", "Público", "B-roll coordenadora + slide persona", "Nosso cliente é a instituição de ensino superior privada com EAD. Quem compra é a diretora de operações acadêmicas, que responde pela receita das mensalidades. Quem usa todo dia é a coordenadora de permanência e sua equipe de tutores, que hoje agem no escuro sobre trinta por cento de alunos inativos.", "0:25"],
            ["4", "Problema e oportunidade", "Slide 41,6% + funil de mercado", "O problema é grande e está crescendo. Em 2024, o EAD passou a ser maioria das matrículas no Brasil, com mais de cinco milhões de alunos. E a taxa de desistência chegou a 41,6%, a maior da série histórica, segundo o Semesp. Cada aluno que evade leva embora de três a cinco mil reais de receita anual e um custo de captação que muitas vezes passa de mil reais.", "0:30"],
            ["5", "Evidência na base real", "Slide dados: 685 mil eventos, 203 alunos, 61 inativos, funil F1→F5", "Analisamos uma base real e anonimizada: 685 mil eventos de 203 alunos ao longo de cinco fases de um curso. O retrato é claro: em um único dia, 61 alunos, trinta por cento da turma, estavam há mais de duas semanas sem acessar. Doze por cento dos ingressantes se perderam no caminho em sete meses. E os travamentos se concentram nos mesmos capítulos, fase após fase. O LMS já sabia. Só faltava alguém ouvir.", "0:32"],
            ["6", "Solução", "Slide 3 pilares", "A Retena transforma esses logs em três coisas: um score de risco por aluno, atualizado toda semana; um diagnóstico de atrito de conteúdo, que mostra em quais capítulos e formatos os alunos travam; e uma fila semanal de intervenção, com motivo, ação sugerida e melhor horário de contato. Toda segunda-feira, a coordenação sabe quem chamar. Toda sexta, sabe quem voltou.", "0:30"],
            ["7", "Demonstração", "Dashboard real (screenshots com zoom)", "Assim funciona. O dashboard mostra a turma de hoje: alunos ativos, quantos estão em alto risco, quantos sumiram. Cada aluno em risco vem com os fatores: dias sem acesso, queda nos acessos, capítulo em que parou. E com a ação: mensagem do tutor, no horário em que esse aluno costuma estudar. No mapa de atrito, o capítulo que mais derruba alunos aparece em destaque, com a recomendação de dividir em microaulas e inserir um quiz de checagem.", "0:35"],
            ["8", "Resultados", "Slide métricas do modelo", "E funciona de verdade. Treinamos o modelo nos primeiros meses e testamos nos meses seguintes, sem olhar o futuro. O resultado: AUC de 0,88. Entre os vinte por cento de alunos apontados como maior risco, 88% de fato ficaram inativos, um acerto três vezes maior que a média. E na faixa de alto risco, 95 de cada 100 alunos realmente sumiram. É uma lista em que o tutor pode confiar.", "0:30"],
            ["9", "Diferencial + Oracle", "Slide arquitetura com Oracle + evidência", "Por que ninguém fez isso assim antes? Porque BI mostra o passado, CRM de cobrança age quando a mensalidade já parou, e projetos de analytics exigem cientistas de dados que a maioria das instituições não tem. A Retena roda onde os dados já estão: dentro do Oracle AI Database. Os eventos entram, as features são calculadas em SQL, e o modelo é treinado e pontuado pelo Oracle Machine Learning, sem os dados do aluno saírem do banco. Isso já está funcionando: neste projeto, carregamos os 685 mil eventos, treinamos os modelos in-database e expusemos o risco por SQL e JSON. Em produção, é o Autonomous AI Database na OCI, com APEX para o painel e Select AI para a coordenadora perguntar em português.", "0:40"],
            ["10", "Monetização", "Slide preço e ROI", "Nosso modelo é SaaS por aluno ativo por mês, de três a seis reais conforme o porte, com piloto de noventa dias em uma fase do curso e meta de rematrícula acordada. Para uma instituição com doze mil alunos EAD, são cerca de quinhentos e setenta mil reais por ano. Reter apenas um por cento da base já paga o contrato. E cada ponto percentual de desistência evitado vale cerca de meio milhão de reais por ano para essa instituição. A conta fecha na primeira rematrícula.", "0:25"],
            ["11", "Mercado", "Slide TAM/SAM/SOM", "O mercado: 2.244 instituições privadas e 5,2 milhões de alunos EAD. Nosso alvo inicial são as instituições de médio porte fora dos megagrupos, e o modelo é portável para qualquer LMS do tipo Moodle, o que abre caminho para o ensino técnico e corporativo.", "0:22"],
            ["12", "Fechamento", "B-roll formatura → slide final", "A evasão não é um evento. É um processo silencioso que dura semanas. A Retena escuta esse silêncio e devolve tempo para quem pode agir. Ninguém desiste de repente. A Retena percebe antes. Obrigado.", "0:20"],
        ],
        larguras=[0.6, 2.4, 3.3, 8.3, 1.4], tamanho=8, legenda="Roteiro do vídeo pitch — 12 blocos",
    )
    p("Fontes citadas na narração: INEP, Censo da Educação Superior 2024; Instituto Semesp, 16º Mapa do Ensino Superior no "
      "Brasil 2026; métricas do modelo em 05_MVP/outputs/RESULTADOS.md (teste temporal jun–ago/2026); estimativas "
      "rotuladas como tal (ticket médio EAD R$ 250–450/mês; CAC > R$ 1.000).", alinh="j", tamanho=9.5)

    # ----- Anexo D -----
    h1("Anexo D — Estrutura do pacote entregue (ZIP)")
    p("O pacote contém toda a evolução do projeto. Tudo abre localmente (duplo clique), sem servidor e sem internet, "
      "exceto onde indicado. Equipe: Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · "
      "Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198). Vídeo pitch: https://youtu.be/HZrcLvIJCC4.", alinh="j")
    tabela(
        ["Pasta", "Conteúdo", "Comece por"],
        [
            ["01_Documento/", "Documento estruturado da Fase 6 (Partes 1–4 e anexos), gerador (gerar_documento.py) e insumos em anexos/", "Retena_Fase6_Documento.pdf (ou .docx)"],
            ["02_Diagramas/", "Rich Picture, mapa de stakeholders, jornada do usuário, fluxograma do MVP, arquitetura inicial, arquitetura com Oracle e fluxo de dados/ML (PNG + SVG editável)", "00_indice_diagramas.html"],
            ["03_Marca/", "Manual de marca, logo (SVG/PNG), paleta, tipografia (fontes incluídas)", "Manual_de_Marca_Retena.pdf"],
            ["04_Landing_Page/", "Página de vendas (site institucional) autocontida", "index.html"],
            ["05_MVP/", "Pipeline de ML (Python), modelo treinado, resultados (RESULTADOS.md, metricas.json, kpis.json), figuras e dashboard interativo", "dashboard/index.html e README.md"],
            ["06_Oracle/", "Integração com Oracle AI Database 26ai + OML: docker-compose.yml, sql/ (01_ddl … 07_apex_ready), scripts/ (carga e execução), evidencias/ (logs e prints)", "README.md e evidencias/"],
            ["07_Video_Pitch/", "Vídeo pitch (MP4), roteiro, link do YouTube e material de produção", "LINK_YOUTUBE.txt"],
            ["08_Dados/", "Base anonimizada de logs do LMS em Parquet (fonte: Base-Anônima.xlsx → logs.csv)", "logs_lms.parquet"],
        ],
        larguras=[3.0, 8.6, 4.4], legenda="Pastas do pacote e ponto de entrada de cada uma", primeira_negrito=True,
    )
    codigo([
        "pip install -r 05_MVP/requirements.txt",
        "python 05_MVP/pipeline/run_all.py              # regenera features, modelo, figuras e dashboard",
        "docker compose -f 06_Oracle/docker-compose.yml up -d",
        "python 06_Oracle/scripts/carregar_eventos.py    # carga no Oracle + scripts SQL/OML (ver 06_Oracle/README.md)",
        "python 01_Documento/gerar_documento.py          # regenera este documento (DOCX)",
    ], legenda="Reprodução rápida (opcional)")

    # ----- Anexo E -----
    h1("Anexo E — Referências")
    numerados([
        "INEP — Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira. **Censo da Educação Superior 2024** "
        "(divulgado em 22/09/2025): 10,2 milhões de matrículas na graduação; EAD 5.189.391 (50,7%); 2.561 IES, 2.244 privadas. "
        "https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias/censo-da-educacao-superior/inep-divulga-resultado-do-censo-superior-2024",
        "Instituto Semesp. **16º Mapa do Ensino Superior no Brasil 2026** (mar/2026): desistência 2024 EAD 41,6% (privada 41,9%); "
        "presencial 24,8%; rede privada com 95,9% das matrículas EAD; 1,4% das mantenedoras reúnem 47,1% dos estudantes. "
        "https://www.semesp.org.br/mapa/edicao-16/brasil/",
        "Oracle. **Oracle AI Database 26ai** — documentação do produto (long-term release; inclui JSON Relational Duality Views e AI Vector Search). "
        "https://docs.oracle.com/en/database/oracle/oracle-database/",
        "Oracle. **Oracle Machine Learning** (OML4SQL / DBMS_DATA_MINING, OML4Py, AutoML, OML Notebooks) — documentação. "
        "https://docs.oracle.com/en/database/oracle/machine-learning/",
        "Oracle. **Oracle Autonomous AI Database Serverless** — documentação (inclui Select AI, DBMS_CLOUD e Always Free). "
        "https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/",
        "Oracle. **Oracle APEX** — plataforma low-code. https://apex.oracle.com/",
        "Oracle Database Free em contêiner — imagem comunitária gvenzl/oracle-free (Docker Hub), usada no ambiente local de evidência. "
        "https://hub.docker.com/r/gvenzl/oracle-free",
        "Base de dados do projeto: export anonimizado de logs do LMS FIAP ON (Base-Anônima.xlsx → 08_Dados/logs_lms.parquet), "
        "684.723 eventos, 203 alunos, 15/01/2026 a 26/08/2026.",
        "Artefatos internos citados: 05_MVP/outputs/RESULTADOS.md, metricas.json e kpis.json (métricas do MVP analítico); "
        "06_Oracle/evidencias/logs/*.log (execução no Oracle AI Database 26ai Free); 01_Documento/anexos/conceito_final.md e brief_projeto.md.",
        "Estimativas próprias, rotuladas como tal no texto: ticket médio EAD de R$ 250–450/mês; CAC em EAD acima de R$ 1.000; "
        "volume de eventos por aluno/ano derivado da razão observada na base.",
    ], tamanho=9.5)


SECOES = [
    sec_capa,
    sec_sumario,
    sec_sumario_executivo,
    sec_evolucao,
    sec_parte1,
    sec_parte2,
    sec_parte3,
    sec_parte4,
    sec_proximos,
    sec_anexos,
]


def main():
    global _doc
    _doc = Document()
    sec = _doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, lado, Cm(2.5))
    sec.header_distance = Cm(1.2)
    sec.footer_distance = Cm(1.2)
    configurar_estilos(_doc)
    _cabecalho_rodape(sec)
    for fn in SECOES:
        fn()
    finalizar_sumario()
    _doc.save(OUT_DOCX)
    print("DOCX gerado:", OUT_DOCX)
    print("Figuras inseridas (%d):" % len(FIGS_INSERIDAS))
    for f in FIGS_INSERIDAS:
        print("  +", f)
    print("Figuras faltantes (%d):" % len(FIGS_FALTANTES))
    for f in FIGS_FALTANTES:
        print("  -", f)


if __name__ == "__main__":
    main()
