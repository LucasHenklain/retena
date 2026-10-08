# Retena — Prototipação, PoC e validação técnica (Startup One · fase de transição para o MVP funcional)

**Equipe:** Lucas Dalmas (RM551178) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198) — FIAP 4ESOA, Startup One / Enterprise Challenge Oracle 2026.
**Entrega:** 10/10/2026. **Links:** site e calculadora https://lucashenklain.github.io/retena/ · dashboard https://lucashenklain.github.io/retena/dashboard/ · repositório https://github.com/LucasHenklain/retena · vídeo pitch https://youtu.be/HZrcLvIJCC4

Esta pasta responde às seis partes da atividade. Os artefatos das fases anteriores referenciados aqui (código Oracle, pipeline Python, dashboard, landing, diagramas, kit da banca) estão nas demais pastas do pacote.

| Parte | Exigência | Onde está | Estado |
|---|---|---|---|
| 1. Protótipo | fluxo principal e principais telas | `01_Prototipo/prototipo_fluxo.md` + `01_Prototipo/prints/` (6 telas); protótipo funcional em `../05_MVP/dashboard/index.html` e publicado | funcional (front-end); registro do resultado do contato como protótipo no navegador |
| 2. Prova de conceito | funcionalidade crítica + integração com banco/API | `02_PoC/poc_evidencia.md`; código e logs em `../06_Oracle/`; scoring ao vivo em `../09_Kit_Banca_Final/dia_da_banca/` | executada e reexecutada (22/09 e 23/09/2026) |
| 3. Validação técnica | viabilidade, desafios, riscos, gargalos, ajustes | `03_Validacao_Tecnica/relatorio_validacao_tecnica.md` (+ PDF) | concluída, com tempos medidos |
| 4. Evolução da arquitetura | diagrama atualizado, crescimento, escalabilidade, manutenção | `04_Arquitetura/08_arquitetura_executada.png` (+ SVG em `../02_Diagramas/`) e `04_Arquitetura/arquitetura_evolucao.md` | concluída |
| 5. Teste de usabilidade | ≥ 2 usuários, clareza, facilidade, feedbacks, melhorias | `05_Usabilidade/protocolo_teste_usabilidade.md`, `formulario_feedback.md`, `consolidacao_feedback.md` | **ver estado em `consolidacao_feedback.md`** (testes conduzidos pela equipe; só entram resultados reais) |
| 6. Roadmap | implementado × Fase 7, prioridades | `06_Roadmap/roadmap.md` (+ PDF) | concluído |

## Novidades desta fase em relação à Fase 6

- Dashboard: visões Diretoria / Coordenação / Time técnico, resumo executivo com receita em risco pelo ticket da IES, **registro do resultado do contato** no painel do aluno (status na fila e receita preservada estimada), links diretos `?modo=` e `?aluno=`.
- Landing: calculadora de retorno e "como funciona em 4 passos".
- Oracle: scoring materializado por job (`PRC_ATUALIZAR_RISCO`, 23–24 s) substituindo a view ao vivo (> 60 s); reexecução completa do pipeline (22/09) e scoring ao vivo na banca (23/09); scripts de operação (`dia_da_banca/`).
- Diagrama 08 com a arquitetura executada e o que fica para a Fase 7.
- Relatório de validação técnica, roadmap priorizado (MoSCoW) e protocolo de usabilidade.

## Como reproduzir

- Protótipo: abrir `../05_MVP/dashboard/index.html` (ou o link publicado); `?modo=diretoria`, `?aluno=Aluno%200227`.
- PoC Oracle: `../06_Oracle/README` e `02_PoC/poc_evidencia.md` (Docker + scripts 01–07, ~10 min).
- PDFs desta pasta: `python gerar_pdfs.py` (Edge headless, fontes da marca).
