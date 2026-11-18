---
titulo: Retena — Documento Consolidado da Startup
subtitulo: Entrega Final · Startup One · Enterprise Challenge Oracle · FIAP 2026 (turma 4ESOA)
data: 27/11/2026
---

# Sumário executivo

**Problema.** Quatro em cada dez alunos de EAD desistem por ano (41,6% em 2024, Semesp) e a instituição descobre tarde, quando a mensalidade para. O LMS registra o desengajamento semanas antes, mas ninguém transforma esse registro em ação.

**Solução.** A Retena lê os logs do LMS **dentro do Oracle AI Database**, pontua o risco de cada aluno com **Oracle Machine Learning** e entrega, toda segunda-feira, a fila de quem contatar, por quê e o que dizer. A coordenação registra o resultado do contato no próprio painel e a diretoria vê, recalculado no banco, quanto de receita está em risco e quanto foi preservado.

**O que mudou nesta entrega (MVP final).** O ciclo agora fecha de ponta a ponta sobre o Oracle: fila lida do snapshot pontuado pelo job semanal (`DBMS_SCHEDULER`), predição ao vivo por aluno (`PREDICTION_PROBABILITY`), registro do contato gravado em `CONTATO_RESULTADO` por uma procedure PL/SQL que atualiza a fila na mesma transação, e visão da diretoria recalculada por uma view. Tudo sobe com um comando (`INICIAR_MVP.cmd`) e é verificado por um teste automatizado de 15 checagens contra o banco.

**Números-chave.**

| Indicador | Valor | Fonte |
|---|---|---|
| Base real anonimizada da IES parceira | 684.723 eventos · 203 alunos · 5 fases · 15/01–26/08/2026 | `08_Dados`, carregada no Oracle |
| Modelo principal (Random Forest in-database) | AUC 0,949 · lift 3,75× no top 20% (teste temporal a partir de 01/06/2026) | `AVALIACAO_MODELOS` (Oracle) |
| Fila atual do MVP | 74 alunos (59 risco alto + 15 médio); 12 no grupo "Agir agora" | `VW_FILA_COORDENACAO` |
| Receita anual em risco na turma da IES parceira | R$ 247.800 (59 × R$ 350 × 12; ticket é estimativa) | `VW_DIRETORIA_RESUMO` |
| Preço | R$ 6 / 4 / 3 por aluno ativo/mês (Pro, por faixa) · Essencial R$ 2 · piloto 90 dias R$ 5 mil | seção 3.2 |
| Mercado | TAM R$ 249 mi/ano · SAM R$ 126 mi/ano · SOM R$ 2,5–4,3 mi de ARR em 3 anos | seção 3.4 |
| Projeção (cenário base) | ARR R$ 0,48 mi → R$ 1,44 mi → R$ 2,50 mi; necessidade de caixa de R$ 484 mil até o equilíbrio | `modelo_financeiro.xlsx` (estimativas) |

**O que ainda depende da equipe.** Os testes com **pelo menos 3 usuários reais** do público-alvo (Parte 2) estão com protocolo, formulário e planilha prontos, mas **ainda não foram realizados**; a seção 2.3 está marcada como pendente e não contém resultados inventados.

**Equipe.** Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198).

---

# Parte 1 — MVP funcional

## 1.1 Do que foi definido na Fase 6 ao que funciona agora

A Fase 6 definiu seis funcionalidades para o MVP (conceito final, seção 6). A tabela mostra o estado de cada uma nesta entrega.

| # | Funcionalidade (Fase 6) | Estado no MVP final | Onde roda |
|---|---|---|---|
| 1 | Ingestão e features semanais por aluno | **Funcionando**: 684.723 eventos carregados; features em SQL (SQL Macro + views) | Oracle: `EVENTOS_LMS`, `VW_FEATURES_ATUAIS`, `BASE_RISCO_SEMANAL` |
| 2 | Score de risco in-database com motivo explicável | **Funcionando**: 3 modelos OML; motivo em linguagem simples a partir de `PREDICTION_DETAILS`; predição ao vivo por aluno em ~15–100 ms | Oracle: `RETENA_INATIVO21_RF`, `PREDICTION_PROBABILITY/DETAILS` |
| 3 | Fila semanal "toda segunda" com registro de contato e resultado | **Funcionando, persistido no banco** (era só no navegador na fase anterior): fila priorizada, mensagem sugerida, registro gravado por procedure | Oracle: `VW_FILA_COORDENACAO`, `PRC_REGISTRAR_CONTATO`, `CONTATO_RESULTADO` |
| 4 | Detector de atrito de conteúdo | **Funcionando no painel offline** (mapa de atrito por fase/capítulo); consultas prontas no banco | `05_MVP/dashboard`, `06_Oracle/sql/07_apex_ready.sql` |
| 5 | Painel executivo de receita em risco em R$ | **Funcionando, recalculado no banco**: receita em risco, perda esperada, receita preservada, meta do piloto; ticket da IES gravado no banco | Oracle: `VW_DIRETORIA_RESUMO`, `PARAMETRO_IES` |
| 6 | Loop de aprendizado + perguntas em português | **Parcial**: o resultado de cada contato é gravado com o risco do momento (`PROB_NO_CONTATO`), base do retreino; job semanal de scoring ativo. Retreino com o rótulo de intervenção e Select AI ficam no roadmap (exigem volume de contatos e o Autonomous) | Oracle: `VW_RESULTADO_CONTATOS`, `JOB_RETENA_SCORING_SEMANAL` |

## 1.2 Fluxo principal executável

<div class="fluxo">
<div><b>1 · Carga</b><span>logs do LMS → <code>EVENTOS_LMS</code></span></div>
<div><b>2 · Features</b><span>SQL Macro por aluno e semana</span></div>
<div><b>3 · Scoring</b><span>Random Forest OML via job de segunda (<code>DBMS_SCHEDULER</code>)</span></div>
<div><b>4 · Fila</b><span>coordenação abre o aluno, vê motivo e mensagem</span></div>
<div><b>5 · Registro</b><span><code>PRC_REGISTRAR_CONTATO</code> grava e atualiza a fila</span></div>
<div><b>6 · Diretoria</b><span><code>VW_DIRETORIA_RESUMO</code> recalcula R$</span></div>
</div>

