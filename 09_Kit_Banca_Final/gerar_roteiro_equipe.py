# -*- coding: utf-8 -*-
"""
Roteiro da apresentação por pessoa (Banca Final, 23/09/2026) — fala de cada slide, tempos, passagens de bastão e quem responde o quê.
Lê sorteio_blocos.json (gerado uma vez com random.SystemRandom) e produz:
  Retena_Roteiro_Equipe.html / .pdf     (PDF via Edge headless, fontes Sora/Inter da marca)
  Retena_Roteiro_Equipe_WhatsApp.txt    (mensagem curta para o grupo)
Uso: python gerar_roteiro_equipe.py
"""
import os, json, subprocess, html

AQUI = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(AQUI)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONTES = "file:///" + os.path.join(ROOT, "03_Marca", "fontes").replace("\\", "/")
LOGO = "file:///" + os.path.join(ROOT, "03_Marca", "logo", "retena_horizontal_escuro_sobre_claro.svg").replace("\\", "/")

sorteio = json.load(open(os.path.join(AQUI, "sorteio_blocos.json"), encoding="utf-8"))
A = sorteio["atribuicao"]; MVP = sorteio["mvp"]
P = {"B1": A["B1"], "B2": A["B2"], "B3": A["B3"], "B4": A["B4"], "MVP": MVP}
primeiro = lambda n: n.split()[0] if not n.startswith("Lucas") else n  # "Lucas Dalmas" fica completo para não confundir os Lucas

BLOCOS = [
    ("B1", "Abertura e problema", "1–4", "1:30"),
    ("B2", "Para quem, solução e como funciona", "5–7", "1:25"),
    ("MVP", "Demonstração do MVP e resultados", "8–9", "1:40"),
    ("B3", "Oracle e modelo de negócio", "10–13", "2:05"),
    ("B4", "Marketing, mercado, impacto, equipe e fechamento", "14–18", "1:45"),
]

