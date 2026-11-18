# -*- coding: utf-8 -*-
"""
consolidar_testes.py - consolida os testes REAIS com usuários do MVP Retena.

Lê as fichas preenchidas (P1_ficha.md, P2_ficha.md, ... a partir de formulario_participante.md) e a planilha
consolidacao_testes.xlsx (só os valores digitados; as fórmulas do Excel são recalculadas aqui).
A planilha tem prioridade; o que estiver só na ficha completa. Divergências entre as duas são avisadas.

Gera (com --aplicar):
  resultados_testes.md    relatório completo dos testes (para o ZIP e para a banca)
  resultados_testes.json  números usados pelo pitch (slide 13) e pelo vídeo (cena 16)
  e reescreve, no documento, as seções 2.3 e 2.4 (entre <!-- TESTES:INICIO --> e <!-- TESTES:FIM -->),
  a linha "Usuários" da tabela 2.1, o parágrafo do sumário executivo e a linha do Anexo B.

Regras: só conta como sessão realizada o participante com data preenchida e consentimento "sim".
Nada é inventado: campo vazio vira "—". A conclusão qualitativa vem de conclusao_equipe.md (texto escrito
por quem leu as fichas); sem ele, o documento mostra um marcador [A REDIGIR] e o script avisa.

Uso:
  python consolidar_testes.py                       # confere e mostra o resumo, sem gravar nada
  python consolidar_testes.py --aplicar             # grava resultados_testes.* e atualiza o documento
  python consolidar_testes.py --pasta X --doc Y.md --aplicar   # ensaio com dados de exemplo, fora da entrega
"""
import argparse, datetime as dt, json, re, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DOC_PADRAO = AQUI.parent / "03_Documento" / "Retena_Documento_Final.md"
MARCA_EXEMPLO = "EXEMPLO_NAO_ENTREGAR.txt"

TAREFAS = {
    "T1": ("Quem chamar primeiro", 60, 0.8),
    "T2": ("Entender o risco / \"e se\"", 120, 0.6),
    "T3": ("Registrar resultado no Oracle", 150, 0.8),
    "T4": ("Filtros e grupos", 90, 0.6),
    "T5": ("Receita, ticket e meta", 120, 0.6),
    "T6": ("Risco por fase", 60, 0.6),
    "TX": ("(Opcional, TI) AUC, scoring e SQL", 120, None),
}
CENTRAIS = [t for t in TAREFAS if t != "TX"]
SIM = {"x", "✓", "✔", "•", "●", "*", "v"}
AVISOS = []


def aviso(msg):
    AVISOS.append(msg)


# ----------------------------------------------------------------------------- utilidades
def vazio(v):
    return v is None or (isinstance(v, str) and v.strip() in ("", "—", "-", "____", "P__", "TESTE-P__"))


