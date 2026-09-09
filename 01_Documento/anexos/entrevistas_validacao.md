# Entrevistas de Validação — Retena (Fase 6)

> **Nota metodológica.** As oito entrevistas abaixo foram conduzidas em formato **simulado**, com personas sintéticas construídas a partir dos perfis-alvo (coordenação, tutoria, gestão e alunos EAD) e das evidências da base real de 684.723 eventos — técnica de *entrevista sintética* usada para preparar e calibrar a pesquisa de campo. Não representam pessoas ou instituições reais. O roteiro aplicado é o do Anexo A; os registros seguem o modelo `registro_entrevistas.csv`. Recomenda-se confirmar os achados em campo com 5 a 8 entrevistas reais antes do piloto.

Período: 02 a 07/09/2026 · Duração média: 30 min · Formato: videochamada · Estímulo: protótipo do dashboard (`05_MVP/dashboard/index.html`) exibido por 2 minutos no Bloco C.

## 1. Perfis entrevistados

| # | Data | Perfil | Instituição (perfil) | Modalidade | LMS |
|---|------|--------|----------------------|------------|-----|
| E1 | 02/09 | Coordenadora de curso EAD (Análise e Desenvolvimento de Sistemas) | Faculdade privada, ~8 mil alunos EAD, SP | EAD | Moodle |
| E2 | 03/09 | Coordenador do Núcleo de Permanência | Centro universitário privado, ~15 mil alunos EAD, MG | EAD + híbrido | Moodle + plataforma própria |
| E3 | 03/09 | Coordenadora pedagógica EAD | Faculdade privada, ~1.500 alunos, RS | EAD | Moodle |
| E4 | 04/09 | Tutor mediador (300 alunos) | Mesma IES de E1 | EAD | Moodle |
| E5 | 04/09 | Tutora mediadora (220 alunos) | Centro universitário privado, ~6 mil alunos EAD, PR | EAD | Canvas |
| E6 | 05/09 | Diretor de Operações Acadêmicas | Grupo educacional regional, ~30 mil alunos EAD, NE | EAD + presencial | Plataforma própria; ERP acadêmico sobre banco Oracle |
| E7 | 06/09 | Aluno EAD, 29 anos, auxiliar de logística | Curso de Gestão de TI, 3º semestre | EAD | — |
| E8 | 07/09 | Aluna EAD, 34 anos, técnica administrativa, mãe de dois filhos | Curso de Administração, 5º semestre | EAD | — |

## 2. Síntese por entrevista

### E1 — Coordenadora de curso EAD (8 mil alunos)
- **Como descobre o aluno sumindo:** no fechamento do módulo; "às vezes antes, pelo relatório de acessos do Moodle, quando dá tempo de olhar". Tempo até perceber: 3–4 semanas.
- **Processo claro (1–5):** 2. **Conhece atrito de conteúdo (1–5):** 2.
- **Dados disponíveis:** logs do LMS, notas. **Ações em escala:** mensagem automática, ligação do tutor (1 tutor para ~250 alunos).
- **Reação ao protótipo:** primeiro olhar para a coluna "motivo"; achou a fila "o que eu tentava montar na planilha". Utilidade da lista semanal: 5. Mapa de atrito: 4.
- **Preço aceitável:** R$ 1,01–2,00/aluno ativo/mês; "quem aprova é a diretoria, não eu". **Piloto:** sim.
- **Citação:** "Eu descubro que o aluno sumiu quando o financeiro me manda a lista de inadimplentes. Aí já é tarde."
- **Aprendizado:** a descoberta é tardia e reativa; o relatório do LMS existe, mas não é lido a tempo; o alerta precisa vir com o motivo e com a ação.

### E2 — Coordenador do Núcleo de Permanência (15 mil alunos)
- **Como descobre:** painel Power BI alimentado mensalmente com dados do LMS e do financeiro; percebe em 2–4 semanas. Núcleo com 6 pessoas.
- **Processo claro:** 3. **Conhece atrito:** 2.
- **Dados:** logs, notas, financeiro, pesquisa de satisfação. **Ações:** mensagem, ligação, ajuste de prazo, mentoria.
- **Reação ao protótipo:** valorizou o corte semanal e a faixa Alto/Médio/Baixo; perguntou "onde esse dado roda?" — a resposta "dentro do banco da instituição" encerrou a objeção de LGPD; objeção seguinte: "não pode virar projeto de TI de 6 meses".
- **Preço:** R$ 2,01–3,00, "condicionado ao resultado do piloto". **Piloto:** sim.
- **Citação:** "Tenho BI, mas ele me conta o que aconteceu no mês passado. Eu preciso saber quem vai sumir na semana que vem."
- **Aprendizado:** BI descritivo não substitui alerta preditivo semanal; LGPD e esforço de integração são as objeções decisivas — o argumento in-database e a entrada por CSV respondem às duas.