# (slide, título, tempo, bloco, o que está na tela, fala)
FALAS = [
    (1, "Capa", "0:20", "B1", "Capa com a tagline.",
     "Boa noite. Toda noite, milhões de brasileiros abrem o notebook depois do trabalho para estudar a distância. Todo ano, quatro em cada dez desistem. Ninguém desiste de repente — mas a instituição só percebe quando a mensalidade para. Nós somos a Retena, e em oito minutos vamos mostrar como perceber antes."),
    (2, "Gancho", "0:15", "B1", "Foto do campus; 5,2 milhões / quatro em cada dez.",
     "Você já reparou como as turmas EAD começam cheias e vão esvaziando? São 5,2 milhões de alunos, metade do ensino superior brasileiro. 41,6% desistem por ano — recorde da série histórica. É o problema que todo mundo vê e ninguém mede a tempo."),
    (3, "Antes e depois", "0:30", "B1", "Duas colunas: Antes × Com a Retena.",
     "Hoje a instituição reage: descobre a evasão no financeiro, quando a mensalidade já parou; age com e-mail genérico e desconto de emergência; a coordenação prioriza no escuro; e ninguém mede quantos voltaram. Com a Retena ela antecipa: na segunda de manhã a coordenação recebe quem está a duas semanas de sumir, por quê e o que dizer; contata no horário em que o aluno estuda; registra o resultado e mede em reais."),
    (4, "Tarde demais", "0:25", "B1", "30% em coral; círculo com 61 alunos; 0 alertas.",
     "Isto não é hipótese. É a base real de uma instituição parceira: 685 mil eventos de LMS de 203 alunos, anonimizados. Em um único dia, 61 alunos — 30% da turma — estavam há mais de duas semanas sem acessar. Zero alertas. Em sete meses, 12% dos ingressantes se perderam. O LMS registrou cada sinal. Faltava alguém ouvir. — {B2} mostra para quem construímos e o que entregamos."),
    (5, "Para quem", "0:20", "B2", "Três cards: Renata, Mariana e o aluno.",
     "Nosso cliente é a instituição privada com EAD. Quem compra é a diretora de operações — a Renata —, que responde pela receita das mensalidades. Quem usa toda segunda é a Mariana, coordenadora de permanência, com seus tutores. E quem ganha é o aluno trabalhador, que estuda das sete às dez da noite."),
    (6, "A solução", "0:30", "B2", "QUEM · ONDE · QUANTO.",
     "A Retena transforma os logs que o LMS já registra em três respostas que o BI não dá. Quem: um score de risco por aluno, explicado em linguagem simples. Onde: o mapa de atrito de conteúdo, o capítulo em que os alunos travam. E quanto: a fila de segunda-feira, com quem chamar, por quê, quando e o que dizer — e o resultado medido em reais. Tudo dentro do banco que a instituição já usa."),
    (7, "Como funciona", "0:35", "B2", "Quatro passos com as ferramentas Oracle.",
     "Em quatro passos. Um: a instituição conecta o LMS, por export CSV ou API, ao banco Oracle — a nossa carga de 684 mil eventos levou 72 segundos. Dois: o risco nasce dentro do banco, com features em SQL e Oracle Machine Learning pontuando cada aluno toda semana; o dado não sai da instituição. Três: a fila chega à coordenação em APEX. Quatro: o resultado volta em reais e o modelo retreina. Sem servidor de ML, sem cientista de dados dedicado. — Agora {MVP} mostra isso funcionando."),
    (8, "Demonstração ao vivo", "1:00", "MVP", "Trocar para o navegador: dashboard publicado, visão Diretoria.",
     "Este é o painel publicado, com a base real. Na visão da diretoria, quatro números: 61 alunos para chamar esta semana; a receita anual em risco — com ticket de 350 reais, 231 mil; se reativarmos um em cada três, 75 mil preservados; e 62 alunos que já silenciaram sem nenhum alerta. Mudo o ticket para 500 e tudo recalcula na hora. Na visão da coordenação, a fila de segunda: busco o Aluno 0227, clico, e aparece o motivo em linguagem simples e a ação sugerida, com o horário certo de contato. Mais abaixo, o mapa de atrito: o capítulo 2 da fase 4 é onde mais alunos travam. E para o time técnico há uma visão separada com métricas e calibração. (Se a internet falhar: slide A1 do apêndice.)"),
    (9, "Resultados", "0:40", "MVP", "Voltar aos slides: 95 em 100, 3×, 0,88; gráfico por faixa.",
     "Funciona? Testamos no futuro: treinamos até maio e testamos de junho a agosto, sem olhar o que ia acontecer. Dos alunos que apontamos como alto risco, 95 em cada 100 de fato sumiram; priorizar pela Retena acerta três vezes mais do que escolher ao acaso; AUC de 0,88. E não é só a nossa amostra: rodamos o mesmo método em 24 mil alunos da Open University e deu 0,92. Dizemos as limitações na cara: amostra de um curso, prevemos silêncio e não cancelamento, e antecipar é mais difícil do que confirmar. — {B3} explica por que isso roda dentro do Oracle."),
    (10, "Por que dentro do Oracle", "0:30", "B3", "Três pilares: LGPD, sem projeto de TI, escala e canal.",
     "Três razões de negócio, não de tecnologia. LGPD: o dado do aluno nunca sai do banco que a instituição já controla — a objeção número um da diretoria desaparece. Sem projeto de TI: features em SQL, Oracle Machine Learning, painel em APEX; primeira fila em 30 dias, sem cientista de dados. E escala e canal: Autonomous Serverless com custo marginal perto de zero, em um setor cujos ERPs e megagrupos já rodam Oracle."),
    (11, "Integração executada", "0:30", "B3", "Print da evidência; 684.723 · 3 modelos · AUC 0,949 · SQL + JSON.",
     "E isso não é um desenho. Carregamos os 685 mil eventos no Oracle AI Database 26ai, calculamos as features em SQL, treinamos três modelos dentro do banco com DBMS_DATA_MINING e expusemos o risco por SQL e JSON. Random Forest com AUC 0,949 no teste temporal. Reexecutamos tudo do zero ontem, sem erros, com evidências e timestamps no repositório. Se perguntarem sobre 0,88 e 0,95: são duas implementações independentes do mesmo problema, ambas com teste temporal."),
    (12, "Ferramentas Oracle", "0:25", "B3", "Tabela: executado × runbook × NEXT × roadmap.",
     "Para a banca ver de uma vez: cinco componentes já executados — o banco 26ai, Oracle Machine Learning, views JSON e Duality View, DBMS_SCHEDULER para o job semanal e a carga via python-oracledb. Autonomous e Object Storage têm runbook pronto de 60 minutos; APEX vai ao NEXT em 24 de outubro; Select AI está no roadmap."),
    (13, "Modelo de negócio", "0:40", "B3", "R$ 4,00; três planos; a conta do cliente de 12 mil alunos.",
     "Como ganhamos dinheiro: assinatura por aluno ativo, por mês. Seis reais até 10 mil alunos, quatro de 10 a 50 mil, três para megagrupos, e um plano Essencial para instituições pequenas. A porta de entrada é um piloto de 90 dias com meta de rematrícula. A conta: uma IES de 12 mil alunos paga 576 mil por ano; reter 137 alunos — 1,1% da base — já paga o contrato; e cada ponto de desistência evitado vale meio milhão. Quem paga é a diretoria, porque compramos rematrícula para ela. — {B4} fecha com como chegamos até essa diretoria."),
    (14, "Marketing digital e aquisição", "0:35", "B4", "Funil em quatro etapas; metas do ano 1.",
     "Nosso funil digital tem quatro etapas. Atrair: landing page com vídeo de vendas e calculadora de ROI, já publicadas, conteúdo com dados do INEP e da Semesp e prospecção direta de diretores de operações. Diagnosticar: de graça — a instituição manda o export do LMS e recebe em 7 dias o painel de receita em risco. Provar: piloto de 90 dias pago. Expandir: contrato anual e o ecossistema Oracle. Metas do ano 1: 30 diagnósticos, 6 pilotos, 2 a 3 contratos e custo de aquisição pago em menos de um trimestre."),
    (15, "Mercado", "0:15", "B4", "TAM · SAM · SOM; go-to-market em três anos.",
     "O mercado: 2.244 instituições privadas e 5,2 milhões de alunos EAD. TAM de 249 milhões por ano; o alvo inicial são as IES médias fora dos megagrupos; e a meta em três anos é de 2,5 a 4,3 milhões de receita recorrente."),
    (16, "Impacto e próximos passos", "0:25", "B4", "Aluno · Instituição · Sociedade; linha do tempo; pedidos.",
     "O impacto: para o aluno, uma formatura; para a instituição, meio milhão por ponto de desistência evitado; para a sociedade, mais formandos no EAD, que já é metade do ensino superior. Próximos passos: NEXT em 24 de outubro com Autonomous e APEX, e o piloto de 90 dias. O que pedimos à banca: apoio ao Always Free, uma instituição parceira e mentoria comercial."),
    (17, "Equipe", "0:10", "B4", "Cinco cards.",
     "Somos cinco engenheiros de software do quarto ano. Tudo o que mostramos está publicado e reproduzível."),
    (18, "Fechamento", "0:20", "B4", "QR codes: vídeo, site, repositório.",
     "A evasão não é um evento. É um silêncio que dura semanas. A Retena escuta esse silêncio, dentro do banco que a instituição já usa, e devolve tempo para quem pode agir. Ninguém desiste de repente. A Retena percebe antes. Obrigado."),
]

