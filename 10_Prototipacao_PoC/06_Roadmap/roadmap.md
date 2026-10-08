# Roadmap de evolução até o MVP final — Retena (Parte 6)

## 1. O que já foi implementado (até 07/10/2026)

| Área | Entregue | Evidência |
|---|---|---|
| Dados | Carga dos 684.723 eventos de LMS da IES parceira no Oracle AI Database 26ai; features em SQL | `06_Oracle/scripts`, `06_Oracle/sql/01–03`, logs em `06_Oracle/evidencias` |
| Modelo | Random Forest e GLM treinados in-database (OML); modelo de referência em Python com validação temporal; benchmark de 6 configurações; portabilidade no OULAD | `06_Oracle/sql/04`, `05_MVP/outputs/RESULTADOS.md`, `05_MVP/portabilidade_oulad` |
| Scoring | Snapshot semanal por job (`DBMS_SCHEDULER`), `PREDICTION_PROBABILITY/DETAILS`, views JSON e Duality View, MERGE idempotente | `06_Oracle/sql/05`, `dia_da_banca/ultimo_scoring.txt` |
| Produto | Dashboard com visões Diretoria / Coordenação / Time técnico, fila de segunda com motivo e ação, mapa de atrito, registro do resultado do contato (protótipo no navegador) | `05_MVP/dashboard/index.html`, publicado em lucashenklain.github.io/retena/dashboard |
| Comercial | Landing page com vídeo de vendas, calculadora de ROI e agendamento; manual de marca; kit da banca | `04_Landing_Page`, `03_Marca`, `09_Kit_Banca_Final` |
| Nuvem | Runbook OCI: conexão dual, exportação CSV gzip, MERGE testado 2× | `06_Oracle/oci` |
| Operação | Preparação do ambiente em 1 min e scoring ao vivo em 25 s | `09_Kit_Banca_Final/dia_da_banca` |

## 2. O que será entregue na Fase 7 (MVP final)

Prioridades pelo método MoSCoW. "Deve" é o que define o MVP funcional; sem isso não há piloto.

| Prioridade | Funcionalidade | Por que | Critério de pronto |
|---|---|---|---|
| **Deve** | Registro do resultado do contato persistido no banco (`CONTATO_RESULTADO`) com API REST (ORDS) | fecha o ciclo e permite medir receita preservada de verdade; hoje só existe no navegador | registro feito no painel aparece em SQL e no relatório semanal |
| **Deve** | Painel em APEX sobre as views JSON (fila, aluno, registro, visão da diretoria) | substitui o HTML estático; lê o snapshot mais recente | mesmas 6 telas do protótipo funcionando no Autonomous |
| **Deve** | Provisionar Autonomous AI Database Always Free e executar o runbook OCI (Object Storage + `DBMS_CLOUD.COPY_DATA`, usuário RETENA, job) | tirar a prova do Docker local e colocar na nuvem | pipeline 01–07 executado no Autonomous com os mesmos números |
| **Deve** | Contrato de entrada do LMS + validação na carga (quarentena de linhas inválidas) | risco R1; cada LMS exporta diferente | carga rejeita e reporta linhas inválidas sem abortar |
| **Deve** | Teste de usabilidade com 2+ usuários e correções identificadas | Parte 5 desta fase; a lista de melhorias entra aqui | relatório `05_Usabilidade/consolidacao_feedback.md` com ações fechadas |
| **Deveria** | Features incrementais (janela móvel de 28 dias) e partição por semana | gargalo de crescimento (89 s → ~90 min em 12 mil alunos) | job semanal abaixo de 10 min para 12 mil alunos simulados |
| **Deveria** | Relatório semanal em PDF para a diretoria (receita em risco, preservada, alunos reativados) | o que a Renata quer ver; venda e renovação | gerado automaticamente toda sexta |
| **Deveria** | Template de mensagem e link direto de WhatsApp (`wa.me`) na fila | a coordenação contata à noite, no canal do aluno | um clique abre a conversa com a mensagem sugerida |
| **Deveria** | Perfis de acesso por papel (coordenação, tutor, gestão) e pseudonimização configurável | LGPD por arquitetura | login APEX com papéis e auditoria |
| **Poderia** | Select AI para perguntas em português sobre a base | demonstração forte para o ecossistema Oracle | 5 perguntas do roteiro respondidas corretamente |
| **Poderia** | Recomendações do mapa de atrito dentro do LMS (conteúdo adaptativo) | módulo do ano 2 do plano de negócio | protótipo de uma recomendação por capítulo |
| **Não agora** | App mobile, integração LTI nativa, multi-idioma | fora do MVP; depende do piloto | — |

## 3. Ordem de desenvolvimento proposta

1. Autonomous Always Free + runbook OCI (destrava APEX e Object Storage).
2. Tabela e API de registro de contato; retreino passa a usar o resultado.
3. APEX com as 6 telas do protótipo, começando pela fila e pelo painel do aluno.
4. Contrato de entrada e validação da carga.
5. Correções do teste de usabilidade.
6. Relatório semanal em PDF e link de WhatsApp.
7. Features incrementais e partição; teste de carga com 12 mil alunos simulados.
8. Select AI e perfis de acesso.

## 4. Dependências e pedidos

- Conta OCI com Autonomous Always Free (ou créditos Oracle for Startups) para os itens 1, 3 e 8.
- Uma IES parceira para o piloto de 90 dias (dados anonimizados, meta de rematrícula acordada).
- Dois usuários reais para o teste de usabilidade desta fase (ver `05_Usabilidade/protocolo_teste_usabilidade.md`).