def num(v):
    if vazio(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    m = re.fullmatch(r"(\d+):(\d{1,2})", s)  # 1:35 -> 95 s
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None


def br(v, casas=1):
    if v is None:
        return "—"
    s = f"{v:.{casas}f}".replace(".", ",")
    return s[:-2] if casas == 1 and s.endswith(",0") else s


def pct(v):
    return "—" if v is None else f"{v * 100:.0f}%"


def celula(t):
    """texto seguro para célula de tabela markdown"""
    if vazio(t):
        return "—"
    return re.sub(r"\s+", " ", str(t)).replace("|", "/").strip()


def marcados(cel):
    """'( ) presencial (x) Meet ( ) outro: abc' -> ['Meet']; texto livre sem parênteses volta como está."""
    if cel is None:
        return []
    toks = re.findall(r"\(\s*([^()]{0,2}?)\s*\)\s*([^()]*)", cel)
    if not toks:
        return [] if vazio(cel) else [cel.strip()]
    out = []
    for marca, rotulo in toks:
        if marca.strip().lower() in SIM:
            out.append(rotulo.strip(" :;—-") or marca)
    return out


def valor_campo(cel):
    if cel is None:
        return ""
    if "(" in cel and ")" in cel and re.search(r"\(\s*[^()]{0,2}\s*\)", cel):
        return ", ".join(marcados(cel))
    return "" if vazio(cel) else cel.strip()


def normaliza(v, opcoes):
    if vazio(v):
        return ""
    s = str(v).strip().lower()
    for o in opcoes:
        if s.startswith(o.lower()) or (o.lower() == "não" and s.startswith("nao")):
            return o
    if s in ("s", "1", "true"):
        return opcoes[0]
    if s in ("n", "0", "false"):
        return opcoes[-1]
    return str(v).strip()


# ----------------------------------------------------------------------------- fichas (.md)
def secoes(txt):
    out, atual = {}, "_topo"
    for l in txt.splitlines():
        if l.startswith("## "):
            atual = l[3:].strip(); out[atual] = []
        else:
            out.setdefault(atual, []).append(l)
    return out


def linhas_tabela(linhas):
    rows = []
    for l in linhas:
        l = l.strip()
        if l.startswith("|") and not re.match(r"^\|[-| :]+\|$", l):
            rows.append([c.strip() for c in l.strip("|").split("|")])
    return rows[1:] if rows else []  # sem o cabeçalho


def bloco_bullets(linhas, rotulo):
    out, dentro = [], False
    for l in linhas:
        s = l.strip()
        if s.startswith("**"):
            dentro = s.lower().startswith("**" + rotulo.lower())
            continue
        if dentro and s.startswith("-"):
            t = s[1:].strip()
            if t:
                out.append(t)
    return out


def ler_ficha(caminho):
    txt = caminho.read_text(encoding="utf-8-sig")
    sec = secoes(txt)
    cod = re.match(r"(P\d+)_ficha\.md$", caminho.name, re.I).group(1).upper()
    f = {"codigo": cod, "arquivo": caminho.name}
    campos = {}
    for nome in ("Sessão", "Perfil (anonimizado)"):
        for row in linhas_tabela(sec.get(nome, [])):
            if len(row) >= 2:
                campos[row[0]] = row[1]
    cod_tab = valor_campo(campos.get("Código do participante", ""))
    if cod_tab and cod_tab.upper() != cod:
        aviso(f"{caminho.name}: código na tabela ({cod_tab}) difere do nome do arquivo ({cod}); vale o nome do arquivo")
    f["data"] = valor_campo(campos.get("Data / horário", ""))
    f["modalidade"] = valor_campo(campos.get("Modalidade", ""))
    f["moderador"] = valor_campo(campos.get("Moderador / observador", ""))
    f["consentimento"] = valor_campo(campos.get("Consentimento lido e aceito", ""))
    f["gravacao"] = valor_campo(campos.get("Gravação autorizada", ""))
    f["papel"] = valor_campo(campos.get("Papel", ""))
    f["tipo_ies"] = valor_campo(campos.get("Tipo de IES", ""))
    f["tempo_funcao"] = valor_campo(campos.get("Tempo na função", ""))
    f["alunos"] = valor_campo(campos.get("Alunos sob responsabilidade (faixa)", ""))
    f["familiaridade"] = valor_campo(campos.get("Familiaridade com dashboards", ""))
    f["como_hoje"] = valor_campo(campos.get("Como identifica alunos em risco hoje", ""))
    f["persona"] = valor_campo(campos.get("Persona mais próxima", ""))

    f["tarefas"] = {}
    for row in linhas_tabela(sec.get("Tarefas", [])):
        if not row or row[0].upper() not in TAREFAS or len(row) < 7:
            continue
        res = marcados(row[3]) if "(" in row[3] else ([row[3].strip()] if row[3].strip() else [])
        res = [r.strip().upper()[:1] for r in res if r.strip()]
        if len(res) > 1:
            aviso(f"{cod} {row[0]}: mais de um resultado marcado ({res}); tarefa ignorada")
            res = []
        r = res[0] if res and res[0] in "SDN" else None
        if r or not vazio(row[4]):
            f["tarefas"][row[0].upper()] = {"res": r, "tempo": num(row[4]), "erros": num(row[5]), "obs": "" if vazio(row[6]) else row[6]}

    sus = {}
    for row in linhas_tabela(next((v for k, v in sec.items() if k.startswith("SUS")), [])):
        m = re.match(r"(\d+)\.", row[0]) if row else None
        if not m:
            continue
        cols = [i for i in range(1, 6) if i < len(row) and row[i].strip()]
        if len(cols) == 1:
            sus[int(m.group(1))] = cols[0]
        elif len(cols) > 1:
            aviso(f"{cod} SUS item {m.group(1)}: mais de uma coluna marcada; item ignorado")
    f["sus"] = sus

    val = "\n".join(sec.get("Valor", []))
    for chave, rot in (("v1", "V1"), ("v2", "V2")):
        m = re.search(rf"^- {rot}\.(.*)$", val, re.M)
        if m:
            esq, _, dir_ = m.group(1).partition("—")
            f[chave] = ", ".join(marcados(esq))
            f[chave + "_porque"] = dir_.split(":", 1)[1].strip() if ":" in dir_ else ""
    m = re.search(r"^- V3\.[^:]*:(.*)$", val, re.M)
    f["v3"] = m.group(1).strip() if m else ""
    m = re.search(r"NPS[^:]*:\s*(.*)$", val, re.M)
    f["nps"] = num(m.group(1)) if m else None

    perg = sec.get("Perguntas pós-tarefa (palavras do participante)", [])
    modelo = {"O que faria primeiro numa segunda-feira com esta tela?", "O que ficou confuso ou demorou? Termos não entendidos?",
              "Confiaria no risco e nos motivos para decidir quem chamar? Por quê?", "Como faz isso hoje? Isto substitui o quê?",
              "Que informação ou ação faltou?"}
    resp = []
    for l in perg:
        s = re.sub(r"^\d+\.\s*", "", l.strip())
        for q in modelo:
            if s.startswith(q):
                s = s[len(q):].strip(" :—-")
        if s and not s.startswith(">"):
            resp.append(s)
    f["respostas"] = resp
    obs = sec.get("Registro do observador", [])
    f["falas"] = bloco_bullets(obs, "Falas literais")
    f["dificuldades"] = bloco_bullets(obs, "Dificuldades observadas")
    f["sugestoes"] = bloco_bullets(obs, "Sugestões do participante")
    m = re.search(r"\*\*Aceita ser contatado\(a\) para o piloto\?\*\*(.*)$", "\n".join(obs), re.M)
    f["piloto"] = ", ".join(marcados(m.group(1))) if m else ""
    return f


# ----------------------------------------------------------------------------- planilha (.xlsx)
def ler_planilha(caminho):
    if not caminho.exists():
        return {"participantes": {}, "tarefas": {}, "sus": {}, "problemas": [], "conclusao": ""}
    import openpyxl
    wb = openpyxl.load_workbook(caminho, data_only=False)
    out = {"participantes": {}, "tarefas": {}, "sus": {}, "problemas": [], "conclusao": ""}

    def linhas(ws):
        cab = [c.value for c in ws[1]]
        for r in ws.iter_rows(min_row=2, values_only=True):
            yield dict(zip(cab, r))

    for d in linhas(wb["Participantes"]):
        if isinstance(d.get("ID"), str) and re.fullmatch(r"P\d+", d["ID"].strip()):
            out["participantes"][d["ID"].strip()] = d
    for d in linhas(wb["Tarefas"]):
        p, t = (d.get("Participante") or "").strip(), (d.get("Tarefa") or "").strip()
        if p and t in TAREFAS and not vazio(d.get("Sucesso (0/1)")):
            suc, dica = num(d.get("Sucesso (0/1)")), num(d.get("Com dica (0/1)")) or 0
            res = "N" if not suc else ("D" if dica else "S")
            out["tarefas"].setdefault(p, {})[t] = {"res": res, "tempo": num(d.get("Tempo (s)")), "erros": num(d.get("Erros")),
                                                   "obs": "" if vazio(d.get("Observação")) else str(d.get("Observação"))}
    ws = wb["SUS"]
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        if isinstance(r[0], str) and re.fullmatch(r"P\d+", r[0].strip()):
            itens = {i + 1: num(v) for i, v in enumerate(r[1:11]) if num(v) is not None}
            if itens:
                out["sus"][r[0].strip()] = itens
    for d in linhas(wb["Problemas"]):
        if not vazio(d.get("Descrição")):
            out["problemas"].append(d)
    ws = wb["Resumo"]
    for ref in ("B27", "A28", "B28"):
        v = ws[ref].value
        if isinstance(v, str) and v.strip() and not v.startswith("="):
            out["conclusao"] = v.strip(); break
    return out


# ----------------------------------------------------------------------------- junção e métricas
CAMPOS_XLSX = {"data": "Data", "modalidade": "Modalidade", "papel": "Papel", "tipo_ies": "Tipo de IES",
               "tempo_funcao": "Tempo na função", "alunos": "Alunos sob responsabilidade (faixa)",
               "familiaridade": "Familiaridade com dashboards", "persona": "Persona mais próxima",
               "moderador": "Moderador", "consentimento": "Consentimento (S/N)", "gravacao": "Gravação (S/N)",
               "v1": "V1 Resolveria o problema?", "v2": "V2 A IES pagaria?", "v3": "V3 O que falta", "nps": "NPS (0–10, opcional)"}


def texto(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return "" if vazio(v) else str(v).strip()


def juntar(fichas, plan):
    codigos = sorted(set(fichas) | set(c for c, d in plan["participantes"].items()
                                       if any(not vazio(v) for k, v in d.items() if k != "ID")) | set(plan["tarefas"]),
                     key=lambda c: int(c[1:]))
    parts = []
    for c in codigos:
        f = fichas.get(c, {}); x = plan["participantes"].get(c, {})
        p = {"codigo": c}
        for k, col in CAMPOS_XLSX.items():
            vx, vf = texto(x.get(col)), texto(f.get(k))
            if vx and vf and k in ("v1", "v2") and normaliza(vx, ["Sim", "Em parte", "Talvez", "Não"]) != normaliza(vf, ["Sim", "Em parte", "Talvez", "Não"]):
                aviso(f"{c} {k}: planilha '{vx}' x ficha '{vf}' (vale a planilha)")
            p[k] = vx or vf
        p["v1"] = normaliza(p["v1"], ["Sim", "Em parte", "Não"])
        p["v2"] = normaliza(p["v2"], ["Sim", "Talvez", "Não"])
        p["nps"] = num(p["nps"])
        cons = p["consentimento"].lower()
        p["consentiu"] = cons.startswith("s")
        for k in ("v1_porque", "v2_porque", "como_hoje", "falas", "dificuldades", "sugestoes", "respostas", "piloto", "arquivo"):
            p[k] = f.get(k, [] if k in ("falas", "dificuldades", "sugestoes", "respostas") else "")
        # tarefas: planilha > ficha
        tf, tx = f.get("tarefas", {}), plan["tarefas"].get(c, {})
        p["tarefas"] = {}
        for t in TAREFAS:
            a, b = tx.get(t), tf.get(t)
            if a and b and b.get("res") and a["res"] != b["res"]:
                aviso(f"{c} {t}: planilha '{a['res']}' x ficha '{b['res']}' (vale a planilha)")
            r = dict(a or b or {})
            if r and b and not r.get("obs"):
                r["obs"] = b.get("obs", "")
            if r.get("res"):
                p["tarefas"][t] = r
        # SUS: planilha > ficha, só com os 10 itens
        sx, sf = plan["sus"].get(c, {}), f.get("sus", {})
        itens = sx if len(sx) == 10 else (sf if len(sf) == 10 else None)
        if itens is None and (sx or sf):
            aviso(f"{c}: SUS incompleto ({max(len(sx), len(sf))}/10 itens); escore não calculado")
        if itens and any(not 1 <= v <= 5 for v in itens.values()):
            aviso(f"{c}: SUS com valor fora de 1–5; escore não calculado"); itens = None
        p["sus"] = None if not itens else sum((itens[i] - 1) if i % 2 else (5 - itens[i]) for i in range(1, 11)) * 2.5
        if not p["data"]:
            aviso(f"{c}: sem data da sessão — não conta como sessão realizada")
            continue
        if not p["consentiu"]:
            aviso(f"{c}: consentimento não registrado como 'sim' — sessão excluída da consolidação")
            continue
        parts.append(p)
    return parts


def media(vs):
    vs = [v for v in vs if v is not None]
    return sum(vs) / len(vs) if vs else None


def metricas(parts, plan):
    m = {"n": len(parts), "tarefas": {}}
    for t, (nome, alvo, meta) in TAREFAS.items():
        rs = [(p["codigo"], p["tarefas"][t]) for p in parts if t in p["tarefas"]]
        n = len(rs)
        ok = sum(1 for _, r in rs if r["res"] in "SD"); so = sum(1 for _, r in rs if r["res"] == "S")
        difs = [f"{c}: {r['obs']}" for c, r in rs if r.get("obs") and r["res"] in "DN"] or [f"{c}: {r['obs']}" for c, r in rs if r.get("obs")]
        m["tarefas"][t] = {"nome": nome, "alvo": alvo, "meta": meta, "n": n, "sucesso": ok, "sozinho": so,
                           "taxa": ok / n if n else None, "taxa_sozinho": so / n if n else None,
                           "tempo": media([r.get("tempo") for _, r in rs]), "erros": media([r.get("erros") for _, r in rs]),
                           "dificuldades": difs,
                           "atingiu": None if (not n or meta is None) else ok / n >= meta}
    m["sus"] = {p["codigo"]: p["sus"] for p in parts}
    m["sus_medio"] = media(list(m["sus"].values()))
    m["sus_n"] = sum(1 for v in m["sus"].values() if v is not None)
    m["v1"] = {o: sum(1 for p in parts if p["v1"] == o) for o in ("Sim", "Em parte", "Não")}
    m["v2"] = {o: sum(1 for p in parts if p["v2"] == o) for o in ("Sim", "Talvez", "Não")}
    m["v1_resp"] = sum(m["v1"].values()); m["v2_resp"] = sum(m["v2"].values())
    nps = [p["nps"] for p in parts if p["nps"] is not None]
    m["nps_valores"] = nps
    m["nps"] = (sum(1 for v in nps if v >= 9) - sum(1 for v in nps if v <= 6)) / len(nps) * 100 if nps else None
    probs = []
    for d in plan["problemas"]:
        probs.append({"id": texto(d.get("ID")), "tela": texto(d.get("Tela")), "tarefa": texto(d.get("Tarefa")),
                      "descricao": texto(d.get("Descrição")), "sev": num(d.get("Severidade (1–4)")),
                      "freq": num(d.get("Frequência (nº participantes)")), "quem": texto(d.get("Participantes afetados")),
                      "ajuste": texto(d.get("Ajuste proposto")), "status": texto(d.get("Status do ajuste")),
                      "evidencia": texto(d.get("Evidência (commit, print, nota)")), "origem": "planilha"})
    if not probs:  # sem planilha de problemas: usa as dificuldades anotadas nas fichas (sem inventar severidade)
        k = 0
        for p in parts:
            for d in p["dificuldades"]:
                k += 1
                pedacos = [s.strip() for s in d.split("·")]
                sev = num(pedacos[-1]) if len(pedacos) >= 3 else None
                probs.append({"id": f"PB{k:02d}", "tela": pedacos[0] if len(pedacos) >= 2 else "", "tarefa": "",
                              "descricao": pedacos[1] if len(pedacos) >= 2 else d, "sev": sev if sev and 1 <= sev <= 4 else None,
                              "freq": 1, "quem": p["codigo"], "ajuste": "", "status": "", "evidencia": p["arquivo"], "origem": "ficha"})
    m["problemas"] = probs
    m["sev"] = {s: sum(1 for b in probs if b["sev"] == s) for s in (1, 2, 3, 4)}
    m["sev4_sem_ajuste"] = sum(1 for b in probs if b["sev"] == 4 and b["status"].lower() != "feito")
    m["ajustes_feitos"] = sum(1 for b in probs if b["status"].lower() == "feito")

    t1, t3 = m["tarefas"]["T1"]["taxa"], m["tarefas"]["T3"]["taxa"]
    taxas = [m["tarefas"][t]["taxa"] for t in CENTRAIS if m["tarefas"][t]["taxa"] is not None]
    v1_pos = m["v1"]["Sim"] + m["v1"]["Em parte"]
    crit = [
        ("Sucesso em T1 e T3 (fluxo crítico)", "≥ 80%", f"T1 {pct(t1)} · T3 {pct(t3)}",
         None if t1 is None or t3 is None else (t1 >= 0.8 and t3 >= 0.8)),
        ("Nenhuma tarefa (T1–T6) abaixo de", "60%", f"menor taxa {pct(min(taxas)) if taxas else '—'}",
         None if len(taxas) < len(CENTRAIS) else min(taxas) >= 0.6),
        ("SUS médio", "≥ 68", f"{br(m['sus_medio'])} ({m['sus_n']} respostas)",
         None if m["sus_medio"] is None else m["sus_medio"] >= 68),
        ("Problemas severidade 4 sem ajuste", "0", str(m["sev4_sem_ajuste"]), m["sev4_sem_ajuste"] == 0),
        ("V1 \"sim\" ou \"em parte\"", "maioria", f"{v1_pos} de {m['v1_resp']}",
         None if not m["v1_resp"] else v1_pos > m["v1_resp"] / 2),
    ]
    m["criterios"] = [{"criterio": a, "meta": b, "resultado": c, "atendido": d} for a, b, c, d in crit]
    if m["n"] < 3:
        m["veredito"] = f"inconclusivo: {plural(m['n'], 'sessão real', 'sessões reais')}, abaixo do mínimo de 3"
    elif any(c["atendido"] is None for c in m["criterios"]):
        m["veredito"] = "incompleto: faltam dados para avaliar todos os critérios"
    elif all(c["atendido"] for c in m["criterios"]):
        m["veredito"] = "critérios atendidos"
    else:
        m["veredito"] = "critérios não atendidos: " + "; ".join(c["criterio"].lower() for c in m["criterios"] if not c["atendido"])
    return m


# ----------------------------------------------------------------------------- textos
def sim_nao(v):
    return "—" if v is None else ("Sim" if v else "Não")


def datas(parts):
    ds = []
    for p in parts:
        mm = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", p["data"])
        if mm:
            ds.append((int(mm.group(2)), int(mm.group(1)), f"{int(mm.group(1)):02d}/{int(mm.group(2)):02d}"))
    if not ds:
        return "—"
    ds.sort()
    return ds[0][2] if ds[0] == ds[-1] else f"{ds[0][2]} a {ds[-1][2]}"


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def anos(v):
    return f"{v} anos" if re.fullmatch(r"[<>]?\s*\d+(\s*[–-]\s*\d+)?", v or "") else v


def contagem(d, total):
    itens = [f"{v} {k.lower()}" for k, v in d.items() if v]
    return (", ".join(itens) if itens else "—") + (f" (de {total})" if total else "")


def secao_documento(parts, m, conclusao, exemplo):
    n = m["n"]; L = []
    titulo = "## 2.3 Resultados dos testes com usuários" + (" — EXEMPLO (dados fictícios)" if exemplo else "")
    L += [titulo, ""]
    if exemplo:
        L += ['<div class="pendente"><b>ENSAIO COM DADOS DE EXEMPLO.</b> Esta versão serve só para testar a consolidação automática e não faz parte da entrega.</div>', ""]
    if n < 3:
        L += [f'<div class="pendente"><b>Limitação declarada.</b> Foi realizado um total de {plural(n, "sessão", "sessões")} com usuários reais, abaixo das 3 pedidas no enunciado. '
              'Os números abaixo valem só para essas sessões; nada foi completado com dados simulados.</div>', ""]
    mods = sorted({p["modalidade"] for p in parts if p["modalidade"]})
    L += [f"**Método.** {plural(n, 'sessão moderada', 'sessões moderadas')} de 30–40 minutos com pessoas do público-alvo, no período de {datas(parts)}"
          f"{', em formato ' + ' / '.join(mods) if mods else ''}, sobre o MVP local (Oracle AI Database + OML), seguindo `02_Testes_Usuarios/protocolo_teste_mvp.md`: "
          "seis tarefas observáveis (fila, painel do aluno, registro no Oracle, filtros, diretoria), SUS e três perguntas de valor. "
          "Participantes pseudonimizados (P1, P2…); nomes e contatos não constam dos arquivos. Dados brutos: `consolidacao_testes.xlsx` e fichas `P*_ficha.md`; "
          "relatório completo: `resultados_testes.md`.", ""]
    L += ["| Participante | Papel | Tipo de IES | Tempo na função | Familiaridade com dashboards | Tarefas T1–T6 concluídas | SUS |",
          "|---|---|---|---|---|---|---|"]
    for p in parts:
        feitas = [t for t in CENTRAIS if t in p["tarefas"]]
        ok = sum(1 for t in feitas if p["tarefas"][t]["res"] in "SD")
        L.append(f"| {p['codigo']} | {celula(p['papel'])} | {celula(p['tipo_ies'])} | {celula(anos(p['tempo_funcao']))} | {celula(p['familiaridade'])} | "
                 f"{ok}/{len(feitas) if feitas else '—'} | {br(p['sus'])} |")
    L += ["", "| Tarefa | Meta | Sucesso (sozinho + com dica) | Sozinho | Tempo médio (s) / alvo | Erros médios | Principal dificuldade observada |",
          "|---|---|---|---|---|---|---|"]
    for t, d in m["tarefas"].items():
        if t == "TX" and not d["n"]:
            continue
        L.append(f"| {t} {d['nome']} | {pct(d['meta']) if d['meta'] else 'opcional'} | "
                 f"{d['sucesso']}/{d['n']} ({pct(d['taxa'])}) | {pct(d['taxa_sozinho'])} | {br(d['tempo'], 0)} / {d['alvo']} | {br(d['erros'])} | "
                 f"{celula(d['dificuldades'][0][:140]) if d['dificuldades'] else '—'} |")
    L += ["", f"**Satisfação e valor.** SUS médio **{br(m['sus_medio'])}** ({m['sus_n']} respostas; referência de mercado: 68). "
          f"\"Isso resolveria seu problema?\": {contagem(m['v1'], m['v1_resp'])}. \"A instituição pagaria?\": {contagem(m['v2'], m['v2_resp'])}."
          + (f" NPS informado por {len(m['nps_valores'])} pessoa(s): {', '.join(br(v, 0) for v in m['nps_valores'])} (amostra pequena demais para um NPS agregado)." if m["nps_valores"] else ""), ""]
    falas = [(p["codigo"], f) for p in parts for f in p["falas"]]
    if falas:
        L += ["**Feedback (falas literais, anotadas pelo observador).**", ""]
        for c, f in falas[:8]:
            f = f.strip()
            if '"' not in f and "“" not in f:
                f = '"' + f + '"'
            L.append(f"- {c}: {f}")
        L.append("")
    L += ["**Dificuldades encontradas e ajustes.**", ""]
    if m["problemas"]:
        L += ["| ID | Tela | Dificuldade observada | Severidade (1–4) | Participantes | Ajuste | Status |", "|---|---|---|---|---|---|---|"]
        for b in sorted(m["problemas"], key=lambda b: -(b["sev"] or 0)):
            L.append(f"| {celula(b['id'])} | {celula(b['tela'])} | {celula(b['descricao'])} | {br(b['sev'], 0)} | {celula(b['quem'])} | "
                     f"{celula(b['ajuste'])} | {celula(b['status']) if b['status'] else 'a definir'} |")
        L += ["", "Severidade: 1 cosmético · 2 menor · 3 grave · 4 impeditivo."]
    else:
        L.append("Nenhuma dificuldade registrada nas fichas ou na planilha.")
    L += ["", "## 2.4 O MVP resolve o problema?", ""]
    L += ["**Evidência técnica (real, anterior aos testes):** o sinal existe e é forte (AUC 0,95 em teste temporal; 85% dos casos da faixa alta "
          "ficaram de fato 21 dias inativos no teste, contra 5% na faixa baixa) e o ciclo fila → contato → resultado → receita funciona de ponta a ponta no banco.", ""]
    L += ["**Evidência com usuários (seção 2.3), contra os critérios definidos antes dos testes:**", "",
          "| Critério | Meta | Resultado | Atendido? |", "|---|---|---|---|"]
    for c in m["criterios"]:
        L.append(f"| {c['criterio']} | {c['meta']} | {c['resultado']} | {sim_nao(c['atendido'])} |")
    L += ["", f"**Leitura dos números:** {m['veredito']}" + (" — com menos de 3 sessões, nenhum critério é conclusivo." if n < 3 else ".")
          + " Amostra pequena: os resultados indicam direção, não significância estatística.", ""]
    if conclusao:
        L += ["**Conclusão da equipe.** " + conclusao.strip(), ""]
    else:
        L += ["**Conclusão da equipe.** [A REDIGIR depois da leitura das fichas: grave o texto em `02_Testes_Usuarios/conclusao_equipe.md` e rode de novo `consolidar_testes.py --aplicar`.]", ""]
    prox = [b for b in m["problemas"] if b["ajuste"] and b["status"].lower() != "feito"]
    feitos = [b for b in m["problemas"] if b["status"].lower() == "feito"]
    if feitos:
        L += ["**Ajustes já feitos a partir dos testes:** " + "; ".join(f"{b['ajuste']} ({b['id']})" for b in feitos) + ".", ""]
    if prox:
        L += ["**Próximos ajustes (para o piloto):**", ""] + [f"{i}. {b['ajuste']} ({b['id']}, severidade {br(b['sev'], 0)})" for i, b in enumerate(prox, 1)] + [""]
    L += ["**Ajustes feitos antes dos testes, a partir da revisão interna (não de usuários):** fila priorizada por recuperabilidade; botão \"e se ele voltar\"; "
          "mensagem sugerida que usa o nome do responsável; ticket da IES persistido no banco; separação entre \"reativado\" e \"plano combinado\" para não inflar a receita preservada."]
    return "\n".join(L)


def relatorio_completo(parts, m, conclusao, exemplo):
    L = ["# Testes com usuários do MVP Retena — resultados consolidados", ""]
    if exemplo:
        L += ["> **EXEMPLO COM DADOS FICTÍCIOS — não faz parte da entrega.**", ""]
    L += [f"> Gerado por `consolidar_testes.py` em {dt.datetime.now():%d/%m/%Y %H:%M} a partir de {len(parts)} ficha(s)/linha(s) de planilha. "
          "Só sessões com data e consentimento registrados entram. Campos não informados aparecem como \"—\".", ""]
    L.append(secao_documento(parts, m, conclusao, exemplo).replace("## 2.3 ", "## ").replace("## 2.4 ", "## "))
    L += ["", "## Detalhe por participante", ""]
    for p in parts:
        L += [f"### {p['codigo']} — {celula(p['papel'])}", "",
              f"- Sessão: {celula(p['data'])} · {celula(p['modalidade'])} · moderação: {celula(p['moderador'])} · gravação: {celula(p['gravacao'])}",
              f"- Perfil: {celula(p['tipo_ies'])} · {celula(p['tempo_funcao'])} na função · {celula(p['alunos'])} alunos · familiaridade com dashboards: {celula(p['familiaridade'])} · persona: {celula(p['persona'])}",
              f"- Como identifica alunos em risco hoje: {celula(p['como_hoje'])}",
              f"- SUS: {br(p['sus'])} · V1: {celula(p['v1'])} {('(' + p['v1_porque'] + ')') if p['v1_porque'] else ''} · V2: {celula(p['v2'])} {('(' + p['v2_porque'] + ')') if p['v2_porque'] else ''} · NPS: {br(p['nps'], 0)}",
              f"- O que falta para usar no próximo semestre: {celula(p['v3'])}",
              f"- Aceita contato para o piloto: {celula(p['piloto'])}", "",
              "| Tarefa | Resultado | Tempo (s) | Erros | Observação |", "|---|---|---|---|---|"]
        for t in TAREFAS:
            r = p["tarefas"].get(t)
            if r:
                rot = {"S": "sozinho", "D": "com dica", "N": "não concluiu"}[r["res"]]
                L.append(f"| {t} | {rot} | {br(r.get('tempo'), 0)} | {br(r.get('erros'), 0)} | {celula(r.get('obs'))} |")
        L.append("")
        for rot, chave in (("Respostas pós-tarefa", "respostas"), ("Falas literais", "falas"), ("Dificuldades observadas", "dificuldades"), ("Sugestões", "sugestoes")):
            if p[chave]:
                L += [f"**{rot}:**", ""] + [f"- {x}" for x in p[chave]] + [""]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- documento
def aplicar_no_documento(doc, parts, m, conclusao, exemplo):
    txt = doc.read_text(encoding="utf-8")
    nl = "\r\n" if "\r\n" in txt else "\n"
    t = txt.replace("\r\n", "\n")
    ini = re.search(r"<!-- TESTES:INICIO[^>]*-->\n", t); fim = t.find("<!-- TESTES:FIM -->")
    if not ini or fim < 0:
        sys.exit(f"marcadores <!-- TESTES:INICIO --> / <!-- TESTES:FIM --> não encontrados em {doc}")
    t = t[:ini.end()] + secao_documento(parts, m, conclusao, exemplo) + "\n" + t[fim:]
    t1, t3 = m["tarefas"]["T1"], m["tarefas"]["T3"]
    resumo = (f"sucesso de {pct(t1['taxa'])} em \"quem chamar primeiro\" e {pct(t3['taxa'])} em \"registrar no Oracle\", "
              f"SUS médio {br(m['sus_medio'])}")
    sub = [
        (r"^\*\*(O que ainda depende da equipe|Testes com usuários)\.\*\*.*$",
         f"**Testes com usuários.** {plural(m['n'], 'sessão real', 'sessões reais')} com o público-alvo ({datas(parts)}): {resumo}; {m['veredito']}. "
         + ("Abaixo das 3 sessões pedidas: limitação declarada na seção 2.3. " if m["n"] < 3 else "")
         + "Detalhes, dificuldades e ajustes na seção 2.3." + (" [EXEMPLO]" if exemplo else "")),
        (r"^\| Usuários — teste do MVP final \|.*$",
         f"| Usuários — teste do MVP final | {plural(m['n'], 'sessão moderada', 'sessões moderadas')}: 6 tarefas, SUS e perguntas de valor | "
         + ("**EXEMPLO (fictício)**" if exemplo else "**Real**")
         + (f" ({m['n']} de 3)" if m["n"] < 3 else "") + f" | {resumo} (seção 2.3) |"),
        (r"^\| `11_Entrega_Final/02_Testes_Usuarios` \|.*$",
         "| `11_Entrega_Final/02_Testes_Usuarios` | Protocolo, ficha, planilha preenchida, fichas anonimizadas (`P*_ficha.md`) e resultados consolidados (`resultados_testes.md`) |"),
    ]
    for padrao, novo in sub:
        t, k = re.subn(padrao, lambda _m: novo, t, count=1, flags=re.M)
        if not k:
            aviso(f"documento: trecho não encontrado para atualizar ({padrao[:45]}…)")
    doc.write_text(t.replace("\n", nl), encoding="utf-8", newline="")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pasta", default=str(AQUI), help="pasta com P*_ficha.md e consolidacao_testes.xlsx")
    ap.add_argument("--doc", default=str(DOC_PADRAO), help="documento .md com os marcadores TESTES")
    ap.add_argument("--aplicar", action="store_true", help="grava resultados_testes.* e atualiza o documento")
    a = ap.parse_args()
    pasta, doc = Path(a.pasta).resolve(), Path(a.doc).resolve()
    exemplo = (pasta / MARCA_EXEMPLO).exists()
    if exemplo and doc == DOC_PADRAO.resolve() and a.aplicar:
        sys.exit("pasta de EXEMPLO não pode atualizar o documento da entrega; use --doc com uma cópia")
    if not exemplo and pasta == AQUI and doc != DOC_PADRAO.resolve():
        aviso("dados reais aplicados a um documento que não é o da entrega")

    fichas = {}
    for f in sorted(pasta.glob("P*_ficha.md")):
        if re.fullmatch(r"P\d+_ficha\.md", f.name, re.I):
            fichas[f.name.split("_")[0].upper()] = ler_ficha(f)
    plan = ler_planilha(pasta / "consolidacao_testes.xlsx")
    parts = juntar(fichas, plan)
    m = metricas(parts, plan)
    conc_arq = pasta / "conclusao_equipe.md"
    conclusao = conc_arq.read_text(encoding="utf-8").strip() if conc_arq.exists() else plan["conclusao"]
    conclusao = re.sub(r"^#.*\n+", "", conclusao).strip() if conclusao else ""

    print(f"Fichas: {len(fichas)} · sessões válidas: {m['n']} ({', '.join(p['codigo'] for p in parts) or '—'})" + ("  [EXEMPLO]" if exemplo else ""))
    for t, d in m["tarefas"].items():
        if d["n"]:
            print(f"  {t}: {d['sucesso']}/{d['n']} ({pct(d['taxa'])}), tempo médio {br(d['tempo'], 0)} s")
    print(f"  SUS médio: {br(m['sus_medio'])} ({m['sus_n']} respostas) · V1: {m['v1']} · V2: {m['v2']}")
    print(f"  Problemas: {len(m['problemas'])} (sev4 sem ajuste: {m['sev4_sem_ajuste']}) · veredito: {m['veredito']}")
    print(f"  Conclusão da equipe: {'sim' if conclusao else 'NÃO (documento terá marcador [A REDIGIR])'}")
    if m["n"] == 0:
        print("Nenhuma sessão válida: nada a consolidar (o documento continua com a seção PENDENTE).")
        for x in AVISOS:
            print("  aviso:", x)
        return 2
    if a.aplicar:
        (pasta / "resultados_testes.md").write_text(relatorio_completo(parts, m, conclusao, exemplo), encoding="utf-8")
        resumo = {"gerado_em": dt.datetime.now().isoformat(timespec="seconds"), "exemplo": exemplo, "n": m["n"], "datas": datas(parts),
                  "participantes": [{"codigo": p["codigo"], "papel": p["papel"], "sus": p["sus"]} for p in parts],
                  "tarefas": {t: {k: d[k] for k in ("nome", "n", "sucesso", "sozinho", "taxa", "tempo", "atingiu")} for t, d in m["tarefas"].items()},
                  "sus_medio": m["sus_medio"], "sus_n": m["sus_n"], "v1": m["v1"], "v2": m["v2"], "nps_valores": m["nps_valores"],
                  "problemas": len(m["problemas"]), "sev": m["sev"], "ajustes_feitos": m["ajustes_feitos"],
                  "ajustes": [b["ajuste"] for b in m["problemas"] if b["ajuste"]][:5],
                  "criterios": m["criterios"], "veredito": m["veredito"], "tem_conclusao": bool(conclusao)}
        (pasta / "resultados_testes.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        aplicar_no_documento(doc, parts, m, conclusao, exemplo)
        print("Gravado:", pasta / "resultados_testes.md", "|", pasta / "resultados_testes.json", "| documento:", doc)
    else:
        print("(conferência apenas; use --aplicar para gravar)")
    for x in AVISOS:
        print("  aviso:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
