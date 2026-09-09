# Portabilidade do método Retena — OULAD (Open University Learning Analytics Dataset)

Pergunta: o método do MVP Retena (base aluno-semana a partir de logs do LMS, rótulo `inativo_21d`, HistGradientBoosting com split temporal) **funciona em outra instituição, sem mudar arquitetura nem hiperparâmetros?** Para responder, o pipeline foi reimplementado sobre o OULAD — dataset público da Open University (Reino Unido) com 7 módulos, 22 apresentações (2013B, 2013J, 2014B, 2014J), 32.593 matrículas e 10,66 milhões de linhas de cliques no VLE.

Todos os números abaixo vêm de `preparar_oulad.py` e `treinar_oulad.py` (saída em `metricas_oulad.json` e `resumo_preparacao.txt`); nada foi digitado à mão. Ambiente: Python 3.13.1, scikit-learn 1.9.0, pandas 2.3.2, Windows 11.

## 1. Dados e base construída

| Item | Valor |
|---|---|
| Fonte | `oulad_uci.zip` (espelho UCI, 46,7 MB); `studentVle.csv` = 453,8 MB, 10.655.280 linhas |
| Agregação aluno × módulo × apresentação × dia | 1.808.119 linhas (parquet de 5,3 MB, fora da entrega) |
| Cortes | t = 28, 35, …, ≤ duração − 21 dias, por apresentação (32 valores de corte, dia 28 ao 245) |
| Filtro por corte | registro ativo em t (`date_unregistration` nula ou > t; `date_registration` ≤ t) **e** ≥ 1 clique até t (mesmo critério do Retena) |
| Excluídos (aluno-corte) | 239.096 sem registro ativo; 14.657 registrados que nunca clicaram até t |
| **Base aluno-semana** | **730.673 linhas, 24.392 alunos distintos, 27.018 matrículas** (parquet de 12,1 MB, fora da entrega) |
| Rótulo principal `inativo_21d` (zero cliques em (t, t+21]) | 21,0% de positivos |
| Rótulo secundário `evadiu_28d` (`date_unregistration` em (t, t+28]) | 2,5% de positivos |
| Subconjunto acionável (cliques nos 28 dias anteriores > 0) | 85,5% das linhas; `inativo_21d` = 10,5% |
| Tempo de `preparar_oulad.py` | 16,7 s (leitura do CSV de 454 MB: 2,4 s; construção da base: ~10 s) |

Features (15), análogas às do Retena e calculadas só com dados de data ≤ t: `cliques_7d/14d/28d`, `dias_ativos_7d/14d/28d`, `recencia_dias`, `cliques_acumulados`, `dias_ativos_acumulados`, `tendencia` (= cliques_7d ÷ (cliques_28d/4 + 1)), `semanas_ativas_ultimas_8`, `entregas_ate_t` e `entregas_28d` (studentAssessment, análogo de "quiz entregue"), `semanas_desde_primeiro_clique`, `dia_corte`. Não têm análogo no OULAD (sem hora do dia nem capítulo): `share_noite`, `share_fim_semana`, `progresso`, `capitulo_*`.

Taxa de `inativo_21d` por apresentação: 2013B 20,0% · 2013J 22,2% · 2014B 23,3% · 2014J 19,0%. Por módulo vai de 9,1% (AAA-2013J) a 29,7% (GGG-2014J). Por corte, sobe de 9,2% (dia 28) para 26–27% no meio do curso e 48,9% no último corte (dia 245), quando o curso está terminando.

## 2. Protocolo

