# Teste com usuários do MVP — Retena

**Status: PENDENTE — aguardando 3 sessões reais.** Nenhum teste foi conduzido ainda; nenhum resultado aqui é real até que a equipe preencha. As entrevistas das fases anteriores foram **simuladas** e continuam rotuladas assim; elas **não** contam para este requisito.

O enunciado exige teste do MVP com **pelo menos 3 usuários do público-alvo**, registrando dificuldades, feedback e ajustes feitos, e análise se o MVP resolve o problema. Este kit organiza isso. Entrega: 27/11/2026.

| Arquivo | Para quê |
|---|---|
| `protocolo_teste_mvp.md` | Objetivo, recrutamento, consentimento/LGPD, preparação, roteiro com 6 tarefas, SUS, métricas, critérios de decisão, formato remoto |
| `formulario_participante.md` | Ficha em branco: uma cópia por sessão (`P1_ficha.md`, `P2_ficha.md`…) |
| `consolidacao_testes.xlsx` | Lançamento dos dados; calcula sucesso, tempos, SUS, NPS e problemas por severidade |
| `consolidacao_testes.md` | Modelo (em branco) da seção "Teste com usuários" |
| `consolidar_testes.py` | Lê as fichas e a planilha, recalcula tudo e escreve as seções 2.3/2.4 do documento + `resultados_testes.md`/`.json` |
| `conclusao_equipe.md` | (criar depois dos testes) conclusão qualitativa em texto livre, que entra na seção 2.4 |

## Passo a passo da equipe

1. **Recrutar** (protocolo §2): ≥ 2 coordenação/tutoria + ≥ 1 diretoria/gestão de IES com EAD; ideal 5 convites para garantir 3 sessões. Agendar 40 min. Nome e contato ficam só na agenda da equipe, nunca nos arquivos de resultado.
2. **Preparar** cada sessão (protocolo §4): `INICIAR_MVP.cmd`, `python verificar_mvp.py`, `python resetar_demo.py --sim` (apaga contatos e volta o ticket a R$ 350; equivale ao SQL de reset do protocolo), conferir fila com 74 alunos e ticket padrão.
3. **Rodar** a sessão (protocolo §5–7): termo de consentimento, contexto, T1–T6 cronometradas sem ajudar, perguntas, SUS e valor. Moderador conduz; observador preenche a ficha. Responsável no registro: `TESTE-Pn`.
4. **Preencher** no mesmo dia: completar a ficha, salvar como `Pn_ficha.md` nesta pasta, lançar os números em `consolidacao_testes.xlsx` (abas Participantes, Tarefas, SUS, Problemas). A aba Resumo calcula tudo.
5. **Ajustar**: problemas de severidade 3–4 viram ajuste no MVP (registrar status e evidência — commit, print ou nota — na aba Problemas). Se der tempo, validar o ajuste com P4/P5.
6. **Devolver**: deixar nesta pasta as fichas `Pn_ficha.md` e a planilha preenchida e escrever em `conclusao_equipe.md` a resposta honesta para "o MVP resolve o problema?" (critérios do protocolo §9). Basta a ficha **ou** a planilha; com as duas, vale a planilha e o script avisa as divergências.

## Como entra no documento final (automático)

```
python consolidar_testes.py            # confere: quantas sessões válidas, taxas, SUS, avisos
python consolidar_testes.py --aplicar  # grava resultados_testes.md/.json e reescreve as seções 2.3 e 2.4 do documento
```

Depois, `python ..\fechar_entrega.py --executar` regera o pitch (slide 13 com os números reais), a cena 16 do vídeo, o documento em PDF e os ZIPs. Só conta sessão com data e consentimento "sim". Com menos de 3 sessões, o documento declara a limitação e o veredito fica "inconclusivo": **nunca completar com dados inventados**. O script foi testado com dados fictícios fora desta pasta; nenhum dado de exemplo entra na entrega.