O roteiro de demonstração (o mesmo do vídeo) é:

1. **Coordenação → fila de segunda.** 74 alunos em três grupos: *Agir agora* (risco alto e último acesso há até 30 dias, 12 alunos), *Atenção* (risco médio, 15) e *Resgate* (risco alto e mais de 30 dias em silêncio). A ordenação por chance de recuperação foi uma correção desta fase: na primeira versão a fila começava por alunos sumidos há 198 dias, o que contrariava a proposta "quem está a duas semanas de sumir".
2. **Painel do aluno.** Risco pelo Random Forest, segunda opinião do GLM, risco de evasão na fase, os três motivos de maior peso, ações no LMS nas últimas 12 semanas, ação sugerida, janela de contato (19h–22h, pico real da turma) e mensagem pronta para copiar. O botão **"Recalcular no Oracle agora"** aplica o modelo no banco naquele instante; **"E se ele voltar esta semana?"** mostra como o risco cai se o aluno retomar (ex.: de 67,3% para 10,6% no Aluno 0068).
3. **Registro do resultado.** Reativado, plano combinado, sem resposta ou vai cancelar, com canal, responsável e observação. **"Gravar no Oracle"** devolve o número do contato e a consulta SQL para conferir.
4. **Time técnico → Prova em SQL.** Consultas fixas executadas ao vivo mostram o registro em `CONTATO_RESULTADO`, o status no snapshot, a visão da diretoria, o scoring OML e o documento JSON da Duality View. O botão **"Rodar o scoring agora"** dispara o job semanal e preserva os status de atendimento. Nas 8 execuções registradas até 17/11/2026 o job levou de 18 s a 4 min (mediana de cerca de 1 min), conforme a carga do notebook; no vídeo, esse trecho aparece acelerado e identificado.
5. **Diretoria.** Alunos para chamar, receita anual em risco, contatos registrados e receita preservada, recalculados a cada registro.

## 1.3 Persistência de dados

Todos os dados do MVP ficam no Oracle AI Database. Os objetos novos desta fase estão em `01_MVP_Oracle/sql/08_mvp_contato_resultado.sql` (idempotente; pode ser executado várias vezes sem perder contatos).

| Objeto | Tipo | Papel |
|---|---|---|
| `CONTATO_RESULTADO` | tabela (append-only) | Cada contato: aluno, resultado, canal, responsável, observação, **risco e faixa no momento do contato**, carimbo do scoring de referência. Sem chave estrangeira para o snapshot de propósito: o snapshot é recriado quando o pipeline roda de novo, e o histórico de contatos nunca pode se perder. |
| `PARAMETRO_IES` | tabela | Ticket mensal, horizonte em meses e meta do piloto; editáveis pelo painel da diretoria. |
| `PRC_REGISTRAR_CONTATO` | procedure PL/SQL | Valida o aluno, grava o contato e atualiza `RISCO_ALUNO_SNAPSHOT.STATUS_ATENDIMENTO` **na mesma transação**. A regra de negócio vive no banco, não no front-end. |
| `VW_FILA_COORDENACAO` | view | Snapshot OML + último contato + tentativas + grupo de prioridade. |
| `VW_DIRETORIA_RESUMO` | view | Números da diretoria calculados no banco a partir do snapshot, dos contatos e dos parâmetros. |
| `VW_RESULTADO_CONTATOS` | view | Taxa de reativação por faixa de risco: o insumo do retreino com o resultado real. |
| `RISCO_ALUNO_SNAPSHOT`, `RISCO_ALUNO_DV` | tabela e JSON Duality View (fases anteriores) | Snapshot semanal com MERGE que preserva o atendimento; documento JSON por aluno com leitura e escrita. |

## 1.4 Interface funcional

A interface é uma aplicação web sem dependências externas (funciona offline), servida pela própria API. A API REST (FastAPI + python-oracledb em modo thin) expõe 12 rotas documentadas em `/docs` (OpenAPI) e não executa SQL arbitrário: as consultas da "Prova em SQL" são fixas.

![Fila de segunda — visão da coordenação](img/mvp_1_fila.png)

![Painel do aluno com predição ao vivo e registro do contato](img/mvp_2_aluno.png)

![Registro gravado no Oracle](img/mvp_3_registro.png)

![Visão da diretoria recalculada no banco](img/mvp_4_diretoria.png)

![Time técnico: modelos, job semanal e prova em SQL](img/mvp_5_tecnico.png)

O **painel offline** da fase anterior (`05_MVP/dashboard/index.html`, publicado em lucashenklain.github.io/retena/dashboard) continua funcionando sem banco, como modo de demonstração e análise completa (mapa de atrito, modelo, funil). Ele usa o modelo Python de referência (corte 23/08/2026: 55 alunos de alto risco + 6 médio = 61 para chamar); o MVP online usa o Random Forest treinado no Oracle (corte 26/08/2026: 59 alto + 15 médio = 74). As duas contagens são de modelos diferentes e estão rotuladas assim; o número oficial do produto passa a ser o do Oracle.

## 1.5 Tecnologia Oracle como estratégia (e não só como requisito)

