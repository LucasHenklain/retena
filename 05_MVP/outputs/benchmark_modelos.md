# Benchmark de modelos (v2) — risco de inatividade em 21 dias

Gerado em 2026-09-09 09:37 por `pipeline/07_benchmark_modelos.py` (Python 3.13.1, scikit-learn 1.9.0, xgboost 3.4.1). Configurações (c), (d) e (e) adaptadas do EduRetain (equipe Retena). **Este benchmark não altera o modelo entregue** (`model/modelo_risco_21d.joblib`) nem os resultados de `RESULTADOS.md`; é uma leitura comparativa adicional.

## 1. Protocolo (idêntico ao `03_treinar_modelo.py`)

- Split: treino: cortes < 2026-06-01 (com embargo de 21 dias); teste: cortes ≥ 2026-06-01.
- Treino: 2.126 linhas. 16 cortes (2026-02-01 → 2026-05-17). 167 alunos. positivos 10.1%.
- Embargo (cortes descartados): 2026-05-24, 2026-05-31.
- Teste: 1.609 linhas. 9 cortes (2026-06-07 → 2026-08-02). 183 alunos. positivos 28.8%.
- Subconjunto acionável: eventos_28d > 0 no corte — n=1298, positivos=191.
- Mesmas 22 features de `metadados.json`; nenhum modelo foi tunado no teste. Limiar fixo 0,5 para recall/precisão/F1/F2; top-20% com k=⌈0,2·n⌉.
- Reprodução do HGB entregue: AUC-ROC obtida 0,882 vs. referência 0,882 (±0.005) → **OK**.

## 2. Modelos comparados

- **HGB (referência entregue)** — HistGradientBoostingClassifier com os hiperparâmetros de model/metadados.json; sem reamostragem/pesos.
- **LR baseline atual (03)** — StandardScaler + LogisticRegression(C=1, lbfgs), exatamente como novo_lr() do 03 — sem class_weight.
- **LR baseline + balanced** — Variante extra: mesmo baseline com class_weight='balanced' (isola o efeito do balanceamento).
- **LR EduRetain (L1 liblinear balanced)** — SimpleImputer(mediana) + StandardScaler + LR liblinear L1 balanced C=1 — adaptado do EduRetain (equipe Retena). A base não tem NaN, então o imputer é no-op.
- **XGBoost (config EduRetain)** — XGBClassifier com scale_pos_weight=8.888 (neg/pos do treino), subsample 0.8, 200 árvores, depth 6, lr 0.01, colsample 0.7 — adaptado do EduRetain (equipe Retena).
- **GradientBoosting (padrão sklearn)** — GradientBoostingClassifier(random_state=42) com defaults (100 árvores, depth 3, lr 0.1) — adaptado do EduRetain (equipe Retena).

## 3. Métricas no teste — conjunto completo (n=1609, positivos 28.8%)

| Modelo | AUC-ROC | AUC-PR | P@top-20% | Recall@0,5 | Prec.@0,5 | F1 | F2 | Brier ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HGB (referência entregue) | 0,882 | 0,839 | 0,882 | 0,580 | **0,924** | 0,713 | 0,626 | 0,120 |
| LR baseline atual (03) | **0,893** | **0,859** | **0,919** | 0,659 | 0,895 | **0,759** | 0,696 | **0,101** |
| LR baseline + balanced | 0,889 | 0,855 | 0,904 | **0,784** | 0,699 | 0,739 | **0,766** | 0,126 |
| LR EduRetain (L1 liblinear balanced) | 0,882 | 0,850 | 0,904 | 0,767 | 0,727 | 0,746 | 0,759 | 0,123 |
| XGBoost (config EduRetain) | 0,874 | 0,818 | 0,866 | 0,539 | 0,899 | 0,674 | 0,586 | 0,109 |
| GradientBoosting (padrão sklearn) | 0,811 | 0,739 | 0,764 | 0,498 | 0,856 | 0,629 | 0,543 | 0,147 |

## 4. Métricas no teste — subconjunto acionável (n=1298, positivos 14.7%)

| Modelo | AUC-ROC | AUC-PR | P@top-20% | Recall@0,5 | Prec.@0,5 | F1 | F2 | Brier ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HGB (referência entregue) | 0,743 | 0,460 | 0,377 | 0,178 | 0,694 | 0,283 | 0,209 | 0,120 |
| LR baseline atual (03) | **0,772** | **0,494** | **0,396** | 0,199 | **0,704** | 0,310 | 0,232 | 0,110 |
| LR baseline + balanced | 0,765 | 0,475 | 0,388 | **0,492** | 0,418 | **0,452** | **0,475** | 0,135 |
| LR EduRetain (L1 liblinear balanced) | 0,745 | 0,461 | 0,373 | 0,455 | 0,437 | 0,446 | 0,452 | 0,135 |
| XGBoost (config EduRetain) | 0,737 | 0,442 | 0,350 | 0,220 | 0,667 | 0,331 | 0,254 | **0,106** |
| GradientBoosting (padrão sklearn) | 0,681 | 0,287 | 0,285 | 0,147 | 0,452 | 0,221 | 0,169 | 0,133 |

