# Relatório de validação técnica — Retena (Parte 3)

**Projeto:** Retena · Startup One / Enterprise Challenge Oracle · FIAP 4ESOA-2026
**Equipe:** Lucas Dalmas (RM551178) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198)
**Período avaliado:** 08/09 a 07/10/2026 (entrega da Fase 6, Banca Final de 23/09 e reexecuções posteriores)
**Fontes:** logs em `06_Oracle/evidencias/` e `06_Oracle/evidencias/logs_reexecucao_2026-09-22/`, `05_MVP/outputs/RESULTADOS.md`, `05_MVP/portabilidade_oulad/RESULTADOS_OULAD.md`, `09_Kit_Banca_Final/dia_da_banca/ultimo_scoring.txt`.

## 1. Resumo executivo

A solução é tecnicamente viável com o que já foi executado: os 684.723 eventos de LMS da instituição parceira foram carregados no Oracle AI Database 26ai Free, as features foram calculadas em SQL, três modelos foram treinados dentro do banco com Oracle Machine Learning e o risco de cada aluno é recalculado por um job semanal em cerca de 24 segundos. O pipeline completo foi reexecutado do zero em 22/09/2026 sem erros e o scoring foi reexecutado ao vivo em 23/09/2026 durante a banca.

Três conclusões mudaram o desenho entre a Fase 6 e agora:

1. **Scoring ao vivo não escala; scoring materializado escala.** A view que recalculava as features sob demanda (`VW_RISCO_ALUNO_ATUAL`) levava mais de 60 segundos por consulta para 203 alunos. Foi substituída pela tabela `RISCO_ALUNO_SNAPSHOT`, atualizada por `PRC_ATUALIZAR_RISCO` via `DBMS_SCHEDULER` (23–24 s). O painel passa a ler a tabela, que responde na hora.
2. **O cálculo semanal de features é o gargalo de crescimento.** O script `03_features_semanais.sql` levou 89 s para um curso de 203 alunos. Para uma IES de 12 mil alunos o volume de eventos é cerca de 60 vezes maior; a extrapolação linear dá da ordem de 90 minutos por semana, aceitável para um job noturno, mas inaceitável para retreino diário ou para multi-IES no mesmo schema. O desenho da Fase 7 adota features incrementais (janela móvel de 28 dias) e um schema por instituição.
3. **O registro do resultado do contato precisa persistir no banco.** No protótipo atual ele existe apenas no navegador (localStorage). Sem esse dado, a receita preservada não é medida de verdade e o retreino com o resultado das intervenções não acontece. É a primeira funcionalidade da Fase 7.

## 2. Viabilidade técnica

| Capacidade | Como foi provada | Resultado medido |
|---|---|---|
| Carga do export do LMS no Oracle | `scripts/carregar_eventos.py` (python-oracledb modo thin, lotes) | 684.723 linhas em 72 s na execução original (08/09) e 146 s na reexecução de 22/09 com o container recém-criado |
| Features em SQL | `02_features_transicao.sql` (9 passos) e `03_features_semanais.sql` (14 passos) | 16 s e 89 s, 0 erros |
| Treino in-database | `04_oml_modelos.sql` com `DBMS_DATA_MINING` (Random Forest e GLM para inatividade em 21 dias; GLM para transição de fase) | 7 s; AUC-ROC 0,949 (RF), 0,945 (GLM) e 0,972 (transição) no teste temporal ≥ jun/2026 |
| Scoring e exposição | `05_scoring_views.sql`: `PREDICTION_PROBABILITY`/`PREDICTION_DETAILS`, snapshot, views JSON, Duality View, job semanal | 67 s na criação; job `JOB_RETENA_SCORING_SEMANAL` em 23–24 s; snapshot com 203 alunos (59 Alto, 15 Médio, 129 Baixo) |
| Avaliação e consultas para APEX | `06_avaliacao.sql`, `07_apex_ready.sql` | 4 s e 6 s |
| Modelo de referência (Python) | `05_MVP/pipeline` com validação temporal e embargo de 21 dias | AUC-ROC 0,882, precisão no top-20% 0,882, lift 3,06×; subconjunto acionável AUC 0,743 |
| Portabilidade do método | mesmo pipeline no OULAD (Open University, 24.392 alunos, split 2013→2014) | AUC-ROC 0,922, lift 3,51×, execução total ~110 s |
| Reprodutibilidade | `docker compose up` + `carregar_eventos.py` + `executar_sql.py` 02–07 | pipeline inteiro em ~7 min, 0 erros (22/09/2026) |
| Caminho para a nuvem | `06_Oracle/oci`: conexão dual (Free local / Autonomous com wallet), exportação CSV gzip (dry-run), MERGE idempotente executado 2× sem duplicar | runbook de 60 min; Object Storage, DBMS_CLOUD, APEX e Select AI ainda sem conta OCI |

Veredito: viável. Nenhum componente exige tecnologia fora do Oracle Autonomous AI Database e de Python; não há servidor de ML, ETL externo nem cientista de dados dedicado na operação.