- **Split temporal por apresentação**: treino = 2013B + 2013J (317.601 linhas, 11.438 alunos, 21,5% positivos); teste = 2014B + 2014J (413.072 linhas, 14.293 alunos, 20,6% positivos). Nenhum aluno-corte de 2014 entra no treino.
- **Modelos idênticos ao Retena**: HistGradientBoosting com `learning_rate 0.05, max_iter 300, max_leaf_nodes 8, min_samples_leaf 40, l2_regularization 2.0` (sem nenhum reajuste para o OULAD) e regressão logística `class_weight='balanced'` com StandardScaler. Tempo de treino: HGB 6,8 s, LR 0,7 s.
- Métricas no teste completo e no subconjunto acionável; top-20% = os 20% de maior probabilidade prevista.

## 3. Resultados — método Retena no OULAD

### 3.1 Rótulo principal `inativo_21d` (teste 2014B + 2014J)

| Métrica | Completo — HGB | Completo — LR | Acionável — HGB | Acionável — LR |
|---|---|---|---|---|
| n / positivos | 413.072 / 85.310 (20,6%) | idem | 354.715 / 37.508 (10,6%) | idem |
| AUC-ROC | **0,922** | 0,912 | **0,853** | 0,833 |
| AUC-PR | **0,813** | 0,795 | **0,418** | 0,365 |
| Brier | 0,080 | 0,120 | 0,076 | 0,116 |
| Precisão @ top-20% (k = 82.614 / 70.943) | 0,724 | 0,708 | 0,342 | 0,322 |
| Recall capturado no top-20% | 0,701 | 0,686 | 0,647 | 0,609 |
| Lift @ top-20% | **3,51×** | 3,43× | **3,23×** | 3,04× |

Figura: `figs/fig_oulad_roc_pr.png` (ROC e Precisão-Recall, completo e acionável).

### 3.2 Comparação direta com o Retena na IES Demo

| | IES Demo (`outputs/RESULTADOS.md`) | OULAD (este estudo) |
|---|---|---|
| Alunos no teste / linhas | 183 / 1.609 | 14.293 / 413.072 |
| Taxa de positivos no teste | 28,8% | 20,6% |
| AUC-ROC (HGB) | 0,882 | 0,922 |
| AUC-PR (HGB) | 0,839 | 0,813 |
| Lift @ top-20% (HGB) | 3,06× | 3,51× |
| Acionável: AUC-ROC / AUC-PR (HGB) | 0,743 / 0,460 (base 14,7%) | 0,853 / 0,418 (base 10,6%) |
| Acionável: lift @ top-20% | 2,56× | 3,23× |
| Faixa Alto (≥ 0,60): % linhas / taxa observada | 17,0% / 95,2% | 14,1% / 85,0% |
| Faixa Médio (0,30–0,60) | 2,4% / 48,7% | 10,4% / 37,1% |
| Faixa Baixo (< 0,30) | 80,6% / 14,3% | 75,5% / 6,4% |
| HGB vs. LR | LR ligeiramente melhor (diferença dentro do ruído de 200 alunos) | HGB melhor em todas as métricas (0,922 vs 0,912; 0,418 vs 0,365 no acionável) |

Leitura: com as **mesmas features conceituais e os mesmos hiperparâmetros**, o ranqueamento (AUC-ROC, lift) ficou igual ou melhor no OULAD; a AUC-PR e a precisão@top-20% ficaram um pouco menores porque a taxa de positivos é menor (20,6% vs 28,8%; 10,6% vs 14,7% no acionável) — o lift, que corrige pela base, subiu nos dois recortes. As faixas de risco fixadas a priori no Retena (0,60 / 0,30) continuam separando bem: 85% de inatividade observada no Alto contra 6% no Baixo.

### 3.3 Estabilidade (HGB, `inativo_21d`)

Por módulo-apresentação de teste (14 grupos): AUC-ROC entre 0,858 (GGG-2014J) e 0,954 (FFF-2014B); AUC-PR entre 0,630 (AAA-2014J, base 12,1%) e 0,882 (FFF-2014B).

