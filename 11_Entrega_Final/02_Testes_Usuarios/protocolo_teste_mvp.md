# Protocolo de teste com usuários — MVP final Retena

> Teste **com pessoas reais do público-alvo**. As entrevistas das fases anteriores foram **simuladas** e continuam rotuladas assim; nada daqui pode reaproveitar falas ou números delas. Evolui o protocolo da Fase 5 (`10_Prototipacao_PoC/05_Usabilidade/protocolo_teste_usabilidade.md`), agora sobre o MVP com Oracle.

## 1. Objetivo

Verificar, com **no mínimo 3 usuários do público-alvo**, se o MVP resolve o problema central: *a coordenação descobrir, toda semana, quem chamar, entender por quê, agir e registrar o resultado — e a diretoria enxergar o valor disso*. Medir eficácia (sucesso nas tarefas), eficiência (tempo, erros), satisfação (SUS) e percepção de valor; registrar dificuldades, feedback e ajustes feitos.

## 2. Perfil e recrutamento

**Elegível (precisa atender a 1 e 2):**
1. Atua hoje (ou atuou nos últimos 2 anos) em **permanência/retenção, tutoria, coordenação de curso ou gestão acadêmica** de IES com oferta **EAD ou híbrida**.
2. Não é integrante da equipe, nem parente/colega direto de integrante que já conheça o projeto em detalhe.

**Composição desejada (mín. 3, ideal 5):** ≥ 2 perfis "Mariana" (coordenação de permanência/tutoria, usa a fila toda semana); ≥ 1 perfil "Renata" (diretoria/gestão acadêmica, decide a compra); tutores e 1 pessoa de TI acadêmica são bem-vindos como P4/P5 (TI faz a tarefa extra TX).

**Onde encontrar:** IES parceira ou contato do piloto; professores/coordenadores da própria FIAP que atuam em EAD; LinkedIn (busca "coordenadora EAD", "permanência estudantil", "tutoria EAD", "sucesso do aluno"); grupos de ABED/associações de EAD; indicação dos primeiros participantes (bola de neve).

**Convite (modelo):** "Estamos testando, como trabalho da FIAP, uma ferramenta que aponta alunos EAD com risco de evasão. Buscamos coordenadoras(es), tutores ou gestores de EAD para uma conversa de 40 minutos, online, em que você usa a ferramenta e nos diz o que funciona e o que não funciona. Não há venda; os dados da tela são sintéticos."

## 3. Consentimento e LGPD

- **Dados da tela:** alunos sintéticos/pseudonimizados (identificador "Aluno NNNN"); o participante não insere dados reais de alunos.
- **Dados do participante:** registrar só código (P1, P2…), papel, tipo de IES e faixa de experiência. Nome, e-mail e instituição ficam fora dos arquivos de resultado (planilha de contatos da equipe, apagada ao fim do projeto).
- **Gravação:** opcional, só com consentimento explícito; uso exclusivo para análise da equipe; apagar após a consolidação. Sem gravação, vale a anotação do observador.
- **Roteiro do termo (ler e registrar o "aceito" no formulário):**
  > "Esta sessão faz parte de um trabalho acadêmico da FIAP (Startup One). Vamos observar você usando um protótipo e anotar suas falas e dificuldades. Não guardaremos seu nome nos resultados: você será identificado(a) como P[n]. Você pode parar a qualquer momento, sem justificar. [Se aplicável] Podemos gravar a tela e o áudio só para nossa análise? A gravação será apagada após a consolidação. Você concorda em participar?"

## 4. Preparação (antes de cada sessão)

- [ ] Subir o MVP: `entrega\11_Entrega_Final\01_MVP_Oracle\INICIAR_MVP.cmd`; abrir http://127.0.0.1:8080.
- [ ] Na mesma pasta, `python verificar_mvp.py` → deve terminar com "TODOS OS PASSOS PASSARAM" (ele apaga o próprio contato de teste).
- [ ] Resetar resultados de sessões anteriores (SQL abaixo, como `STARTUP` em `localhost:1521/FREEPDB1`).
- [ ] Conferir: fila com 74 alunos "Na fila", ticket mensal no valor padrão (R$ 350), aba Coordenação aberta, gaveta fechada.
- [ ] Separar formulário em branco (`formulario_participante.md`) e cronômetro; definir moderador e observador.
- [ ] Remoto: testar áudio, compartilhamento e controle remoto 10 min antes.

