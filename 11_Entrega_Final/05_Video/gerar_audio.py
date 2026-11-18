# -*- coding: utf-8 -*-
"""Narração do vídeo da Fase 6 com voz neural pt-BR (edge-tts, serviço de voz do Microsoft Edge, gratuito).
Uso: python gerar_audio.py [--voz pt-BR-AntonioNeural] [--rate -4%]   (lê a narração de roteiro.json → audio/NN.mp3)
"""
import argparse, asyncio, json, os, ssl, sys

# Rede corporativa com inspeção TLS: junta o bundle público (certifi) com a cadeia da empresa, se existir,
# e faz todo contexto SSL do processo usar esse arquivo (o edge-tts cria o próprio contexto com cafile fixo).
_corp = os.path.expanduser("~/.claude/certs/corporate-ca-chain.pem")
if os.path.exists(_corp):
    import certifi, tempfile
    _bundle = os.path.join(tempfile.gettempdir(), "ca-bundle-edge-tts.pem")
    with open(_bundle, "wb") as f:
        f.write(open(certifi.where(), "rb").read() + b"\n" + open(_corp, "rb").read())
    _orig = ssl.create_default_context
    ssl.create_default_context = lambda *a, **k: _orig(*a, **{**k, "cafile": _bundle})

try:
    import edge_tts
except ImportError:
    sys.exit("instale: python -m pip install edge-tts")

AQUI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--voz", default="pt-BR-AntonioNeural"); ap.add_argument("--rate", default="-4%"); ap.add_argument("--so", default="")
args = ap.parse_args()
roteiro = json.load(open(os.path.join(AQUI, "roteiro.json"), encoding="utf-8-sig"))

async def gerar():
    for cena in roteiro["cenas"]:
        if args.so and cena["id"] != args.so: continue
        saida = os.path.join(AQUI, cena["audio"]); os.makedirs(os.path.dirname(saida), exist_ok=True)
        com = edge_tts.Communicate(cena["narracao"], args.voz, rate=args.rate)
        await com.save(saida)
        print(cena["id"], "->", cena["audio"], os.path.getsize(saida) // 1024, "KB")

asyncio.run(gerar())
