# Retena — Resumo para a Banca Final (23/09/2026)

> Radar de permanência para o ensino superior EAD. "Ninguém desiste de repente. A Retena percebe antes."
> Equipe: Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)

Links para ter abertos: vídeo https://youtu.be/HZrcLvIJCC4 · site https://lucashenklain.github.io/retena/ · dashboard https://lucashenklain.github.io/retena/dashboard/ · evidências Oracle https://lucashenklain.github.io/retena/evidencias/evidencias.html

---

## 1. Elevator pitch (30 segundos)

Quatro em cada dez alunos de EAD desistem por ano, e a instituição só descobre quando a mensalidade para. O LMS já registra cada sinal semanas antes: o aluno acessa menos, trava num capítulo, some. A Retena lê esses logs dentro do Oracle AI Database, pontua o risco de cada aluno com Oracle Machine Learning e entrega, toda segunda, a lista de quem contatar, por quê e o que ajustar no conteúdo. Vendemos proteção de receita para diretores de operações; quem usa é a coordenação de permanência. Já provamos o modelo em uma base real de 685 mil eventos, rodando dentro do banco.

## 2. Os números que sustentam a história

| O que dizer | Número | Fonte |
|---|---|---|
| Desistência anual no EAD (2024), recorde | 41,6% (presencial: 24,8%) | Semesp, 16º Mapa do Ensino Superior 2026 |
| EAD virou maioria das matrículas | 5,19 mi alunos (50,7%); 2.244 IES privadas | INEP, Censo 2024 |
| Na base real, alunos há mais de 14 dias sem acesso em um único dia | 61 de 203 (30%), sem nenhum alerta | Base anonimizada do curso (684.723 eventos, jan–ago/2026) |
| Perda no funil das 5 fases | 12% dos ingressantes em 7 meses (94% → 94% → 92% → 88%) | Base real |
| Modelo Python (teste temporal jun–ago) | AUC-ROC 0,88; 88% de precisão no top-20% de risco; lift 3,06×; faixa Alto com 95% de inatividade observada | 05_MVP/outputs/RESULTADOS.md |
| Modelo in-database Oracle (Random Forest, DBMS_DATA_MINING) | AUC 0,949 no teste temporal; 684.723 eventos carregados; 3 modelos treinados no banco | 06_Oracle/evidencias |
| Preço | R$ 6 / 4 / 3 por aluno ativo/mês por faixa de volume; mínimo R$ 5 mil/mês; setup R$ 10–25 mil | Conceito, seção 3.6 |
| Conta do cliente-referência (12 mil alunos EAD) | R$ 576 mil/ano; se paga retendo 137 alunos (1,1% da base); cada ponto de desistência evitado vale ~R$ 500 mil/ano | Conceito, seção 3.6 (ticket R$ 350/mês, estimativa) |
| Mercado | TAM R$ 249 mi/ano · SAM R$ 126 mi/ano · SOM R$ 2,5–4,3 mi ARR em 3 anos | Conceito, seção 3.6 |

## 3. Roteiro sugerido para a apresentação (8 minutos + perguntas)

| Tempo | Bloco | Mensagem central | O que mostrar |
|---|---|---|---|
| 0:00–0:40 | Gancho e quem somos | "Ninguém desiste de repente." A evasão é um processo silencioso de semanas; a IES descobre no financeiro. | Slide de capa / site |
| 0:40–1:40 | Problema e público | 41,6% de desistência EAD; dupla persona: Renata (diretora de operações, compra proteção de receita) e Mariana (coordenadora de permanência, usa a fila toda segunda). | Números do problema |
| 1:40–2:40 | Evidência na base real | 685 mil eventos, 203 alunos, 5 fases; 30% da turma em silêncio há mais de 14 dias; travamentos nos mesmos capítulos; pico de estudo 19h–22h (aluno trabalhador). | Funil e heatmap de atrito |
| 2:40–3:40 | Solução e MVP | Três entregas semanais: score de risco explicável, mapa de atrito de conteúdo e fila de intervenção com resultado em R$. Ritual "toda segunda, quem chamar; toda sexta, quem voltou". | 3 pilares |
| 3:40–4:40 | Demonstração ao vivo | Dashboard: KPIs, fila de segunda (clicar em um aluno para abrir fatores e ação), mapa de atrito, seção do modelo. | https://lucashenklain.github.io/retena/dashboard/ |
| 4:40–5:40 | Oracle: por que dentro do banco | Features em SQL, treino e scoring com DBMS_DATA_MINING, PREDICTION_PROBABILITY/DETAILS, views JSON; o dado do aluno não sai da IES (LGPD); sem servidor de ML nem cientista de dados; Autonomous AI Database + APEX + Select AI em produção. | Diagrama 06 e página de evidências |
| 5:40–6:30 | Resultados e honestidade | AUC 0,88 no teste temporal (Python) e 0,95 in-database (Oracle); 88% de precisão no top-20%; limitações: amostra de um curso, rótulo comportamental, subconjunto acionável com AUC 0,74. | Cards de métricas |
| 6:30–7:20 | Negócio e mercado | SaaS por aluno ativo/mês, piloto de 90 dias com meta de rematrícula, conta do cliente-referência; TAM/SAM/SOM; megagrupos via ecossistema Oracle na fase 2. | Tabela de preços |
| 7:20–8:00 | Fechamento | "A evasão não é um evento, é um silêncio. A Retena escuta esse silêncio e devolve tempo para quem pode agir." Pedido: apoio para provisionar o Autonomous AI Database Always Free e um piloto com uma IES parceira até o NEXT. | Slide final |