| Apresentação / módulo | n | Positivos | AUC-ROC HGB | AUC-PR HGB | AUC-ROC LR | AUC-PR LR |
|---|---|---|---|---|---|---|
| 2014B (todos os módulos) | 157.754 | 23,3% | 0,927 | 0,843 | 0,924 | 0,833 |
| 2014J (todos os módulos) | 255.318 | 19,0% | 0,917 | 0,789 | 0,903 | 0,764 |
| AAA-2014J | 10.419 | 12,1% | 0,900 | 0,630 | 0,872 | 0,580 |
| BBB-2014B / 2014J | 31.286 / 50.418 | 24,9% / 23,8% | 0,899 / 0,886 | 0,808 / 0,759 | 0,895 / 0,866 | 0,797 / 0,733 |
| CCC-2014B / 2014J | 33.808 / 52.541 | 21,7% / 17,4% | 0,931 / 0,906 | 0,848 / 0,768 | 0,930 / 0,896 | 0,844 / 0,752 |
| DDD-2014B / 2014J | 24.483 / 40.009 | 22,2% / 15,6% | 0,949 / 0,929 | 0,880 / 0,797 | 0,946 / 0,926 | 0,873 / 0,789 |
| EEE-2014B / 2014J | 15.347 / 29.446 | 22,1% / 17,6% | 0,940 / 0,932 | 0,867 / 0,825 | 0,933 / 0,915 | 0,851 / 0,792 |
| FFF-2014B / 2014J | 32.234 / 52.396 | 21,8% / 16,7% | 0,954 / 0,951 | 0,882 / 0,852 | 0,949 / 0,939 | 0,869 / 0,830 |
| GGG-2014B / 2014J | 20.596 / 20.089 | 28,2% / 29,7% | 0,871 / 0,858 | 0,776 / 0,760 | 0,872 / 0,819 | 0,773 / 0,714 |

Por corte (32 cortes de teste): AUC-ROC entre 0,850 e 0,949, AUC-PR entre 0,489 e 0,889. Como no Retena, o começo do curso é o período mais difícil (dia 28: 9,6% de positivos, AUC-PR 0,489) e a AUC-PR cresce com a taxa de positivos (dia 196: 24,8%, AUC-PR 0,887). O módulo CCC só existe em 2014, isto é, o modelo o pontuou sem nunca ter visto o módulo — AUC-ROC 0,931 / 0,906.

| Corte (dia) | n | Positivos | AUC-ROC | AUC-PR |
|---|---|---|---|---|
| 28 | 15.255 | 9,6% | 0,885 | 0,489 |
| 56 | 14.783 | 15,6% | 0,893 | 0,641 |
| 84 | 14.327 | 17,8% | 0,901 | 0,740 |
| 112 | 13.917 | 19,4% | 0,930 | 0,805 |
| 140 | 13.550 | 20,2% | 0,946 | 0,863 |
| 168 | 13.098 | 27,6% | 0,931 | 0,869 |
| 196 | 12.832 | 24,8% | 0,946 | 0,887 |
| 224 | 7.489 | 21,3% | 0,947 | 0,885 |
| 245 | 4.735 | 47,6% | 0,850 | 0,856 |

### 3.4 Calibração e faixas (HGB, teste)

| Bin de probabilidade | n | Prob. média | Taxa observada |
|---|---|---|---|
| 0,0–0,1 | 234.939 | 0,029 | 2,8% |
| 0,1–0,2 | 49.306 | 0,143 | 13,7% |
| 0,2–0,3 | 27.676 | 0,246 | 23,4% |
| 0,3–0,4 | 18.301 | 0,347 | 30,6% |
| 0,4–0,5 | 13.779 | 0,448 | 38,8% |
| 0,5–0,6 | 10.697 | 0,548 | 46,3% |
| 0,6–0,7 | 9.070 | 0,649 | 57,4% |
| 0,7–0,8 | 7.375 | 0,749 | 69,2% |
| 0,8–0,9 | 8.392 | 0,854 | 82,8% |
| 0,9–1,0 | 33.537 | 0,968 | 96,4% |

