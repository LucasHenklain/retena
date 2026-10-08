# Protótipo da solução — fluxo principal e telas (Parte 1)

**Tipo:** protótipo parcial funcional (front-end), não navegável em Figma: é o dashboard real, com dados reais anonimizados, publicado em https://lucashenklain.github.io/retena/dashboard/ (cópia offline em `../../05_MVP/dashboard/index.html`). A landing page comercial está em https://lucashenklain.github.io/retena/ (cópia em `../../04_Landing_Page/index.html`).

As capturas desta pasta (`prints/`) foram geradas automaticamente a partir do protótipo em 07/10/2026.

## 1. Fluxo principal do usuário

Duas pessoas, dois momentos:

**A. Renata, diretora de operações (compra)** — landing page → calculadora de ROI com os números da própria instituição → agendar piloto de 90 dias.

**B. Mariana, coordenadora de permanência (usa toda semana)** — a "segunda-feira com critério":

| Passo | Quando | Tela | O que faz | Resultado |
|---|---|---|---|---|
| 1 | Domingo 23h (automático) | — | o job no Oracle recalcula o risco de cada aluno (`JOB_RETENA_SCORING_SEMANAL`) | snapshot da semana |
| 2 | Segunda 8h | **Visão Diretoria** | vê quantos alunos chamar, a receita em risco e o que dá para recuperar; ajusta o ticket | prioridade da semana em R$ |
| 3 | Segunda 8h | **Fila de segunda** (visão Coordenação) | preset "Quem chamar hoje" (alto risco e ainda ativos), busca, ordenação | lista de quem contatar primeiro |
| 4 | Segunda a quinta, 19h–22h | **Painel do aluno** | lê o motivo em linguagem simples e a ação sugerida; contata o aluno | conversa com contexto |
| 5 | Logo após o contato | **Registrar resultado** (no painel do aluno) | marca Reativado / Plano combinado / Sem resposta / Vai cancelar, com observação | status na fila e contagem na visão da diretoria |
| 6 | Quando sobra tempo | **Mapa de atrito** | vê em que capítulo os alunos travam e as recomendações | pauta para a coordenação pedagógica |
| 7 | Sexta | **Visão Diretoria** | resultados registrados na semana e receita preservada estimada | prestação de contas |
| 8 | Sob demanda | **Visão Time técnico** | métricas, calibração, estabilidade do modelo | confiança no modelo |

## 2. Principais telas

| # | Tela | Captura | Interações |
|---|---|---|---|
| 1 | Visão Diretoria (resumo executivo) | `prints/01_visao_diretoria.png` | seletor de visão; campo de ticket recalcula receita em risco e preservada; chips "Como agir" |
| 2 | Visão Coordenação: fila de segunda-feira | `prints/02_fila_segunda.png` | busca, filtros por faixa e situação, ordenação por coluna, preset "Quem chamar hoje"; clique abre o aluno |
| 3 | Painel do aluno com registro do resultado | `prints/03_painel_aluno.png` | fatores, ação sugerida, atividade recente, progresso; botões de resultado e observação (persistem no navegador) |
| 4 | Mapa de atrito de conteúdo | `prints/04_mapa_atrito.png` | heatmap fase × capítulo com tooltip; 8 maiores fricções; 20 recomendações |
| 5 | Visão Time técnico (modelo) | `prints/05_time_tecnico.png` | métricas no teste temporal, faixas, importância, curvas, estabilidade |
| 6 | Landing: calculadora de ROI e agendamento | `prints/06_landing_roi.png` | alunos, ticket e desistência recalculam receita perdida, custo da Retena e alunos a reter; CTA para o piloto |

## 3. O que é funcional e o que é simulado no protótipo

| Elemento | Estado |
|---|---|
| Números de risco, fatores, ação sugerida, mapa de atrito, métricas | reais, calculados pelo pipeline sobre a base anonimizada (corte 23/08/2026) |
| Seletor de visão, busca, filtros, ordenação, painel do aluno, ticket | funcionais |
| Registro do resultado do contato | funcional no navegador (localStorage); vai para o banco na Fase 7 |
| Link direto para um aluno (`?aluno=Aluno%200227`) e para uma visão (`?modo=diretoria`) | funcionais |
| Atualização automática do painel a partir do snapshot do Oracle | não: o HTML é regenerado pelo pipeline; o APEX substitui isto na Fase 7 |
| Envio de mensagem ao aluno (WhatsApp) | não; roadmap |

## 4. Como abrir

- Online: https://lucashenklain.github.io/retena/dashboard/?modo=diretoria
- Offline: abrir `05_MVP/dashboard/index.html` no navegador (sem servidor); as fontes vêm de `03_Marca/fontes`.