Dica: quem apresenta a demonstração deve abrir o dashboard antes de começar e deixar a busca em "Aluno 0227" pronta.

## 4. Perguntas prováveis da banca e respostas curtas

1. **"203 alunos é pouco para treinar um modelo."** É pouco, e dizemos isso no documento. Por isso usamos validação temporal (treinamos em fevereiro–maio e testamos em junho–agosto, sem olhar o futuro), reportamos o subconjunto acionável separadamente (AUC 0,74) e desenhamos o produto para retreinar mensalmente com os dados de cada instituição. O modelo é portátil porque usa só logs de navegação, que todo LMS tem.

2. **"Por que os dois modelos têm AUC diferentes (0,88 e 0,95)?"** São duas implementações independentes do mesmo problema: o pipeline Python é a referência metodológica, com mais features e embargo de 21 dias; o modelo Oracle prova a arquitetura in-database, com um conjunto de features em SQL um pouco diferente. Os dois usam teste temporal a partir de junho. O ponto não é o decimal: é que o sinal existe e roda dentro do banco.

3. **"Por que Oracle e não um pipeline Python com qualquer banco?"** Três razões de negócio: LGPD e jurídico ("o dado do aluno não sai da instituição" elimina a objeção número um da diretora), time-to-value (features em SQL, treino com DBMS_DATA_MINING e painel em APEX, sem servidor de ML nem cientista de dados dedicado) e canal (ERPs acadêmicos e grandes grupos já rodam Oracle). Tecnicamente já executamos tudo isso no Oracle AI Database 26ai Free: carga, features, três modelos, scoring e views JSON, com evidências no pacote.

4. **"O que exatamente vocês preveem?"** A probabilidade de o aluno ficar 21 dias sem nenhuma ação no LMS, recalculada todo domingo. É um proxy comportamental de evasão, não o cancelamento administrativo, porque o cancelamento chega tarde e o silêncio é o ponto em que o contato ainda funciona. Também temos um segundo modelo que antecipa quem não inicia a fase seguinte (AUC média 0,93).

5. **"Como vocês validaram com o mercado?"** Em três frentes: validação quantitativa com a base real, fontes secundárias (INEP e Semesp) e um instrumento de entrevistas de 12 perguntas. As oito entrevistas documentadas foram conduzidas em formato simulado, com personas sintéticas construídas a partir dos perfis-alvo e dos dados, para calibrar o roteiro e antecipar objeções; estão rotuladas assim no documento e serão confirmadas em campo antes do piloto. Se a banca perguntar, responder exatamente isso, sem rodeios.

6. **"Quem paga e quanto?"** Quem paga é o diretor de operações acadêmicas, porque compramos rematrícula para ele. SaaS por aluno ativo/mês: R$ 6 até 10 mil alunos, R$ 4 de 10 a 50 mil e R$ 3 acima disso, mínimo de R$ 5 mil/mês e setup de R$ 10–25 mil. Uma IES de 12 mil alunos paga R$ 576 mil/ano e se paga retendo 1,1% da base. Para IES pequenas criamos o plano Essencial, mais barato, porque as entrevistas mostraram que a dor existe mas o orçamento é mínimo.

7. **"Isso não é só um BI?"** BI mostra o passado e CRM de cobrança age quando a mensalidade já parou. A Retena antecipa (recência, tendência de queda, capítulo travado), prioriza (quem, por quê, quando e o que dizer) e fecha o ciclo (registro do resultado, receita preservada em R$ e retreino). O loop de intervenções cria um dado proprietário por cliente que um BI genérico não tem.

8. **"E a LGPD? Vocês tratam dados de alunos."** O processamento acontece dentro do banco que a IES já controla; fora do painel os alunos aparecem pseudonimizados ("Aluno NNNN"); a base legal é a execução do contrato educacional e o interesse legítimo de apoio acadêmico; o tom é de apoio, nunca de cobrança ou vigilância.

9. **"Como isso escala?"** Um schema por IES no Autonomous AI Database Serverless, com auto-scaling; ingestão por CSV padrão do LMS (Object Storage + DBMS_CLOUD) ou API; jobs semanais com DBMS_SCHEDULER; painel em APEX; custo marginal por aluno próximo de zero, então a margem bruta alvo é 80%. Megagrupos entram na fase 2 via ecossistema Oracle.

10. **"Qual é o próximo passo concreto?"** Provisionar o Autonomous AI Database Always Free, publicar a primeira aplicação APEX e fechar um piloto de 90 dias em uma fase de um curso, pago simbolicamente (R$ 5 mil) e com meta de rematrícula acordada, convertendo em contrato anual se a meta for atingida. Meta interna: demonstrar isso no NEXT, em 24/10.

