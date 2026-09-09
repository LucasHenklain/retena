# -*- coding: utf-8 -*-
"""
Montagem do vídeo pitch a partir de um roteiro JSON.

Uso:
    python build_video.py roteiro.json saida.mp4 [--no-subs]

Estrutura do roteiro.json:
{
  "fps": 30, "largura": 1920, "altura": 1080,
  "fonte_legenda": "Segoe UI", "tamanho_legenda": 44,
  "cenas": [
    {"id": "01", "tipo": "slide", "html": "slides/01.html", "audio": "audio/01.mp3",
     "movimento": "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static",
     "legenda": "Texto exibido como legenda (opcional; se ausente usa 'narracao')",
     "narracao": "Texto narrado", "duracao_min": 4.0, "pausa_fim": 0.6},
    {"id": "02", "tipo": "video", "video": "broll/02.mp4", "audio": "audio/02.mp3", ...},
    {"id": "03", "tipo": "imagem", "imagem": "img/03.png", "audio": "audio/03.mp3", ...}
  ]
}
Cada cena vira um clipe com a duração = max(duracao_audio + pausa_fim, duracao_min).
Slides HTML são renderizados com Edge headless para PNG (1920x1080) e recebem
movimento suave (Ken Burns) via ffmpeg zoompan. Vídeos de b-roll são loopados/cortados.
Legendas: geradas em ASS (uma linha por trecho de frase) e queimadas no vídeo.
"""
import json, os, subprocess, sys, math, re, shutil, textwrap
from pathlib import Path

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE):
    EDGE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-4000:])
        raise SystemExit(f"Falha: {' '.join(map(str, cmd))[:300]}")
    return r


def ffprobe_duration(path):
    cmd = [FFMPEG.replace("ffmpeg", "ffprobe")] if os.path.exists(FFMPEG.replace("ffmpeg", "ffprobe")) else None
    # imageio-ffmpeg não traz ffprobe: usa o próprio ffmpeg para ler a duração
    r = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    if not m:
        raise SystemExit(f"Sem duração para {path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def render_slide(html_path, png_path, w, h):
    url = "file:///" + str(Path(html_path).resolve()).replace("\\", "/")
    profile = Path(os.environ.get("TEMP", ".")) / "retena_edge_profile"
    r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--no-first-run", "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={profile}",
                        f"--window-size={w},{h}", f"--screenshot={png_path}", url], capture_output=True, timeout=120)
    if not os.path.exists(png_path):
        raise SystemExit(f"Screenshot não gerado: {png_path}")


def split_caption(text, max_chars=62):
    """Divide a narração em trechos curtos para legenda, respeitando pontuação."""
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[\.\!\?;:])\s+", text)
    chunks = []
    for p in parts:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            # quebra por vírgulas e depois por palavras
            sub = re.split(r"(?<=,)\s+", p)
            buf = ""
            for s in sub:
                if len(buf) + len(s) + 1 <= max_chars:
                    buf = (buf + " " + s).strip()
                else:
                    if buf: chunks.append(buf)
                    buf = s
            if buf:
                if len(buf) > max_chars:
                    chunks.extend(textwrap.wrap(buf, max_chars))
                else:
                    chunks.append(buf)
    return [c for c in chunks if c]


def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(cenas, tempos, fonte, tamanho, w, h, path):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Legenda,{fonte},{tamanho},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,4,14,0,2,120,120,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cena, (t0, dur_audio, dur_total) in zip(cenas, tempos):
        texto = cena.get("legenda") or cena.get("narracao") or ""
        if not texto or cena.get("sem_legenda"):
            continue
        chunks = split_caption(texto)
        total_chars = sum(len(c) for c in chunks) or 1
        cursor = t0 + 0.15
        avail = max(dur_audio - 0.15, 0.5)
        for c in chunks:
            d = avail * len(c) / total_chars
            lines.append(f"Dialogue: 0,{ass_time(cursor)},{ass_time(min(cursor + d, t0 + dur_total))},Legenda,,0,0,0,,{c}")
            cursor += d
    Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def motion_filter(kind, dur, fps, w, h, ajuste="cobrir", cor_fundo="white"):
    frames = int(round(dur * fps))
    if ajuste == "conter":
        pre = f"scale={w*2}:{h*2}:force_original_aspect_ratio=decrease,pad={w*2}:{h*2}:(ow-iw)/2:(oh-ih)/2:color={cor_fundo},setsar=1,"
    else:
        pre = f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},setsar=1,"
    if kind == "static":
        return pre + f"scale={w}:{h},fps={fps},format=yuv420p"
    # zoompan trabalha sobre a imagem ampliada para evitar tremor.
    # Movimento suave por padrão: zoom máximo 1,07 (corta ≤3,5% por lado, dentro da margem dos slides);
    # ajuste="forte" (fotos) permite até 1,16.
    base = pre
    zmax = 1.16 if ajuste == "forte" else 1.07
    passo = zmax - 1.0
    inc = f"{passo / max(frames, 1):.6f}"
    if kind == "zoom_in":
        z = f"min(zoom+{inc},{zmax})"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    elif kind == "zoom_out":
        z = f"if(eq(on,1),{zmax},max(zoom-{inc},1.0))"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    elif kind == "pan_left":
        z = f"{1.0 + passo * 0.8:.3f}"; x = f"(iw-iw/zoom)*(1-on/{max(frames,1)})"; y = "ih/2-(ih/zoom/2)"
    elif kind == "pan_right":
        z = f"{1.0 + passo * 0.8:.3f}"; x = f"(iw-iw/zoom)*(on/{max(frames,1)})"; y = "ih/2-(ih/zoom/2)"
    else:
        z = f"min(zoom+{inc},{zmax})"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    return base + f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},format=yuv420p"