Com 400 mil linhas a calibração é quase diagonal (o HGB superestima levemente entre 0,4 e 0,8) — na IES Demo os bins intermediários oscilavam por terem 10–30 observações. Faixas: Alto 58.374 linhas (14,1%) com 85,0% de inatividade observada; Médio 42.777 (10,4%) com 37,1%; Baixo 311.921 (75,5%) com 6,4%.

### 3.5 O que o modelo usa (importância por permutação, HGB, AUC-ROC, amostra de 100.000 linhas de teste, 5 repetições)

| # | Feature | Queda de AUC | DP | # | Feature | Queda de AUC | DP |
|---|---|---|---|---|---|---|---|
| 1 | `dias_ativos_28d` | 0,0510 | 0,0010 | 6 | `dias_ativos_acumulados` | 0,0018 | 0,0001 |
| 2 | `recencia_dias` | 0,0275 | 0,0001 | 7 | `entregas_28d` | 0,0016 | 0,0001 |
| 3 | `semanas_ativas_ultimas_8` | 0,0149 | 0,0003 | 8 | `cliques_7d` | 0,0006 | 0,0001 |
| 4 | `dia_corte` | 0,0133 | 0,0003 | 9 | `cliques_acumulados` | 0,0005 | 0,0001 |
| 5 | `entregas_ate_t` | 0,0049 | 0,0003 | 10 | `cliques_14d` | 0,0005 | 0,0000 |

Coeficientes padronizados da LR (positivo = mais risco), 6 maiores em módulo: `dias_ativos_28d` −1,15; `recencia_dias` +1,14; `semanas_ativas_ultimas_8` −0,58; `dias_ativos_7d` −0,48; `dia_corte` +0,40; `dias_ativos_acumulados` −0,29.

Mesma conclusão da IES Demo: **dias ativos e recência valem mais do que volume de cliques**. No Retena as quatro features mais importantes eram `dias_ativos_acumulados`, `dias_ativos_28d`, `eventos_acumulados` e `recencia_dias`; no OULAD, `dias_ativos_28d` e `recencia_dias` lideram, e `semanas_ativas_ultimas_8` (regularidade) entra em terceiro. O sinal dos coeficientes é o mesmo nas duas bases.

### 3.6 Rótulo secundário `evadiu_28d` (desmatrícula administrativa em (t, t+28])

| Métrica | Completo — HGB | Completo — LR | Acionável — HGB | Acionável — LR |
|---|---|---|---|---|
| n / positivos | 413.072 / 10.824 (2,6%) | idem | 354.715 / 8.303 (2,3%) | idem |
| AUC-ROC | 0,730 | 0,718 | 0,732 | 0,722 |
| AUC-PR | 0,065 | 0,061 | 0,062 | 0,059 |
| Precisão @ top-20% | 0,063 | 0,061 | 0,057 | 0,056 |
| Recall capturado no top-20% | 0,484 | 0,464 | 0,491 | 0,481 |
| Lift @ top-20% | 2,42× | 2,32× | 2,45× | 2,40× |

Leitura honesta: prever **quando** o aluno formaliza a desmatrícula (janela de 4 semanas) é muito mais difícil do que prever o silêncio no LMS — o comportamento antecede a decisão administrativa por tempo variável. O modelo ainda concentra metade das desmatrículas no quintil de maior risco (lift 2,4×), mas com precisão de 6% não sustenta uma fila operacional sozinho. Isso reforça a escolha do Retena pelo rótulo comportamental como gatilho de ação; a desmatrícula é o desfecho que se quer evitar, não o alvo que se consegue prever com precisão semana a semana.

## 4. Comparação com o setup EduRetain (colega de equipe) — reproduzido no mesmo OULAD