PERGUNTAS = {
    "B1": ["\"203 alunos é pouco\" → validação temporal, subconjunto acionável (AUC 0,74), retreino por IES; OULAD com 24 mil alunos confirma (quem apresentou o MVP complementa).",
           "\"Como validaram com o mercado?\" → dados reais, INEP/Semesp e instrumento de 12 perguntas. REGRA DE HONESTIDADE: as 8 entrevistas foram simuladas com personas sintéticas para calibrar o roteiro, estão rotuladas assim no documento e serão confirmadas em campo antes do piloto. Responder exatamente isso.",
           "Fontes dos números do problema: INEP Censo 2024 (5,19 mi EAD, 50,7%); Semesp, 16º Mapa 2026 (41,6%)."],
    "B2": ["\"O que exatamente vocês preveem?\" → probabilidade de 21 dias sem ação no LMS (proxy de evasão), recalculada todo domingo; segundo modelo antecipa quem não inicia a próxima fase (AUC 0,93).",
           "\"Isso não é só um BI?\" → BI mostra o passado, CRM cobra tarde; a Retena antecipa, prioriza e fecha o ciclo com resultado em R$ e retreino (apêndice A11).",
           "\"E a LGPD / vigilância do aluno?\" → processamento dentro do banco da IES, pseudonimização fora do painel, base legal do contrato educacional, tom de apoio (apêndice A6). Perguntas sobre o mapa de atrito e a jornada da coordenadora (A13, A7)."],
    "MVP": ["Tudo sobre o MVP e o modelo: features, split temporal, métricas (A2), benchmark com os modelos do colega (A10), OULAD (A4) e por que não usamos split aleatório (A5).",
            "\"Por que 0,88 e 0,95 são diferentes?\" → implementações independentes (Python × in-database), ambas com teste temporal; o ponto é que o sinal existe e roda dentro do banco.",
            "Demonstração de reserva: apêndice A1."],
    "B3": ["\"Quais ferramentas Oracle usaram de fato?\" → 5 executadas (26ai, OML/DBMS_DATA_MINING, views JSON + Duality View, DBMS_SCHEDULER, python-oracledb), 2 com runbook (Autonomous, Object Storage/DBMS_CLOUD), APEX no NEXT, Select AI no roadmap (slide 12, apêndice A6/A15).",
           "\"Por que Oracle e não Python com qualquer banco?\" → LGPD, time-to-value e canal (slide 10).",
           "\"Como escala? Quanto custa operar?\" → um schema por IES no Autonomous Serverless, auto-scaling, custo marginal ≈ 0, margem bruta alvo 80%; \"Quem paga e quanto?\" → slide 13."],
    "B4": ["\"Como o marketing traz clientes de forma rentável?\" → funil atrair → diagnóstico gratuito → piloto pago → contrato; metas do ano 1 são metas, medidas no funil.",
           "\"Concorrentes?\" → BI embarcado (Moodle Analytics, Canvas Insights), consultorias, CRMs; ninguém junta risco + atrito + resultado em R$ dentro do banco da IES.",
           "\"Riscos?\" → apêndice A8 (dados por IES, orçamento da coordenação, integração, LGPD, nome 'retina'). \"Por que a Oracle deveria apostar?\" → consumo recorrente de Autonomous/OML/APEX por IES, setor que já roda Oracle, prova executada."],
}