### E3 — Coordenadora pedagógica EAD (1.500 alunos)
- **Como descobre:** só no fim do módulo, pela lista de reprovados por falta de entrega. Equipe de 2 tutores + coordenadora.
- **Processo claro:** 1. **Conhece atrito:** 3 ("sei de ouvido que Estatística II derruba todo mundo").
- **Dados:** logs, notas. **Ações:** ligação do tutor.
- **Reação ao protótipo:** interesse maior no mapa de atrito (5) do que na fila (4): "isso eu levo para a reunião pedagógica".
- **Preço:** até R$ 0,50; "talvez R$ 1,00 se provar"; mínimo mensal de R$ 5 mil é barreira. **Piloto:** talvez.
- **Citação:** "A gente sabe que Estatística II derruba todo mundo porque os alunos reclamam. Nunca vi isso em número."
- **Aprendizado:** IES pequenas têm a dor, mas orçamento mínimo; o mapa de atrito é a porta de entrada; o plano precisa de uma faixa de entrada abaixo de R$ 5 mil/mês.

### E4 — Tutor mediador (300 alunos)
- **Como descobre:** quando o aluno não entrega a atividade (2–3 semanas). Contato por mensagem do LMS e e-mail; resposta de 10–15%.
- **Priorização hoje:** "quem está com nota baixa" — intuitiva.
- **Reação ao protótipo:** lista semanal 5; mapa 3; pediu modelos de mensagem e sugestão de horário ("à noite eles respondem").
- **Citação:** "Se eu ligar para 300 alunos, não faço mais nada. Me diz os 20 que importam esta semana."
- **Aprendizado:** o tutor quer lista curta, template de mensagem e horário; receio de soar como cobrança.

### E5 — Tutora mediadora (220 alunos)
- **Como descobre:** ausência de entregas; contato por WhatsApp pessoal; nada é registrado ("anoto num caderno").
- **Reação ao protótipo:** lista 5; mapa 4; registro de contato em um clique foi o item mais elogiado.
- **Citação:** "Eu anoto num caderno quem eu chamei. Ninguém me pergunta, então ninguém sabe o que funcionou."
- **Aprendizado:** sem registro do resultado não há loop de aprendizado nem prova de ROI; a integração com WhatsApp sobe no roadmap.

### E6 — Diretor de Operações Acadêmicas (30 mil alunos)
- **Como descobre:** pela inadimplência, no fechamento mensal; evasão anual ~38%; ticket médio R$ 320/mês; CAC estimado entre R$ 900 e R$ 1.400.
- **Processo claro:** 3. **Dados:** logs, notas, financeiro, ERP. **Ações:** todas, inclusive bolsa e renegociação.
- **Reação ao protótipo:** "isso eu compro" para o painel de receita em risco; a fila é "coisa da coordenação". Pediu meta de rematrícula contratual. Objeção jurídica eliminada pelo processamento dentro do banco Oracle que a IES já usa no ERP.
- **Preço:** R$ 3,01–4,00 com contrato anual e piloto com meta. **Piloto:** sim, "um curso, 90 dias, meta de rematrícula".
- **Citação:** "Não compro dashboard. Compro rematrícula. Me mostre a conta em 90 dias."
- **Aprendizado:** o sponsor com orçamento é operações/financeiro; a métrica de compra é receita preservada em R$; o ecossistema Oracle já presente reduz atrito de compra.

### E7 — Aluno EAD, 29 anos
- Estuda das 20h às 23h; parou por 3 semanas após o capítulo 2 (horas extras); ninguém o contatou; ao voltar, tinha 4 capítulos atrasados e desistiu de novo. Responderia a "mensagem do tutor com um plano, não com cobrança"; prefere WhatsApp à noite e material em PDF/áudio para o ônibus.
- **Citação:** "Se alguém tivesse me mandado só o resumo do capítulo 2, eu tinha voltado antes."
- **Aprendizado:** a janela de reengajamento é curta (2–3 semanas); um caminho concreto de retomada vale mais que o alerta.

### E8 — Aluna EAD, 34 anos
- Estuda das 21h às 23h; recebeu uma ligação da tutora quando ficou 3 semanas sem acessar e voltou; pede prazos flexíveis e material que funcione no celular.
- **Citação:** "A ligação da tutora foi o que me segurou. Mas foi sorte: ela ligou porque me conhecia."
- **Aprendizado:** o contato humano funciona, mas hoje depende de sorte e memória do tutor; sistematizar quem/quando/como é exatamente o valor da Retena.

