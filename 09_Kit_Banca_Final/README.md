# Kit oficial da Banca Final — Retena (23/09/2026) · versão comercial (v3)

Tudo o que a equipe precisa para apresentar, no design da marca Retena (mesmos tokens da landing page e do manual de marca).

Esta versão funde a narrativa de venda (gancho → antes/depois → "tarde demais" → solução → como funciona → prova → Oracle → negócio → marketing → mercado → impacto) com os dados reais e a integração Oracle executada. Um argumento por slide, número grande, pouco texto; a parte técnica foi para o apêndice A1–A15 e para os slides 11–12 (evidência e mapa da stack Oracle). A versão anterior, mais técnica, está preservada em `versao_anterior_tecnica/`.

| Arquivo | Uso |
|---|---|
| `Retena_Banca_Final.pptx` | Deck para apresentar: 18 slides principais + apêndice técnico A1–A15 para perguntas. Transições em *fade*, notas do apresentador em cada slide, gráficos nativos editáveis. Fonte Segoe UI (padrão do Windows). |
| `Retena_Banca_Final.pdf` | Mesmo deck em PDF (fontes embutidas) — plano B para qualquer máquina ou projetor. |
| `Retena_Guia_do_Apresentador.pdf` | Roteiro cronometrado (8 min), notas por slide, perguntas prováveis com respostas curtas (incluindo as do time Oracle: ferramentas usadas, marketing rentável, por que apostar), riscos, checklist do dia e regra de honestidade. |
| `Retena_OnePager_Banca.pdf` | Folha A4 para entregar à banca: problema, solução, números, Oracle, negócio, aquisição, equipe e QR codes (vídeo, site, repositório). Imprimir 5 cópias. |
| `qr/` | QR codes em PNG (vídeo, site, repositório) na cor da marca. |
| `notas_apresentador.json` | Notas por slide em formato reutilizável. |
| `versao_anterior_tecnica/` | Deck v2 (20 + 8 slides, mais denso) em PPTX/PDF, com seu gerador e notas — para consulta ou se a banca pedir mais detalhe técnico. |
| `gerar_kit_banca.py` · `gerar_materiais_apoio.py` | Geradores. Para alterar texto: editar o `.py`, rodar `python gerar_kit_banca.py`, abrir o PPTX no PowerPoint e exportar o PDF; depois `python gerar_materiais_apoio.py`. |

## Estrutura do deck (8 minutos)

| # | Slide | Tempo | # | Slide | Tempo |
|---|---|---|---|---|---|
| 1 | Capa | 0:20 | 10 | Por que dentro do Oracle (3 pilares) | 0:30 |
| 2 | Gancho: 5,2 mi alunos, 4 em 10 desistem | 0:15 | 11 | Integração executada (evidência) | 0:30 |
| 3 | Antes e depois | 0:30 | 12 | Ferramentas Oracle: executado × runbook × roadmap | 0:25 |
| 4 | Tarde demais: 30% em silêncio, 0 alertas | 0:25 | 13 | Modelo de negócio (R$ 4/aluno ativo; a conta) | 0:40 |
| 5 | Para quem (compra, usa, beneficiário) | 0:20 | 14 | Marketing digital e aquisição (funil + metas) | 0:35 |
| 6 | A solução: quem, onde, quanto | 0:30 | 15 | Mercado (TAM/SAM/SOM, GTM) | 0:15 |
| 7 | Como funciona em 4 passos (com as ferramentas Oracle) | 0:35 | 16 | Impacto e próximos passos | 0:25 |
| 8 | Demonstração ao vivo (dashboard: visão Diretoria → Coordenação) | 1:00 | 17 | Equipe | 0:10 |
| 9 | Resultados em linguagem simples (95 em 100, 3×, OULAD) | 0:40 | 18 | Fechamento com QR codes | 0:20 |

Apêndice: A1 prints da demonstração (reserva) · A2 métricas · A3 fluxo de dados · A4 OULAD · A5 split temporal · A6 LGPD/OCI · A7 jornada · A8 riscos · A9 rich picture · A10 benchmark · A11 diferencial · A12 validação H1–H6 · A13 mapa de atrito · A14 evidência na base · A15 arquitetura Oracle.

## Checklist do dia

1. Abrir o dashboard publicado (`https://lucashenklain.github.io/retena/dashboard/`), escolher a visão **Diretoria** no seletor do topo e deixar a busca da fila em "Aluno 0227"; abrir a landing (`https://lucashenklain.github.io/retena/`, seção **ROI**) em outra aba.
2. Abrir o PDF do deck como reserva; testar o vídeo em janela anônima (`https://youtu.be/HZrcLvIJCC4`).
3. Modo apresentador com notas ligado. Tempo-alvo: 8 minutos nos slides 1–18; o apêndice A1 é a reserva se a internet falhar; o resto do apêndice só sob demanda.
4. Levar o one-pager impresso (5 cópias) e o guia.

## Links

- Vídeo pitch (4:48): https://youtu.be/HZrcLvIJCC4
- Site (calculadora de ROI), dashboard e evidências: https://lucashenklain.github.io/retena/
- Repositório: https://github.com/LucasHenklain/retena

Equipe: Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198).
