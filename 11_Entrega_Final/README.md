# Retena — Entrega Final (Startup One · Enterprise Challenge Oracle · FIAP 2026)

> Ninguém desiste de repente. A Retena percebe antes.

Equipe: Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198) — Engenharia de Software, turma 4ESOA.

> **No GitHub:** os dados da IES parceira (`08_Dados/*.parquet`) e o MP4 do vídeo (68 MB) não são versionados. Para rodar o MVP do zero, use o ZIP da entrega (canal privado da equipe) ou coloque o parquet em `08_Dados/`. O vídeo vai para o YouTube (link em `05_Video/README.md`). **Para os testes com usuários, comece por [02_Testes_Usuarios](02_Testes_Usuarios/README.md).**

## Comece por aqui

| O que | Onde |
|---|---|
| **Documento consolidado** (Partes 1–5: MVP, testes, modelo de negócio, lançamento, pitch) | `03_Documento/Retena_Documento_Final.pdf` (editável: `.docx` e `.md`) |
| **Pitch em PDF** | `04_Pitch/Retena_Pitch_Final.pdf` (editável: `.pptx`) |
| **Vídeo (5 min 24 s) com demonstração real** | `05_Video/Retena_Video_Final.mp4` · link: ver `05_Video/README.md` |
| **MVP funcional** (Oracle + API + painel) | `01_MVP_Oracle/` — duplo clique em `INICIAR_MVP.cmd` na raiz do repositório |
| **Kit de testes com usuários** (protocolo, ficha, planilha) | `02_Testes_Usuarios/` |
| **Projeção financeira** (planilha com fórmulas) | `03_Documento/modelo_financeiro.xlsx` |

## Rodar o MVP

Pré-requisitos: Docker Desktop em execução e Python 3.10+. Dê dois cliques em **`INICIAR_MVP.cmd`**. Na primeira execução o script baixa o Oracle AI Database 26ai Free, carrega os 684.723 eventos de `08_Dados/` e treina os modelos dentro do banco (10–15 min); depois abre http://127.0.0.1:8080. Sem Docker, o painel offline (dados estáticos, sem gravação) abre direto em `05_MVP/dashboard/index.html`. Detalhes e opções (Linux/macOS, portas, verificação automática): `01_MVP_Oracle/README.md`.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `` | Tudo o que é novo nesta entrega (MVP, testes, documento, pitch, vídeo) |
| `06_Oracle/` | Pipeline Oracle usado pelo MVP: SQL 01–07 (carga, features, OML, scoring, job, Duality View, avaliação), scripts, evidências, runbook OCI |
| `08_Dados/` | Base real da IES parceira, **anonimizada** (logs do LMS em parquet) — uso restrito à avaliação; não publicar |
| `05_MVP/` | Painel offline e pipeline Python de referência das fases anteriores |
| `03_Marca/`, `04_Landing_Page/`, `02_Diagramas/` | Identidade visual, landing page com calculadora de ROI, diagramas |
| `10_Prototipacao_PoC/`, `01_Documento/anexos/` | Fase de prototipação/PoC e anexos da Fase 6 (conceito, instrumento, entrevistas **simuladas** e rotuladas assim) |
| `09_Kit_Banca_Final/` | Somente o gerador de slides reaproveitado pelo pitch final |

## Pendências declaradas (dependem da equipe)

- **Testes com pelo menos 3 usuários reais** do público-alvo: protocolo, ficha e planilha prontos; a seção 2.3 do documento está marcada como pendente e não contém resultados inventados.
- **Link público do vídeo** (upload no YouTube).
- Papéis individuais do time no documento (faltam: RM97881, RM97592, RM99350, RM99198; hoje marcados "a confirmar").
