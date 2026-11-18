# -*- coding: utf-8 -*-
"""
empacotar_final.py - gera o ZIP da ENTREGA FINAL (pasta única "Retena_Entrega_Final/").

  python empacotar_final.py               -> Retena_Entrega_Final_StartupOne.zip (com o MP4 do vídeo)
  python empacotar_final.py --sem-video   -> ..._sem_video.zip (caso a plataforma limite o tamanho)

O ZIP é gravado em StartupOne/ (fora de entrega/). Na raiz do pacote ficam LEIA-ME.md e INICIAR_MVP.cmd
(cópias de 11_Entrega_Final/), e as pastas mantêm os nomes de entrega/ para os caminhos relativos funcionarem.
Fica de fora o que é pesado e regenerável ou não pertence à entrega: vídeo da fase anterior (570 MB, está no YouTube),
quadros/áudios de produção do vídeo, documentos das fases anteriores, .env, caches e configurações locais.
"""
import fnmatch, hashlib, os, sys, zipfile
from pathlib import Path

ENTREGA = Path(__file__).resolve().parent.parent
RAIZ_ZIP = "Retena_Entrega_Final"
SEM_VIDEO = "--sem-video" in sys.argv
DESTINO = ENTREGA.parent / ("Retena_Entrega_Final_StartupOne" + ("_sem_video" if SEM_VIDEO else "") + ".zip")

INCLUIR = ["11_Entrega_Final", "06_Oracle", "08_Dados", "05_MVP", "03_Marca", "04_Landing_Page", "02_Diagramas",
           "10_Prototipacao_PoC", "01_Documento/anexos", "09_Kit_Banca_Final/gerar_kit_banca.py"]
EXCLUIR_DIRS = ["11_Entrega_Final/05_Video/_work", "11_Entrega_Final/05_Video/demo", "11_Entrega_Final/05_Video/img",
                "11_Entrega_Final/05_Video/audio", "__pycache__", ".claude", "_tmp_trim", "node_modules",
                # vão para a raiz do pacote (os caminhos deles partem da raiz)
                "11_Entrega_Final/LEIA-ME.md", "11_Entrega_Final/INICIAR_MVP.cmd"]
EXCLUIR_ARQ = ["*.pyc", "~$*", ".env", "*.pid", "api.out.log", "api.err.log", "Thumbs.db", "*.zip"]
if SEM_VIDEO:
    EXCLUIR_ARQ.append("*.mp4")


def excluido(rel: str) -> bool:
    partes = rel.split("/")
    if any(rel == d or rel.startswith(d + "/") or ("/" not in d and d in partes) for d in EXCLUIR_DIRS):
        return True
    return any(fnmatch.fnmatch(partes[-1], p) for p in EXCLUIR_ARQ)


def arquivos():
    for item in INCLUIR:
        p = ENTREGA / item
        if p.is_file():
            yield p
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and not excluido(f.relative_to(ENTREGA).as_posix()):
                yield f


def main():
    if DESTINO.exists():
        DESTINO.unlink()
    manifesto, total = [], 0
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for extra, nome in ((ENTREGA / "11_Entrega_Final" / "LEIA-ME.md", "LEIA-ME.md"),
                            (ENTREGA / "11_Entrega_Final" / "INICIAR_MVP.cmd", "INICIAR_MVP.cmd")):
            z.write(extra, f"{RAIZ_ZIP}/{nome}")
        for f in arquivos():
            rel = f.relative_to(ENTREGA).as_posix()
            comp = zipfile.ZIP_STORED if f.suffix.lower() in (".mp4", ".png", ".jpg", ".zip", ".parquet", ".xlsx", ".docx", ".pptx") else zipfile.ZIP_DEFLATED
            z.write(f, f"{RAIZ_ZIP}/{rel}", compress_type=comp)
            total += f.stat().st_size
            manifesto.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}")
        z.writestr(f"{RAIZ_ZIP}/MANIFESTO_SHA256.txt", "\n".join(manifesto) + "\n")
    print(f"{DESTINO}  |  {len(manifesto)} arquivos  |  {total/1e6:.1f} MB sem compressão  |  ZIP {DESTINO.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