## 3. Principais desafios de implementação

1. **Formato do export do LMS.** A carga depende do export em CSV/XLSX com as colunas do log de navegação. Cada LMS (Moodle, Canvas, Blackboard) exporta de forma diferente; a Fase 7 define um contrato de entrada mínimo (aluno, data-hora, tipo de evento, fase/módulo, capítulo/recurso) e um mapeamento por LMS.
2. **Rótulo comportamental.** O alvo é "21 dias sem ação no LMS", não o cancelamento administrativo. Isso torna o modelo portátil, mas exige calibrar o limiar por instituição e explicar a diferença para a diretoria.
3. **Duas implementações do modelo.** O pipeline Python (referência metodológica) e o modelo OML (arquitetura in-database) têm conjuntos de features ligeiramente diferentes (AUC 0,88 e 0,95 não são comparáveis um a um). A Fase 7 unifica: as features passam a ser calculadas apenas em SQL e o Python vira ferramenta de avaliação.
4. **Painel estático.** O dashboard entregue é HTML gerado pelo pipeline, hospedado no GitHub Pages: ótimo para demonstrar, mas não lê o banco. O painel definitivo é APEX sobre as views JSON já existentes.
5. **Horário do banco em UTC.** O container e o Autonomous trabalham em UTC; todo carimbo exibido precisa de conversão (`AT TIME ZONE 'America/Sao_Paulo'`), já aplicada no scoring ao vivo.

## 4. Riscos técnicos identificados

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Export do LMS muda de formato ou chega incompleto | média | alto | contrato de entrada + validação na carga (contagem, datas, alunos) + quarentena de linhas inválidas |
| R2 | Deriva do modelo entre semestres (calendário, novos cursos) | alta | médio | retreino mensal pelo job, monitor de AUC por corte (já medido: 0,80–0,97) e alerta se cair abaixo de 0,80 |
| R3 | Amostra pequena por IES no início | alta | médio | modelo inicial treinado na base de referência + OULAD; retreino após 8 semanas de dados da IES |
| R4 | Tempo do cálculo semanal cresce linearmente com o volume | alta | alto | features incrementais por janela móvel, particionamento por semana, um schema por IES |
| R5 | Segredos e acesso (senha em `.env`, usuário único) | média | alto | wallet do Autonomous, perfis de acesso por papel (coordenação, tutor, gestão), TDE e auditoria nativos |
| R6 | Exposição de dados pessoais no painel | baixa | alto | pseudonimização fora do painel ("Aluno NNNN"), base legal documentada, opt-in de contato |
| R7 | Dependência de conta OCI para APEX e Object Storage | alta | médio | runbook pronto; demonstração local com Oracle Free continua válida; pedido de Always Free/Oracle for Startups |
| R8 | Perda de disponibilidade do container local em demonstrações | média | baixo | scripts `dia_da_banca/` (preparação em 1 min, servidor local de reserva, prints de reserva) |

## 5. Gargalos de performance e arquitetura

| Ponto | Medição | Diagnóstico | Ajuste |
|---|---|---|---|
| View de risco ao vivo | > 60 s por consulta (203 alunos) | recalcula todas as features a cada SELECT | snapshot materializado + job semanal (feito) |
| Features semanais | 89 s para 684.723 eventos | varre todo o histórico a cada execução | janela móvel de 28 dias e tabelas de agregados por semana (Fase 7) |
| Carga inicial | 72–146 s | inserção em lotes pelo cliente | aceitável; na nuvem, `DBMS_CLOUD.COPY_DATA` a partir do Object Storage (runbook) |
| Painel estático | regenerado a cada execução do pipeline | não reflete registros nem o snapshot mais recente | APEX lendo `VW_RISCO_JSON`/Duality View (Fase 7) |
| Registro de contato | só no navegador | sem persistência nem retreino | tabela `CONTATO_RESULTADO` + API REST (ORDS) (Fase 7, prioridade 1) |
| Multi-IES | não testado | um schema único misturaria instituições | um schema por IES no Autonomous Serverless, com auto-scaling |

## 6. Ajustes no desenho da arquitetura

1. Scoring passa a ser materializado em tabela (`RISCO_ALUNO_SNAPSHOT`) e atualizado por job; a view ao vivo fica apenas para auditoria.
2. Entrada de dados por contrato: CSV padrão → Object Storage → `DBMS_CLOUD.COPY_DATA` → tabela `EVENTOS_LMS` particionada por semana.
3. Registro do resultado do contato persistido no banco e consumido pelo retreino.
4. Painel em APEX sobre as views JSON existentes; o dashboard HTML permanece como protótipo e material de demonstração.
5. Um schema por instituição; o modelo de referência é compartilhado até a IES ter 8 semanas de dados próprios.

O diagrama atualizado está em `04_Arquitetura/08_arquitetura_executada.png` e a explicação de escalabilidade e manutenção em `04_Arquitetura/arquitetura_evolucao.md`.
