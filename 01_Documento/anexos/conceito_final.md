# CONCEITO FINAL — Retena

> Consolidação da proposta vencedora (Retena / product), com enxertos aprovados pelos jurados: ritual "toda segunda" e fechamento de ciclo em R$ (Tenaz), dupla persona e dashboard de receita em risco (Ancora), aderência aos números reais do dataset, piloto de 90 dias em uma fase e tagline narrativa (Fôlego). Preço reajustado para cima conforme os três vereditos.

## 1. Nome e tagline (decisão final + 3 alternativas)

**Nome final: Retena**

- Origem: **reten**ção + **antena**. Capta sinais fracos no LMS (recência, tendência de queda, capítulo travado) antes de o silêncio virar evasão.
- Três sílabas, pronúncia natural em pt-BR, grafia sem acento (domínio e busca limpos: retena.com.br / retena.app), sem colisão com edtechs conhecidas. Funciona como verbo interno da IES ("passar no Retena", "a lista do Retena").
- Risco apontado pelos jurados (soar como "retina" / marca farmacêutica) é mitigado pela tagline narrativa e pelo símbolo: a marca nunca aparece sem o "batimento do aluno".

**Tagline principal (narrativa, enxerto da Fôlego):**
> **Ninguém desiste de repente. A Retena percebe antes.**

**Tagline de apoio (produto/ação, enxerto da Tenaz):**
> Toda segunda, quem está a duas semanas de sumir. E o que fazer.

**Alternativas reservadas (nomes de módulo ou plano B):**
1. **Pulso** — o painel semanal do coordenador (módulo "Pulso da turma").
2. **Alento** — módulo de reativação / aluno recuperado (enxerto da Fôlego).
3. **Maré** — visão de coorte e receita em risco por fase (enxerto da Fôlego/Ancora).

## 2. Posicionamento

Para **coordenadoras de permanência e diretoras de operações acadêmicas de IES privadas com EAD**, a **Retena** é o radar de permanência que transforma os logs brutos do LMS (Moodle/FIAP ON) em **score de risco de evasão por aluno**, **diagnóstico de atrito de conteúdo** e **fila semanal de intervenção com receita preservada em R$**, rodando **dentro do Oracle Autonomous AI Database**, sem pipeline externo e sem projeto de TI.

Diferente de BI passivo (mostra o passado) e de CRM de cobrança (age quando a mensalidade já parou), a Retena diz **quem contatar, por quê, quando e o que ajustar no curso**, com valor visível em 30 dias e ROI medido em rematrícula.

Categoria: *retenção preditiva in-database para o ensino superior EAD*. Frase-síntese para o formulário da banca (≤300 caracteres):
> "Coordenadores de EAD só descobrem a evasão quando a mensalidade para. A Retena lê os logs do LMS, pontua o risco de cada aluno dentro do banco Oracle e entrega toda segunda quem contatar, por quê e o que mudar no conteúdo."

## 3. Problema (1 frase + 3 evidências da base)

**Frase:** Quatro em cada dez alunos EAD desistem por ano, e a instituição descobre tarde — no financeiro ou na rematrícula — embora o LMS registre semanas antes cada sinal de desengajamento.

**Evidências da base real (Base-Anônima.xlsx → logs.csv, 684.723 eventos, 203 alunos, 15/01–26/08/2026):**
1. **Inatividade silenciosa é massiva:** em 26/08, 61 alunos (30%) estavam há mais de 14 dias sem acesso, 47 (23%) há mais de 30 dias e 35 (17%) há mais de 60 dias — um terço da turma já "sumiu" sem que ninguém tenha um alerta.
2. **A perda é gradual e mensurável no funil:** dos ativos na F1, 94,3% chegam à F2, 94,3% à F3, 92,0% à F4 e 88,0% à F5 — 12% dos ingressantes perdidos em ~7 meses; 9 alunos aparecem só na F1 (abandono precoce) e 8 param após a F4.
3. **O conteúdo trava em pontos previsíveis:** na F5, 25 alunos estão parados nos capítulos 1–2; a cauda de travamento concentra-se nos caps 1–3 de cada fase, com formato quase monolítico (Player HTML ≈323 mil eventos vs. PDF ≈18,6 mil, vídeo/áudio quase nulos) e pico de uso 19h–22h de segunda a quinta — perfil de aluno trabalhador.

