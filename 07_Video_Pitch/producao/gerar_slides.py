# -*- coding: utf-8 -*-
"""
Gera os slides HTML (1920x1080) do vídeo pitch a partir de `slides.json` e dos tokens de marca `marca.json`.

Uso: python gerar_slides.py slides.json marca.json pasta_saida/

Layouts suportados (campo "layout"):
- capa:        {titulo, subtitulo, rodape}
- numero:      {numero, legenda, fonte, contexto}
- bullets:     {titulo, itens[], destaque}
- split:       {titulo, texto, imagem, lado: "esq"|"dir"}
- imagem:      {imagem, legenda, escurecer: true|false}
- citacao:     {texto, autor}
- cards:       {titulo, cards: [{titulo, texto, icone}]}
- fluxo:       {titulo, passos: [texto...]}
- tabela:      {titulo, cabecalho[], linhas[[]]}
- fechamento:  {titulo, subtitulo, chamada, rodape}
Todos aceitam "marca_d_agua": true para exibir o logo no canto.
"""
import json, sys, html
from pathlib import Path


def css(m):
    fontes = m.get("fontes", {})
    face = ""
    for f in m.get("arquivos_fonte", []):
        face += f"@font-face{{font-family:'{f['familia']}';src:url('{f['arquivo']}');font-weight:{f.get('peso','400')};font-style:normal;}}\n"
    return f"""
{face}
:root{{--primaria:{m['cores']['primaria']};--secundaria:{m['cores']['secundaria']};--acento:{m['cores']['acento']};
--alerta:{m['cores'].get('alerta','#F59E0B')};--critico:{m['cores'].get('critico','#EF4444')};--fundo:{m['cores'].get('fundo','#F6F7FB')};
--texto:{m['cores'].get('texto','#0F172A')};--texto-claro:#FFFFFF;--neutra:{m['cores'].get('neutra','#94A3B8')};}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1920px;height:1080px;overflow:hidden;font-family:'{fontes.get('texto','Inter')}','Segoe UI',system-ui,sans-serif;color:var(--texto);background:var(--fundo)}}
h1,h2,h3,.titulo{{font-family:'{fontes.get('titulo','Manrope')}','{fontes.get('texto','Inter')}','Segoe UI',sans-serif;letter-spacing:-0.02em}}
.slide{{position:relative;width:1920px;height:1080px;padding:120px 140px;display:flex;flex-direction:column;justify-content:center}}
.escuro{{background:radial-gradient(1200px 800px at 20% 10%,color-mix(in srgb,var(--primaria) 70%,var(--secundaria)),var(--primaria) 60%);color:var(--texto-claro)}}
.claro{{background:linear-gradient(180deg,#FFFFFF,var(--fundo))}}
.logo{{position:absolute;top:56px;left:140px;display:flex;align-items:center;gap:18px;font-family:'{fontes.get('titulo','Manrope')}',sans-serif;font-weight:800;font-size:34px;letter-spacing:-0.01em}}
.logo img{{height:56px}}
.rodape{{position:absolute;bottom:52px;left:140px;right:140px;display:flex;justify-content:space-between;font-size:24px;opacity:.75}}
.faixa{{position:absolute;left:0;top:0;bottom:0;width:18px;background:linear-gradient(180deg,var(--acento),var(--secundaria))}}
.kicker{{font-size:30px;font-weight:700;text-transform:uppercase;letter-spacing:.18em;color:var(--acento);margin-bottom:28px}}
h1{{font-size:96px;line-height:1.02;font-weight:800;max-width:1500px}}
h2{{font-size:72px;line-height:1.08;font-weight:800;max-width:1560px;margin-bottom:48px}}
p.sub{{font-size:40px;line-height:1.35;max-width:1400px;opacity:.9;margin-top:36px}}
ul.itens{{list-style:none;display:grid;gap:26px;font-size:42px;line-height:1.3;max-width:1560px}}
ul.itens li{{display:flex;gap:26px;align-items:flex-start}}
ul.itens li::before{{content:"";flex:0 0 18px;height:18px;margin-top:20px;border-radius:50%;background:var(--acento)}}
.numero{{font-size:300px;font-weight:800;line-height:.95;letter-spacing:-.04em;background:linear-gradient(90deg,var(--acento),#FFFFFF);-webkit-background-clip:text;background-clip:text;color:transparent}}
.numero-legenda{{font-size:56px;font-weight:700;margin-top:24px;max-width:1500px;line-height:1.15}}
.fonte{{font-size:26px;opacity:.7;margin-top:28px}}
.destaque{{margin-top:56px;padding:34px 44px;border-left:14px solid var(--acento);background:rgba(255,255,255,.08);font-size:40px;line-height:1.3;border-radius:0 24px 24px 0;max-width:1560px}}
.claro .destaque{{background:rgba(15,23,42,.05)}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:center;height:100%}}
.split img{{width:100%;height:760px;object-fit:cover;border-radius:36px;box-shadow:0 40px 80px rgba(0,0,0,.35)}}
.split p{{font-size:40px;line-height:1.4}}
.full{{position:absolute;inset:0;width:1920px;height:1080px;object-fit:cover}}
.veu{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,15,35,.25),rgba(5,15,35,.75))}}
.legenda-img{{position:absolute;left:140px;right:140px;bottom:140px;font-size:64px;font-weight:800;color:#fff;line-height:1.1;max-width:1500px;text-shadow:0 6px 30px rgba(0,0,0,.6)}}
.citacao{{font-size:66px;line-height:1.25;font-weight:600;max-width:1560px}}
.citacao::before{{content:"“";color:var(--acento);font-size:140px;line-height:0;vertical-align:-40px;margin-right:16px}}
.autor{{font-size:34px;opacity:.8;margin-top:40px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:36px}}
.card{{background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.14);border-radius:28px;padding:40px;min-height:300px}}
.claro .card{{background:#fff;border-color:rgba(15,23,42,.08);box-shadow:0 20px 50px rgba(15,23,42,.08)}}
.card .icone{{font-size:54px;margin-bottom:22px}}
.card h3{{font-size:38px;margin-bottom:16px;line-height:1.15}}
.card p{{font-size:30px;line-height:1.35;opacity:.9}}
.fluxo{{display:flex;gap:26px;align-items:stretch}}
.passo{{flex:1;background:rgba(255,255,255,.08);border-radius:26px;padding:34px 30px;font-size:32px;line-height:1.3;position:relative;border:2px solid rgba(255,255,255,.14)}}
.claro .passo{{background:#fff;border-color:rgba(15,23,42,.08)}}
.passo .n{{display:flex;width:64px;height:64px;border-radius:50%;background:var(--acento);color:#fff;font-weight:800;font-size:32px;align-items:center;justify-content:center;margin-bottom:22px}}
table{{border-collapse:collapse;width:100%;font-size:34px}}
th{{text-align:left;padding:22px 26px;background:var(--acento);color:#fff;font-weight:800}}
td{{padding:22px 26px;border-bottom:2px solid rgba(255,255,255,.12)}}
.claro td{{border-bottom-color:rgba(15,23,42,.1)}}
tr:nth-child(even) td{{background:rgba(255,255,255,.04)}}
.claro tr:nth-child(even) td{{background:rgba(15,23,42,.03)}}
.chamada{{display:inline-block;margin-top:56px;padding:30px 60px;border-radius:999px;background:var(--acento);color:#fff;font-weight:800;font-size:44px}}
"""


