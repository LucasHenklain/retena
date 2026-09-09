# Resultados do MVP — risco de evasão (IES Demo)

Gerado automaticamente por `pipeline/03_treinar_modelo.py`. Todos os números vêm do pipeline; nada foi ajustado à mão.

## 1. Problema e dados

- **Objetivo principal**: prever, a cada domingo (corte t), se o aluno ficará **21 dias sem nenhuma ação no LMS** (`inativo_21d`).
- **Fonte**: logs do LMS de um único curso em 5 fases sequenciais (15/01/2026 → 26/08/2026), 684.723 eventos brutos, 203 alunos matriculados, 196 com alguma ação própria na plataforma (7 só têm eventos administrativos — matrícula/nota — e nunca acessaram).
- **Evento de atividade**: ação do próprio aluno (origem `web`, evento não administrativo). Lançamentos de nota, matrículas e rotinas automáticas não contam como engajamento nem como "sinal de vida" para o rótulo.
- **Base aluno-semana rotulada**: 4,083 linhas, 183 alunos, taxa global de positivos 18.1%.

## 2. Protocolo de avaliação

- Split **temporal**: treino: cortes < 2026-06-01 (com embargo de 21 dias); teste: cortes ≥ 2026-06-01.
- Treino: 2,126 linhas, 16 cortes (2026-02-01 → 2026-05-17), 167 alunos, positivos 10.1%.
- Cortes descartados por embargo (janela de rótulo invadiria o teste): 2026-05-24, 2026-05-31.
- Teste: 1,609 linhas, 9 cortes (2026-06-07 → 2026-08-02), 183 alunos, positivos 28.8%.
- Hiperparâmetros do HGB escolhidos por validação temporal interna ao treino (últimos 4 cortes de treino), critério AUC-PR: `{'learning_rate': 0.05, 'max_iter': 300, 'max_leaf_nodes': 8, 'min_samples_leaf': 40, 'l2_regularization': 2.0}`.
- Depois da avaliação, o modelo foi **retreinado no conjunto completo rotulado** e é esse o artefato usado no scoring.

## 3. Modelo principal — métricas no teste (jun–ago/2026)

| Métrica | HistGradientBoosting | Regressão Logística (baseline) |
|---|---|---|
| AUC-ROC | **0.882** | 0.893 |
| AUC-PR (average precision) | **0.839** | 0.859 |
| Taxa de positivos (referência da AUC-PR) | 28.8% | 28.8% |
| Brier score (menor é melhor) | 0.120 | 0.101 |
| Precisão @ limiar 0,5 | 0.924 | 0.895 |
| Recall @ limiar 0,5 | 0.580 | 0.659 |
| F1 @ limiar 0,5 | 0.713 | 0.759 |
| Precisão @ top-20% de risco (k=322) | **0.882** | 0.919 |
| Recall capturado no top-20% | 0.612 | 0.638 |
| Lift no top-20% vs. base | 3.06× | 3.19× |

**Matriz de confusão (HGB, limiar 0,5)** — VN=1123, FP=22, FN=195, VP=269 (n=1609).

### 3.1 Subconjunto acionável (alunos com ≥ 1 evento nos 28 dias anteriores ao corte)

Parte dos positivos é trivial: alunos já sumidos há semanas continuam sumidos. O subconjunto abaixo exclui esses casos e mede o que interessa à operação — antecipar o desligamento de quem ainda está presente.

| Métrica | HGB | Logística |
|---|---|---|
| n / positivos | 1298 / 191 (14.7%) | idem |
| AUC-ROC | **0.743** | 0.772 |
| AUC-PR | **0.460** | 0.494 |
| Precisão @ top-20% (k=260) | 0.377 | 0.396 |
| Lift no top-20% | 2.56× | 2.69× |
| Recall @ 0,5 | 0.178 | 0.199 |
| Precisão @ 0,5 | 0.694 | 0.704 |

### 3.2 Estabilidade por corte de teste (HGB)

| Corte | n | Positivos | AUC-ROC | AUC-PR |
|---|---|---|---|---|
| 2026-06-07 | 174 | 17.8% | 0.972 | 0.844 |
| 2026-06-14 | 178 | 21.3% | 0.967 | 0.899 |
| 2026-06-21 | 178 | 22.5% | 0.957 | 0.909 |
| 2026-06-28 | 178 | 32.6% | 0.897 | 0.855 |
| 2026-07-05 | 179 | 37.4% | 0.801 | 0.802 |
| 2026-07-12 | 179 | 39.7% | 0.816 | 0.821 |
| 2026-07-19 | 179 | 30.7% | 0.890 | 0.868 |
| 2026-07-26 | 181 | 28.7% | 0.922 | 0.893 |
| 2026-08-02 | 183 | 28.4% | 0.903 | 0.878 |

### 3.3 Calibração (HGB, teste, bins uniformes de 0,1)

| Bin de probabilidade | n | Prob. média prevista | Taxa observada |
|---|---|---|---|
| 0.0–0.1 | 1246 | 0.006 | 12.4% |
| 0.1–0.2 | 34 | 0.136 | 58.8% |
| 0.2–0.3 | 17 | 0.255 | 58.8% |
| 0.3–0.4 | 11 | 0.338 | 54.5% |
| 0.4–0.5 | 10 | 0.449 | 40.0% |
| 0.5–0.6 | 18 | 0.543 | 50.0% |
| 0.6–0.7 | 20 | 0.626 | 65.0% |
| 0.7–0.8 | 18 | 0.733 | 94.4% |
| 0.8–0.9 | 29 | 0.863 | 100.0% |
| 0.9–1.0 | 206 | 0.981 | 97.6% |

### 3.4 Faixas de risco