**Evidências de mercado (fontes do brief):** desistência EAD 41,6% em 2024 (Semesp, 16º Mapa do Ensino Superior, 2026); EAD = 50,7% das matrículas, 5,19 mi alunos (INEP, Censo 2024); desistência acumulada do ciclo 2020–2024 na EAD privada: 68,1%.

## 4. Público-alvo

### Persona compradora (sponsor com orçamento) — enxerto da Ancora
- **Nome:** Renata Albuquerque, 46 anos.
- **Cargo:** Diretora de Operações Acadêmicas (responde por EAD, permanência e receita de mensalidades) em um Centro Universitário privado de porte médio.
- **IES:** ~12 mil alunos EAD, 5 polos, LMS Moodle customizado, ERP acadêmico rodando Oracle. Não pertence a mega grupo.
- **Rotina:** reuniões semanais de resultado com reitoria e financeiro; acompanha rematrícula por ciclo; aprova orçamento de tecnologia acadêmica até ~R$ 500 mil/ano; cobra a coordenação por metas de permanência.
- **Metas:** reduzir desistência anual EAD de ~41% para <35% em 2 anos; elevar rematrícula; justificar cada real gasto como proteção de receita recorrente.
- **Dores:** descobre evasão quando a receita cai; relatórios de BI mostram o que já aconteceu; projetos de TI para "analytics" duram meses; medo de vazar dados de alunos (LGPD).
- **KPIs:** taxa de desistência anual, receita em risco por coorte (R$), receita preservada por reativação (R$), custo de retenção vs. CAC (> R$ 1.000, estimativa).
- **Objeções:** "Já tenho BI no Moodle"; "Meu time não tem cientista de dados"; "Dados dos alunos não saem da instituição"; "Quanto isso devolve em rematrícula?"; "Integração vai virar projeto de TI".

### Persona usuária (uso diário do painel)
- **Nome:** Mariana Costa, 34 anos, Coordenadora de Permanência e Sucesso do Aluno, reporta a Renata. Lidera 12 tutores.
- **Rotina:** segunda-feira de manhã abre a fila do Retena, distribui contatos aos tutores, acompanha respostas até sexta; mensalmente apresenta reativações e R$ preservado.
- **Dor:** hoje tutores agem no escuro sobre 30% de inativos; sem critério de prioridade nem registro do que funcionou.
- **KPI:** % de alunos em risco reengajados em 30 dias; tempo entre sinal e contato; taxa de resposta por horário de contato.
- **Objeções:** "Mais uma planilha para preencher"; "Não quero parecer cobrança para o aluno".

### Beneficiário final
- **Aluno EAD trabalhador** (perfil do dataset: estuda 19h–22h, segunda a quinta), que trava em um capítulo, perde ritmo por 2–3 semanas e, sem ninguém perceber, desiste — perdendo o investimento feito e a chance do diploma. A Retena faz alguém chamá-lo no momento certo, no horário certo, com um caminho concreto para retomar.
- **Tutores:** deixam de ligar aleatoriamente e passam a receber lista priorizada com motivo, modelo de mensagem e horário sugerido.

## 5. Proposta de valor

**Para a diretora (compra):** proteção de receita recorrente. Cada coorte mostra receita em risco em R$; cada reativação registrada vira receita preservada em R$ no relatório mensal. Contrato se paga com poucas rematrículas a mais.

**Para a coordenadora (usa):** toda segunda, uma fila priorizada de quem está a duas semanas de sumir, com motivo em linguagem simples, tutor responsável, modelo de mensagem e janela de contato sugerida (19h–22h). Zero planilha; o registro do contato acontece no próprio painel.

**Para a IES (governança):** o modelo treina e pontua dentro do Oracle Autonomous AI Database que a instituição já conhece; dados de alunos não saem do banco (LGPD), sem infraestrutura de ML separada, implantação em semanas via CSV/API do LMS.