| Componente Oracle | Papel no MVP | Por que é estratégico | Estado |
|---|---|---|---|
| Oracle AI Database 26ai (Free em Docker; Autonomous AI Database em produção) | Guarda eventos, features, modelos, snapshot, contatos e parâmetros | **LGPD vira argumento de venda**: o dado do aluno não sai do banco da instituição; responde à objeção número 1 da diretora e do jurídico | Executado |
| Oracle Machine Learning (`DBMS_DATA_MINING`) | Treina Random Forest e GLM; `PREDICTION_PROBABILITY` e `PREDICTION_DETAILS` em SQL | **Sem servidor de ML nem cientista de dados dedicado**: custo de servir baixo (seção 3.3) e implantação em semanas | Executado |
| `DBMS_SCHEDULER` | Job semanal de scoring (segunda 06:00) | O ritual "toda segunda" é garantido pelo banco, não por um cron externo | Executado |
| PL/SQL + views | Regra do registro de contato e cálculo da diretoria | Uma única fonte de verdade; qualquer front-end (o nosso, APEX ou o do LMS) vê o mesmo número | Executado |
| JSON Relational Duality View | Documento JSON por aluno, leitura e escrita | Integração com LMS e apps sem duplicar dados | Executado |
| Autonomous AI Database Serverless + Object Storage (`DBMS_CLOUD`) | Produção multi-IES (um schema por instituição), ingestão de CSV do LMS | **Canal**: ERPs acadêmicos e megagrupos já rodam Oracle; a Retena entra como extensão do que a IES tem | Runbook pronto (`06_Oracle/oci`), não provisionado |
| APEX / ORDS | Painel low-code e REST nativo no Autonomous | Substitui a API Python quando o produto rodar no Autonomous | Roadmap (seção 3.6) |
| Select AI | Perguntas em português sobre as views | Diferencial de demonstração para o ecossistema Oracle | Roadmap |

**Decisão desta fase sobre APEX/ORDS.** O roadmap da prototipação previa o painel em APEX. Subir ORDS/APEX localmente sobre a imagem Free exige instalar e configurar o ORDS e o APEX no container, o que não é reproduzível com segurança para quem abrir o ZIP. Optamos por uma API Python fina (as regras ficam em PL/SQL e views) que roda em qualquer máquina com Docker; a migração para APEX/ORDS no Autonomous é direta porque as consultas já estão no banco.

## 1.6 Como executar e verificar

```
entrega\11_Entrega_Final\01_MVP_Oracle\INICIAR_MVP.cmd
```

O script confere Docker e Python, reaproveita ou cria o container `oracle-free`, executa o pipeline completo se o banco estiver vazio (carga, features, treino OML, scoring e avaliação: 10 a 15 minutos na primeira vez (12 min medidos num banco novo a partir do ZIP), mais o download da imagem), cria os objetos do MVP, sobe a API e abre `http://127.0.0.1:8080`. Em Linux/macOS: `docker compose --profile completo up -d --build`. Detalhes em `01_MVP_Oracle/README.md`.

O teste ponta a ponta `python verificar_mvp.py` executa o fluxo como a coordenadora e confere cada passo **direto no banco**, sem confiar na API: saúde, fila, painel do aluno, predição ao vivo e "e se", registro (linha em `CONTATO_RESULTADO` e status no snapshot), saída da fila, receita preservada (+ticket × 12) e limpeza. Resultado em 16/11/2026: **todos os 15 passos passaram** (`01_MVP_Oracle/logs/verificacao_mvp.txt`).

## 1.7 Limitações conhecidas (ditas com clareza)

- **Dados congelados.** O export do LMS termina em 26/08/2026. Rodar o scoring de novo carimba a data, mas não muda os riscos; em produção a carga é semanal.
- **Reativação estimada.** "Receita preservada" conta o último contato marcado como reativado × ticket × 12. Em produção, a reativação será confirmada quando o LMS registrar novo acesso em até 7 dias.
- **Contatos de demonstração.** Os contatos que aparecem no vídeo e nas imagens foram registrados pela equipe para demonstrar o fluxo; **nenhum aluno real foi contatado**.
- **Sem login.** O MVP ainda não tem perfis de acesso (coordenação, tutor, gestão); está no roadmap como "Deveria".
- **Autonomous, APEX e Select AI não provisionados.** O runbook OCI está pronto e testado na parte de exportação/MERGE; a conta OCI depende da equipe.
- **Amostra pequena.** 203 alunos de um curso. Por isso validação temporal, portabilidade testada no OULAD (AUC 0,922, fase anterior) e retreino por instituição.

---

# Parte 2 — Teste e validação

## 2.1 O que já foi validado (e como)

| Frente | O que foi feito | Natureza | Resultado |
|---|---|---|---|
| Técnica — modelo | Validação temporal (treino até maio, teste a partir de 01/06/2026) no Oracle | **Real** | RF AUC 0,949; GLM 0,945; transição de fase 0,972; lift 3,75× no top 20% |
| Técnica — portabilidade | Mesmo método no dataset público OULAD | **Real** | AUC 0,922; lift 3,51× (fase anterior) |
| Técnica — MVP | Teste automatizado ponta a ponta contra o banco | **Real** | 15/15 passos (16/11/2026) |
| Mercado — fontes secundárias | INEP (Censo 2024) e Semesp (16º Mapa) | **Real** | 41,6% de desistência EAD; 5,19 mi de matrículas EAD |
| Mercado — entrevistas da Fase 6 | 8 entrevistas com personas sintéticas para calibrar o roteiro | **Simuladas, rotuladas assim** | Usadas só para preparar perguntas e objeções; não contam como validação com usuários |
| Usuários — teste do MVP final | Protocolo com 6 tarefas, SUS e perguntas de valor | **Pendente** | Seção 2.3 |

## 2.2 Protocolo do teste com usuários do MVP final

O kit completo está em `02_Testes_Usuarios/`: protocolo (`protocolo_teste_mvp.md`), ficha por participante, planilha de consolidação com fórmulas (`consolidacao_testes.xlsx`: tarefas, SUS, problemas por severidade, resumo) e o modelo desta seção. Resumo:

- **Quem:** pelo menos 3 pessoas do público-alvo, com prioridade para coordenação de permanência ou tutoria EAD (persona usuária) e pelo menos uma de gestão acadêmica (persona compradora).
- **Como:** sessão de 30–40 minutos, presencial ou remota, com o MVP rodando na máquina do facilitador; termo de consentimento; dados pseudonimizados.
- **Tarefas:** encontrar quem chamar primeiro; entender por que o aluno está na fila; registrar o resultado do contato; conferir o impacto na visão da diretoria; ajustar o ticket; (opcional, perfil técnico) conferir o registro em SQL.
- **Medidas:** sucesso por tarefa, tempo, erros, SUS (10 itens) e três perguntas de valor ("isso resolveria seu problema?", "pagaria?", "o que falta?").
- **Critério de decisão (proposto):** o MVP resolve o problema para o público-alvo se as tarefas centrais (encontrar quem chamar e registrar o resultado) tiverem sucesso de pelo menos 80%, o SUS médio for de pelo menos 68 e a maioria dos participantes disser que usaria a fila na rotina semanal.

<!-- TESTES:INICIO (seções 2.3 e 2.4 são regeradas por 02_Testes_Usuarios/consolidar_testes.py --aplicar) -->
## 2.3 Resultados dos testes com usuários — PENDENTE

<div class="pendente"><b>Seção pendente.</b> Os testes com pelo menos 3 usuários reais do público-alvo ainda não foram realizados. Nada abaixo foi inventado: quando a equipe trouxer as fichas preenchidas, a planilha `consolidacao_testes.xlsx` calcula os indicadores e esta seção é preenchida (participantes anonimizados P1–P3, dificuldades, feedback, ajustes feitos e análise).</div>

| Participante | Perfil | Sucesso nas tarefas | Tempo médio | SUS | Principal dificuldade |
|---|---|---|---|---|---|
| P1 | [A PREENCHER PELA EQUIPE] | — | — | — | — |
| P2 | [A PREENCHER PELA EQUIPE] | — | — | — | — |
| P3 | [A PREENCHER PELA EQUIPE] | — | — | — | — |

| Problema encontrado | Severidade | Ajuste feito | Status |
|---|---|---|---|
| [A PREENCHER PELA EQUIPE] | — | — | — |

## 2.4 O MVP resolve o problema?

**O que já dá para afirmar com evidência real:** o sinal existe e é forte (AUC 0,95 em teste temporal; 85% dos casos da faixa alta ficaram de fato 21 dias inativos no teste, contra 5% na faixa baixa); o ciclo fila → contato → resultado → receita funciona de ponta a ponta no banco; e a fila coloca primeiro quem ainda dá para segurar.

**O que ainda precisa ser provado com usuários reais:** se a coordenação entende os motivos sem ajuda, se o registro cabe na rotina (meta: menos de 30 segundos por contato) e se a diretoria confia no número de receita preservada. Esta resposta será fechada com os testes da seção 2.3; não a antecipamos.

**Ajustes já feitos nesta fase a partir da revisão interna (não de usuários):** fila priorizada por recuperabilidade; botão "e se ele voltar"; mensagem sugerida que usa o nome do responsável; ticket da IES persistido no banco; separação entre "reativado" e "plano combinado" para não inflar a receita preservada.
<!-- TESTES:FIM -->

---

# Parte 3 — Modelo de negócio consolidado

## 3.1 Business Model Canvas atualizado

<div class="bmc">
<div class="bmc-pk"><h4>Parceiros-chave</h4><ul><li>Oracle (Autonomous AI Database, OML, APEX; programa Oracle for Startups)</li><li>IES parceira do piloto (dados anonimizados)</li><li>Integradores de LMS (Moodle) e ERPs acadêmicos</li><li>Associações do setor (Semesp, ABED) para eventos e conteúdo</li></ul></div>
<div class="bmc-ka"><h4>Atividades-chave</h4><ul><li>Implantação: conectar o export do LMS em até 30 dias</li><li>Treino e retreino dos modelos por instituição, no banco</li><li>Customer success: ritual "toda segunda" e relatório de R$</li><li>Venda consultiva via diagnóstico gratuito</li></ul></div>
<div class="bmc-kr"><h4>Recursos-chave</h4><ul><li>Pipeline Oracle executado (SQL, OML, job, views, procedure)</li><li>Base de contatos e resultados por cliente (dado proprietário do loop)</li><li>Marca, landing com calculadora de ROI, kit comercial</li><li>Equipe de 5 sócios (dados, engenharia, produto, negócio)</li></ul></div>
<div class="bmc-vp"><h4>Proposta de valor</h4><ul><li><b>Diretora:</b> proteção de receita recorrente, medida em R$ toda semana</li><li><b>Coordenadora:</b> toda segunda, quem chamar, por quê, quando e o que dizer — sem planilha</li><li><b>IES:</b> o dado do aluno não sai do banco (LGPD), sem servidor de ML</li><li><b>Aluno:</b> ser chamado antes de desistir, no horário em que estuda</li></ul></div>
<div class="bmc-cr"><h4>Relacionamento</h4><ul><li>Diagnóstico gratuito em 7 dias → piloto de 90 dias com meta acordada → contrato anual</li><li>CS dedicado na implantação; relatório mensal de receita preservada</li><li>Comunidade de coordenadoras (boas práticas de contato)</li></ul></div>
<div class="bmc-ch"><h4>Canais</h4><ul><li>LinkedIn/ABM para diretores de operações acadêmicas</li><li>Landing com calculadora de ROI e agendamento</li><li>Eventos Semesp/ABED; conteúdo com dados INEP/Semesp</li><li>Ecossistema Oracle (fase 2: megagrupos)</li></ul></div>
<div class="bmc-cs"><h4>Segmentos</h4><ul><li><b>ICP:</b> IES privadas com EAD, de 3 a 15 mil alunos ativos, fora dos megagrupos</li><li>Secundário: IES pequenas (plano Essencial)</li><li>Fase 2: megagrupos (50 mil+ alunos)</li></ul></div>
<div class="bmc-co"><h4>Estrutura de custos</h4><ul><li>Equipe (maior custo): sócios, CS/implantação, vendas, engenharia</li><li>Oracle Autonomous AI Database: R$ 0 no piloto (Always Free); ~R$ 2,8 mil/mês por banco de produção de 2 ECPU (estimativa)</li><li>Marketing digital, comercial, G&A</li></ul></div>
<div class="bmc-rs"><h4>Fontes de receita</h4><ul><li>Assinatura por aluno ativo/mês (Essencial, Pro, Enterprise)</li><li>Setup/implantação (R$ 10–25 mil)</li><li>Piloto de 90 dias (R$ 5 mil)</li><li>Upsell: conteúdo adaptativo, multi-campus, API</li></ul></div>
</div>

