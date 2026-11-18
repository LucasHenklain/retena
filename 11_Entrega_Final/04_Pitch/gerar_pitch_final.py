# -*- coding: utf-8 -*-
"""
gerar_pitch_final.py - Pitch da ENTREGA FINAL da Retena (PPTX editável + PDF via PowerPoint).

Reaproveita os utilitários e a identidade visual do kit da Banca Final (09_Kit_Banca_Final/gerar_kit_banca.py:
tokens de marca, cards, pulso, tabelas, QR) executando só a parte de utilitários daquele script.
Cobre os 10 pontos do enunciado: problema, solução, demonstração do MVP, mercado, modelo de negócio,
tecnologia (integração Oracle), diferencial, crescimento, projeções e time.
Números: base real anonimizada, banco Oracle (VW_DIRETORIA_RESUMO, AVALIACAO_MODELOS), modelo_financeiro.json
(estimativas rotuladas). Uso: python gerar_pitch_final.py [--sem-pdf]
"""
import json, os, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTREGA = AQUI.parent.parent
KIT = ENTREGA / "09_Kit_Banca_Final" / "gerar_kit_banca.py"
DOC = AQUI.parent / "03_Documento"

# --- utilitários do kit (até o primeiro slide), executados com __file__ do kit para os caminhos baterem
src = KIT.read_text(encoding="utf-8")
prefixo = src.split("# ================================================================= 1 CAPA")[0]
ns = {"__file__": str(KIT), "__name__": "kit_utils"}
exec(compile(prefixo, str(KIT), "exec"), ns)
globals().update({k: v for k, v in ns.items() if not k.startswith("__") and k not in ("AQUI", "ROOT", "OUT", "N")})
OUT = str(AQUI / "Retena_Pitch_Final.pptx")
FIN = json.loads((DOC / "modelo_financeiro.json").read_text(encoding="utf-8"))
TELA = lambda n: str(DOC / "img" / n)


def rodape(slide, escuro, n):  # versão da entrega final
    c = DIM2 if escuro else CINZA
    text(slide, 0.6, 7.05, 9.5, 0.3, "Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA · Entrega final 27/11/2026", size=9.5, cor=c)
    text(slide, 12.0, 7.05, 0.75, 0.3, f"{n:02d}", size=9.5, cor=c, align=PP_ALIGN.RIGHT)
    logo(slide, escuro)


def mi(v):
    return f"R$ {v/1e6:.2f} mi".replace(".", ",")