Setup reproduzido de `eduretain/feature_engineering.py` e `model.py`: alvo `final_result == 'Withdrawn'` (uma linha por matrícula, 32.593; 31,2% positivos); features até o dia 30 — `vle_total_clicks`, `vle_active_days`, `vle_max_clicks_single_day` (máximo por dia, após agregação diária), `vle_clicks_per_active_day`, `assess_avg_score`, `assess_submitted_count`, `assess_total_days_late` — mais os campos de cadastro usados pelo EduRetain (`num_of_prev_attempts`, `studied_credits`, `highest_education`, `age_band`, `gender`, `disability`, `code_module`), com o mesmo pré-processamento (mediana + StandardScaler; ordinal; one-hot `drop='first', handle_unknown='ignore'`). Modelos: LR liblinear L1 balanced C=1 (EduRetain) e o HGB do Retena. Tempo por ajuste: 0,2–0,6 s.

| Cenário | n treino | n teste | Taxa positivos | Modelo | AUC-ROC | AUC-PR | Precisão @ top-20% | Lift |
|---|---|---|---|---|---|---|---|---|
| (a) aleatório 80/20 estratificado (como o EduRetain) | 26.074 | 6.519 | 31,2% | LR EduRetain | 0,814 | 0,714 | 0,780 | 2,50× |
| (a) idem | 26.074 | 6.519 | 31,2% | HGB Retena | 0,834 | 0,748 | 0,807 | 2,59× |
| (b) temporal 2013 → 2014 | 13.529 | 19.064 | 33,8% | LR EduRetain | 0,790 | 0,700 | 0,772 | 2,29× |
| (b) idem | 13.529 | 19.064 | 33,8% | HGB Retena | 0,821 | 0,754 | 0,828 | 2,45× |
| (c) temporal, teste sem quem já se desmatriculou até o dia 30 | 13.529 | 15.700 | 19,6% | LR EduRetain | 0,659 | 0,315 | 0,334 | 1,70× |
| (c) idem | 13.529 | 15.700 | 19,6% | HGB Retena | 0,692 | 0,336 | 0,376 | 1,92× |

**Inflação do split aleatório, (a) − (b)**: LR EduRetain +0,024 em AUC-ROC e +0,013 em AUC-PR; HGB +0,014 em AUC-ROC e −0,007 em AUC-PR. É uma inflação real mas modesta: o OULAD tem apresentações muito parecidas entre anos, então o vazamento entre alunos do mesmo período custa pouco. No split temporal, o módulo CCC (só em 2014) aparece como categoria desconhecida — o `handle_unknown='ignore'` do EduRetain absorve isso corretamente.

**O ponto mais importante é outro**: 5.127 das 32.593 matrículas (15,7%) têm `date_unregistration ≤ 30`, e 99,8% delas terminam como `Withdrawn`. No corte do dia 30 esses alunos **já saíram** — zero cliques, zero entregas — e o modelo os acerta trivialmente. Retirando-os do teste (cenário c), o desempenho do setup EduRetain cai para AUC-ROC 0,66–0,69 e AUC-PR 0,32–0,34 (base 19,6%). É o análogo direto do "subconjunto acionável" do Retena: o que sobra é o desempenho sobre quem ainda pode ser retido. Recomendação para o pipeline EduRetain: (i) excluir do treino/avaliação as matrículas com `date_unregistration ≤ cutoff_days`, ou (ii) tratar o desfecho como censurado — e reportar o número correspondente ao cenário (c) ao lado do número global.

Contraste com o método Retena no mesmo dataset e mesmo split temporal: 0,853 de AUC-ROC no subconjunto acionável (vs 0,69 no cenário c). Não são o mesmo alvo — `inativo_21d` a cada semana vs `Withdrawn` ao fim do curso a partir do dia 30 —, mas mostram que **o grão semanal com features de recência e regularidade carrega muito mais sinal acionável do que uma fotografia única do dia 30**.

## 5. O que se mantém, o que muda

