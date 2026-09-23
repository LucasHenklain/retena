# Dia da banca neste notebook — 23/09/2026

Tudo roda a partir desta pasta (há um atalho `Retena_Banca.cmd` na Área de Trabalho que abre o passo 1).

| Quando | O quê | Como |
|---|---|---|
| De manhã, com calma (5 min) | Preparar o notebook: Docker + Oracle, job de scoring com carimbo de hoje, servidor local de reserva, abas no Edge (dashboard na visão Diretoria, site no ROI, vídeo) e o deck no PowerPoint | `1_Preparar.cmd` — deixar a janela aberta (mantém o notebook acordado) |
| Antes de entrar | Conferir a fila: digitar "Aluno 0227" na busca (visão Coordenação) e voltar para Diretoria; testar áudio do vídeo | no Edge |
| Na pergunta "isso roda mesmo?" | Scoring ao vivo: roda o job semanal dentro do Oracle e mostra o carimbo, as faixas, o top 5, os modelos e o histórico do job | `2_Scoring_ao_vivo.cmd` (25 s) |
| Sem internet | Dashboard e site locais (o passo 1 já abre as versões locais se o site publicado não responder); vídeo em `07_Video_Pitch/Retena_Pitch_Banca_Final.mp4`; deck em PDF; prints no apêndice A1 | URLs em `preparacao.log` |
| Sem Docker/Oracle | Evidências publicadas (`06_Oracle/evidencias/evidencias.html`) e o último resultado em `ultimo_scoring.txt` | — |

## O que dizer sobre o scoring ao vivo

"Os logs do LMS vão até 26 de agosto porque a base da instituição parceira é um export anonimizado. O que roda hoje é o scoring dentro do banco: o job semanal recalculou as features em SQL e re-pontuou os 203 alunos com os modelos de Oracle Machine Learning. O carimbo é de hoje, os números são os mesmos — o modelo não muda porque não chegou dado novo."

## Opções

- `1_Preparar.cmd -SemAbrir` prepara sem abrir Edge/PowerPoint; `-SemJob` não roda o job.
- `python scoring_ao_vivo.py --sem-rodar` só mostra o estado atual, sem executar o job.
- Log da preparação em `preparacao.log`; último scoring em `ultimo_scoring.txt`.