# ================================================================= 1 CAPA
s = novo(True, motivo=False)
img_cover(s, IMG("04_Landing_Page", "img", "aluno_noite.jpg"), 7.45, 0, 5.883, 7.5); veu(s, 7.45, 0, 5.883, 7.5, AZUL, 40)
rect(s, 7.45, 0, 0.06, 7.5, VERDE); pulso(s, 8.6, 4.9, 3.8, pct=45, espessura=16)
s.shapes.add_picture(lg, P(0.7), P(0.7), height=P(0.9))
pill(s, 0.7, 2.05, 5.6, "Entrega final · MVP funcional sobre Oracle AI Database", bg=CARD_ESC, fg=VERDE, size=9.5, h=0.34)
text(s, 0.7, 2.6, 6.5, 2.1, [[("Ninguém desiste", True, BRANCO)], [("de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=36, spacing=1.02)
text(s, 0.7, 4.85, 6.3, 0.95, "Radar de permanência para o ensino superior EAD: toda segunda, quem chamar, por quê e o que dizer — e quanto de receita voltou. Tudo dentro do Oracle.", size=13.5, cor=DIM, spacing=1.3)
text(s, 0.7, 6.05, 6.5, 0.7, ["Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592)", "Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)"], size=10.5, cor=DIM, spacing=1.3)
text(s, 0.7, 6.95, 6.5, 0.3, "Startup One · Enterprise Challenge Oracle · FIAP 2026 · Engenharia de Software", size=9.5, cor=DIM2)
notes(s, ns["N"], "Capa", "Ninguém desiste de repente. Nós somos a Retena, e hoje mostramos o MVP rodando de ponta a ponta dentro do Oracle.")

# ================================================================= 2 PROBLEMA
s = novo(True, motivo=False)
img_cover(s, IMG("04_Landing_Page", "img", "campus.jpg"), 0, 0, 13.333, 7.5); veu(s, 0, 0, 13.333, 7.5, AZUL, 66)
logo(s, True, x=0.9, y=0.7, h=0.55)
kicker(s, 0.9, 1.8, 10, "Problema")
text(s, 0.9, 2.2, 11.4, 2.3, [[("Quatro em cada dez alunos de EAD desistem por ano.", True, BRANCO)], [("A instituição descobre quando a mensalidade para.", True, VERDE)]], size=32, spacing=1.08)
for i, (n, l, sub) in enumerate([("41,6%", "desistência anual no EAD", "Semesp, 2024"), ("5,19 mi", "alunos em EAD (50,7%)", "INEP, Censo 2024"),
                                 ("30%", "da turma real sumida há 14+ dias", "62 de 203 alunos, sem alerta")]):
    card(s, 0.9 + i * 3.9, 4.55, 3.6, 1.75, escuro=True)
    stat(s, 1.15 + i * 3.9, 4.7, 3.2, n, l, sub, escuro=True, size=30)
text(s, 0.9, 6.6, 11.5, 0.3, "Base real: 684.723 eventos de LMS de uma IES parceira, 203 alunos, 15/01–26/08/2026, anonimizada. O LMS registra o silêncio semanas antes — ninguém estava ouvindo.", size=10, cor=DIM2)
notes(s, ns["N"], "Problema", "41,6% de desistência no EAD. Na nossa base real, 30% da turma estava há mais de 14 dias sem acesso, e ninguém tinha um alerta.")

# ================================================================= 3 SOLUÇÃO
s = novo(False)
titulo(s, "Solução", "Toda segunda: quem chamar, por quê, o que dizer. E quanto voltou.")
passos = [("Lê", "os logs do LMS que a IES já tem (CSV/API) e monta sinais semanais por aluno", "SQL no Oracle"),
          ("Prevê", "o risco de 21 dias sem acesso, com o motivo em linguagem simples", "Oracle Machine Learning"),
          ("Prioriza", "a fila de segunda: primeiro quem ainda dá para segurar, com mensagem pronta", "DBMS_SCHEDULER + views"),
          ("Fecha o ciclo", "a coordenação registra o resultado; a diretoria vê a receita preservada em R$", "PL/SQL + CONTATO_RESULTADO")]
for i, (t, d, o) in enumerate(passos):
    x = 0.6 + i * 3.08
    card(s, x, 2.05, 2.85, 3.9); numero(s, x + 0.25, 2.3, 0.6, i + 1)
    text(s, x + 0.25, 3.05, 2.4, 0.5, t, size=20, cor=AZUL, bold=True)
    text(s, x + 0.25, 3.6, 2.45, 1.5, d, size=12.5, cor=GRAFITE, spacing=1.25)
    pill(s, x + 0.25, 5.35, 2.35, o, bg=VERDE_CLARO, fg=VERDE_ESC, size=9)
text(s, 0.6, 6.25, 12, 0.6, "Para a coordenadora: zero planilha. Para a diretora: proteção de receita medida toda semana. Para a IES: o dado do aluno não sai do banco (LGPD).", size=13, cor=AZUL, bold=True)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Solução", "Quatro passos, todos dentro do banco. A novidade desta entrega é o quarto: o ciclo fecha com o resultado do contato gravado e a receita recalculada.")

# ================================================================= 4 DEMO 1
s = novo(False)
titulo(s, "Demonstração do MVP · coordenação", "A fila de segunda e o painel do aluno, lidos do Oracle")
img_fit(s, TELA("mvp_1_fila.png"), 0.6, 1.95, 6.3, 4.6, rounded=True)
img_fit(s, TELA("mvp_2_aluno.png"), 7.0, 1.95, 5.75, 4.6, rounded=True)
text(s, 0.6, 6.55, 6.3, 0.45, "74 alunos na fila, em grupos: Agir agora (12) · Atenção (15) · Resgate", size=11, cor=GRAFITE)
text(s, 7.0, 6.55, 5.8, 0.45, "Motivo, ações por semana, predição ao vivo e “e se ele voltar?” (67% → 11%)", size=11, cor=GRAFITE)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Demo 1", "Prints reais do MVP rodando localmente. A fila vem do snapshot pontuado pelo Random Forest no banco; o botão recalcula a predição no Oracle naquele instante.")

# ================================================================= 5 DEMO 2
s = novo(False)
titulo(s, "Demonstração do MVP · registro e diretoria", "O contato vira linha no banco e a receita é recalculada")
img_fit(s, TELA("mvp_3_registro.png"), 0.6, 1.95, 6.3, 4.6, rounded=True)
img_fit(s, TELA("mvp_4_diretoria.png"), 7.0, 1.95, 5.75, 4.6, rounded=True)
text(s, 0.6, 6.55, 6.3, 0.45, "PRC_REGISTRAR_CONTATO grava em CONTATO_RESULTADO e atualiza a fila na mesma transação", size=11, cor=GRAFITE)
text(s, 7.0, 6.55, 5.8, 0.45, "VW_DIRETORIA_RESUMO: risco R$ 247,8 mil/ano; preservada +R$ 4.200 por reativado", size=11, cor=GRAFITE)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Demo 2", "Registro de demonstração feito pela equipe (nenhum aluno real foi contatado). A diretoria muda na hora porque o cálculo está numa view.")

# ================================================================= 6 ORACLE
s = novo(True)
titulo(s, "Tecnologia · integração Oracle", "Tudo roda dentro do banco onde o dado do aluno já está", escuro=True)
linhas = [["Oracle AI Database 26ai", "684.723 eventos, features em SQL, snapshot, contatos", "Executado"],
          ["Oracle Machine Learning", "Random Forest + 2 GLM; PREDICTION_PROBABILITY / DETAILS", "Executado"],
          ["DBMS_SCHEDULER", "Job de scoring toda segunda 06:00 (mediana ~1 min)", "Executado"],
          ["PL/SQL + views", "Registro do contato e visão da diretoria no banco", "Executado"],
          ["JSON Duality View", "Documento JSON por aluno, leitura e escrita", "Executado"],
          ["Autonomous AI Database + DBMS_CLOUD", "Produção multi-IES; ingestão do CSV do LMS", "Runbook pronto"],
          ["APEX / ORDS · Select AI", "Painel low-code e perguntas em português", "Roadmap"]]
tabela(s, 0.6, 1.95, 8.2, 4.4, ["Componente", "Papel no MVP", "Estado"], linhas, [2.6, 4.2, 1.4], escuro=True, size=11)
card(s, 9.1, 1.95, 3.65, 4.4, escuro=True)
kicker(s, 9.35, 2.15, 3.2, "Por que é estratégia")
bullets(s, 9.35, 2.6, 3.2, ["LGPD vira argumento de venda: o dado não sai da IES",
                            "Sem servidor de ML nem cientista de dados: Oracle custa ~R$ 0,2–0,3 por aluno/mês",
                            "Canal: ERPs acadêmicos e megagrupos já rodam Oracle"], size=11.5, cor=BRANCO)
rodape(s, True, ns["N"])
notes(s, ns["N"], "Oracle", "Cinco componentes executados e evidenciados; Autonomous com runbook; APEX e Select AI no roadmap. Escolhemos API Python fina porque ORDS/APEX local não é reproduzível para quem abrir o ZIP; as regras estão em PL/SQL e migram direto.")

# ================================================================= 7 PROVA
s = novo(False)
titulo(s, "Prova técnica", "Funciona, e dá para conferir em SQL")
prova = [("0,949", "AUC (Random Forest)", "OML in-database, teste temporal a partir de 01/06/2026"),
         ("3,75×", "lift no top 20%", "85% da faixa alta ficou de fato inativa"),
         ("15/15", "checagens ponta a ponta", "verificar_mvp.py confere direto no banco"),
         ("~0,1 s", "predição ao vivo", "PREDICTION_PROBABILITY por aluno, sob demanda")]
for i, (n, l, sub) in enumerate(prova):
    x = 0.6 + i * 3.08
    card(s, x, 2.05, 2.85, 2.3); stat(s, x + 0.25, 2.25, 2.45, n, l, sub, size=32)
card(s, 0.6, 4.6, 12.15, 2.0)
text(s, 0.85, 4.75, 11.7, 0.4, "Um comando sobe tudo", size=14, cor=AZUL, bold=True)
text(s, 0.85, 5.15, 11.7, 1.4, ["INICIAR_MVP.cmd → Docker com Oracle 26ai Free → (banco vazio) carga + treino OML + scoring em 10–15 min → tabelas do MVP → API → navegador.",
                                "Linux/macOS: docker compose --profile completo up. Portabilidade do método já testada no dataset público OULAD (AUC 0,922)."], size=12, cor=GRAFITE, spacing=1.3)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Prova", "Números do banco: AVALIACAO_MODELOS. O teste automatizado registra um contato, confere a linha em SQL, confere a receita preservada e limpa.")

# ================================================================= 8 MERCADO
s = novo(False)
titulo(s, "Mercado", "R$ 249 milhões por ano só no EAD brasileiro")
for i, (sig, v, d) in enumerate([("TAM", "R$ 249 mi/ano", "5,19 mi alunos EAD × R$ 48/ano (INEP 2024)"),
                                  ("SAM", "R$ 126 mi/ano", "2,63 mi alunos em IES privadas fora dos megagrupos (Semesp)"),
                                  ("SOM · 3 anos", "R$ 2,5–4,3 mi ARR", "52 mil alunos em 10–11 IES médias + 1 megagrupo no cenário otimista")]):
    w = 12.15 - i * 1.2; x0 = 0.6 + i * 0.6
    rect(s, x0, 2.05 + i * 1.45, w, 1.25, [AZUL, AZUL_M, VERDE][i], radius=0.08)
    text(s, x0 + 0.3, 2.18 + i * 1.45, 2.2, 1.0, sig, size=16, cor=BRANCO if i < 2 else AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x0 + 2.5, 2.18 + i * 1.45, 3.4, 1.0, v, size=24, cor=VERDE if i < 2 else AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x0 + 6.0, 2.18 + i * 1.45, w - 6.2, 1.0, d, size=12, cor=DIM if i < 2 else AZUL, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.6, 6.45, 12, 0.4, "Contexto: desistência de 41,6% e CAC do aluno acima de R$ 1.000 (estimativa): reter ficou mais barato que captar.", size=11, cor=GRAFITE)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Mercado", "Contas conferidas nesta entrega; o preço usado no SAM/SOM é o preço efetivo médio de R$ 4 por aluno/mês.")

# ================================================================= 9 MODELO DE NEGÓCIO
s = novo(False)
titulo(s, "Modelo de negócio", "SaaS por aluno ativo, com piloto que se paga em 90 dias")
tabela(s, 0.6, 2.0, 7.4, 2.4, ["Plano", "Preço por aluno ativo/mês", "Mínimo"],
       [["Essencial", "R$ 2,00 (até 5 mil alunos)", "R$ 2,5 mil"],
        ["Pro", "R$ 6 até 10 mil · R$ 4 até 50 mil · R$ 3 acima", "R$ 5 mil"],
        ["Enterprise", "Pro + 30% (multi-campus, API, SLA)", "proposta"]], [1.5, 4.5, 1.4], size=11.5, destaque_linha=2)
bullets(s, 0.6, 4.65, 7.4, ["Setup R$ 10–25 mil · piloto de 90 dias R$ 5 mil com meta medida no painel (30% dos alunos de alto risco reengajados)",
                            "Custo de servir baixo: Oracle Always Free no piloto; ~R$ 2,8 mil/mês por banco de produção (estimativa)",
                            "Margem bruta de 73% nos anos 2–3, com meta de 80% em escala (estimativa)"], size=12)
card(s, 8.35, 2.0, 4.4, 4.6)
kicker(s, 8.6, 2.2, 4, "Cliente-referência (12 mil alunos)")
stat(s, 8.6, 2.6, 4, "R$ 576 mil/ano", "12.000 × R$ 4 × 12", None, size=28)
stat(s, 8.6, 3.85, 4, "137 alunos", "retidos por ano pagam o contrato", "1,1% da base · ticket R$ 350/mês (estimativa)", size=28, cor_num=VERDE_ESC)
text(s, 8.6, 5.55, 3.95, 0.9, "Cada ponto percentual de desistência evitado vale ~R$ 500 mil/ano para essa IES.", size=11.5, cor=AZUL, bold=True)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Negócio", "Tabela consolidada nesta entrega: Essencial R$ 2; Enterprise é Pro + 30%. Regra de faixa evita salto em 10 mil alunos.")

# ================================================================= 10 DIFERENCIAL
s = novo(True)
titulo(s, "Diferencial", "BI mostra o passado. CRM cobra tarde. A Retena age antes — e mede.", escuro=True)
tabela(s, 0.6, 2.05, 12.15, 3.4, ["", "BI do LMS", "CRM / cobrança", "Consultoria", "Retena"],
       [["Quando age", "depois", "mensalidade já parou", "projeto pontual", "semanas antes, toda segunda"],
        ["Diz quem chamar e por quê", "não", "não", "parcial", "sim, com motivo"],
        ["Mede o resultado em R$", "não", "parcial", "relatório", "no banco, a cada contato"],
        ["Dado sai da IES?", "não", "sim", "sim", "não (ML in-database)"],
        ["Precisa de cientista de dados?", "—", "—", "sim", "não"]], [3.0, 2.0, 2.4, 2.0, 2.75], escuro=True, size=11.5)
text(s, 0.6, 5.75, 12, 0.9, "Defesa: o ciclo fechado gera um dado proprietário por cliente (cada contato e seu resultado retreina o modelo daquela IES) e o canal Oracle abre a fase 2.", size=13.5, cor=BRANCO, spacing=1.3)
rodape(s, True, ns["N"])
notes(s, ns["N"], "Diferencial", "Risco honesto: um LMS grande pode embutir algo parecido. A defesa é ROI medido e o dado de resultados de contato.")

# ================================================================= 11 CRESCIMENTO
s = novo(False)
titulo(s, "Lançamento e crescimento", "Começar por quem tem dor e alçada: IES médias com EAD")
card(s, 0.6, 2.0, 5.9, 4.6)
kicker(s, 0.85, 2.2, 5.5, "Público prioritário (ICP)")
bullets(s, 0.85, 2.65, 5.4, ["IES privadas com EAD, 3 a 15 mil alunos, fora dos megagrupos",
                             "Decide: diretora de operações acadêmicas (receita). Usa: coordenação de permanência",
                             "Moodle ou LMS que exporte logs; de preferência já com Oracle",
                             "Primeiro: converter a IES parceira em piloto-referência (meta: 18 reativações)"], size=12)
card(s, 6.85, 2.0, 5.9, 4.6)
kicker(s, 7.1, 2.2, 5.5, "Funil do ano 1 (metas)")
for i, (n, t) in enumerate([("30", "diagnósticos gratuitos em 7 dias (isca: o export do LMS)"), ("6", "pilotos pagos de 90 dias"), ("2", "contratos anuais · R$ 480 mil de ARR")]):
    numero(s, 7.1, 2.7 + i * 0.95, 0.7, n, size=14)
    text(s, 8.0, 2.78 + i * 0.95, 4.5, 0.6, t, size=13, cor=AZUL, bold=True)
text(s, 7.1, 5.6, 5.4, 0.9, "Canais: LinkedIn/ABM para diretores, calculadora de ROI na landing, conteúdo INEP/Semesp, eventos Semesp/ABED e ecossistema Oracle for Startups.", size=11, cor=GRAFITE, spacing=1.25)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Lançamento", "Crescimento sustentável: expandir dentro da conta (de uma fase para todos os cursos), contratar CS e vendas só no ano 2, fase 2 com megagrupos via Oracle.")

# ================================================================= 12 PROJEÇÕES
s = novo(False)
titulo(s, "Projeções (estimativas)", "De R$ 0,48 mi a R$ 2,5 mi de ARR em três anos")
img_fit(s, str(DOC / "img" / "projecao.png"), 0.6, 1.95, 7.6, 3.2)
tabela(s, 0.6, 5.25, 7.6, 1.55, ["", "Ano 1", "Ano 2", "Ano 3"],
       [["IES · alunos", "2 · 10 mil", "6 · 30 mil", "11 · 52 mil"],
        ["Receita bruta", mi(FIN["receita_bruta"][0]), mi(FIN["receita_bruta"][1]), mi(FIN["receita_bruta"][2])],
        ["EBITDA", mi(FIN["ebitda"][0]), mi(FIN["ebitda"][1]), mi(FIN["ebitda"][2])]], [2.2, 1.8, 1.8, 1.8], size=10.5)
card(s, 8.55, 1.95, 4.2, 4.85)
kicker(s, 8.8, 2.15, 3.8, "Leitura")
bullets(s, 8.8, 2.6, 3.75, [f"Necessidade de caixa até o equilíbrio: R$ {FIN['necessidade_caixa']/1e3:.0f} mil → pré-seed de R$ 600 mil",
                            "Equilíbrio operacional na virada do ano 3 para o 4 (cenário base)",
                            f"Otimista (+1 megagrupo): ARR {mi(FIN['arr_ano3_otimista'])} e EBITDA positivo no ano 3",
                            f"LTV/CAC ~{FIN['ltv_cac']:.0f}× · payback do CAC ~{FIN['payback_meses']:.0f} meses"], size=11.5)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Projeções", "Todas as premissas estão em modelo_financeiro.xlsx; preços publicados, custos estimados pela equipe, Oracle a preço de lista.")

# ================================================================= 13 VALIDAÇÃO
s = novo(False)
titulo(s, "Validação", "O que está provado e o que ainda falta provar")
card(s, 0.6, 2.0, 5.9, 4.6); kicker(s, 0.85, 2.2, 5.5, "Provado (real)", cor=VERDE_ESC)
bullets(s, 0.85, 2.65, 5.4, ["Sinal forte em teste temporal (AUC 0,95) na base real da IES parceira",
                             "Método portátil: OULAD, AUC 0,922",
                             "Fluxo completo no banco: 15/15 checagens automatizadas",
                             "Dor e mercado: INEP e Semesp"], size=12.5)
card(s, 6.85, 2.0, 5.9, 4.6); rect(s, 6.85, 2.0, 0.08, 4.6, AMBAR)
kicker(s, 7.1, 2.2, 5.5, "Pendente (com protocolo pronto)", cor=RGBColor(0x8A, 0x5A, 0x00))
bullets(s, 7.1, 2.65, 5.4, ["Testes do MVP com 3+ usuários reais do público-alvo: 6 tarefas, SUS e perguntas de valor",
                            "Critério: ≥ 80% de sucesso nas tarefas centrais e SUS ≥ 68",
                            "Entrevistas da Fase 6 foram simuladas e seguem rotuladas assim",
                            "Piloto de 90 dias com a IES parceira"], size=12.5, dot=AMBAR)
rodape(s, False, ns["N"])
notes(s, ns["N"], "Validação", "Sem resultados inventados: a seção de testes com usuários do documento está marcada como pendente até a equipe trazer as fichas.")

# ================================================================= 14 TIME + FECHAMENTO
s = novo(True)
titulo(s, "Time e próximo passo", "Cinco engenheiros, um problema de R$ 249 milhões", escuro=True)
for i, (nome, rm, papel) in enumerate(EQUIPE):
    x = 0.6 + i * 2.45
    card(s, x, 2.05, 2.25, 1.35, escuro=True)
    text(s, x + 0.2, 2.2, 2.0, 0.4, nome, size=13, cor=BRANCO, bold=True)
    text(s, x + 0.2, 2.6, 2.0, 0.6, rm + (" · " + papel if papel else ""), size=11, cor=DIM)
text(s, 0.6, 3.75, 8.0, 1.6, [[("O que pedimos: ", True, VERDE), ("uma IES para o piloto de 90 dias, Oracle for Startups (Autonomous AI Database) e mentoria comercial.", False, BRANCO)]], size=15, spacing=1.3)
text(s, 0.6, 5.25, 8.0, 1.2, [[("Ninguém desiste de repente.", True, BRANCO)], [("A Retena percebe antes.", True, VERDE)]], size=26, spacing=1.05)
for i, (nome, url, rot) in enumerate([("site", LINKS["site"], "Site"), ("repo", LINKS["repo"], "Repositório")]):
    p = qr(f"final_{nome}", url)
    s.shapes.add_picture(p, P(9.3 + i * 1.75), P(3.85), height=P(1.5))
    text(s, 9.3 + i * 1.75, 5.4, 1.5, 0.3, rot, size=10, cor=DIM, align=PP_ALIGN.CENTER)
rodape(s, True, ns["N"])
notes(s, ns["N"], "Fechamento", "A evasão não é um evento, é um silêncio. A Retena escuta esse silêncio dentro do banco que a instituição já usa.")

prs.save(OUT)
(AQUI / "notas_pitch.json").write_text(json.dumps(NOTAS, ensure_ascii=False, indent=1), encoding="utf-8")
print("PPTX:", OUT, "slides:", ns["N"])

if "--sem-pdf" not in sys.argv:
    pdf = OUT.replace(".pptx", ".pdf")
    ps = f"""$pp = New-Object -ComObject PowerPoint.Application
$d = $pp.Presentations.Open('{OUT}', $true, $false, $false)
$d.SaveAs('{pdf}', 32)
$d.Close(); $pp.Quit()"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=240)
    print("PDF:", pdf)
