# Teste de usabilidade inicial — Retena (Parte 5)

**Objetivo:** verificar, com pelo menos 2 usuários reais, se o dashboard da Retena é claro e fácil de usar para a tarefa principal: descobrir quem chamar na segunda-feira, entender por quê e registrar o resultado.
**Duração:** 20 minutos por pessoa (5 de contexto, 10 de tarefas, 5 de perguntas). **Moderador:** um integrante da equipe. **Observador:** outro integrante anota tempos e dificuldades.
**Ambiente:** https://lucashenklain.github.io/retena/dashboard/ (ou a cópia local em `05_MVP/dashboard/index.html`), notebook ou desktop, navegador Edge/Chrome. Não explicar a tela antes: o teste mede se ela se explica sozinha.

## Perfil desejado dos participantes

Pessoas que lidam com gestão de pessoas, educação ou operação (coordenação, tutoria, secretaria acadêmica, RH, gestores). Não vale integrante da equipe. Registrar apenas iniciais, papel e familiaridade com dashboards (baixa / média / alta).

## Roteiro do moderador

1. **Contexto (ler em voz alta):** "Você é coordenadora de permanência de um curso EAD. É segunda-feira de manhã. Esta tela foi feita para dizer quem está em risco de desistir. Vou pedir algumas tarefas; pense em voz alta. Não existe resposta errada: se algo não ficar claro, o problema é da tela, não seu."
2. **Tarefas** (cronometrar cada uma; anotar se concluiu sozinho, com dica ou não concluiu):

| # | Tarefa | Sucesso esperado | Mede |
|---|---|---|---|
| T1 | "Quantos alunos precisam ser chamados esta semana e quanto de receita está em risco?" | Lê os cartões da visão Diretoria (61 alunos; R$ 231 mil) | Clareza da visão executiva |
| T2 | "O ticket mensal da sua instituição é R$ 500. Atualize e diga o novo valor em risco." | Altera o campo e lê R$ 330 mil | Descoberta do controle |
| T3 | "Encontre o aluno 0227 e me diga por que ele está em risco e o que fazer." | Vai à visão Coordenação (ou Tudo), busca, abre o painel, lê fatores e ação | Navegação entre visões, busca, painel |
| T4 | "Você ligou para ele e ele disse que vai voltar na quinta. Registre isso." | Usa 'Registrar resultado' → 'Plano combinado' no painel e vê o status na fila | Fluxo crítico (registro) |
| T5 | "Em qual capítulo os alunos mais travam?" | Vai ao mapa de atrito e aponta o cap. 2 da fase 4 | Leitura do mapa |
| T6 | "Quais são os 3 alunos de alto risco que ainda estão ativos?" | Usa o preset 'Quem chamar hoje' ou filtra Alto + Ativo | Filtros |

3. **Perguntas finais (anotar literalmente):**
   - O que você faria primeiro, numa segunda-feira, com esta tela?
   - O que ficou confuso ou demorou para encontrar?
   - Que informação faltou?
   - De 1 a 5, quão fácil foi usar? De 1 a 5, quão clara foi a navegação?
   - Você usaria isto toda semana? Por quê?

## O que registrar (um formulário por participante)

Use `formulario_feedback.md` (uma cópia por pessoa). Preencher: iniciais e papel; para cada tarefa, tempo em segundos, resultado (sozinho / com dica / não concluiu) e observação; respostas finais; notas de 1 a 5.

## Regras de honestidade

- Só entram no relatório testes realmente conduzidos, com data, moderador e participante identificados por iniciais.
- Não corrigir nem "ajudar" o participante durante as tarefas; se travar por mais de 60 s, dar uma dica e marcar "com dica".
- As melhorias identificadas vão para `consolidacao_feedback.md` e para o roadmap (Parte 6) com prioridade.