**O que mudou em relação à Fase 6:** o canal passou a ser liderado pelo diagnóstico gratuito (isca de baixo custo, já que a carga de um export leva minutos no banco); o relacionamento ganhou a meta do piloto medida no próprio painel; e os custos agora incluem o Oracle de forma explícita.

## 3.2 Monetização (tabela de preços consolidada)

| Plano | Preço por aluno ativo/mês | Mínimo mensal | Para quem | Inclui |
|---|---|---|---|---|
| **Essencial** | R$ 2,00 (até 5 mil alunos) | R$ 2,5 mil | IES pequenas | Score com motivo, fila semanal, registro de contato |
| **Pro** (principal) | R$ 6,00 até 10 mil · R$ 4,00 de 10 a 50 mil · R$ 3,00 acima de 50 mil | R$ 5 mil | IES médias (ICP) | Essencial + painel da diretoria em R$, mapa de atrito, relatório mensal |
| **Enterprise** | Pro + 30% (negociado) | sob proposta | Grupos multi-campus | Pro + multi-campus, API, SLA, retreino dedicado |

- **Setup/implantação:** R$ 10–25 mil por instituição, conforme LMS e número de cursos.
- **Piloto de 90 dias:** R$ 5 mil por todo o piloto, em uma fase de um curso, com meta de reativação acordada (o painel mede: 30% dos alunos de alto risco reengajados em 30 dias); ao bater a meta, converte em contrato anual.
- **Regra de faixa (correção desta fase):** a faixa vale para o volume total de alunos, e a fatura mensal é o **menor valor** entre "alunos × preço da faixa" e "piso da próxima faixa × preço da próxima faixa". Sem essa regra, uma IES com 10.000 alunos pagaria R$ 60 mil/mês e uma com 10.500 pagaria R$ 42 mil; com a regra, quem tem entre 6.667 e 10.000 alunos paga no máximo R$ 40 mil/mês.
- **Cliente-referência (inalterado):** 12 mil alunos × R$ 4 × 12 = **R$ 576 mil/ano**; com ticket de R$ 350/mês (estimativa), cada aluno retido preserva R$ 4.200/ano e o contrato se paga com **137 alunos retidos por ano (1,1% da base)**.

## 3.3 Estrutura de custos

**Custos de servir (variam com a base de clientes).**

| Item | Ano 1 | Ano 2 | Ano 3 | Base do cálculo |
|---|---|---|---|---|
| Oracle Autonomous AI Database | R$ 16,6 mil | R$ 67,0 mil | R$ 135,6 mil | Pilotos no **Always Free** (custo zero; até 2 bancos de 20 GB por tenancy); produção paga a partir do 2º semestre do ano 1: 2 ECPU (ano 1), 4 ECPU (ano 2), 8 ECPU em 2 bancos (ano 3) × US$ 0,336/ECPU-hora + armazenamento US$ 0,1156/GB-mês, câmbio R$ 5,50 |
| Outros custos de servir | R$ 9,6 mil | R$ 24,0 mil | R$ 48,0 mil | Monitoramento, backup externo, e-mail, suporte (estimativa) |
| Customer success / implantação | — | R$ 163 mil | R$ 326 mil | Sócios fazem a implantação no ano 1; 1 e depois 2 pessoas (custo com encargos, estimativa) |

O Oracle custa entre **R$ 0,19 e R$ 0,28 por aluno ativo por mês** (estimativa), contra um preço efetivo de R$ 4,00: a infraestrutura de ML in-database pesa menos de 7% da receita de assinatura. O custo que realmente importa é o de pessoas na implantação, coberto pelo setup.

**Custos fixos e de crescimento.**

| Item | Ano 1 | Ano 2 | Ano 3 |
|---|---|---|---|
| Sócios (5), pró-labore | R$ 180 mil | R$ 480 mil | R$ 660 mil |
| Vendas (SDR/executivo) | — | R$ 122 mil | R$ 245 mil |
| Engenharia (dev pleno) | — | — | R$ 204 mil |
| Marketing digital | R$ 36 mil | R$ 120 mil | R$ 200 mil |
| Comercial e viagens | R$ 24 mil | R$ 60 mil | R$ 90 mil |
| G&A (contabilidade, jurídico/LGPD, ferramentas) | R$ 36 mil | R$ 60 mil | R$ 84 mil |
| Comissões (8% do ARR novo) | R$ 38 mil | R$ 77 mil | R$ 84 mil |

Todos os valores de custo são **estimativas da equipe**. O preço do Oracle é o de lista publicado pela Oracle no lançamento do modelo ECPU e deve ser confirmado no price list vigente; o programa Oracle for Startups pode oferecer créditos que reduzem esse custo, não considerados na projeção.

## 3.4 Mercado e projeção financeira simplificada (3 anos)

**Mercado (contas mantidas e conferidas).**

- **TAM:** 5.189.391 matrículas EAD (INEP, Censo 2024) × R$ 4 × 12 = **R$ 249 mi/ano**.
- **SAM:** 95,9% na rede privada (Semesp) × 52,9% fora dos megagrupos = 2,63 mi alunos × R$ 48/ano = **R$ 126 mi/ano**.
- **SOM (3 anos):** 52 mil alunos em 10–11 IES médias × R$ 48/ano = **R$ 2,5 mi de ARR**; com 1 megagrupo na fase 2 (50 mil alunos × R$ 36/ano), **R$ 4,3 mi**.