Na sessão, o participante grava contatos com **Responsável = `TESTE-P1`** (P2, P3…), para o reset achar só esses registros:

```sql
-- reset entre sessões: devolve à fila os alunos tratados no teste e o ticket padrão
UPDATE RISCO_ALUNO_SNAPSHOT s SET STATUS_ATENDIMENTO = 'PENDENTE', OBSERVACAO = NULL
 WHERE s.NOME IN (SELECT NOME FROM CONTATO_RESULTADO WHERE RESPONSAVEL LIKE 'TESTE-P%')
   AND NOT EXISTS (SELECT 1 FROM CONTATO_RESULTADO c WHERE c.NOME = s.NOME AND c.RESPONSAVEL NOT LIKE 'TESTE-P%');
DELETE FROM CONTATO_RESULTADO WHERE RESPONSAVEL LIKE 'TESTE-P%';
UPDATE PARAMETRO_IES SET VALOR = 350 WHERE CHAVE = 'TICKET_MENSAL';
COMMIT;
```

## 5. Roteiro da sessão (30–40 min)

| Bloco | Tempo | Conteúdo |
|---|---|---|
| Abertura | 5 min | Termo de consentimento; perfil (papel, IES, experiência, como identifica alunos em risco hoje). |
| Contexto | 1 min | Ler: *"É segunda de manhã. Você é responsável pela permanência de um curso EAD. Esta tela diz quem está em risco de desistir. Pense em voz alta. Se algo não ficar claro, o problema é da tela, não seu."* Não explicar a interface. |
| Tarefas | 15–20 min | T1–T6 abaixo (TX só para perfil técnico). Cronometrar; não ajudar; após 60 s travado, dar uma dica e marcar "com dica"; após 2× o tempo-alvo, encerrar a tarefa como "não concluiu". |
| Pós-tarefa | 5 min | Perguntas da seção 6. |
| Questionários | 5 min | SUS + 3 perguntas de valor (+ NPS opcional). |
| Fechamento | 2 min | Agradecer; perguntar se aceita ser contatado(a) de novo para o piloto. |

### Tarefas observáveis

| # | Tela | Enunciado (ler ao participante) | Critério de sucesso | Tempo-alvo | O que observar |
|---|---|---|---|---|---|
| T1 | Coordenação | "Quem você chamaria primeiro esta semana? Por quê?" | Escolhe aluno do grupo **Agir agora** e justifica com a coluna "por quê" / dias sem acesso / risco 21 dias | 60 s | Entende os 3 grupos e a ordem? Lê "risco 21 dias (%)" corretamente? |
| T2 | Painel do aluno | "Abra esse aluno. Explique com suas palavras por que ele está em risco e o que mudaria se ele voltasse esta semana." | Abre a gaveta, cita ≥ 2 dos 3 motivos, usa **"E se ele voltar esta semana?"** e interpreta a queda do risco | 120 s | Entende RF/GLM/evasão na fase? Lê o gráfico de 12 semanas? Confia ou desconfia do número? |
| T3 | Painel do aluno | "Você mandou a mensagem sugerida pelo WhatsApp e ele combinou de voltar na quinta. Registre isso." (Responsável: `TESTE-Pn`) | **Copiar mensagem** + resultado **Plano combinado**, canal, responsável → **Gravar no Oracle** e lê o número do contato | 150 s | Acha o registro sem ajuda? Hesita entre resultados? Percebe a confirmação? |
| T4 | Coordenação | "Onde está agora o aluno que você acabou de tratar? E quem são os alunos do grupo Resgate — o que os diferencia de Agir agora?" | Usa o filtro **Já tratados** e encontra o aluno; explica que Resgate = alto risco sem acesso há mais de 30 dias | 90 s | Descobre os filtros Na fila/Já tratados/Todos e faixa? Entende o critério dos grupos? |
| T5 | Diretoria | "Sua diretora pergunta quanto de receita anual está em risco. O ticket real é R$ 500: atualize e diga o novo valor. Estamos perto da meta do piloto?" | Lê o cartão de receita em risco, altera ticket e **Salvar no banco**, lê o novo valor e a meta (30% dos alto risco reativados) | 120 s | Entende "receita preservada (estimativa)"? Acha o campo do ticket? |
| T6 | Diretoria | "Em que fase do curso o risco está mais concentrado? O que você faria com isso?" | Aponta a fase de maior risco no gráfico "risco por fase" e propõe uma ação coerente | 60 s | Lê o gráfico sem ajuda? Conecta com uma decisão? |
| TX (opcional, TI) | Time técnico | "Mostre que o modelo roda dentro do Oracle e atualize a fila agora." | Lê AUC dos modelos, usa **Rodar o scoring agora** e abre uma consulta da **Prova em SQL** | 120 s | Confia na evidência? Sente falta de algo (logs, agenda do job, permissões)? |