def fmt(t): return t.format(**{k: primeiro(v) for k, v in P.items()})

CSS = f"""
@font-face{{font-family:'Sora';src:url('{FONTES}/Sora-Variable.ttf');font-weight:100 800}}
@font-face{{font-family:'Inter';src:url('{FONTES}/Inter-Variable.ttf');font-weight:100 900}}
@page{{size:A4;margin:13mm 15mm 15mm}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,'Segoe UI',sans-serif;color:#3A4A5C;background:#fff;font-size:9.8pt;line-height:1.42}}
h1,h2,h3{{font-family:Sora,Inter,sans-serif;color:#0B2545;margin:0}}
.cab{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #2EC4B6;padding-bottom:4mm;margin-bottom:6mm}} .cab img{{height:10mm}} .cab .meta{{text-align:right;font-size:8.5pt;color:#94A3B8}}
.eyebrow{{font-size:8.5pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#2EC4B6;margin-bottom:2mm}}
h1{{font-size:21pt;line-height:1.1;margin-bottom:3mm}} h2{{font-size:13.5pt;margin:6mm 0 3mm;page-break-after:avoid}} h3{{font-size:10.5pt;margin:3mm 0 1.5mm}}
p{{margin:0 0 2.5mm}} ul{{margin:0 0 3mm 5mm;padding:0}} li{{margin-bottom:1.5mm}}
table{{width:100%;border-collapse:collapse;font-size:9pt;margin:2mm 0 4mm}} th{{background:#0B2545;color:#fff;text-align:left;padding:2mm 2.5mm;font-weight:700}} td{{padding:2mm 2.5mm;border-bottom:1px solid #E2E8F0;vertical-align:top}} tr{{page-break-inside:avoid}}
.grid5{{display:grid;grid-template-columns:repeat(5,1fr);gap:3mm;margin:3mm 0 4mm}}
.pessoa{{border:1px solid #E2E8F0;border-radius:3mm;padding:3mm 3.5mm;background:#F6F7F9}} .pessoa .b{{font-size:8pt;font-weight:700;color:#2EC4B6;letter-spacing:.1em}} .pessoa .n{{font-family:Sora;font-weight:800;color:#0B2545;font-size:11pt;line-height:1.15;margin:1mm 0}} .pessoa .s{{font-size:8.2pt}} .pessoa.mvp{{background:#0B2545;border-color:#0B2545}} .pessoa.mvp .n,.pessoa.mvp .s{{color:#fff}}
.bloco{{border-left:4px solid #2EC4B6;padding:1mm 0 1mm 4mm;margin:0 0 4mm}} .bloco.mvp{{border-left-color:#FFB703}}
.slide{{display:grid;grid-template-columns:22mm 1fr;gap:3mm;padding:2.5mm 0;border-bottom:1px dashed #E2E8F0;page-break-inside:avoid}} .slide:last-child{{border-bottom:none}}
.slide .num{{font-family:Sora;font-weight:800;color:#0B2545;font-size:12pt;line-height:1}} .slide .num small{{display:block;font-family:Inter;font-weight:600;font-size:8pt;color:#94A3B8;margin-top:1mm}}
.slide .tit{{font-weight:700;color:#0B2545}} .slide .tela{{font-size:8.3pt;color:#94A3B8;margin:0.5mm 0 1.5mm}} .slide .fala{{color:#1F2937}}
.bast{{background:#E6F7F5;border-radius:2mm;padding:0.5mm 2mm;font-weight:700;color:#0B2545}}
.card{{background:#F6F7F9;border:1px solid #E2E8F0;border-radius:3mm;padding:3.5mm 4.5mm;margin:0 0 3.5mm}}
.nota{{background:#FFF4D6;border-radius:2.5mm;padding:3mm 4mm;font-size:9pt;page-break-inside:avoid}}
.rod{{margin-top:6mm;border-top:1px solid #E2E8F0;padding-top:2mm;font-size:8pt;color:#94A3B8;display:flex;justify-content:space-between}}
.pb{{page-break-before:always}}
"""

