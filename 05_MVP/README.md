# Retena — MVP analítico de risco de evasão

Pipeline reprodutível que transforma **logs brutos de um LMS** (Moodle-like) em três entregas para a operação acadêmica de uma IES:

1. **Fila semanal de risco** — para cada aluno, a probabilidade de passar **21 dias sem nenhuma ação no LMS** (`inativo_21d`), a faixa (Alto / Médio / Baixo), os fatores em linguagem simples e uma ação sugerida para o tutor.
2. **Mapa de atrito de conteúdo** — onde, fase a fase e capítulo a capítulo, os alunos travam, com recomendações de ajuste de conteúdo.
3. **Dashboard autocontido** (`dashboard/index.html`) — um único arquivo que abre por duplo clique, sem servidor nem internet, com KPIs, "Fila de segunda-feira" interativa, heatmap de atrito e a seção de transparência do modelo.

Dados de demonstração: um curso de 5 fases da "IES Demo" (jan–ago/2026), 203 alunos matriculados, ~680 mil eventos. Os resultados completos, com discussão honesta de limitações, estão em [`outputs/RESULTADOS.md`](outputs/RESULTADOS.md).

## Como rodar

```powershell
# Python >= 3.11 (validado em 3.13). Na raiz de 05_MVP:
pip install -r requirements.txt

# Pipeline completo (01 -> 06), parando na primeira etapa que falhar
python pipeline/run_all.py

# Só figuras + dashboard (reaproveita outputs já gerados)
python pipeline/run_all.py --de 05

# Uma etapa isolada
python pipeline/06_gerar_dashboard.py
```

Pré-requisito da etapa 01: o parquet bruto em `../08_Dados/logs_lms.parquet`. As demais etapas leem apenas os artefatos de `outputs/`. Os scripts resolvem caminhos a partir da própria pasta, então funcionam de qualquer diretório de trabalho.

Para abrir o dashboard: duplo clique em `dashboard/index.html`. Logo e fontes (Sora/Inter) vêm de `../../03_Marca/`; se o navegador bloquear fontes locais via `file://` (comportamento padrão do Chrome/Edge), a página cai para "Segoe UI" sem perder layout. Para capturar com Edge headless preservando as fontes da marca, use `--allow-file-access-from-files`.

## Estrutura

```
05_MVP/
├── README.md                     este arquivo
├── requirements.txt              pandas, numpy, scikit-learn, pyarrow, matplotlib, joblib
├── pipeline/
│   ├── comum.py                  caminhos, constantes do curso, classificação de eventos, faixas de risco
│   ├── 01_preparar_eventos.py    normaliza eventos brutos -> eventos_normalizados.parquet
│   ├── 02_features_semanais.py   base aluno-semana (22 features + rótulo) e base aluno-fase
│   ├── 03_treinar_modelo.py      treino/avaliação temporal; grava modelos, metricas.json e RESULTADOS.md
│   ├── 04_scoring_e_atrito.py    scoring do corte atual, KPIs, atrito de conteúdo e recomendações
│   ├── 05_gerar_figuras.py       8 PNGs (1600 px, paleta da marca) em outputs/figs/
│   ├── 06_gerar_dashboard.py     dashboard/index.html autocontido (CSS + JS + SVG + JSON inline)
│   └── run_all.py                executa 01 -> 06 em ordem
├── model/
│   ├── modelo_risco_21d.joblib          HistGradientBoosting (+ baseline logístico)
│   ├── modelo_transicao_fases.joblib    regressão logística de evasão entre fases
│   └── metadados.json                   features, hiperparâmetros, datas e métricas
├── outputs/
│   ├── eventos_normalizados.parquet     eventos com flag de atividade própria do aluno
│   ├── base_treino_semanal.parquet      aluno-semana rotulada (4.083 linhas)
│   ├── base_scoring_atual.parquet       aluno-semana do corte atual (196 alunos)
│   ├── base_transicao_fases.parquet     aluno-fase (610 linhas)
│   ├── risco_alunos_atual.csv           fila de risco: probabilidade, faixa, situação, fatores, ação
│   ├── atrito_conteudo.csv              taxa de queda, esforço relativo e índice por fase x capítulo
│   ├── recomendacoes_conteudo.csv       20 recomendações priorizadas
│   ├── kpis.json                        KPIs, funil, curva semanal, recência, top-5 de atrito
│   ├── metricas.json                    métricas, curvas ROC/PR, calibração, importâncias
│   ├── dicionario_features.md           definição de cada coluna
│   ├── RESULTADOS.md                    relatório completo de resultados e limitações
│   └── figs/                            fig_*.png + dashboard_screenshot.png + dashboard_hero_1920x1080.png
└── dashboard/
    └── index.html                       painel "Quem chamar hoje"
```

## Decisões de modelagem (resumo)

1. **Rótulo comportamental**: `inativo_21d` = nenhuma ação própria do aluno nos 21 dias após o corte semanal (domingo). É um proxy operacional de risco, não cancelamento de matrícula.
2. **Só ações do aluno contam**: lançamentos de nota, matrículas e rotinas automáticas são excluídos de features e rótulo (lista em `comum.py`).
3. **Grão aluno-semana**: 27 cortes de 01/02 a 02/08/2026; features usam apenas eventos com data ≤ corte (sem vazamento temporal).
4. **22 features de comportamento**: volume e dias ativos em 7/14/28 dias, recência, tendência, progresso na fase, questionários, entregas, hábitos (noite / fim de semana) e acumulados.
5. **Split temporal com embargo**: treino em cortes < 01/06 (descartando os 2 cortes cuja janela de rótulo invadiria o teste), teste em jun–ago/2026. Hiperparâmetros por validação temporal interna, critério AUC-PR.
6. **Modelo**: HistGradientBoosting; regressão logística como baseline. Com ~200 alunos a diferença entre eles não é significativa; o HGB foi mantido pela flexibilidade para novas features.
7. **Retreino final** no conjunto rotulado completo; é esse artefato que faz o scoring do corte atual (23/08/2026).
8. **Faixas fixadas a priori**: Alto ≥ 0,60 (vale ação humana), Médio 0,30–0,60 (intervenção automática barata), Baixo < 0,30.
9. **Subconjunto acionável** reportado separadamente (alunos com evento nos 28 dias anteriores): é o número relevante para a operação, e é naturalmente mais baixo.
10. **Modelo secundário de transição entre fases** (regressão logística, leave-one-phase-out) e **índice de atrito** = taxa de queda × esforço relativo, por capítulo.