Para cada tarefa registrar: sucesso (sozinho / com dica / não concluiu), tempo (s), nº de erros (clique ou caminho errado, interpretação errada), falas literais.

## 6. Perguntas pós-tarefa (anotar literalmente)

1. O que você faria primeiro, numa segunda-feira, com esta tela?
2. O que ficou confuso ou demorou para encontrar? Algum termo que não entendeu?
3. Você confiaria no risco e nos motivos mostrados para decidir quem chamar? Por quê?
4. Como você faz isso hoje (planilha, relatório do LMS, intuição)? Isto substitui o quê?
5. Que informação ou ação faltou?

## 7. Questionários

**SUS** (1 = discordo totalmente … 5 = concordo totalmente):

1. Eu acho que gostaria de usar este sistema com frequência.
2. Eu acho o sistema desnecessariamente complexo.
3. Eu achei o sistema fácil de usar.
4. Eu acho que precisaria do apoio de um suporte técnico para usar este sistema.
5. Eu acho que as várias funções do sistema estão muito bem integradas.
6. Eu acho que o sistema apresenta muita inconsistência.
7. Eu imagino que as pessoas aprenderão a usar este sistema rapidamente.
8. Eu achei o sistema atrapalhado de usar.
9. Eu me senti confiante ao usar o sistema.
10. Eu precisei aprender várias coisas novas antes de conseguir usar o sistema.

Escore = [(soma de (item ímpar − 1)) + (soma de (5 − item par))] × 2,5 (0–100; referência de mercado ≈ 68).

**Perguntas de valor:**
- V1. Isto resolveria o seu problema de saber quem chamar e provar o resultado? ( ) sim ( ) em parte ( ) não — por quê?
- V2. Sua instituição pagaria por isto? Quem decidiria e quanto faria sentido? ( ) sim ( ) talvez ( ) não
- V3. O que falta para você usar isto de verdade no próximo semestre?
- NPS (opcional): de 0 a 10, quanto recomendaria a um colega de outra IES?

## 8. Métricas

| Métrica | Como calcular |
|---|---|
| Taxa de sucesso por tarefa | concluídas (sozinho + com dica) ÷ participantes; reportar também "sozinho" |
| Tempo médio por tarefa | média dos tempos das sessões concluídas, comparada ao tempo-alvo |
| Erros por tarefa | média de erros |
| SUS | escore por participante e média |
| Problemas | contagem por severidade (1 cosmético, 2 menor, 3 grave, 4 impeditivo) e frequência |
| Valor | nº de "sim/em parte" em V1 e V2; NPS se coletado |

Tudo é lançado em `consolidacao_testes.xlsx`, que calcula os indicadores na aba Resumo.

## 9. Critérios de decisão

**O MVP resolve o problema se**, com ≥ 3 participantes reais:
- T1 e T3 (o fluxo crítico: escolher quem chamar e registrar o resultado) têm sucesso ≥ 80%, e nenhuma tarefa fica abaixo de 60%;
- SUS médio ≥ 68;
- não resta problema de severidade 4 sem ajuste feito;
- a maioria dos participantes responde "sim" ou "em parte" em V1, com justificativa ligada ao problema (saber quem chamar / provar resultado).

Se algum critério falhar, registrar o ajuste, aplicá-lo no MVP quando possível e, se houver prazo, repetir a tarefa afetada com um novo participante (P4/P5). Resultados negativos entram no documento como estão.

## 10. Formato remoto

- **Preferido:** Google Meet ou Microsoft Teams com o **facilitador compartilhando a tela** do MVP local. No Teams, usar "Dar controle" para o participante operar; no Meet (sem controle remoto), o participante dita os cliques ("clique em…") e o observador conta as hesitações. Registrar a modalidade no formulário.
- **Alternativa:** túnel temporário (ex.: Cloudflare Tunnel, ngrok) **apenas para a porta 8080 da aplicação**, com URL não divulgada, aberto só durante a sessão e encerrado em seguida. **Nunca expor a porta 1521 do Oracle** nem publicar o endereço; o banco fica só na máquina da equipe.
- Presencial: notebook da equipe, participante no mouse, observador ao lado.