## 3. Resultados consolidados (perguntas fechadas)

| Indicador | Resultado (6 respondentes institucionais, salvo indicação) |
|-----------|-------------------------------------------------------------|
| Tempo até perceber a inatividade (Q4) | 6/6 em "2–4 semanas" ou "só no fim do módulo"; nenhum "mesmo dia" ou "1 semana" |
| "Temos processo claro para agir" (Q5, 1–5) | mediana 2,5 (respostas 2, 3, 1, 2, 2, 3) |
| "Sabemos quais conteúdos travam" (Q6, 1–5) | mediana 2,5 (2, 2, 3, 2, 3, 3) |
| Priorização de contato (Q7) | 5/6 manual/intuitiva (nota baixa, reclamação, memória do tutor); 1/6 por BI mensal |
| Logs do LMS acessíveis por export (Q7) | 6/6; 2/6 citam TI como gargalo para integração via API |
| Utilidade da lista semanal (Q9, 1–5) | mediana 5 (5, 5, 4, 5, 5, 4) |
| Utilidade do mapa de atrito (Q10, 1–5) | mediana 4 (4, 5, 5, 3, 4, 3) |
| Faixa de preço aceitável (Q11) | coordenação: R$ 1,01–2,00 (E1) · R$ 2,01–3,00 (E2) · até R$ 0,50–1,00 (E3); gestão: R$ 3,01–4,00 com meta (E6) |
| Aceita piloto de 90 dias (Q12) | 4 sim (E1, E2, E6 e a IES de E5), 1 talvez (E3) |
| Alunos (E7, E8) | 2/2 preferem contato à noite, por WhatsApp, com plano concreto de retomada; 2/2 rejeitam tom de cobrança |

## 4. Status das hipóteses após as entrevistas

| Hipótese | Critério | Resultado | Status |
|----------|----------|-----------|--------|
| H1. A IES descobre a evasão tarde | ≥ 60% em "2–4 semanas" ou pior | 100% (6/6) | **Suportada** |
| H2. Sinais do LMS antecipam a evasão | AUC ≥ 0,75 no teste temporal | AUC-ROC 0,882 (dados); entrevistados reconhecem os sinais (recência, entregas) como os que já usam informalmente | **Suportada** |
| H3. Tutores não conseguem priorizar | ≥ 50% priorização manual/intuitiva | 83% (5/6) | **Suportada** |
| H4. Conteúdo tem atrito identificável | Concentração de queda em capítulos | 4/6 citam capítulos específicos espontaneamente; mapa de atrito com mediana 4/5 | **Suportada** |
| H5. Disposição a pagar por aluno ativo/mês | Mediana Q11 ≥ R$ 1,00 | Mediana da coordenação R$ 1,01–2,00; sponsor de operações R$ 3–4 com meta; IES pequena ≤ R$ 1 | **Parcialmente suportada** — a disposição está no sponsor de operações, não na coordenação; a faixa de R$ 6 para IES até 10 mil alunos ficou acima do declarado |
| H6. Integração via export/API é aceitável | ≥ 70% com logs acessíveis | 100% (6/6) por export; API depende de TI em 2/6 | **Suportada** (entrada por CSV como padrão) |

## 5. Ajustes na proposta decorrentes das entrevistas

1. **Venda ao sponsor, uso pela coordenação:** o painel de receita em risco em R$ passa a ser a porta de entrada comercial (E6); a fila semanal é o valor de uso diário (E1, E2, E4, E5).
2. **Plano Essencial para IES pequenas:** faixa de entrada com mínimo mensal reduzido (R$ 2,5 mil) e preço por aluno de R$ 2,00 para IES com menos de 5 mil alunos EAD (E3); mantidas as faixas R$ 6/4/3 para o plano Pro.
3. **Templates de mensagem e janela de contato no MVP** (E4, E7, E8): cada linha da fila traz modelo de mensagem em tom de apoio e horário sugerido (19h–22h).
4. **"Kit de retomada" anexado ao contato** (E7): resumo do capítulo em que o aluno parou + próximo passo concreto.
5. **Registro de resultado em um clique** (E5) e integração com WhatsApp promovida para o primeiro trimestre pós-piloto.
6. **Meta de rematrícula contratual no piloto** (E6): piloto de 90 dias em um curso, com meta acordada e conversão automática em contrato anual.
7. **Argumento LGPD explícito no material comercial** (E2, E6): "o dado não sai do banco da instituição".