**Projeção (cenário base; ano 1 = 2027).**

| | Ano 1 | Ano 2 | Ano 3 |
|---|---|---|---|
| IES clientes (fim do ano) | 2 | 6 | 11 |
| Alunos ativos sob contrato | 10 mil | 30 mil | 52 mil |
| **ARR no fim do ano** | **R$ 480 mil** | **R$ 1,44 mi** | **R$ 2,50 mi** |
| Receita bruta do ano (assinatura + setup + pilotos) | R$ 300 mil | R$ 1,06 mi | R$ 2,09 mi |
| Receita líquida (−10% de impostos, estimativa) | R$ 270 mil | R$ 954 mil | R$ 1,88 mi |
| Lucro bruto (margem bruta) | R$ 244 mil (90%) | R$ 700 mil (73%) | R$ 1,37 mi (73%) |
| Despesas operacionais | R$ 314 mil | R$ 919 mil | R$ 1,57 mi |
| **EBITDA** | **−R$ 71 mil** | **−R$ 219 mil** | **−R$ 194 mil** |
| Caixa acumulado sem captação | −R$ 71 mil | −R$ 290 mil | −R$ 484 mil |

![ARR e EBITDA projetados (cenário base e otimista)](img/projecao.png)

**Leitura.** No cenário base a Retena chega ao fim do ano 3 com receita recorrente mensal de cerca de R$ 208 mil, acima do custo mensal projetado; o equilíbrio operacional acontece na virada do ano 3 para o 4, e a **necessidade de caixa até lá é de R$ 484 mil**. Por isso a estratégia prevê uma rodada pré-seed de **R$ 600 mil** (necessidade + 25% de margem), buscada em fomento não diluidor (Centelha, PIPE/FAPESP) e investidores-anjo, mais créditos do Oracle for Startups. No **cenário otimista** (um megagrupo no 2º semestre do ano 3, via ecossistema Oracle), o ARR do ano 3 chega a **R$ 4,3 mi** e o EBITDA do ano 3 fica positivo em cerca de **R$ 440 mil**.

**Premissas principais (todas estimativas, detalhadas na aba "Premissas" de `modelo_financeiro.xlsx`):** preço efetivo médio de R$ 4,00 por aluno/mês (mix de Pro com desconto de conversão do piloto e Essencial; é o mesmo R$ 48/ano do SAM/SOM); IES média de cerca de 5 mil alunos; contratos do ano 1 começam no 2º semestre; setup médio de R$ 15 mil; 6, 8 e 10 pilotos por ano.

## 3.5 Unit economics e KPIs

| Métrica | Valor (estimativa) | Como se calcula |
|---|---|---|
| ARR por IES média | R$ 240 mil | 5 mil alunos × R$ 4 × 12 |
| CAC por IES (ano 2) | R$ 95 mil | (marketing + comercial + vendas + comissões) ÷ novas IES |
| Payback do CAC | ~6 meses | CAC ÷ lucro bruto mensal por IES (margem 80% em regime) |
| LTV por IES | R$ 960 mil | ARR × 80% × 5 anos de vida média (churn de 20%/ano, conservador) |
| LTV/CAC | ~10× | — |
| Custo Oracle por aluno ativo | R$ 0,19–0,28/mês | seção 3.3 |

O kit da banca citava "CAC pago em menos de um trimestre"; com custos de equipe de vendas explícitos, o payback estimado é de cerca de 6 meses. Corrigimos o número para o mais conservador.

**KPIs que a Retena acompanha (e onde cada um é medido).**

| Camada | KPI | Meta | Onde mede |
|---|---|---|---|
| Resultado do cliente | % de alunos de alto risco reengajados em 30 dias | ≥ 30% (meta do piloto) | `VW_DIRETORIA_RESUMO` |
| Resultado do cliente | Receita preservada (R$/mês) vs. custo da assinatura | ≥ 1× no piloto, ≥ 3× no ano | painel da diretoria |
| Uso | % da fila contatada até quarta-feira; tempo sinal → contato | ≥ 70%; ≤ 3 dias | `CONTATO_RESULTADO` |
| Modelo | AUC e lift no top 20% em teste temporal, por IES | AUC ≥ 0,80; lift ≥ 2,5× | `AVALIACAO_MODELOS` |
| Negócio | ARR, nº de IES, conversão piloto → contrato | metas da seção 3.4; ≥ 50% | CRM |
| Negócio | Margem bruta, payback do CAC, churn de logos | ≥ 75%; ≤ 9 meses; ≤ 20%/ano | financeiro |
| Marketing | Diagnósticos gratuitos/mês, custo por diagnóstico | 30 no ano 1 | landing + CRM |

## 3.6 Do MVP ao produto escalável

| Etapa | O que muda | Oracle | Quando |
|---|---|---|---|
| MVP (agora) | 1 IES, Docker local, API Python fina, regras em PL/SQL | AI Database 26ai Free, OML, Scheduler | Nov/2026 |
| Piloto | Banco na nuvem, carga do export do LMS, login por papel | **Autonomous AI Database Always Free**, Object Storage + `DBMS_CLOUD` (runbook pronto) | 1º semestre de 2027 |
| Produto | Um schema por IES; painel em APEX e REST pelo ORDS; relatório semanal em PDF; link de WhatsApp com mensagem pronta | Autonomous pago com auto-scaling, APEX, ORDS | 2º semestre de 2027 |
| Escala | Features incrementais (janela móvel) e partição por semana; retreino com o resultado dos contatos; Select AI | Particionamento, `DBMS_SCHEDULER`, Select AI | 2028 |
| Fase 2 | Megagrupos, multi-campus, conteúdo adaptativo por capítulo | Banco dedicado por grupo, AI Vector Search | 2029 |