Faixas adotadas: **Alto** ≥ 0.60, **Médio** 0.30–0.60, **Baixo** < 0.30. Justificativa: 0,60 significa "mais provável ficar inativo do que não", com margem para erro de calibração — é o ponto em que compensa uma ação humana (contato do tutor). 0,30 é cerca de 1,5–2× a taxa média de positivos (18.1%), suficiente para acionar uma intervenção automática barata (mensagem). A tabela mostra a taxa observada em cada faixa no teste:

| Faixa | n | % das linhas | Taxa observada de inatividade |
|---|---|---|---|
| Alto | 273 | 17.0% | 95.2% |
| Médio | 39 | 2.4% | 48.7% |
| Baixo | 1297 | 80.6% | 14.3% |

### 3.5 Importância por permutação (HGB, teste, métrica AUC-ROC, 15 repetições) — top 12

| # | Feature | Queda média de AUC | DP |
|---|---|---|---|
| 1 | `dias_ativos_acumulados` | 0.0254 | 0.0043 |
| 2 | `dias_ativos_28d` | 0.0245 | 0.0061 |
| 3 | `eventos_acumulados` | 0.0162 | 0.0039 |
| 4 | `recencia_dias` | 0.0113 | 0.0032 |
| 5 | `share_noite_28d` | 0.0078 | 0.0018 |
| 6 | `share_fim_semana_28d` | 0.0020 | 0.0008 |
| 7 | `capitulo_max_fase_atual` | 0.0015 | 0.0006 |
| 8 | `eventos_28d` | 0.0015 | 0.0028 |
| 9 | `dias_ativos_7d` | 0.0015 | 0.0005 |
| 10 | `progresso_28d` | 0.0014 | 0.0004 |
| 11 | `semanas_ativas_ultimas_8` | 0.0014 | 0.0008 |
| 12 | `quiz_iniciados_28d` | 0.0009 | 0.0004 |

Coeficientes padronizados da regressão logística (sinal positivo = aumenta o risco), 8 maiores em módulo: `dias_ativos_28d` -1.79; `eventos_acumulados` -1.55; `eventos_14d` +1.28; `dias_ativos_acumulados` -1.24; `recencia_dias` +1.00; `capitulo_max_fase_atual` +0.84; `fase_atual` +0.84; `pct_capitulos_fase_atual` -0.67.

## 4. Modelo secundário — evasão entre fases

- Grão aluno-fase (fases 1–4): 610 linhas, 175 alunos, taxa de evasão para a fase seguinte 7.5%.
- Modelo: regressão logística (StandardScaler, `class_weight='balanced'`), validação **leave-one-phase-out** (treina em 3 transições, testa na 4ª).

| Transição testada | n | Evadiram | AUC-ROC | AUC-PR | Precisão @ top-20% |
|---|---|---|---|---|---|
| F1→F2 | 150 | 8 | 0.985 | 0.663 | 0.267 |
| F2→F3 | 154 | 8 | 0.916 | 0.574 | 0.194 |
| F3→F4 | 156 | 11 | 0.954 | 0.751 | 0.312 |
| F4→F5 | 150 | 19 | 0.850 | 0.615 | 0.433 |
| **Média** | | | **0.926** | **0.651** | |

Coeficientes padronizados (sinal positivo = aumenta a chance de não iniciar a fase seguinte), 6 maiores em módulo: `eventos_fase` -1.26; `progresso` -1.19; `recencia_fim_fase` +1.18; `dias_ativos_fase` -1.00; `atraso_inicio_dias` +0.74; `entregas` +0.59.

## 5. Interpretação honesta e limitações

- **Amostra pequena e curso único**: ~200 alunos de um só curso/instituição. As linhas aluno-semana são correlacionadas (o mesmo aluno aparece em vários cortes), então o número efetivo de observações independentes é muito menor que o número de linhas. Os intervalos de confiança das métricas são largos e o modelo **não deve ser considerado validado para outras instituições** sem re-treino.
- **Positivos fáceis**: parte do desempenho global vem de alunos que já estavam inativos há semanas (recência alta) e permaneceram inativos. A seção 3.1 mostra o desempenho no subconjunto acionável, que é o número relevante para a operação e é naturalmente mais baixo.
- **Não-estacionariedade**: a taxa de positivos varia muito ao longo do semestre (baixa em fev–abr, alta em jun–jul, com o intervalo entre F4 e F5). O período de teste (jun–ago) é estruturalmente diferente do treino (fev–mai); isso é realista para uso em produção, mas penaliza as métricas e afeta a calibração.
- **Rótulo comportamental, não administrativo**: `inativo_21d` mede silêncio no LMS, não cancelamento de matrícula. Um aluno pode ficar 3 semanas sem acessar e voltar (ex.: férias, avaliação presencial). Trata-se de um proxy operacional de risco, cuja utilidade é priorizar contato do tutor.
- **Transição de fases**: com 8–19 evasões por transição, as AUCs por fold oscilam bastante; o valor médio é indicativo, não conclusivo.
- **Sem dados socioeconômicos, notas ou histórico acadêmico**: só logs de navegação. Isso limita o teto de desempenho, mas torna a solução portátil para qualquer LMS Moodle-like.
- **Calibração**: as probabilidades do gradient boosting são razoavelmente ordenadas (AUC), mas as faixas devem ser lidas como prioridades relativas; a tabela 3.3 indica onde o modelo super/subestima.

## 6. Artefatos

- `model/modelo_risco_21d.joblib` — HGB retreinado em todo o conjunto rotulado (+ baseline logístico).
- `model/modelo_transicao_fases.joblib` — regressão logística de transição de fases.
- `model/metadados.json` — features, datas, hiperparâmetros e métricas.
- `outputs/metricas.json` — todas as métricas, curvas ROC/PR e calibração usadas nas figuras e no dashboard.
