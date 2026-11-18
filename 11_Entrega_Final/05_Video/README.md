# Vídeo da entrega final — Retena

- **Arquivo:** `Retena_Video_Final.mp4` (1920×1080, 5 min 24 s, narração pt-BR e legendas embutidas).
- **Link público (YouTube):** [A PREENCHER PELA EQUIPE após o upload] — o vídeo da fase anterior continua em https://youtu.be/HZrcLvIJCC4.

## O que aparece

| Tempo aprox. | Conteúdo |
|---|---|
| 0:00–0:50 | Abertura, problema e solução (slides do pitch) |
| 0:50–3:03 | **Demonstração real do MVP**, gravada da tela com o sistema rodando nesta máquina (Oracle AI Database 26ai Free em Docker + API): fila de segunda, painel do aluno com predição ao vivo e "e se", registro do contato gravado no Oracle, prova em SQL (último contato, status da fila, Duality View), job de scoring `DBMS_SCHEDULER` (trecho acelerado e identificado na tela) e visão da diretoria recalculada |
| 3:03–5:24 | Por que Oracle, mercado, modelo de negócio, diferencial, lançamento, projeções, validação e time |

O contato registrado no vídeo é de **demonstração** (responsável "Mariana (demonstração)"); nenhum aluno real foi contatado. Depois da gravação o contato foi apagado e o ticket voltou a R$ 350.

## Como foi produzido (reproduzível)

1. `python gerar_audio.py --rate "+2%"` — narração com voz neural pt-BR (edge-tts) a partir de `roteiro.json`.
2. `python gravar_demo.py` — com o MVP no ar, grava cada cena da demonstração com Playwright + screencast do Chromium, cadenciada pela duração da narração (`audio/duracoes.json`).
3. Slides: páginas de `../04_Pitch/Retena_Pitch_Final.pdf` exportadas para `img/`.
4. `python build_video.py <caminho absoluto>\roteiro.json <caminho absoluto>\Retena_Video_Final.mp4` — monta, sincroniza e queima as legendas (ffmpeg via imageio-ffmpeg).