def build(roteiro_path, out_path, subs=True):
    roteiro = json.loads(Path(roteiro_path).read_text(encoding="utf-8-sig"))
    base = Path(roteiro_path).parent
    fps = roteiro.get("fps", 30); w = roteiro.get("largura", 1920); h = roteiro.get("altura", 1080)
    work = base / "_work"; work.mkdir(exist_ok=True)
    clips = []; tempos = []; t = 0.0
    for cena in roteiro["cenas"]:
        cid = cena["id"]
        audio = base / cena["audio"] if cena.get("audio") else None
        dur_audio = ffprobe_duration(audio) if audio else 0.0
        dur = max(dur_audio + cena.get("pausa_fim", 0.6), cena.get("duracao_min", 3.0))
        clip = work / f"clip_{cid}.mp4"
        if cena["tipo"] in ("slide", "imagem"):
            if cena["tipo"] == "slide":
                png = work / f"slide_{cid}.png"
                render_slide(base / cena["html"], png, w, h)
            else:
                png = base / cena["imagem"]
            vf = motion_filter(cena.get("movimento", "zoom_in"), dur, fps, w, h, cena.get("ajuste", "cobrir"), cena.get("cor_fundo", "white"))
            cmd = [FFMPEG, "-y", "-loop", "1", "-framerate", str(fps), "-i", str(png)]
            if audio:
                cmd += ["-i", str(audio)]
            cmd += ["-vf", vf, "-t", f"{dur:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
            if audio:
                cmd += ["-af", f"apad=whole_dur={dur:.3f}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest"]
            else:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-c:a", "aac", "-shortest"]
            cmd += [str(clip)]
            run(cmd)
        elif cena["tipo"] == "video":
            src = base / cena["video"]
            cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", str(src)]
            if audio:
                cmd += ["-i", str(audio)]
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},format=yuv420p"
            cmd += ["-vf", vf, "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
            if audio:
                cmd += ["-map", "0:v:0", "-map", "1:a:0", "-af", f"apad=whole_dur={dur:.3f}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
            else:
                cmd += ["-an"]
            cmd += [str(clip)]
            run(cmd)
        elif cena["tipo"] == "sequencia":
            # vários visuais em sequência sobre a mesma narração; o último preenche o tempo restante
            itens = cena["itens"]; fixos = sum(i.get("duracao", 0) for i in itens[:-1])
            resto = max(dur - fixos, 2.0)
            partes = []
            for k, item in enumerate(itens):
                d_item = item.get("duracao", 0) if k < len(itens) - 1 else resto
                parte = work / f"clip_{cid}_{k}.mp4"
                if item["tipo"] == "video":
                    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},format=yuv420p"
                    run([FFMPEG, "-y", "-stream_loop", "-1", "-i", str(base / item["video"]), "-vf", vf, "-t", f"{d_item:.3f}",
                         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(parte)])
                else:
                    if item["tipo"] == "slide":
                        png = work / f"slide_{cid}_{k}.png"; render_slide(base / item["html"], png, w, h)
                    else:
                        png = base / item["imagem"]
                    vf = motion_filter(item.get("movimento", "zoom_in"), d_item, fps, w, h, item.get("ajuste", "cobrir"), item.get("cor_fundo", "white"))
                    run([FFMPEG, "-y", "-loop", "1", "-framerate", str(fps), "-i", str(png), "-vf", vf, "-t", f"{d_item:.3f}",
                         "-r", str(fps), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(parte)])
                partes.append(parte)
            lst = work / f"lista_{cid}.txt"
            lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in partes), encoding="utf-8")
            visual = work / f"visual_{cid}.mp4"
            run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(visual)])
            cmd = [FFMPEG, "-y", "-i", str(visual)]
            if audio:
                cmd += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-af", f"apad=whole_dur={dur:.3f}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
            else:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac"]
            cmd += ["-t", f"{dur:.3f}", "-c:v", "copy", str(clip)]
            run(cmd)
        else:
            raise SystemExit(f"Tipo desconhecido: {cena['tipo']}")
        clips.append(clip); tempos.append((t, dur_audio, dur)); t += dur
        print(f"cena {cid}: audio {dur_audio:.1f}s -> clipe {dur:.1f}s (acum {t:.1f}s)")
    # concatena
    lista = work / "lista.txt"
    lista.write_text("\n".join(f"file '{c.as_posix()}'" for c in clips), encoding="utf-8")
    concat = work / "concat.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(concat)])
    final_in = concat
    if subs:
        ass = work / "legendas.ass"
        build_ass(roteiro["cenas"], tempos, roteiro.get("fonte_legenda", "Segoe UI"), roteiro.get("tamanho_legenda", 44), w, h, ass)
        ass_path = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
        run([FFMPEG, "-y", "-i", str(concat), "-vf", f"ass='{ass_path}'", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "copy", str(out_path)])
    else:
        shutil.copy(concat, out_path)
    print(f"OK -> {out_path}  duração total {t/60:.2f} min ({t:.1f}s)")
    return t


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    build(sys.argv[1], sys.argv[2], subs="--no-subs" not in sys.argv)
