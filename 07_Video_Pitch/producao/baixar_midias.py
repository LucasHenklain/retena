# -*- coding: utf-8 -*-
"""Baixa narrações e clipes gerados no Higgsfield para a pasta de produção e mede durações."""
import urllib.request, re, subprocess
from pathlib import Path
import imageio_ffmpeg

BASE = Path(__file__).resolve().parent
(BASE / "audio").mkdir(exist_ok=True); (BASE / "broll").mkdir(exist_ok=True)
U = "https://d8j0ntlcm91z4.cloudfront.net/user_3AVHYMg83CIaM34rmJGHzY4ngsl/"
AUDIO = {
    "01": "hf_20260908_185802_cf3b5483-b1f5-470a-bc61-ec784ed33a1c.mp3",
    "02": "hf_20260908_185252_d19b623b-79a9-45c4-a373-ec96e8cdfc64.mp3",
    "03": "hf_20260908_185803_30a92d89-7b90-47ad-ba71-45243042392d.mp3",
    "04": "hf_20260908_185802_d69266ed-43ff-44cf-b441-4b0d32a3f943.mp3",
    "05": "hf_20260908_185253_7a011a9d-cea6-4129-9d73-216c96ab2758.mp3",
    "06": "hf_20260908_185251_b976e820-a3f9-4747-9014-2be6469d7770.mp3",
    "07": "hf_20260908_185251_b70f2e80-7ef5-4180-9d6e-e0cf282b1ed8.mp3",
    "08": "hf_20260908_185802_44f636af-4688-4862-af1f-2069a2034d8d.mp3",
    "09": "hf_20260908_185252_757a7869-31aa-4557-81f2-dd4c18b2f658.mp3",
    "10": "hf_20260908_185802_10127c0e-116b-4180-b5fd-1271f2a68d8e.mp3",
    "11": "hf_20260908_185252_a8cf992a-cd79-4e71-b755-ece34c524bd3.mp3",
    "12": "hf_20260908_185802_0120b5b5-5af4-477f-bd51-dcc33756dc50.mp3",
}
VIDEO = {
    "clip_01_aluno_noite": "hf_20260908_185807_69cf7614-51ac-4b45-bfb7-2020cd78ee06.mp4",
    "clip_08_desistindo": "hf_20260908_185258_4ac670f1-8488-41c2-8fed-fe11bb191bd1.mp4",
    "clip_02_coordenadora": "hf_20260908_185257_31254a09-3581-4ff1-9b62-bc79ecfb03e6.mp4",
    "clip_04_tutor": "hf_20260908_185257_55441a96-750c-4a8f-8a67-7dd1ba4a8b80.mp4",
    "clip_06_formatura": "hf_20260908_185301_4068ca71-1bf4-43a9-b974-c42241333856.mp4",
}
FF = imageio_ffmpeg.get_ffmpeg_exe()

def dur(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

total = 0
for k, f in AUDIO.items():
    p = BASE / "audio" / f"{k}.mp3"
    if not p.exists(): urllib.request.urlretrieve(U + f, p)
    d = dur(p); total += d; print(f"audio {k}: {d:.1f}s")
print(f"TOTAL narração: {total:.1f}s = {total/60:.2f} min")
for k, f in VIDEO.items():
    p = BASE / "broll" / f"{k}.mp4"
    if not p.exists(): urllib.request.urlretrieve(U + f, p)
    print(f"video {k}: {dur(p):.1f}s")