def logo_html(m):
    if m.get("logo_arquivo"):
        return f"<div class='logo'><img src='{m['logo_arquivo']}' alt='{html.escape(m['nome'])}'/></div>"
    return f"<div class='logo'><span>{html.escape(m['nome'])}</span></div>"


def render(slide, m):
    L = slide["layout"]; tema = slide.get("tema", "escuro")
    e = html.escape
    logo = logo_html(m) if slide.get("marca_d_agua", True) else ""
    rodape = f"<div class='rodape'><span>{e(slide.get('rodape', m.get('tagline','')))}</span><span>{e(m.get('rodape_direita',''))}</span></div>"
    body = ""
    if L == "capa":
        body = f"<div class='faixa'></div><div class='kicker'>{e(slide.get('kicker',''))}</div><h1>{slide['titulo']}</h1><p class='sub'>{e(slide.get('subtitulo',''))}</p>"
    elif L == "numero":
        body = f"<div class='kicker'>{e(slide.get('kicker',''))}</div><div class='numero'>{e(slide['numero'])}</div><div class='numero-legenda'>{slide['legenda']}</div><div class='fonte'>{e(slide.get('fonte',''))}</div>"
    elif L == "bullets":
        itens = "".join(f"<li><span>{i}</span></li>" for i in slide["itens"])
        dest = f"<div class='destaque'>{slide['destaque']}</div>" if slide.get("destaque") else ""
        body = f"<div class='kicker'>{e(slide.get('kicker',''))}</div><h2>{slide['titulo']}</h2><ul class='itens'>{itens}</ul>{dest}"
    elif L == "split":
        img = f"<img src='{slide['imagem']}' alt=''/>"
        txt = f"<div><div class='kicker'>{e(slide.get('kicker',''))}</div><h2>{slide['titulo']}</h2><p>{slide['texto']}</p></div>"
        body = f"<div class='split'>{img + txt if slide.get('lado','esq')=='esq' else txt + img}</div>"
    elif L == "imagem":
        body = f"<img class='full' src='{slide['imagem']}' alt=''/>" + ("<div class='veu'></div>" if slide.get("escurecer", True) else "") + f"<div class='legenda-img'>{slide.get('legenda','')}</div>"
    elif L == "citacao":
        body = f"<div class='citacao'>{slide['texto']}</div><div class='autor'>— {e(slide.get('autor',''))}</div>"
    elif L == "cards":
        cards = "".join(f"<div class='card'><div class='icone'>{c.get('icone','')}</div><h3>{c['titulo']}</h3><p>{c['texto']}</p></div>" for c in slide["cards"])
        body = f"<div class='kicker'>{e(slide.get('kicker',''))}</div><h2>{slide['titulo']}</h2><div class='cards'>{cards}</div>"
    elif L == "fluxo":
        passos = "".join(f"<div class='passo'><div class='n'>{i+1}</div>{p}</div>" for i, p in enumerate(slide["passos"]))
        body = f"<div class='kicker'>{e(slide.get('kicker',''))}</div><h2>{slide['titulo']}</h2><div class='fluxo'>{passos}</div>"
    elif L == "tabela":
        th = "".join(f"<th>{c}</th>" for c in slide["cabecalho"])
        tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in slide["linhas"])
        body = f"<div class='kicker'>{e(slide.get('kicker',''))}</div><h2>{slide['titulo']}</h2><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"
    elif L == "fechamento":
        body = f"<div class='faixa'></div><h1>{slide['titulo']}</h1><p class='sub'>{slide.get('subtitulo','')}</p><div class='chamada'>{e(slide.get('chamada',''))}</div>"
    else:
        raise SystemExit(f"layout desconhecido: {L}")
    return f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>{e(slide.get('id',''))}</title><style>{css(m)}</style></head><body><div class='slide {tema}'>{logo}{body}{rodape}</div></body></html>"


if __name__ == "__main__":
    slides = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    marca = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig"))
    out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    # os caminhos em marca.json são relativos a uma pasta de 2 níveis (ex.: 05_MVP/dashboard);
    # os slides ficam 3 níveis abaixo de `entrega/`, então ajustamos o prefixo relativo.
    prefixo = sys.argv[4] if len(sys.argv) > 4 else "../../../"
    def _fix(p): return p.replace("../../", prefixo, 1) if isinstance(p, str) and p.startswith("../../") else p
    for k in ("logo_arquivo", "logo_escuro_sobre_claro", "simbolo"):
        if k in marca: marca[k] = _fix(marca[k])
    for f in marca.get("arquivos_fonte", []): f["arquivo"] = _fix(f["arquivo"])
    for s in slides:
        (out / f"{s['id']}.html").write_text(render(s, marca), encoding="utf-8")
        print("slide", s["id"], s["layout"])