def cab(): return f'<div class="cab"><img src="{LOGO}" alt="Retena"/><div class="meta">Roteiro da equipe<br/>Banca Final · 23/09/2026</div></div>'

# ---- página 1: quem faz o quê
cards = ""
for cod, nome, sl, t in BLOCOS:
    cls = "pessoa mvp" if cod == "MVP" else "pessoa"
    cards += f'<div class="{cls}"><div class="b">{"MVP" if cod == "MVP" else cod} · slides {sl}</div><div class="n">{html.escape(P[cod])}</div><div class="s">{html.escape(nome)} · {t}</div></div>'
tab = "".join(f"<tr><td><b>{cod if cod != 'MVP' else 'MVP'}</b></td><td>{html.escape(P[cod])}</td><td>{html.escape(nome)}</td><td>{sl}</td><td>{t}</td></tr>" for cod, nome, sl, t in BLOCOS)
p1 = f"""{cab()}<div class="eyebrow">Roteiro da apresentação · 8 minutos · 5 apresentadores</div>
<h1>Quem fala o quê, palavra por palavra.</h1>
<p>Cinco blocos em sequência, sem voltar slide. {html.escape(MVP)} apresenta o MVP (demonstração ao vivo e resultados); os outros quatro blocos foram <b>sorteados</b> em {sorteio['quando']} ({sorteio['metodo']}) e registrados em <code>sorteio_blocos.json</code>. Cada fala termina com a passagem de bastão já escrita — quem recebe começa sem introdução.</p>
<div class="grid5">{cards}</div>
<table><tr><th>Bloco</th><th>Apresentador(a)</th><th>Conteúdo</th><th>Slides</th><th>Tempo</th></tr>{tab}<tr><td colspan="4"><b>Total</b></td><td><b>8:25</b></td></tr></table>
<div class="card"><h3>Regras do palco</h3><ul>
<li><b>Um notebook, {html.escape(primeiro(MVP))} opera</b> (a demonstração precisa do navegador). Quem fala diz "próximo" ou faz um gesto; o operador acompanha o roteiro. Dashboard já aberto na visão <b>Diretoria</b>, fila com "Aluno 0227" digitado; landing na seção ROI em outra aba; PDF do deck como plano B.</li>
<li><b>Bastão:</b> a última frase de cada bloco chama a próxima pessoa pelo nome. Quem recebe não agradece nem se apresenta — vai direto ao conteúdo.</li>
<li><b>Tempo:</b> 8:25 no roteiro; ensaiar duas vezes cronometrando cada bloco. Se estourar, cortar primeiro os parênteses das falas, nunca os números.</li>
<li><b>Números:</b> falar como está escrito (95 em 100, 3 vezes, 576 mil). Nunca arredondar 41,6% para "quase metade" — a banca vai conferir.</li>
<li><b>Perguntas:</b> {html.escape(primeiro(P['B1']))} coordena e passa a palavra a quem tem a resposta (tabela na última página). Resposta curta, com o slide do apêndice na tela quando houver.</li></ul></div>
<div class="nota"><b>Regra de honestidade (todos):</b> as 8 entrevistas foram simuladas com personas sintéticas para calibrar o instrumento, estão rotuladas assim no documento e serão confirmadas em campo antes do piloto. As metas de marketing são metas. Os dois AUC (0,88 Python e 0,949 Oracle) vêm de implementações independentes, ambas com teste temporal. Ninguém improvisa número.</div>"""

