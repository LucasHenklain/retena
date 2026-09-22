# Retena — Radar de permanência para o ensino superior EAD

> Startup One + Enterprise Challenge Oracle · FIAP 4ESOA-2026 · Fase 6: Refinamento, Validação e Estruturação do MVP
> "Ninguém desiste de repente. A Retena percebe antes."

Este pacote contém toda a evolução do projeto. Tudo abre localmente (duplo clique), sem servidor e sem internet.

## Comece por aqui

| Pasta | Conteúdo | Abrir |
|-------|----------|-------|
| `01_Documento/` | Documento estruturado da Fase 6 (Partes 1–4 + anexos: instrumento de validação, respostas do formulário da banca, roteiro do pitch, referências) | `Retena_Fase6_Documento.pdf` (fonte editável: `.docx`) |
| `02_Diagramas/` | Rich Picture, Mapa de Stakeholders, Jornada do Usuário, Fluxograma do MVP, Arquitetura inicial, Arquitetura com Oracle, Fluxo de dados/ML (PNG + SVG editável) | `00_indice_diagramas.html` |
| `03_Marca/` | Manual de marca (16 p.), logo em 12 versões (SVG/PNG), tokens `marca.json`, fontes Sora/Inter | `Manual_de_Marca_Retena.pdf` |
| `04_Landing_Page/` | Página de vendas autocontida (mock do produto, resultados, Oracle, planos, piloto, FAQ) | `index.html` |
| `05_MVP/` | Pipeline de ML em Python (features semanais, modelo de risco 21 dias, transição de fases, mapa de atrito), resultados e dashboard interativo | `dashboard/index.html` · `outputs/RESULTADOS.md` |
| `06_Oracle/` | Integração com Oracle AI Database 26ai + Oracle Machine Learning: DDL, features em SQL, modelos in-database, scoring, views JSON, consultas APEX e evidências reais (logs, prints) | `evidencias/evidencias.html` · `README.md` |
| `07_Video_Pitch/` | Roteiro do pitch, link do YouTube e material de produção (Higgsfield MCP + ffmpeg). O MP4 (4 min 48 s) fica na pasta local e vai ao YouTube; por regra da atividade não entra no ZIP | `LINK_YOUTUBE.txt` · `roteiro_pitch.md` |
| `08_Dados/` | Base anonimizada de logs do LMS em Parquet (684.723 eventos, 203 alunos; fonte: `Base-Anônima.xlsx`) | — |
| `09_Kit_Banca_Final/` | Kit oficial da Banca Final (23/09/2026): deck de 29 slides (PPTX + PDF), guia do apresentador, one-pager com QR codes | `Retena_Banca_Final.pptx` · `README.md` |

## Dois modelos, duas evidências

- **MVP analítico (Python, `05_MVP`)** — referência metodológica do documento: base aluno-semana com rótulo `inativo_21d`, split temporal (treino < jun/2026, teste ≥ jun/2026), HistGradientBoosting: AUC-ROC 0,882, precisão 88% no top-20% de risco, lift 3,06×, faixa Alto com 95% de inatividade observada. Limitações em `05_MVP/outputs/RESULTADOS.md`.
- **Modelo in-database (Oracle, `06_Oracle`)** — prova da arquitetura "o modelo roda onde o dado mora": mesmos eventos carregados no Oracle AI Database 26ai Free, features em SQL, Random Forest e GLM treinados com `DBMS_DATA_MINING`, scoring por `PREDICTION_PROBABILITY`/`PREDICTION_DETAILS`: AUC 0,949 no teste temporal (conjunto de features e janelas ligeiramente diferentes do pipeline Python, por isso os números não são idênticos; ambos usam teste temporal ≥ jun/2026).

## Reprodução rápida (opcional)

```bash
pip install -r 05_MVP/requirements.txt
python 05_MVP/pipeline/run_all.py                 # regenera features, modelo, figuras e dashboard
docker compose -f 06_Oracle/docker-compose.yml up -d
powershell -File 06_Oracle/scripts/run_all.ps1     # carga, features, modelos OML, scoring e evidências
```

## Vídeo pitch e site publicado

- YouTube (não listado): **https://youtu.be/HZrcLvIJCC4** (4 min 48 s). Testar em janela anônima antes de enviar o formulário (prazo 13/09/2026). Respostas do formulário em `01_Documento/anexos/formulario_banca_respostas.md`.
- Landing page publicada (GitHub Pages): **https://lucashenklain.github.io/retena/** — inclui `/dashboard/`, `/evidencias/evidencias.html` e `/diagramas/`. Repositório: https://github.com/LucasHenklain/retena. Para republicar após alterações: `python 04_Landing_Page/montar_site_publicacao.py <pasta>` e `git push` da pasta gerada para a branch `main`.

## Sobre as entrevistas da Parte 2

As oito entrevistas documentadas (Parte 2.2 e Anexo A.6, detalhamento em `01_Documento/anexos/entrevistas_validacao.md` e `registro_entrevistas.csv`) foram conduzidas em **formato simulado, com personas sintéticas** construídas a partir dos perfis-alvo e das evidências da base real, e estão rotuladas assim no documento. Recomenda-se confirmar os achados em campo com 5 a 8 entrevistas reais antes do piloto, usando o mesmo roteiro (Anexo A).

## Versão 2 (09/09/2026) — o que foi acrescentado após a entrega na plataforma

A versão 1 entregue na plataforma não foi alterada (hashes conferidos pelo manifesto `../manifesto_v1.csv`). A versão 2, para a Banca Final, incorpora o melhor do pipeline EduRetain de um integrante da equipe, sem trocar o modelo nem os números já reportados:

| Acrescentado | Onde | Resultado |
|---|---|---|
| Benchmark de modelos no mesmo split temporal (logística L1 balanceada, XGBoost com scale_pos_weight, GradientBoosting; seleção por F2) | `05_MVP/pipeline/07_benchmark_modelos.py`, `05_MVP/outputs/benchmark_modelos.md` | Nenhuma configuração supera o baseline já existente; a vantagem em F2 dos modelos balanceados é efeito de limiar; HGB permanece o modelo entregue |
| Portabilidade do método no OULAD (Open University, 32.593 matrículas, 10,66 mi cliques) | `05_MVP/portabilidade_oulad/` | Mesmos hiperparâmetros, split temporal 2013 → 2014: AUC-ROC 0,922 e lift 3,51× em 14.293 alunos; mesmas features dominam |
| Caminho OCI executável: runbook Autonomous Always Free + Object Storage + DBMS_CLOUD, conexão dual (local/wallet), exportação para bucket, MERGE idempotente | `06_Oracle/oci/` | Executado no Free local: conexão, dry-run da exportação (684.723 linhas) e MERGE 2× sem duplicar; partes OCI marcadas como runbook |
| Documento e apresentação atualizados (seções 3.7, 3.8 e 4.9; slide 11) | `01_Documento/Retena_Fase6_Documento_v2.pdf` (64 p.), `Retena_Apresentacao_Banca_v2.pptx` | Versões v1 preservadas ao lado |
| Parecer interno EduRetain × Retena | `01_Documento/Parecer_EduRetain_vs_Retena.md` | Base da decisão de integrar, não substituir |

## Pendência restante

- Alinhar a nomenclatura dos problemas da Fase 5 com o documento anterior da equipe (Parte 1.1).

## Equipe

- Lucas Dalmas — RM551178 (líder)
- Lucas Emanuel — RM97881
- Kayque Moraes — RM97592
- Lucas Henklain — RM99350
- Vinicius Pinheiro — RM99198
