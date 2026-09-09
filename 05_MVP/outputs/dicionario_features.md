# Dicionário de features — MVP de risco de evasão

Gerado automaticamente por `pipeline/02_features_semanais.py`.

## Definições gerais

- **Evento de atividade**: ação do próprio aluno no LMS (origem `web`, evento não administrativo). Eventos gerados por tutor/coordenação/rotinas (lançamento de nota, matrícula, cron) são excluídos de contagens de engajamento e do rótulo.
- **Cortes**: domingos de 2026-02-01 a 2026-08-23 (t inclui o domingo).
- **Horizonte do rótulo**: 21 dias após o corte.
- Apenas alunos com ≥ 1 evento de atividade até t entram no corte t.

## Base aluno-semana (`base_treino_semanal.parquet` e `base_scoring_atual.parquet`)

- Treino rotulado: 4,083 linhas, 183 alunos, 27 cortes (2026-02-01 → 2026-08-02), taxa de positivos 18.1%.
- Scoring atual: 196 alunos no corte 2026-08-23 (sem rótulo).

| Coluna | Descrição |
|---|---|
| `corte` | Data do corte semanal t (domingo). Features usam apenas eventos com data ≤ t. |
| `aluno_id` | Identificador anonimizado do aluno ("Aluno NNNN"). |
| `eventos_7d` | Nº de eventos de atividade do aluno em (t−7d, t]. |
| `eventos_14d` | Nº de eventos de atividade em (t−14d, t]. |
| `eventos_28d` | Nº de eventos de atividade em (t−28d, t]. |
| `dias_ativos_7d` | Nº de dias distintos com atividade em (t−7d, t]. |
| `dias_ativos_14d` | Nº de dias distintos com atividade em (t−14d, t]. |
| `dias_ativos_28d` | Nº de dias distintos com atividade em (t−28d, t]. |
| `recencia_dias` | Dias entre o último evento de atividade (≤ t) e t. 999 se nunca houve evento. |
| `progresso_28d` | Nº de eventos "Progresso de conteúdo atualizado" em 28 dias. |
| `capitulos_distintos_28d` | Nº de pares (fase, capítulo) distintos acessados em 28 dias. |
| `capitulo_max_fase_atual` | Maior capítulo acessado na fase atual (0 se nenhum evento com capítulo). |
| `pct_capitulos_fase_atual` | capitulo_max_fase_atual ÷ total de capítulos da fase (F1=10, F2=12, F3=10, F4=11, F5=8). |
| `quiz_iniciados_28d` | Nº de tentativas de questionário iniciadas em 28 dias. |
| `quiz_entregues_28d` | Nº de tentativas de questionário entregues em 28 dias. |
| `entregas_28d` | Nº de entregas de tarefa/atividade em 28 dias. |
| `tendencia` | eventos_7d ÷ (eventos_28d/4 + 1). ≈1 = ritmo estável; <0,5 = queda forte; >1 = aceleração. |
| `share_noite_28d` | Fração dos eventos de 28 dias ocorridos entre 19h e 23h. |
| `share_fim_semana_28d` | Fração dos eventos de 28 dias ocorridos em sábado/domingo. |
| `semanas_ativas_ultimas_8` | Nº de janelas semanais (entre as 8 anteriores a t) com ≥ 1 evento. |
| `eventos_acumulados` | Total de eventos de atividade do aluno até t. |
| `dias_ativos_acumulados` | Total de dias distintos com atividade até t. |
| `fase_atual` | Fase mais avançada (1–5) em que o aluno já teve evento até t. |
| `semanas_desde_primeiro_evento` | Semanas completas entre o primeiro evento do aluno e t. |
| `primeiro_evento` | Data do primeiro evento de atividade do aluno (auxiliar, não usada no modelo). |
| `ultimo_evento` | Data do último evento de atividade até t (auxiliar, não usada no modelo). |
| `inativo_21d` | RÓTULO: 1 se o aluno não tem nenhum evento de atividade em (t, t+21d]; NaN na base de scoring. |

## Base de transição de fases (`base_transicao_fases.parquet`)

- 610 linhas aluno-fase; taxa de evasão entre fases 7.5%.
- Início de cada fase estimado pelo percentil 5 das datas de evento; fim = início da fase seguinte.

| Coluna | Descrição |
|---|---|
| `aluno_id` | Identificador do aluno. |
| `fase` | Fase k (1–4) de origem da transição k → k+1. |
| `eventos_fase` | Nº de eventos de atividade na fase k até o fim estimado da fase. |
| `dias_ativos_fase` | Dias distintos com atividade na fase k. |
| `span_dias` | Dias entre primeiro e último evento na fase k (+1). |
| `capitulo_max` | Maior capítulo acessado na fase k. |
| `pct_capitulos` | capitulo_max ÷ total de capítulos da fase k. |
| `quiz_iniciados` | Tentativas de questionário iniciadas na fase k. |
| `quiz_entregues` | Tentativas de questionário entregues na fase k. |
| `entregas` | Entregas de tarefa na fase k. |
| `progresso` | Eventos de progresso de conteúdo na fase k. |
| `share_noite` | Fração de eventos entre 19h e 23h na fase k. |
| `share_fim_semana` | Fração de eventos em fim de semana na fase k. |
| `recencia_fim_fase` | Dias entre o último evento do aluno na fase k e o fim estimado da fase. |
| `atraso_inicio_dias` | Dias entre o início estimado da fase e o primeiro evento do aluno na fase. |
| `eventos_ultimas_2sem` | Eventos nas 2 últimas semanas da fase k. |
| `tendencia_fase` | eventos_ultimas_2sem ÷ (média quinzenal anterior + 1). |
| `primeiro_evento` | Data do primeiro evento na fase (auxiliar). |
| `ultimo_evento` | Data do último evento na fase (auxiliar). |
| `evadiu_proxima_fase` | RÓTULO: 1 se o aluno não tem nenhum evento de atividade na fase k+1. |