**Gargalo conhecido e plano:** o recálculo completo das features leva cerca de 89 s para 203 alunos; projetado linearmente, passaria de 1 hora com 12 mil alunos. A correção (features incrementais e partição) está priorizada como "Deveria" no roadmap e é condição para o primeiro cliente de porte médio.

## 3.7 Correções de consistência feitas nesta entrega

A auditoria dos números publicados encontrou divergências entre materiais. Esta é a versão oficial:

| Tema | Antes | Onde | Agora |
|---|---|---|---|
| Plano Essencial | "−25% do Pro" (conceito e landing) vs. "R$ 2,00, mínimo R$ 2,5 mil" (kit, one-pager, documento v2) | `conceito_final.md` §9; `04_Landing_Page`; documento v2 | **R$ 2,00 até 5 mil alunos, mínimo R$ 2,5 mil** (versão comercial mais recente) |
| Mapa de atrito no Essencial | Incluído no Essencial (documento v2) vs. só no Pro (conceito, landing) | documento v2 | **Só no Pro** |
| Enterprise | "R$ 3,00" (kit) vs. "Pro + 30%" (conceito) | `gerar_kit_banca.py` | **Pro + 30%**; R$ 3,00 é a faixa de volume 50 mil+ do Pro |
| Salto entre faixas | 10.000 alunos pagavam mais que 10.500 | calculadora da landing | Regra do menor valor (seção 3.2) |
| Preço usado no SOM | R$ 48/ano sem explicação, embora IES médias estejam na faixa de R$ 6 | conceito §10 | Definido como **preço efetivo médio** (desconto de conversão + mix Essencial) |
| Metas do ano 1 | "3 pilotos + 2 contratos" vs. "30 diagnósticos, 6 pilotos, 2–3 contratos" | conceito, kit, one-pager | **30 diagnósticos → 6 pilotos → 2 contratos** |
| Nº de IES no ano 3 | 8–12 vs. 10–12 | conceito | **10–11 IES (52 mil alunos)** |
| Payback do CAC | "< 1 trimestre" | kit, guia, resumo | **~6 meses** (estimativa com custos de vendas explícitos) |
| Alunos para chamar | 61 (painel offline, modelo Python) vs. 74 (MVP, modelo Oracle) | painel offline vs. MVP | Ambos corretos para seus modelos; **o número oficial passa a ser o do Oracle** |
| Always Free | "1 OCPU" vs. "2 ECPU" | documentos da prototipação e do 06_Oracle | **Até 2 bancos por tenancy, 20 GB cada, até 30 sessões, CPU fixa** (documentação Oracle) |

Os materiais das fases anteriores ficam como registro histórico; a landing page publicada ainda mostra a calculadora antiga e será atualizada no próximo push autorizado.

---

# Parte 4 — Estratégia de lançamento

## 4.1 Público-alvo prioritário

**Perfil de cliente ideal (ICP):** IES privada com EAD, **3 a 15 mil alunos ativos**, fora dos megagrupos, com Moodle (ou LMS que exporte logs em CSV), uma diretoria de operações acadêmicas com meta de permanência e, de preferência, ERP ou banco Oracle. É o miolo do SAM (2,63 mi de alunos) e o perfil do cliente-referência.

**Quem decide e quem usa:** Renata, diretora de operações acadêmicas, compra proteção de receita; Mariana, coordenadora de permanência, usa a fila toda segunda. A mensagem é diferente para cada uma (receita em R$ para Renata; "zero planilha, quem chamar e o que dizer" para Mariana).

**Por que começar aqui:** o ciclo de venda de uma IES média é de semanas, não de anos; o contrato mínimo (R$ 5 mil/mês) é aprovado na alçada da diretoria; e os megagrupos exigem referência e SLA que só teremos depois de 5–6 clientes.

## 4.2 Aquisição dos primeiros clientes

**Playbook dos primeiros 90 dias após a banca:**

1. **IES parceira → piloto-referência.** Converter a instituição que cedeu os dados no primeiro piloto de 90 dias, com a meta já calculada no painel (18 reativações = 30% de 59 alunos de alto risco).
2. **Lista de 60 IES do ICP** (Censo INEP + LinkedIn), priorizando quem usa Moodle e Oracle.
3. **Diagnóstico gratuito em 7 dias** como isca: a IES envia o export do LMS; devolvemos a fila e a receita em risco em R$. Custo marginal quase zero (a carga da base real levou cerca de 1 minuto no banco).
4. **Prospecção direta (ABM) no LinkedIn** para diretores de operações, com o número da própria IES estimado pela calculadora de ROI.
5. **Conteúdo com dados públicos** (INEP, Semesp) e presença em eventos Semesp/ABED.
6. **Canal Oracle:** Oracle for Startups e parceiros que atendem educação, para chegar a quem já roda Oracle.

**Funil do ano 1 (metas, não promessas):** 30 diagnósticos → 6 pilotos pagos → 2 contratos anuais (R$ 480 mil de ARR). Conversões-alvo: 20% de diagnóstico para piloto, 33–50% de piloto para contrato.

## 4.3 Posicionamento competitivo

| Alternativa | O que faz bem | Onde falha para este problema | Como a Retena se diferencia |
|---|---|---|---|
| BI embarcado no LMS (relatórios do Moodle, Canvas) | Mostra o passado, já está instalado | Descritivo, sem priorização nem ação | Prediz risco por aluno e diz quem chamar, por quê e o que dizer |
| CRM educacional / régua de cobrança | Opera contato em escala | Age quando a mensalidade já parou | Age semanas antes, no sinal de engajamento |
| Consultorias de retenção | Diagnóstico profundo | Projeto pontual, caro, sem rotina semanal | Ritual semanal automatizado com R$ medido |
| Planilha da coordenação | Barata e flexível | Manual, sem critério, sem histórico | Fila priorizada e histórico de contatos no banco |
| Plataformas de analytics com ML externo | Modelos sofisticados | Dado sai da instituição; exige time de dados | ML **dentro do banco da IES**; sem cientista de dados |