**Mantém-se**: (1) o HGB com os hiperparâmetros do Retena funciona sem retreino de arquitetura — AUC-ROC 0,922 e lift 3,5× em outra instituição, outro país, outro LMS; (2) as mesmas features dominam (dias ativos em 28 dias, recência, regularidade semanal); (3) as faixas 0,60 / 0,30 continuam separando risco (85% vs 6%); (4) o padrão "começo do curso é mais difícil, AUC-PR cresce com a taxa de positivos" se repete; (5) o subconjunto acionável é sempre o número mais baixo e o mais relevante.

**Muda**: (1) com 400 mil linhas, o HGB passa a vencer a regressão logística de forma consistente (na IES Demo a diferença estava dentro do ruído); (2) sem hora do dia e capítulo, perdem-se `share_noite`, `share_fim_semana` e progresso — e mesmo assim a AUC-ROC subiu, sinal de que as features de regularidade carregam o essencial; (3) a calibração fica quase diagonal, o que permite usar as probabilidades de forma mais literal do que na IES Demo; (4) a taxa de positivos é menor (20,6% vs 28,8%), o que reduz AUC-PR e precisão@top-20% em termos absolutos mesmo com ranqueamento melhor.

## 6. Limitações

- **Tempo relativo, não calendário**: o OULAD conta dias desde o início da apresentação; feriados, férias e sazonalidade real não são observáveis. O `dia_corte` compensa em parte (4ª feature mais importante) porque as apresentações têm estrutura parecida.
- **Fim de curso**: nos últimos cortes (dias 238–245) a taxa de inatividade sobe para 41–49% porque alunos terminam as atividades e param de clicar — inatividade que não é risco. Numa operação, os cortes finais devem ser tratados com regra própria (como no Retena, que só pontua até o fim do conteúdo).
- **Linhas correlacionadas**: cada matrícula aparece em até 32 cortes; o n efetivo é da ordem de 15 mil matrículas de teste, não 413 mil linhas. Ainda assim é ~80× a IES Demo.
- **Só 2 "anos" para split temporal**: treino em 2013, teste em 2014; não é possível medir deriva de longo prazo.
- **Sem dados socioeconômicos no método Retena** (por decisão de portabilidade); o OULAD os tem, e o setup EduRetain os usa. Não foram adicionados ao modelo Retena para manter a comparação honesta com a IES Demo.
- **`evadiu_28d`**: rótulo raro (2,6%) e de timing incerto; AUC-PR 0,065 deve ser lido como "ranqueamento útil, precisão baixa", não como falha do método.
- **Comparação com EduRetain**: o alvo e o grão são diferentes por construção; a comparação vale para o *protocolo de avaliação* (split, exclusão de já-desmatriculados), não para dizer que um modelo "é melhor" que o outro no mesmo alvo.

## 7. Frase-síntese para o pitch

> "O mesmo método, sem mudar arquitetura nem hiperparâmetros, treinado em 11,4 mil alunos de 2013 e testado em 14,3 mil alunos de 2014 da Open University (outro país, outro LMS), alcançou AUC-ROC 0,92 e concentrou 70% dos alunos que ficariam 3 semanas inativos nos 20% de maior risco — lift 3,5×, o mesmo padrão dos 0,88 e 3,1× medidos na IES Demo."

## 8. Reprodução

```powershell
# Descompactar o OULAD fora da entrega (7 CSVs) e apontar as variáveis:
$env:OULAD_RAW_DIR  = "<pasta com os CSVs>"
$env:OULAD_WORK_DIR = "<pasta de trabalho para os parquets>"
python preparar_oulad.py     # ~17 s  -> parquets no OULAD_WORK_DIR + resumo_preparacao.txt
python treinar_oulad.py      # ~93 s  -> metricas_oulad.json + figs/fig_oulad_roc_pr.png (63 s são da importância por permutação)
```

Tempo total de execução (preparação + treino): **~110 s** em um notebook Windows; pico de memória na preparação ~0,6 GB (matrizes matrícula × dia, 257 MB de acumulados).