## 5. Leitura honesta

- **Por F2 (critério de seleção do EduRetain)**: vence **LR baseline + balanced** no completo (0,766) e **LR baseline + balanced** no acionável (0,475). HGB: 0,626 / 0,209.
- **Por AUC-PR (critério do Retena)**: vence **LR baseline atual (03)** no completo (0,859) e **LR baseline atual (03)** no acionável (0,494). HGB: 0,839 / 0,460.
- **Melhor Brier (calibração)**: LR baseline atual (03) (0,101) no completo; XGBoost (config EduRetain) (0,106) no acionável.

**O que os números dizem:**

1. **Nenhuma configuração do EduRetain supera o baseline logístico que já estava no `03`.** A LR do EduRetain (L1, balanced) fica em AUC-PR 0,850 (completo) / 0,461 (acionável) contra 0,859 / 0,494 do baseline atual; o XGBoost com a config do EduRetain (0,818 / 0,442) fica abaixo do HGB (0,839 / 0,460) e o GradientBoosting padrão é o pior do grupo (0,739 / 0,287). Essas configs foram desenhadas para outro dataset (OULAD, com features cadastrais e ~20 mil linhas); aqui, com 2.126 linhas de treino, a taxa de aprendizado 0,01 com 200 árvores e profundidade 6 do XGBoost não converge para o mesmo nível dos modelos rasos.
2. **A vantagem em F2 é efeito de limiar, não de ranqueamento.** Os três modelos com `class_weight='balanced'`/`scale_pos_weight` ganham F2@0,5 porque inflacionam as probabilidades e cruzam o limiar 0,5 com mais frequência (recall@0,5 de 0,784 na LR balanced vs. 0,580 no HGB), mas suas métricas de ordenação (AUC-ROC / AUC-PR) são iguais ou **piores** que as versões não balanceadas (LR balanced AUC-PR 0,855 vs. LR baseline 0,859). Movendo o limiar do HGB para 0,3 — a fronteira da faixa "Médio", fixada a priori no README — o F2 do HGB vai de 0,626 para 0,643 (acionável: 0,209 → 0,236), sem re-treinar nada. Comparar F2 em limiar fixo 0,5 entre modelos com e sem reponderação, como faz a seleção do EduRetain, favorece mecanicamente os reponderados; o Retena já usa faixas (0,3 / 0,6) justamente para separar a qualidade do ranking da decisão operacional.
3. **Se o critério fosse estritamente AUC-PR ou F2, a regressão logística venceria — por margem pequena e já conhecida.** A diferença HGB → LR baseline é de 0,020 em AUC-PR no completo e 0,034 no acionável; isso já está registrado em `RESULTADOS.md` (seção 3) e no README (decisão 6). Com ~200 alunos e linhas aluno-semana correlacionadas, essa diferença está dentro da incerteza amostral e não é um achado novo trazido pelas configs do EduRetain. Não há vencedor "com folga": o melhor AUC-PR acionável do benchmark (0,494) e o do HGB (0,460) distam 0,034.
4. **Por que o HGB permanece o modelo entregue.** (i) Reproduz exatamente o que foi reportado (AUC-ROC 0,882); (ii) tem a melhor precisão@0,5 do grupo (0,924 completo) — no desenho operacional do Retena, a faixa Alto exige ação humana e falso-positivo custa tempo de tutor; (iii) lida nativamente com interações e novas features sem re-escalonamento, motivo original da escolha; (iv) trocar o artefato por um ganho não significativo quebraria a rastreabilidade entre `metadados.json`, `metricas.json`, figuras e dashboard já entregues. O que este benchmark **acrescenta** de acionável é a evidência de que o limiar 0,3 (faixa Médio) recupera o recall que os modelos balanceados obtêm com reponderação — reforçando a política de faixas em vez de um limiar único.

**Limitações deste benchmark:** um único split temporal (sem intervalos de confiança); métricas em limiar fixo dependem da calibração de cada modelo; nenhum candidato foi tunado (as configs do EduRetain foram usadas como vieram, adaptadas para 22 features numéricas sem categorias). Um teste pareado por corte (9 cortes de teste) ou bootstrap por aluno seria o próximo passo para afirmar significância.

## 6. Artefatos

- `outputs/benchmark_modelos.json` — todas as métricas, split, versões e vencedores por critério.
- `outputs/figs/fig_benchmark_modelos.png` — AUC-PR e F2 por modelo (completo × acionável).
- `pipeline/07_benchmark_modelos.py` — script reprodutível (`python pipeline/07_benchmark_modelos.py`).