11. **"Concorrentes?"** BI embarcado nos LMS (Moodle Analytics, Canvas Insights), consultorias de retenção e CRMs educacionais. Nenhum deles junta risco por aluno, atrito por capítulo e resultado da intervenção em R$ rodando dentro do banco da instituição. Nosso risco é o LMS embutir algo parecido; nossa defesa é o ciclo fechado com ROI medido e o canal Oracle.

12. **"O nome pode ser confundido com 'retina'."** Sabemos; por isso a marca nunca aparece sem a tagline e a linha do batimento, e os domínios retena.com.br/.app ficam limpos. Temos nomes reserva para módulos (Pulso, Alento, Maré).

13. **"Quais ferramentas Oracle vocês usaram de fato, e quais são só plano?"** Executados e evidenciados com timestamps: Oracle AI Database 26ai Free (Docker) com 684.723 eventos e features em SQL; Oracle Machine Learning via DBMS_DATA_MINING (Random Forest e GLM treinados no banco, PREDICTION_PROBABILITY e PREDICTION_DETAILS); views de scoring e JSON Duality View; job semanal com DBMS_SCHEDULER; carga e MERGE idempotente via python-oracledb. Com runbook pronto (60 minutos, números esperados documentados): Autonomous AI Database Serverless e Object Storage com DBMS_CLOUD.COPY_DATA. APEX vai ao NEXT em 24/10; Select AI está no roadmap. Cinco de nove componentes já rodam; reexecutamos tudo do zero em 22/09 sem erros.

14. **"Como o marketing digital traz clientes de forma rentável?"** Funil em quatro etapas, com ativos já publicados: landing page com vídeo de vendas, calculadora de ROI e agendamento; conteúdo com dados do INEP e da Semesp e prospecção direta (LinkedIn/ABM) de diretores de operações, além de eventos Semesp e ABED. A isca é o diagnóstico gratuito: a IES envia o export do LMS e em 7 dias recebe o painel de receita em risco em R$ (a mesma carga que fizemos em 72 s, custo quase zero). O piloto de 90 dias é pago (R$ 5 mil) e cobre o custo do diagnóstico; o contrato anual do cliente-referência vale R$ 576 mil. Metas do ano 1, medidas no funil: 30 diagnósticos, 6 pilotos, 2–3 contratos e CAC pago em menos de um trimestre de assinatura. São metas, não promessas.

15. **"Por que a Oracle deveria apostar nisso?"** Porque é consumo recorrente de Autonomous AI Database, Oracle Machine Learning e APEX por instituição (um schema por cliente), em um setor que já roda Oracle nos ERPs acadêmicos e nos megagrupos; porque a prova é executada, não desenhada; e porque o caso é replicável para ensino técnico e corporativo com o mesmo método. O que pedimos: apoio ao Always Free (ou Oracle for Startups), uma IES parceira para o piloto e mentoria comercial.

## 5. O que foi entregue (para citar se perguntarem sobre o pacote)

- Documento estruturado de 58 páginas com as Partes 1–4, próximos passos e anexos (instrumento de validação, entrevistas, respostas do formulário, roteiro do pitch, referências).
- 7 diagramas atualizados: rich picture, mapa de stakeholders, jornada do usuário, fluxograma do MVP, arquitetura inicial, arquitetura com Oracle e fluxo de dados/ML.
- Manual de marca de 16 páginas, logo em 12 versões e landing page publicada.
- MVP analítico em Python com dashboard interativo (196 alunos pontuados, fila de segunda, mapa de atrito, métricas do modelo).
- Integração Oracle executada de verdade: Oracle AI Database 26ai Free em Docker, 684.723 eventos carregados via python-oracledb, features em SQL, Random Forest e GLM treinados com DBMS_DATA_MINING, scoring por SQL, views JSON, consultas prontas para APEX e evidências com timestamps.
- Vídeo pitch de 4 min 48 s, narrado em português e legendado, com b-roll gerado por IA (Higgsfield).

## 6. Riscos que a própria equipe reconhece

| Risco | Mitigação já desenhada |
|---|---|
| Poucos dados por IES; rótulo é proxy comportamental | Validação temporal, retreino mensal, faixas lidas como prioridade relativa |
| Coordenação tem dor, mas não orçamento | Venda ao diretor de operações com painel de receita em risco; piloto com meta |
| Integração vira projeto de TI | Entrada por CSV padrão do LMS; APEX pronto em dias; primeira fila em 30 dias |
| LGPD e percepção de vigilância | Processamento in-database, pseudonimização, tom de apoio |
| Concorrência do BI embarcado; nome | Ciclo fechado com ROI; canal Oracle; marca sempre com tagline e símbolo |

## 7. Frase de fechamento

"A evasão não é um evento. É um processo silencioso que dura semanas. A Retena escuta esse silêncio, dentro do banco que a instituição já usa, e devolve tempo para quem pode agir. Ninguém desiste de repente. A Retena percebe antes."
