# Parecer interno — EduRetain × pacote Retena (Fase 6)

> Avaliação feita contra o enunciado da Fase 6 (Partes 1–4 + entregáveis) e os critérios da Banca Final. Uso interno da equipe.

## Veredito

O pacote Retena atende a atividade; o EduRetain, sozinho, não. O EduRetain é um bom componente de engenharia (equivale a parte da Parte 4) e deve ser **absorvido** pelo Retena, não competir com ele.

## Comparação por item do enunciado

| Item exigido | Retena | EduRetain | Observação |
|---|---|---|---|
| Parte 1: problema, persona, justificativa | Completa | Ausente | README descreve um pipeline, não um problema de negócio. |
| Parte 2: validação, aprendizados, rich picture/stakeholders, ajustes | Completa (entrevistas rotuladas como simuladas; H1–H6) | Ausente | Sem validação, sem stakeholders, sem diagramas. |
| Parte 3: solução, MVP, jornada, diferencial, fluxograma | Completa, dashboard funcional sobre base real | Parcial (score, faixa, alerta em tabela) | Limiares 0,35/0,65 não justificados; sem jornada, diferencial ou fluxograma. |
| Parte 4: arquitetura, escala, Oracle, justificativa, diagrama | Completa; OML in-database executado; Autonomous como roadmap | Parcial forte: Object Storage, Autonomous, staging, MERGE, docs de provisionamento | Oracle usado como armazenamento; modelo roda em Python fora do banco. |
| Evidência Oracle | Logs, TXT, CSV, PNG com timestamps | Nenhuma | Troubleshooting sugere execução real, mas sem métrica, log, modelo ou print; `sample_data` é sintético. |
| Diagramas | 7 (PNG/SVG) | 1 em ASCII | — |
| Vídeo pitch | Publicado (4:48) | Ausente | Eliminatório para a seleção. |
| ZIP funcional local | Sim | Exige bucket OCI, wallet e credenciais | — |
| Monetização e mercado | Completos | Ausentes | — |
| Modelo e métricas | Split temporal com embargo; AUC 0,88; limitações declaradas; OML AUC 0,95 | XGBoost/GB/LR por F2; split aleatório 80/20; sem métricas reportadas | Seleção por F2 é boa; split aleatório tende a inflar; dataset público (OULAD). |

## O que vale incorporar (v2)

1. **Caminho OCI real**: Object Storage + Autonomous Always Free (guia de provisionamento) → transformar o roadmap do Retena em runbook executável e, se possível, em evidência na OCI antes do dia 23/09.
2. **Padrões de engenharia**: `MERGE` idempotente para o snapshot de risco, XGBoost como candidato, `scale_pos_weight` calculado, seleção por F2 em benchmark comparativo (sem trocar o modelo entregue).
3. **Segundo dataset**: rodar o método Retena no OULAD para provar a portabilidade afirmada no pitch e responder à crítica de "só 203 alunos".

Se o EduRetain for apresentado isoladamente, precisa antes de: métricas reais do conjunto de teste, print da tabela `PREDICAO_EVASAO_ALUNO` no Oracle, aviso de que `sample_data` é sintético e justificativa dos limiares.
