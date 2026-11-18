# -*- coding: utf-8 -*-
"""
fechar_entrega.py - fecha a entrega final da Retena com um comando, assim que a equipe devolver o material.

Entradas (nada é inventado; o que estiver vazio continua como pendência declarada):
  fechamento.json                         link do YouTube e papel de cada integrante (preenchido à mão)
  02_Testes_Usuarios/P*_ficha.md + .xlsx  testes REAIS com usuários (consolidados por consolidar_testes.py)
  02_Testes_Usuarios/conclusao_equipe.md  conclusão qualitativa dos testes (opcional, recomendado)

O que faz com --executar:
  1. consolida os testes (seções 2.3/2.4, tabela 2.1, sumário e Anexo B do documento), se houver sessões válidas
  2. aplica papéis do time (documento, pitch) e link do YouTube (documento, LEIA-ME, 05_Video/README, QR no pitch)
  3. regera o pitch (PPTX + PDF)
  4. vídeo: exporta os slides 13 e 14 do pitch para a montagem, troca a narração da cena 16 (validação) pela
     versão com os números reais dos testes, regera só o áudio dessa cena e remonta o MP4 (demo gravada não muda)
  5. atualiza os tempos do vídeo citados no documento, no LEIA-ME e no README do vídeo
  6. regera o documento (HTML, PDF, DOCX) e os dois ZIPs (completo e sem vídeo)
  7. confere: ZIPs íntegros e com manifesto batendo, vídeo ≤ 7 min, PDFs abrindo, pendências restantes

Uso:
  python fechar_entrega.py                 # só mostra o estado e o que seria feito
  python fechar_entrega.py --executar      # faz tudo
  python fechar_entrega.py --executar --sem-video   # não mexe no vídeo (ex.: sem tempo para remontar)
"""
import argparse, hashlib, json, re, shutil, subprocess, sys, zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTREGA = AQUI.parent
PY = sys.executable
DOC_MD = AQUI / "03_Documento" / "Retena_Documento_Final.md"
DOC_PDF = DOC_MD.with_suffix(".pdf")
PITCH_PDF = AQUI / "04_Pitch" / "Retena_Pitch_Final.pdf"
VID = AQUI / "05_Video"
VIDEO = VID / "Retena_Video_Final.mp4"
ROTEIRO = VID / "roteiro.json"
LEIA = AQUI / "LEIA-ME.md"
TESTES = AQUI / "02_Testes_Usuarios"
ZIPS = [ENTREGA.parent / "Retena_Entrega_Final_StartupOne.zip", ENTREGA.parent / "Retena_Entrega_Final_StartupOne_sem_video.zip"]
LIMITE_VIDEO_S = 7 * 60


def passo(t):
    print(f"\n=== {t}")