**Para o aluno:** ser chamado antes de desistir, no horário em que estuda, com um caminho para destravar o capítulo.

Promessa mensurável: **valor visível em 30 dias** (primeira fila e primeiras reativações), **ROI provado em 90 dias** (piloto em uma fase com meta de rematrícula acordada).

## 6. MVP — 6 funcionalidades priorizadas

| # | Funcionalidade | Dados que usa | Oracle |
|---|---|---|---|
| 1 | **Ingestão e features semanais por aluno** (CSV/API Moodle/FIAP ON): eventos/semana, dias ativos, recência, capítulos alcançados, tentativas/entregas de quiz, tendência 2 semanas vs. anteriores, mix HTML/PDF, faixa horária | Colunas Hora, Nome completo, Contexto do Evento, Componente, Nome do evento, Origem (684.723 eventos) | Tabelas + SQL analítico no Autonomous DB (Free em Docker no dev) |
| 2 | **Score de risco in-database** com faixas verde/amarelo/vermelho e **motivo explicável** ("14 dias sem acesso, queda de 70% em eventos, parado no cap 2 da F5") | Features da #1; rótulo histórico = aluno que sumiu >30 dias ou não avançou de fase | OML / DBMS_DATA_MINING (XGBoost ou GLM), PREDICTION_PROBABILITY e PREDICTION_DETAILS em SQL |
| 3 | **Fila semanal de intervenção "Toda segunda"** com responsável nomeado, modelo de mensagem, janela de contato sugerida (pico 19h–22h) e registro de contato/resultado (reativado / não / sem resposta) | Score da #2, horário de atividade do aluno, histórico de contatos | APEX (formulários e workflow), tabela de intervenções |
| 4 | **Detector de atrito de conteúdo**: capítulos onde alunos travam (ex.: F5 caps 1–2, 25 alunos), tempo médio por capítulo, mix de formato, taxa de quiz entregue/iniciado | Contexto do Evento (capítulo), Progresso de conteúdo atualizado, questionários | SQL analítico + APEX (mapa de calor por fase/capítulo) |
| 5 | **Painel executivo de receita em risco em R$** por coorte e fase (funil F1→F5, inativos >14/30/60 dias, alunos vermelhos × ticket médio) e receita preservada acumulada | Score da #2, resultados da #3, ticket médio informado pela IES (parâmetro) | APEX (dashboard), Oracle Analytics Cloud opcional |
| 6 | **Loop de aprendizado + perguntas em português**: resultado de cada intervenção realimenta o retreino mensal; coordenadora pergunta "quais alunos da F3 pararam no cap 2 este mês?" | Tabela de intervenções (#3), features (#1) | Retreino agendado via DBMS_SCHEDULER; Select AI sobre as views de negócio |

Fora do MVP (roadmap): recomendação automática de formato alternativo por capítulo (módulo "conteúdo adaptativo"), integração com WhatsApp/e-mail, multi-campus, API pública.

## 7. Jornada principal do usuário (Mariana, segunda-feira)

1. **Domingo 23h (automático):** job semanal recalcula features e scores no Autonomous DB; fila é gerada e e-mail-resumo sai para Mariana e tutores.
2. **Segunda 8h:** Mariana abre o painel APEX; vê "Pulso da turma": 203 alunos, 31 vermelhos, 44 amarelos, receita em risco desta semana em R$.
3. **Prioriza a fila:** ordenada por probabilidade × valor; cada linha traz motivo explicável (ex.: "12 dias sem acesso, tendência −65%, parado no cap 2 da F5").
4. **Distribui:** atribui tutores responsáveis em dois cliques; o sistema sugere modelo de mensagem e janela de contato (19h–22h, terça ou quarta).
5. **Tutor contata** o aluno no horário sugerido, com uma ação concreta ("vamos retomar o cap 2 juntos; segue o resumo em PDF").
6. **Registra o resultado** no painel: respondeu / não respondeu / voltou a acessar; o sistema marca reativação automaticamente quando o LMS registra novo acesso em 7 dias.
7. **Quinta:** Mariana confere o mapa de atrito da F5 e percebe que caps 1–2 concentram travamentos; abre um ticket para a coordenação pedagógica com a recomendação (dividir capítulo, adicionar vídeo curto).
8. **Pergunta em português** via Select AI: "quantos alunos amarelos da F4 não fizeram quiz nas últimas 2 semanas?" e ajusta a fila.
9. **Fim do mês:** relatório executivo para Renata: alunos reativados, taxa de resposta por horário, receita preservada em R$ vs. custo da assinatura.
10. **Retreino mensal:** resultados registrados realimentam o modelo; o score da próxima segunda já incorpora o que funcionou naquela IES.

## 8. Diferencial competitivo e por que não foi resolvido assim antes

**Diferencial (o que só a Retena faz junto):**
- **Sinais precoces, não tardios:** recência, tendência de queda e capítulo travado antecipam semanas o sinal financeiro que BI e CRM usam.
- **Quem + onde + resultado:** risco por aluno, atrito por capítulo e reativação medida em R$ no mesmo painel — fecha o ciclo aluno-conteúdo-intervenção-ROI.
- **In-database:** treino e scoring dentro do Oracle Autonomous AI Database; dados não saem da IES (LGPD), sem cientista de dados nem servidor de ML.
- **Loop proprietário:** cada intervenção registrada retreina o modelo; a defensibilidade cresce por cliente e por mês.
- **Ritual, não relatório:** a fila de segunda transforma dado em disciplina operacional para o tutor.

**Por que não foi resolvido assim antes:**
1. **Dado preso em relatórios estáticos:** LMS entregam logs e dashboards descritivos; a evasão era medida no financeiro, quando já é tarde.
2. **ML exigia pipeline pesado:** até recentemente, prever risco significava exportar dados, montar infraestrutura de ML e contratar cientista de dados — inviável para IES médias e arriscado sob a LGPD (2020+). ML in-database maduro (OML no 26ai, Always Free) removeu essa barreira.
3. **Nunca se fechou o ciclo:** BI mostra, CRM cobra, mas ninguém registrava o resultado da intervenção para provar ROI e melhorar o modelo.
4. **O problema explodiu agora:** EAD virou maioria em 2024 (50,7%, INEP) com desistência de 41,6% (Semesp) e CAC acima de R$ 1.000 (estimativa): reter ficou mais barato que captar, e a diretora passou a ter orçamento para isso.

## 9. Modelo de negócio e precificação (com contas)

**Modelo:** SaaS B2B cobrado por aluno ativo/mês, em três faixas de volume (ajuste para cima frente à proposta original de R$ 1,50–3,00, conforme os três jurados) e três planos.

| Faixa de volume | Preço por aluno ativo/mês |
|---|---|
| 1k–10k alunos | R$ 6,00 |
| 10k–50k alunos | R$ 4,00 |
| 50k+ alunos (mega grupos, fase 2) | R$ 3,00 |

- **Mínimo mensal:** R$ 5.000 (protege contra contas pequenas).
- **Setup e integração LMS (uma vez):** R$ 10 mil a R$ 25 mil, conforme LMS e número de cursos.
- **Planos:** Essencial (score, motivo, fila semanal) / Pro (+ mapa de atrito, painel executivo de R$, Select AI) / Enterprise (multi-campus, API, SLA, retreino dedicado). Preço acima é do Pro; Essencial −25%, Enterprise +30%.
- **Cunha de entrada:** piloto de 90 dias em **uma fase de um curso**, pago simbolicamente (R$ 5 mil, o mínimo mensal, por todo o piloto), com **meta de rematrícula acordada**; ao atingir a meta, converte automaticamente em contrato anual.
- **Upsell:** módulo de conteúdo adaptativo (recomendação de formato por capítulo) e Oracle Analytics Cloud para grupos.
- **Margem bruta alvo:** 80% (custo de infraestrutura Autonomous DB por aluno é marginal; custo principal é onboarding).

**Conta do cliente-referência (Renata, 12 mil alunos EAD):**
- Assinatura: 12.000 × R$ 4,00 = **R$ 48 mil/mês = R$ 576 mil/ano** (+ setup R$ 20 mil).
- Receita preservada por aluno retido: ticket EAD R$ 250–450/mês (estimativa do brief) → **R$ 3–5 mil/ano**; usamos R$ 4.200/ano (R$ 350/mês).
- Alunos a reter para pagar o contrato: R$ 576 mil ÷ R$ 4.200 ≈ **137 alunos/ano ≈ 11–12 por mês**, ou **1,1% da base**.
- Referência: com desistência de ~41%, essa IES perde ~4.900 alunos/ano. Evitar **2,8% dessas desistências** já paga a Retena; cada ponto percentual de desistência evitado (~120 alunos) vale ~R$ 500 mil/ano. Além disso, cada aluno retido evita um CAC > R$ 1.000 (estimativa).
- Meta do piloto de 90 dias: reengajar 30% dos alunos vermelhos da fase-piloto em 30 dias (na base, 61 inativos >14 dias → ~18 reativações) — evidência suficiente para a conversão.

## 10. TAM / SAM / SOM (com contas e fontes do brief)

Corrigido o apontamento dos jurados: o mercado é calculado sobre **EAD**, não sobre graduação total.

- **TAM (Brasil, EAD graduação):** 5.189.391 matrículas EAD (INEP, Censo da Educação Superior 2024, divulgado 22/09/2025) × R$ 4,00 × 12 meses ≈ **R$ 249 mi/ano**. Mercado expandido (graduação total, presencial incluso, 10,2 mi matrículas × R$ 48/ano) ≈ R$ 490 mi/ano.
- **SAM (EAD privada, excluindo mega grupos):** rede privada concentra 95,9% das matrículas EAD (Semesp, 16º Mapa do Ensino Superior 2026) → 5,19 mi × 95,9% ≈ 4,98 mi alunos. Excluindo os mega grupos (1,4% das mantenedoras com 47,1% dos estudantes, Semesp) como mercado inicial: 4,98 mi × 52,9% ≈ **2,63 mi alunos × R$ 48/ano ≈ R$ 126 mi/ano**. Os mega grupos (≈2,35 mi alunos, ≈R$ 85 mi/ano a R$ 3,00) ficam como fase 2, via canal Oracle.
- **SOM (3 anos):** 2% do SAM ≈ **52 mil alunos ativos em 8–12 IES médias** (média 5 mil alunos cada) × R$ 48/ano ≈ **R$ 2,5 mi ARR**; com 1 mega grupo piloto na fase 2 (50 mil alunos × R$ 36/ano), **R$ 4,3 mi ARR**. Trajetória: ano 1 = 3 pilotos + 2 contratos (R$ 0,5 mi ARR); ano 2 = 6 IES (R$ 1,4 mi); ano 3 = 10–12 IES + 1 grupo (R$ 2,5–4,3 mi).
- **Contexto de dor:** desistência EAD 41,6% em 2024 (Semesp); >2 milhões de matrículas EAD perdidas por ano (estimativa do brief); cada aluno retido por 12 meses preserva R$ 3–5 mil (estimativa).

## 11. Estratégia Oracle

**Serviço principal (coração): Oracle Autonomous AI Database (Serverless, 26ai) com Oracle Machine Learning in-database.**
- Features semanais, treino (DBMS_DATA_MINING: XGBoost ou GLM para classificação binária "vai sumir em 30 dias") e scoring (PREDICTION_PROBABILITY, PREDICTION_DETAILS para o motivo explicável) acontecem **no mesmo banco onde o dado mora**. Nenhum ETL, nenhum servidor de ML, nenhum dado de aluno em nuvem de terceiros.
- Retreino mensal agendado (DBMS_SCHEDULER) incorporando os resultados das intervenções.

**Serviços secundários:**
- **Oracle APEX:** painel da coordenadora (fila, mapa de atrito, registro de contato) e dashboard executivo de receita em risco, em low-code, entregue em dias.
- **Select AI:** perguntas em português sobre views de negócio ("quem parou no cap 2 da F5 este mês?").
- **OCI Object Storage:** landing dos CSVs exportados do LMS; carga via DBMS_CLOUD.
- **OML Notebooks / OML4Py:** exploração de features e comparação de algoritmos (AutoML) pela equipe.
- **Roadmap:** JSON Relational Duality Views para API do painel; AI Vector Search para similaridade entre capítulos (módulo adaptativo); OCI Functions + API Gateway para webhooks de LMS; Oracle Analytics Cloud para grupos.

**Por que é decisão estratégica, não tecnicismo:**
1. **LGPD e venda:** "o dado não sai da instituição" elimina a objeção número 1 da diretora e do jurídico.
2. **Custo e time-to-value:** Always Free viabiliza o MVP e o piloto; APEX substitui meses de front-end; uma equipe de engenharia pequena opera sem cientista de dados dedicado.
3. **Canal de distribuição:** ERPs acadêmicos e mega grupos já rodam Oracle; a Retena entra como extensão do que a IES já tem, reduzindo atrito de compra e abrindo a fase 2 via ecossistema Oracle.
4. **Defensibilidade:** o loop de retreino por cliente cria dado proprietário dentro do banco do cliente, difícil de replicar por BI genérico.

**Caminho local Free → Autonomous:**
1. **Hoje (evidência produzida):** Oracle Database Free (imagem gvenzl/oracle-free) em Docker local; carga do logs.csv via python-oracledb; tabelas de features; modelo treinado com DBMS_DATA_MINING; scoring via PREDICTION_PROBABILITY em SQL. Tudo roda offline no ZIP do entregável.
2. **Piloto:** provisionar Autonomous AI Database Always Free (OCI), migrar schema e modelo via Data Pump/SQL scripts (mesmo dialeto, zero reescrita), publicar APEX e habilitar Select AI.
3. **Produção:** Autonomous pago com auto-scaling, um schema (ou banco) por IES para isolamento, OCI Object Storage para ingestão e Oracle Analytics Cloud para grupos.

## 12. Identidade visual

**Paleta**

| Nome | Hex | Uso |
|---|---|---|
| Azul-profundo | #0B2545 | Marca, títulos, fundo de slides de abertura (confiança institucional) |
| Verde-sinal | #2EC4B6 | Aluno ativo / reativado, faixa verde do score, linha do batimento |
| Âmbar-alerta | #FFB703 | Faixa amarela, alertas, destaques de risco moderado |
| Coral-urgência | #FF6B4A | Faixa vermelha (enxerto da Fôlego: urgência humana, não alarme frio); uso restrito |
| Off-white | #F6F7F9 | Fundo de UI e slides |
| Grafite | #3A4A5C | Texto corrido, dados em tabela |

**Tipografia (Google Fonts):** **Sora** (títulos, 600/700) e **Inter** (UI, dados, tabelas, 400/500; números com tabular figures).

**Símbolo / metáfora do logo:** uma linha de pulso (o "batimento do aluno") que ameaça cair e é sustentada, transformando-se em trilha contínua ascendente até um ponto final (a formatura). Fusão do pulso da Retena com a "linha segurada" da Tenaz. O traço horizontal do pulso pode servir de sublinhado do logotipo "Retena"; a linha em verde-sinal sobre azul-profundo é a versão principal; monocromática em azul para documentos.

**Tom de voz:** humano, direto, sem alarmismo. Fala de "perceber antes" e "chamar de volta", nunca de "cobrar" ou "vigiar". Números sempre acompanhados de uma pessoa ("25 alunos parados no cap 2", não "25 registros"). Frases curtas; verbo de ação no fim ("...E aja.").

**Do:**
- Mostrar sempre um motivo em linguagem simples ao lado de cada score.
- Usar verde para reativação e progresso; celebrar retornos.
- Citar fontes (INEP, Semesp) e rotular estimativas como estimativas.
- Manter a linha do batimento em toda peça de marca.

**Don't:**
- Não usar vermelho puro, sirenes ou linguagem de "inadimplência"/"cobrança".
- Não exibir dados nominais de alunos em materiais externos (sempre "Aluno NNNN").
- Não usar ícone de olho/retina (reforça a confusão sonora) nem âncora/pinça.
- Não prometer "prever com 100%"; falar de probabilidade e priorização.

## 13. Estrutura do pitch (4m30s = 270 s)

| # | Bloco | Duração | Mensagem-chave |
|---|---|---|---|
| 1 | Público | 20 s | "Falo com quem responde pela permanência em uma IES privada de EAD: a diretora de operações que assina e a coordenadora que liga para o aluno." |
| 2 | Problema | 40 s | "4 em 10 alunos EAD desistem por ano (Semesp) e a IES descobre quando a mensalidade para. Na base real que analisamos, 30% da turma estava há mais de 14 dias sem acesso e ninguém tinha um alerta. Ninguém desiste de repente." |
| 3 | Oportunidade | 25 s | "EAD virou maioria em 2024 (INEP): 5,2 mi alunos, 2 mi matrículas perdidas por ano, CAC acima de R$ 1.000. Reter ficou mais barato que captar, e o LMS já registra cada sinal." |
| 4 | Solução | 40 s | "A Retena lê os logs do LMS, pontua o risco de cada aluno dentro do Oracle Autonomous AI Database e entrega, toda segunda, quem contatar, por quê, quando e o que ajustar no conteúdo — com o resultado medido em R$." |
| 5 | Demonstração | 60 s | Painel APEX ao vivo: funil 94%→94%→92%→88%; fila de segunda com motivos; 25 alunos parados nos caps 1–2 da F5; registro de contato; SQL com PREDICTION_PROBABILITY rodando in-database; pergunta em português via Select AI. |
| 6 | Diferencial | 25 s | "BI mostra o passado, CRM cobra tarde. Só a Retena junta quem, onde e resultado, sem tirar o dado da instituição, e cada intervenção retreina o modelo. Isso só ficou viável com ML in-database maduro." |
| 7 | Monetização | 25 s | "SaaS por aluno ativo: R$ 3 a 6/mês, mínimo R$ 5 mil, piloto de 90 dias com meta acordada. IES de 12 mil alunos paga R$ 576 mil/ano e se paga retendo 137 alunos, 1,1% da base." |
| 8 | Mercado | 20 s | "TAM R$ 249 mi/ano em EAD; SAM R$ 126 mi nas IES privadas fora dos mega grupos; SOM de R$ 2,5–4,3 mi ARR em 3 anos, com mega grupos via ecossistema Oracle na fase 2." |
| 9 | Fechamento | 15 s | "Ninguém desiste de repente. A Retena percebe antes — e diz o que fazer. Retena: o radar de permanência dentro do banco que a IES já usa." |

Total: 20 + 40 + 25 + 40 + 60 + 25 + 25 + 20 + 15 = **270 s (4m30s)**, com 30 s de folga para o limite de 5 min.

## 14. Riscos e mitigação

| # | Risco | Mitigação |
|---|---|---|
| 1 | **Modelo com poucos dados por IES** (203 alunos na base; rótulo de evasão parcial porque a F5 está em andamento) | Começar com regras + GLM interpretável, rótulo proxy (>30 dias inativo ou não avançou de fase), validação temporal; migrar para XGBoost conforme volume; retreino mensal com resultados das intervenções. Rotular métricas como preliminares. |
| 2 | **Coordenadora tem dor, mas não orçamento; ciclo de venda longo** | Dupla persona: vender proteção de receita à diretora de operações com dashboard de R$ em risco; piloto de 90 dias pago simbolicamente com meta de rematrícula e conversão automática. |
| 3 | **Integração com LMS vira projeto de TI** | Entrada por CSV exportado (padrão Moodle) já validada na base real; API como segundo passo; APEX pronto em dias; SLA de "primeira fila em 30 dias". |
| 4 | **LGPD e percepção de vigilância do aluno** | Dados nunca saem do banco da IES; pseudonimização (Aluno NNNN) fora do painel; tom de voz de apoio, não cobrança; opt-in de contato registrado; base legal de execução de contrato educacional documentada. |
| 5 | **Concorrência de BI embarcado no LMS ou grandes edtechs; nome confundido com "retina"** | Diferenciar pelo ciclo fechado (intervenção + ROI + retreino) e pelo canal Oracle; registrar retena.com.br/.app e marca INPI cedo; nunca exibir o nome sem a tagline e a linha do batimento; nomes reserva (Pulso, Alento, Maré) como módulos. |