Números principais no teste temporal: AUC-ROC 0,882, AUC-PR 0,839, precisão@top-20% 0,882 (lift 3,06×); no subconjunto acionável, AUC-ROC 0,743 e AUC-PR 0,460. Faixa Alto com 95,2% de inatividade observada; Baixo com 14,3%.

## Limitações

- **Amostra pequena e curso único** (~200 alunos, uma IES); linhas aluno-semana correlacionadas. Intervalos de confiança largos; não validado para outras instituições sem re-treino.
- **Positivos fáceis** inflam as métricas globais (quem já sumiu continua sumido). Leia o subconjunto acionável.
- **Não-estacionariedade**: a taxa de inatividade varia de 10% a 40% ao longo do semestre; o teste (jun–ago) é estruturalmente diferente do treino (fev–mai), o que afeta calibração.
- **Rótulo é silêncio no LMS**, não evasão administrativa: férias e avaliações presenciais geram falsos positivos.
- **Só logs de navegação** — sem notas, dados socioeconômicos ou histórico acadêmico. Limita o teto, mas torna a solução portátil.
- **Cores da marca** (verde / amarelo / coral) têm contraste baixo sobre branco; por isso toda cor de status no dashboard e nas figuras vem acompanhada de rótulo textual.

Detalhes, tabelas por corte e discussão completa: [`outputs/RESULTADOS.md`](outputs/RESULTADOS.md).

## Benchmark de modelos (v2)

Comparação adicional em `outputs/benchmark_modelos.md` (script `pipeline/07_benchmark_modelos.py`, figura `outputs/figs/fig_benchmark_modelos.png`), no mesmo split temporal com embargo e nas mesmas 22 features do modelo entregue; o HGB de referência reproduz AUC-ROC 0,882. Configurações de LR (liblinear L1 balanced), XGBoost (scale_pos_weight) e GradientBoosting adaptadas do EduRetain (equipe Retena).
Por AUC-PR vence a regressão logística baseline já reportada no `03` (0,859 vs. 0,839 no teste completo; 0,494 vs. 0,460 no acionável) — diferença pequena, dentro da incerteza amostral de ~200 alunos.
Por F2@0,5 vencem os modelos reponderados (LR balanced 0,766; LR EduRetain 0,759; HGB 0,626): efeito de limiar, não de ranqueamento — em AUC-PR ficam iguais ou abaixo das versões não balanceadas, e o HGB em limiar 0,3 (faixa Médio) sobe para F2 0,643.
Nenhuma configuração do EduRetain supera o baseline logístico atual; XGBoost (AUC-PR 0,818) e GradientBoosting padrão (0,739) ficam abaixo do HGB (0,839).
O HGB permanece o modelo entregue (reprodução exata, melhor precisão@0,5 = 0,924, rastreabilidade de `metadados.json`/`metricas.json`/figuras/dashboard); nenhum artefato já entregue foi alterado.

## Portabilidade: OULAD (v2)

O método Retena foi reaplicado, sem alterar arquitetura nem hiperparâmetros, ao OULAD (Open University, UK: 7 módulos, 22 apresentações, 32.593 matrículas, 10,66 mi cliques) — scripts, métricas e figura em `portabilidade_oulad/` (`preparar_oulad.py`, `treinar_oulad.py`, `metricas_oulad.json`, `figs/fig_oulad_roc_pr.png`, relatório `RESULTADOS_OULAD.md`); dados brutos e parquets ficam fora da entrega.
Base aluno-semana de 730.673 linhas (24.392 alunos, cortes semanais do dia 28 ao 245), rótulo `inativo_21d` com 21,0% de positivos; split temporal por apresentação (treino 2013B+2013J, teste 2014B+2014J com 14.293 alunos).
HGB no teste: AUC-ROC 0,922, AUC-PR 0,813, lift 3,51× no top-20% (IES Demo: 0,882 / 0,839 / 3,06×); no subconjunto acionável, AUC-ROC 0,853 e AUC-PR 0,418 (IES Demo: 0,743 / 0,460); mesmas features dominantes (dias ativos em 28 dias, recência, regularidade) e faixas 0,60/0,30 com 85% vs 6% de inatividade observada.
Rótulo administrativo `evadiu_28d` (2,6% de positivos) é bem mais difícil: AUC-ROC 0,730, lift 2,4× — reforça a escolha do rótulo comportamental como gatilho operacional.
Setup EduRetain reproduzido no mesmo OULAD (alvo `Withdrawn`, features até o dia 30): split aleatório infla a AUC-ROC em +0,024 (LR) / +0,014 (HGB) frente ao split temporal; excluindo os 15,7% de alunos já desmatriculados até o dia 30 (99,8% deles `Withdrawn`), a AUC-ROC cai de 0,79–0,82 para 0,66–0,69 — recomenda-se reportar esse recorte junto do número global.