def rodar(args, **kw):
    print("  $", " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args], text=True, capture_output=True, encoding="utf-8", errors="replace", **kw)
    saida = (r.stdout or "") + (r.stderr or "")
    for l in saida.strip().splitlines()[-6:]:
        print("   ", l)
    return r


def ler(p):
    return p.read_text(encoding="utf-8-sig")  # tolera BOM (Bloco de Notas)


def gravar(p, txt):
    """grava preservando CRLF/LF do arquivo original"""
    orig = p.read_bytes().decode("utf-8") if p.exists() else ""
    nl = "\r\n" if "\r\n" in orig else "\n"
    p.write_text(txt.replace("\r\n", "\n").replace("\n", nl), encoding="utf-8", newline="")


def trocar_linha(txt, padrao, nova, onde):
    novo, k = re.subn(padrao, lambda _m: nova, txt, count=1, flags=re.M)
    if not k:
        print(f"  aviso: trecho não encontrado em {onde}: {padrao[:50]}")
    return novo


# --------------------------------------------------------------------------- números por extenso (narração)
UNI = "zero um dois três quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezesseis dezessete dezoito dezenove".split()
DEZ = "_ _ vinte trinta quarenta cinquenta sessenta setenta oitenta noventa".split()


def extenso(n, fem=False):
    n = int(n)
    if n == 100:
        return "cem"
    if n < 20:
        s = UNI[n]
    else:
        s = DEZ[n // 10] + ("" if n % 10 == 0 else " e " + UNI[n % 10])
    if fem:
        s = re.sub(r"\bum$", "uma", re.sub(r"\bdois$", "duas", s))
    return s


def narracao_validacao(t):
    """texto da cena 16 a partir dos números REAIS consolidados (resultados_testes.json)"""
    n = t["n"]; t1 = t["tarefas"]["T1"]; t3 = t["tarefas"]["T3"]; sus = t.get("sus_medio")
    pessoas = f"{extenso(n, True)} {'pessoa' if n == 1 else 'pessoas'}"
    if n < 3:
        fala = (f"Sendo honestos: o sinal e o fluxo estão provados com dados reais. Testamos o MVP com {pessoas} do público-alvo, "
                "menos do que as três que planejamos; os resultados estão no documento, sem nada inventado.")
        leg = (f"Sendo honestos: o sinal e o fluxo estão provados com dados reais. Testamos o MVP com {n} {'pessoa' if n == 1 else 'pessoas'} "
               "do público-alvo, menos do que as 3 que planejamos; os resultados estão no documento, sem nada inventado.")
        return fala, leg
    v = lambda k: "encontrou" if k == 1 else "encontraram"
    r = lambda k: "registrou" if k == 1 else "registraram"
    fala = (f"Sendo honestos: o sinal e o fluxo estão provados com dados reais, e agora também com usuários. Testamos o MVP com {pessoas} do público-alvo: "
            f"{extenso(t1['sucesso'], True)} de {extenso(t1['n'], True)} {v(t1['sucesso'])} quem chamar primeiro, "
            f"{extenso(t3['sucesso'], True)} de {extenso(t3['n'], True)} {r(t3['sucesso'])} o contato no Oracle")
    leg = (f"Sendo honestos: o sinal e o fluxo estão provados com dados reais, e agora também com usuários. Testamos o MVP com {n} pessoas do público-alvo: "
           f"{t1['sucesso']} de {t1['n']} {v(t1['sucesso'])} quem chamar primeiro, {t3['sucesso']} de {t3['n']} {r(t3['sucesso'])} o contato no Oracle")
    if sus is not None:
        fala += f", e a nota média de usabilidade foi {extenso(round(sus))} de cem."
        leg += f", e a nota média de usabilidade (SUS) foi {str(round(sus, 1)).replace('.', ',')} de 100."
    else:
        fala += "."; leg += "."
    final = (" Os critérios que definimos antes dos testes foram atendidos." if t["veredito"] == "critérios atendidos" else
             " Nem todos os critérios que definimos antes foram atendidos; o que falhou e os ajustes estão no documento.")
    return fala + final, leg + final


# --------------------------------------------------------------------------- etapas
def estado():
    fech = json.loads(ler(AQUI / "fechamento.json"))
    papeis = {k: v.strip() for k, v in fech.get("papeis", {}).items() if isinstance(v, str) and v.strip()}
    yt = fech.get("youtube", "").strip()
    r = subprocess.run([PY, TESTES / "consolidar_testes.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    sessoes = r.returncode == 0
    return fech, papeis, yt, sessoes, r.stdout.strip()


def aplicar_papeis_e_link(papeis, yt):
    t = ler(DOC_MD)
    for m in list(re.finditer(r"^\| ([^|]+?) \| (RM\d+) \| ([^|]*?) \|$", t, flags=re.M)):
        nome, rm, atual = m.groups()
        novo = papeis.get(rm) or (atual if "confirmar" not in atual else "[papel a confirmar pela equipe]")
        t = t.replace(m.group(0), f"| {nome} | {rm} | {novo} |")
    if yt:
        t = trocar_linha(t, r"^O pitch final está em .*$",
                         f"O pitch final está em `04_Pitch/Retena_Pitch_Final.pdf` e o vídeo com demonstração real em `05_Video/` "
                         f"(também no YouTube: {yt}). O roteiro cobre os dez pontos pedidos:", "documento (Parte 5)")
    gravar(DOC_MD, t)
    if yt:
        r = ler(VID / "README.md")
        r = trocar_linha(r, r"^- \*\*Link público \(YouTube\):\*\*.*$", f"- **Link público (YouTube):** {yt}", "05_Video/README.md")
        gravar(VID / "README.md", r)
        l = ler(LEIA)
        l = re.sub(r"(`11_Entrega_Final/05_Video/Retena_Video_Final\.mp4`) · link: [^|]*\|", lambda m: f"{m.group(1)} · YouTube: {yt} |", l)
        gravar(LEIA, l)


def atualizar_pendencias_leia(papeis, yt, testes_json):
    l = ler(LEIA)
    itens = []
    if not testes_json:
        itens.append("- **Testes com pelo menos 3 usuários reais** do público-alvo: protocolo, ficha e planilha prontos; a seção 2.3 do documento está marcada como pendente e não contém resultados inventados.")
    else:
        if testes_json["n"] < 3:
            itens.append(f"- **Testes com usuários:** {testes_json['n']} sessão(ões) real(is), abaixo das 3 pedidas; limitação declarada na seção 2.3 do documento.")
        if not testes_json.get("tem_conclusao"):
            itens.append("- Conclusão qualitativa dos testes (`02_Testes_Usuarios/conclusao_equipe.md`) ainda não escrita.")
    if not yt:
        itens.append("- **Link público do vídeo** (upload no YouTube).")
    faltam = [rm for rm in ("RM97881", "RM97592", "RM99350", "RM99198") if rm not in papeis]
    if faltam:
        itens.append(f"- Papéis individuais do time no documento (faltam: {', '.join(faltam)}; hoje marcados \"a confirmar\").")
    corpo = "\n".join(itens) if itens else "Nenhuma: testes consolidados, link do vídeo e papéis do time preenchidos."
    l = re.sub(r"## Pendências declaradas.*\Z", "## Pendências declaradas (dependem da equipe)\n\n" + corpo + "\n", l, flags=re.S)
    if testes_json:
        l = re.sub(r"^\| \*\*Kit de testes com usuários\*\*.*$",
                   "| **Testes com usuários** (resultados, fichas anonimizadas, protocolo, planilha) | `11_Entrega_Final/02_Testes_Usuarios/` — comece por `resultados_testes.md` |", l, flags=re.M)
    gravar(LEIA, l)


def exportar_slides(nums):
    import pymupdf
    d = pymupdf.open(PITCH_PDF); mudou = []
    for n in nums:
        destino = VID / "img" / f"slide_{n:02d}.png"
        antes = hashlib.sha256(destino.read_bytes()).hexdigest() if destino.exists() else ""
        pix = d[n - 1].get_pixmap(matrix=pymupdf.Matrix(1920 / d[n - 1].rect.width, 1080 / d[n - 1].rect.height))
        pix.save(destino)
        if hashlib.sha256(destino.read_bytes()).hexdigest() != antes:
            mudou.append(n)
    return mudou


def ajustar_cena16(testes_json):
    rot = json.loads(ROTEIRO.read_text(encoding="utf-8-sig"))
    cena = next(c for c in rot["cenas"] if c["id"] == "16")
    cena.setdefault("narracao_pendente", cena["narracao"])  # guarda a versão "testes são o próximo passo"
    if testes_json:
        fala, leg = narracao_validacao(testes_json)
    else:
        fala, leg = cena["narracao_pendente"], None
    mudou = cena["narracao"] != fala
    cena["narracao"] = fala
    if leg and leg != fala:
        cena["legenda"] = leg
    else:
        cena.pop("legenda", None)
    ROTEIRO.write_text(json.dumps(rot, ensure_ascii=False, indent=1), encoding="utf-8")
    return mudou, fala


def duracao(arq):
    import imageio_ffmpeg
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(arq)], capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


def mmss(s):
    return f"{int(s // 60)}:{int(s % 60):02d}"


def atualizar_tempos_video():
    clips = sorted((VID / "_work").glob("clip_*.mp4"))
    if len(clips) != 17:
        print("  aviso: clipes da montagem não encontrados; tempos não atualizados"); return
    ini, t = [], 0.0
    for c in clips:
        ini.append(t); t += duracao(c)
    total = duracao(VIDEO) or t
    d = ler(DOC_MD)
    d = trocar_linha(d, r"^\| Validação \| Slide 13 \|.*$", f"| Validação | Slide 13 | ~{mmss(ini[15])} |", "documento (Parte 5)")
    d = trocar_linha(d, r"^\| Time \| Slide 14 \|.*$", f"| Time | Slide 14 | ~{mmss(ini[16])} (fechamento) |", "documento (Parte 5)")
    gravar(DOC_MD, d)
    txt_total = f"{int(total // 60)} min {int(total % 60)} s"
    for arq in (VID / "README.md", LEIA):
        x = ler(arq)
        x = re.sub(r"\d+ min \d+ s", txt_total, x)
        x = re.sub(r"\| 3:03–\d+:\d+ \|", f"| {mmss(ini[9])}–{mmss(total)} |", x)
        gravar(arq, x)
    print(f"  vídeo: {mmss(total)} · validação em {mmss(ini[15])} · time em {mmss(ini[16])}")


def conferir():
    passo("Conferência final")
    ok = True
    dur = duracao(VIDEO)
    print(f"  vídeo: {mmss(dur) if dur else '?'} (limite 7:00) -> {'ok' if dur and dur <= LIMITE_VIDEO_S else 'PROBLEMA'}")
    ok &= bool(dur and dur <= LIMITE_VIDEO_S)
    import pymupdf
    for pdf in (DOC_PDF, PITCH_PDF):
        n = len(pymupdf.open(pdf))
        print(f"  {pdf.name}: {n} páginas")
    for z in ZIPS:
        if not z.exists():
            print(f"  {z.name}: NÃO ENCONTRADO"); ok = False; continue
        with zipfile.ZipFile(z) as zf:
            ruim = zf.testzip()
            nomes = zf.namelist()
            raiz = nomes[0].split("/")[0]
            man = zf.read(f"{raiz}/MANIFESTO_SHA256.txt").decode().splitlines()
            div = 0
            for linha in man:
                h, rel = linha.split("  ", 1)
                if hashlib.sha256(zf.read(f"{raiz}/{rel}")).hexdigest() != h:
                    div += 1
            proib = [n for n in nomes if re.search(r"EXEMPLO_NAO_ENTREGAR|ensaio|\.env$|\.pid$", n)]
            essenciais = ["LEIA-ME.md", "INICIAR_MVP.cmd", "11_Entrega_Final/03_Documento/Retena_Documento_Final.pdf",
                          "11_Entrega_Final/04_Pitch/Retena_Pitch_Final.pdf", "08_Dados/logs_lms.parquet"]
            if "sem_video" not in z.name:
                essenciais.append("11_Entrega_Final/05_Video/Retena_Video_Final.mp4")
            faltando = [e for e in essenciais if f"{raiz}/{e}" not in nomes]
        estado_z = "ok" if not ruim and not div and not proib and not faltando else "PROBLEMA"
        ok &= estado_z == "ok"
        print(f"  {z.name}: {z.stat().st_size / 1e6:.1f} MB, {len(nomes)} arquivos, manifesto {len(man) - div}/{len(man)}"
              f"{', corrompido: ' + ruim if ruim else ''}{', proibidos: ' + str(proib) if proib else ''}{', faltando: ' + str(faltando) if faltando else ''} -> {estado_z}")
    pend = []
    for arq in (DOC_MD, VID / "README.md", LEIA):
        for i, l in enumerate(ler(arq).splitlines(), 1):
            if re.search(r"\[A PREENCHER|\[A REDIGIR|a confirmar|— PENDENTE", l):
                pend.append(f"{arq.relative_to(AQUI)}:{i}: {l.strip()[:110]}")
    print(f"  marcadores de pendência restantes: {len(pend)}")
    for p in pend[:15]:
        print("   -", p)
    return ok


def main():
    ap = argparse.ArgumentParser(description="Fecha a entrega final da Retena")
    ap.add_argument("--executar", action="store_true"); ap.add_argument("--sem-video", action="store_true"); ap.add_argument("--sem-zip", action="store_true")
    a = ap.parse_args()
    fech, papeis, yt, sessoes, resumo_testes = estado()
    passo("Estado")
    print(f"  YouTube: {yt or 'NÃO INFORMADO'}")
    print(f"  Papéis: {len(papeis)}/5 informados ({', '.join(f'{k}={v}' for k, v in papeis.items())})")
    print("  Testes:", resumo_testes.splitlines()[0] if resumo_testes else "?")
    if not a.executar:
        print("\n(somente leitura; rode com --executar para aplicar, regerar e empacotar)")
        conferir(); return 0

    passo("1. Testes com usuários")
    tj = TESTES / "resultados_testes.json"
    if sessoes:
        r = rodar([PY, TESTES / "consolidar_testes.py", "--aplicar"])
        if r.returncode:
            sys.exit("consolidação falhou")
    else:
        print("  nenhuma sessão válida: seção 2.3 continua PENDENTE")
        if tj.exists() and json.loads(ler(tj)).get("exemplo"):
            sys.exit("resultados_testes.json da entrega é de EXEMPLO: apague-o")
    testes_json = json.loads(ler(tj)) if (sessoes and tj.exists()) else None

    passo("2. Papéis do time e link do vídeo")
    aplicar_papeis_e_link(papeis, yt)

    passo("3. Pitch")
    if rodar([PY, AQUI / "04_Pitch" / "gerar_pitch_final.py"], timeout=600).returncode:
        sys.exit("pitch falhou")

    if not a.sem_video:
        passo("4. Vídeo (cena 16 + slides 13/14)")
        slides = exportar_slides([13, 14])
        mudou_fala, fala = ajustar_cena16(testes_json)
        print(f"  slides alterados: {slides or 'nenhum'} · narração da cena 16 {'nova' if mudou_fala else 'igual'}: {fala[:90]}…")
        if mudou_fala:
            if rodar([PY, VID / "gerar_audio.py", "--so", "16", "--rate", "+2%"], timeout=300).returncode:
                sys.exit("áudio da cena 16 falhou (rede/edge-tts)")
        if slides or mudou_fala:
            tmp = VID / "Retena_Video_Final.novo.mp4"
            if rodar([PY, VID / "build_video.py", ROTEIRO.resolve(), tmp.resolve()], timeout=3600).returncode or not tmp.exists():
                sys.exit("montagem do vídeo falhou (o MP4 anterior foi mantido)")
            shutil.move(tmp, VIDEO)
            atualizar_tempos_video()
        else:
            print("  nada mudou no vídeo")

    passo("5. Documento e LEIA-ME")
    atualizar_pendencias_leia(papeis, yt, testes_json)
    if rodar([PY, AQUI / "03_Documento" / "gerar_documento_final.py"], timeout=600).returncode:
        sys.exit("documento falhou")

    if not a.sem_zip:
        passo("6. ZIPs")
        for extra in ([], ["--sem-video"]):
            if rodar([PY, AQUI / "empacotar_final.py", *extra], timeout=1200).returncode:
                sys.exit("empacotamento falhou")
    return 0 if conferir() else 1


if __name__ == "__main__":
    sys.exit(main())