# ---- páginas 2+: falas por bloco
blocos_html = ""
for cod, nome, sl, t in BLOCOS:
    cls = "bloco mvp" if cod == "MVP" else "bloco"
    blocos_html += f'<div class="{cls}"><h2>{"MVP" if cod == "MVP" else cod} · {html.escape(P[cod])} — {html.escape(nome)} <span style="color:#94A3B8;font-weight:600;font-size:10pt">(slides {sl} · {t})</span></h2>'
    for n, tit, tt, b, tela, fala in FALAS:
        if b != cod: continue
        f = html.escape(fmt(fala))
        if " — " in f and f.rsplit(" — ", 1)[1].startswith(("Lucas", "Kayque", "Vinicius", "Agora")):
            corpo, bast = f.rsplit(" — ", 1); f = f"{corpo} <span class='bast'>→ {bast}</span>"
        blocos_html += f'<div class="slide"><div class="num">{n:02d}<small>{tt}</small></div><div><div class="tit">{html.escape(tit)}</div><div class="tela">Na tela: {html.escape(tela)}</div><div class="fala">{f}</div></div></div>'
    blocos_html += "</div>"
p2 = f'<div class="pb"></div>{cab()}<div class="eyebrow">Falas por bloco</div><h1>O roteiro, slide a slide.</h1><p>Texto para falar, não para ler: decorar a primeira e a última frase de cada slide e os números; o meio pode ser dito com as próprias palavras.</p>{blocos_html}'

