# Vídeo Pitch — Retena (Banca Final · Enterprise Challenge Oracle)

- **Arquivo final:** `Retena_Pitch_Banca_Final.mp4` (1920×1080, 30 fps, H.264 + AAC, ~4 min 48 s — abaixo do limite de 5 min).
- **Roteiro completo:** `roteiro_pitch.md` (12 blocos: Público → Problema → Oportunidade → Solução → Demonstração → Diferencial → Monetização → Mercado → Fechamento).
- **Link do YouTube (não listado):** https://youtu.be/HZrcLvIJCC4 — também em `LINK_YOUTUBE.txt`; testar em janela anônima antes de enviar o formulário.
- **Atenção:** por regra da atividade, o MP4 **não** vai dentro do ZIP entregue na plataforma (o `empacotar.ps1` já o exclui); ele fica nesta pasta local para o upload no YouTube.

## Como o vídeo foi produzido (via MCP Higgsfield + montagem local)

| Etapa | Ferramenta | Detalhe |
|-------|-----------|---------|
| Narração em português | Higgsfield MCP · `text2speech_v2` (ElevenLabs multilingual), voz preset "Andre" | 12 blocos gerados em lote (`generate_audio_batch`); 7 blocos regravados mais curtos para caber em 5 min; transcrição de conferência com faster-whisper (idioma pt, 4/4 vozes testadas corretas). Blocos 09 e 10 com `atempo=1.05` (imperceptível). |
| Imagens de b-roll | Higgsfield MCP · `soul_2` (2K, 16:9) | 8 cenas realistas (aluno à noite, coordenadora, campus, tutor, formatura, data center…), sem marcas nem texto legível. |
| Clipes de vídeo | Higgsfield MCP · `kling3_0_turbo` (5 s, 720p, image-to-video) | 5 clipes animados a partir das imagens (movimento sutil, sem cortes). |
| Slides | `producao/gerar_slides.py` + `slides.json` + `../03_Marca/marca.json` | HTML 1920×1080 com a identidade Retena (Sora/Inter, paleta) renderizados em PNG pelo Edge headless. |
| Demonstração | `producao/demo/` | Capturas reais do dashboard do MVP (`05_MVP/dashboard/index.html`): fila de segunda e mapa de atrito. |
| Montagem | `producao/build_video.py` + `roteiro.json` | ffmpeg (imageio-ffmpeg): movimento suave (zoompan), sequências por cena, concatenação, legendas ASS queimadas geradas a partir da narração. |

Créditos Higgsfield consumidos: ≈ 52 (de 107,5 disponíveis).

## Reconstruir o vídeo

```powershell
cd 07_Video_Pitch\producao
python gerar_slides.py slides.json ..\..\03_Marca\marca.json slides
python build_video.py roteiro.json ..\Retena_Pitch_Banca_Final.mp4
```

Requisitos: Python 3.13 com `imageio-ffmpeg` e `Pillow`; Microsoft Edge (renderização dos slides). Para trocar a voz, regenerar os MP3 em `producao/audio/` (mesmos nomes 01–12) e rodar o `build_video.py` novamente.

## Estrutura

```
07_Video_Pitch/
├── Retena_Pitch_Banca_Final.mp4
├── roteiro_pitch.md
├── LINK_YOUTUBE.txt
└── producao/
    ├── roteiro.json          # cenas, sequências, áudio, legendas
    ├── slides.json           # conteúdo dos slides
    ├── gerar_slides.py · build_video.py · baixar_midias.py · preview_slides.py
    ├── slides/               # HTML dos slides
    ├── audio/                # narração 01–12 (mp3) + v1_longas/ (versões descartadas)
    ├── broll/                # imagens e clipes gerados no Higgsfield
    └── demo/                 # capturas do dashboard usadas na demonstração
```