**Frase de posicionamento:** para diretoras de operações e coordenadoras de permanência de IES privadas com EAD, a Retena é o radar de permanência que diz toda segunda quem chamar e mede em R$ o que voltou, rodando dentro do Oracle da própria instituição. Diferente de BI (passado) e de CRM de cobrança (tarde demais), fecha o ciclo aluno → contato → resultado → receita.

**Risco competitivo honesto:** um LMS grande pode embutir algo parecido. Nossas defesas são o ciclo fechado com ROI medido, o dado proprietário de resultados de contato por cliente (que melhora o modelo de cada IES) e o canal Oracle.

## 4.4 Crescimento sustentável

- **Expansão dentro da conta:** começar por uma fase de um curso (piloto) e expandir para todos os cursos EAD; a receita cresce com o número de alunos sem novo custo de aquisição (meta de NRR acima de 110%).
- **Margem que melhora com escala:** o custo Oracle por aluno cai com a densidade de clientes por banco; a implantação é padronizada (contrato de entrada do LMS + validação de carga).
- **Crescer no ritmo do caixa:** contratar CS e vendas só quando o ARR justificar (ano 2); rodada pré-seed de R$ 600 mil cobre a necessidade de caixa do cenário base.
- **Fase 2 via ecossistema:** megagrupos e ensino técnico/corporativo com o mesmo método; módulo de conteúdo adaptativo como upsell.
- **Impacto mensurável:** cada aluno que volta é receita preservada e um diploma a mais; o relatório mensal mostra os dois.

---

# Parte 5 — Pitch

O pitch final está em `04_Pitch/Retena_Pitch_Final.pdf` e o vídeo com demonstração real em `05_Video/`. O roteiro cobre os dez pontos pedidos:

| Ponto do enunciado | Onde no pitch | Onde no vídeo |
|---|---|---|
| Problema | Slide 2 | ~0:11 |
| Solução | Slide 3 | ~0:34 |
| Demonstração do MVP | Slides 4–5 (prints) | ~0:50–3:03 (gravação real da tela) |
| Tecnologia e integração Oracle | Slides 6–7 | durante a demonstração e ~3:03 |
| Mercado | Slide 8 | ~3:31 |
| Modelo de negócio | Slide 9 | ~3:46 |
| Diferencial | Slide 10 | ~4:09 |
| Crescimento (lançamento) e projeções | Slides 11–12 | ~4:22 e ~4:40 |
| Validação | Slide 13 | ~4:57 |
| Time | Slide 14 | ~5:11 (fechamento) |

---

# Time

Engenharia de Software, FIAP, turma 4ESOA.

| Integrante | RM | Papel |
|---|---|---|
| Lucas Dalmas | RM551178 | Líder da equipe |
| Lucas Emanuel | RM97881 | [papel a confirmar pela equipe] |
| Kayque Moraes | RM97592 | [papel a confirmar pela equipe] |
| Lucas Henklain | RM99350 | [papel a confirmar pela equipe] |
| Vinicius Pinheiro | RM99198 | [papel a confirmar pela equipe] |

O time combina engenharia de software, dados e negócio; os cinco sócios fazem a implantação no ano 1 (seção 3.3) antes da primeira contratação de customer success.

---

# Anexo A — Fontes

- INEP. Censo da Educação Superior 2024 (divulgado em 22/09/2025): 5.189.391 matrículas EAD, 50,7% do total.
- Semesp. 16º Mapa do Ensino Superior no Brasil (2026): desistência anual EAD de 41,6% (2024); 95,9% das matrículas EAD na rede privada; megagrupos (1,4% das mantenedoras) com 47,1% dos estudantes.
- Oracle. Autonomous Database ECPU FAQ e página de preços do Autonomous AI Database (ECPU US$ 0,336/hora; armazenamento ATP US$ 0,1156/GB-mês) — oracle.com/autonomous-database/pricing.
- Oracle. Always Free Autonomous AI Database (até 2 bancos por tenancy, 20 GB, até 30 sessões) — docs.oracle.com/en-us/iaas/Content/GSG/Concepts/alwaysfree.htm.
- Base real anonimizada da IES parceira (684.723 eventos de LMS, 15/01–26/08/2026); métricas dos modelos em `AVALIACAO_MODELOS` (Oracle) e `05_MVP/outputs/RESULTADOS.md`.
- Estimativas da equipe: ticket de R$ 350/mês (faixa R$ 250–450 do brief), custos de equipe, câmbio, impostos, taxas de conversão.

# Anexo B — Estrutura do pacote entregue

| Pasta | Conteúdo |
|---|---|
| `11_Entrega_Final/01_MVP_Oracle` | MVP: API, front-end, SQL do MVP, `INICIAR_MVP.cmd`, `docker-compose.yml`, teste `verificar_mvp.py`, README |
| `11_Entrega_Final/02_Testes_Usuarios` | Protocolo, ficha, planilha e modelo da seção de resultados (pendente) |
| `11_Entrega_Final/03_Documento` | Este documento (PDF, DOCX e Markdown) e o modelo financeiro (`.xlsx` e `.py`) |
| `11_Entrega_Final/04_Pitch` | Pitch em PDF (e PPTX editável) |
| `11_Entrega_Final/05_Video` | Vídeo com demonstração real, roteiro e scripts de produção |
| `06_Oracle` | Pipeline Oracle completo (SQL 01–07, scripts, evidências, runbook OCI) |
| `05_MVP`, `08_Dados` | Painel offline, pipeline Python de referência e base anonimizada usada pela carga |
| `01`–`04`, `09`, `10` | Materiais das fases anteriores (documento da Fase 6, diagramas, marca, landing, kit da banca, prototipação) |