# ---- última página: perguntas e ensaio
perg = ""
for cod, nome, sl, t in BLOCOS:
    perg += f'<div class="card"><h3>{html.escape(P[cod])} responde</h3><ul>' + "".join(f"<li>{html.escape(x)}</li>" for x in PERGUNTAS[cod]) + "</ul></div>"
p3 = f"""<div class="pb"></div>{cab()}<div class="eyebrow">Perguntas da banca</div><h1>Quem responde o quê.</h1>
<p>{html.escape(primeiro(P['B1']))} coordena: ouve a pergunta inteira, repete em uma frase e passa a quem tem a resposta. Quem responde fala por até 40 segundos e, se houver, coloca o slide do apêndice na tela. Se ninguém souber: "não medimos isso ainda; está no plano do piloto" — nunca inventar.</p>
{perg}
<div class="card"><h3>Ensaio de hoje (30 min)</h3><ul>
<li>Passada 1 completa, cronometrada por bloco; anotar quem estourou.</li>
<li>Passada 2 só das passagens de bastão (últimas frases + primeiras frases), até ficarem sem pausa.</li>
<li>Demonstração ensaiada 3 vezes no dashboard publicado: Diretoria → mudar ticket → Coordenação → "Aluno 0227" → atrito. Testar também com a internet do celular.</li>
<li>Cada um lê as perguntas do seu card em voz alta uma vez.</li></ul></div>
<div class="rod"><span>Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026</span><span>Material completo: 09_Kit_Banca_Final (deck, PDF, guia, one-pager)</span></div>"""

doc = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Retena · Roteiro da equipe</title><style>{CSS}</style></head><body>{p1}{p2}{p3}</body></html>"
hp = os.path.join(AQUI, "Retena_Roteiro_Equipe.html"); open(hp, "w", encoding="utf-8").write(doc)
pdf = os.path.join(AQUI, "Retena_Roteiro_Equipe.pdf")
if os.path.exists(pdf): os.remove(pdf)
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
                f"--user-data-dir={os.environ.get('TEMP')}\\edge_kit", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file:///" + hp.replace("\\", "/")], capture_output=True, timeout=180)
print("roteiro pdf:", os.path.exists(pdf))

# ---- mensagem para o grupo
linhas = [f"*Banca Final Retena — amanhã (23/09) · roteiro e divisão*", "",
          f"Sorteio feito ({sorteio['quando']}). Ordem de fala:"]
for cod, nome, sl, t in BLOCOS:
    tag = "MVP" if cod == "MVP" else cod
    linhas.append(f"{'▶️' if cod != 'MVP' else '💻'} *{P[cod]}* — {nome} (slides {sl}, {t}){' — demonstração ao vivo' if cod == 'MVP' else ''}")
linhas += ["", "Total: 8:25. Em anexo:",
           "• Retena_Roteiro_Equipe.pdf — a fala de cada slide, palavra por palavra, com a passagem de bastão e quem responde o quê nas perguntas",
           "• Retena_Banca_Final.pdf — o deck (18 slides + apêndice técnico)",
           "• Retena_Guia_do_Apresentador.pdf e Retena_OnePager_Banca.pdf",
           "", "Pedidos para hoje:",
           "1. Cada um decora a primeira e a última frase dos seus slides e os números (não arredondar).",
           "2. Ensaio cronometrado hoje à noite: uma passada completa + passagens de bastão.",
           f"3. {primeiro(P['B1'])} coordena as perguntas e distribui; ninguém inventa número.",
           "4. Regra de honestidade: entrevistas foram simuladas (está no documento); metas de marketing são metas.",
           "", "Links: dashboard https://lucashenklain.github.io/retena/dashboard/ (visão Diretoria) · site https://lucashenklain.github.io/retena/ · vídeo https://youtu.be/HZrcLvIJCC4"]
open(os.path.join(AQUI, "Retena_Roteiro_Equipe_WhatsApp.txt"), "w", encoding="utf-8").write("\n".join(linhas))
print("whatsapp txt ok")
