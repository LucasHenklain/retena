# -*- coding: utf-8 -*-
"""
gravar_demo.py - grava a DEMONSTRAÇÃO REAL do MVP (API + Oracle rodando) para o vídeo.

Usa o Edge via Playwright e o screencast do Chromium (CDP Page.startScreencast, JPEG q90, 1920x1080) numa única aba,
cena a cena, cadenciando as ações pela duração da narração (audio/duracoes.json). Nada é simulado: cada clique chama a
API, que lê/grava no Oracle. O registro de contato é de DEMONSTRAÇÃO (responsável "Mariana (demonstração)") e é
apagado no fim, junto com a volta do ticket para R$ 350 (use --manter para não limpar).

Pré-requisitos: MVP no ar (01_MVP_Oracle/iniciar.ps1) e nenhum contato registrado ainda (o script confere).
Uso: python gravar_demo.py [--url http://127.0.0.1:8080] [--so 05] [--manter]
"""
import argparse, base64, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

import oracledb
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
DEMO = AQUI / "demo"; DEMO.mkdir(exist_ok=True)
try:
    import imageio_ffmpeg; FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
DUR = json.loads((AQUI / "audio" / "duracoes.json").read_text())
RESP = "Mariana (demonstração)"
ALUNO = "Aluno 0068"

CURSOR_JS = """
(() => {
  const mk = () => {
    if (document.getElementById('__cur')) return;
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="#0B2545" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'-40px', top:'-40px', zIndex:2147483647, pointerEvents:'none', transition:'none'});
    document.documentElement.appendChild(c);
    const st = document.createElement('style');
    st.textContent = '@keyframes __rip{from{transform:translate(-50%,-50%) scale(.2);opacity:.85}to{transform:translate(-50%,-50%) scale(1.6);opacity:0}}' +
      '.__rip{position:fixed;width:44px;height:44px;border-radius:50%;background:rgba(46,196,182,.55);pointer-events:none;z-index:2147483646;animation:__rip .55s ease-out forwards}';
    document.documentElement.appendChild(st);
    document.addEventListener('mousemove', e => { c.style.left = (e.clientX - 3) + 'px'; c.style.top = (e.clientY - 2) + 'px'; }, true);
    document.addEventListener('mousedown', e => { const r = document.createElement('div'); r.className = '__rip';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.documentElement.appendChild(r); setTimeout(() => r.remove(), 700); }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mk); else mk();
})();
"""


class Gravador:
    """Screencast do Chromium: guarda cada quadro com o carimbo de tempo e monta um MP4 de taxa constante."""
    def __init__(self, page):
        self.page = page; self.cdp = page.context.new_cdp_session(page); self.frames = []; self.ativo = False
        self.cdp.on("Page.screencastFrame", self._quadro)

    def _quadro(self, p):
        if self.ativo:
            arq = self.dir / f"f{len(self.frames):05d}.jpg"
            arq.write_bytes(base64.b64decode(p["data"]))
            self.frames.append((p["metadata"]["timestamp"], arq))
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]})
        except Exception:
            pass

    def iniciar(self, nome):
        self.nome = nome; self.dir = DEMO / f"_frames_{nome}"
        shutil.rmtree(self.dir, ignore_errors=True); self.dir.mkdir(parents=True)
        self.frames = []; self.ativo = True; self.t0 = time.time()
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 90, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})
        self.page.mouse.move(*self.pos, steps=1)   # força o primeiro quadro
        self.page.wait_for_timeout(250)

    def parar(self, alvo_s=None, acelerar_para=None):
        self.page.wait_for_timeout(200)
        fim = time.time()
        self.cdp.send("Page.stopScreencast"); self.ativo = False
        if not self.frames:
            raise SystemExit(f"sem quadros na cena {self.nome}")
        lst = self.dir / "lista.txt"; linhas = []
        for i, (ts, arq) in enumerate(self.frames):
            prox = self.frames[i + 1][0] if i + 1 < len(self.frames) else fim
            linhas += [f"file '{arq.as_posix()}'", f"duration {max(prox - ts, 0.001):.4f}"]
        linhas.append(f"file '{self.frames[-1][1].as_posix()}'")
        lst.write_text("\n".join(linhas), encoding="utf-8")
        real = fim - self.frames[0][0]
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white"
        if acelerar_para and real > acelerar_para:
            vf += f",setpts=PTS*{acelerar_para / real:.4f}"
        out = DEMO / f"{self.nome}.mp4"
        r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf + ",fps=30,format=yuv420p",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "16", str(out)], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-1500:]); raise SystemExit("ffmpeg falhou")
        shutil.rmtree(self.dir, ignore_errors=True)
        print(f"  {self.nome}: {len(self.frames)} quadros, {real:.1f} s reais" + (f" -> acelerado para {acelerar_para:.1f} s" if acelerar_para and real > acelerar_para else ""))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--url", default="http://127.0.0.1:8080"); ap.add_argument("--manter", action="store_true")
    a = ap.parse_args(); base = a.url.rstrip("/")
    conn = oracledb.connect(user="STARTUP", password="Startup2026", dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))
    cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM CONTATO_RESULTADO")
    if cur.fetchone()[0]:
        raise SystemExit("Já existem contatos registrados; limpe antes de gravar (o vídeo mostra o primeiro registro).")
    for k in list(os.environ):
        if k.startswith(("CHROME_", "CLAUDE", "ELECTRON_")):
            os.environ.pop(k)

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5, locale="pt-BR")
        ctx.add_init_script(CURSOR_JS)
        ctx.add_init_script("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = 'html{scroll-behavior:auto!important}'; document.head.appendChild(s); });")
        pg = ctx.new_page()
        g = Gravador(pg); g.pos = (640, 360)
        pos = [640, 360]

        def mover(x, y, passos=12):
            pg.mouse.move(x, y, steps=passos); pos[:] = [x, y]; g.pos = (x, y)

        def ate(loc, dx=0.5, dy=0.5, passos=12):
            loc.scroll_into_view_if_needed(); bb = loc.bounding_box()
            mover(bb["x"] + bb["width"] * dx, bb["y"] + bb["height"] * dy, passos)

        def clicar(loc, pausa=350):
            ate(loc); pg.wait_for_timeout(pausa)
            bb = loc.bounding_box()                      # re-mede: a pagina pode ter rolado nesse meio-tempo
            mover(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 3)
            pg.mouse.down(); pg.mouse.up()

        def digitar(loc, texto):
            clicar(loc); pg.keyboard.press("Control+A"); pg.keyboard.type(texto, delay=22)

        def completar(t0, alvo):
            resto = alvo - (time.time() - t0)
            if resto > 0:
                pg.wait_for_timeout(int(resto * 1000))

        alvo = lambda cid: DUR[cid] + 0.6 + 0.8

        # aquecimento: a 1a PREDICTION_PROBABILITY apos subir a API carrega o modelo (~5 s); nao queremos isso no video
        for u, m, d in (("/api/saude", "GET", None), ("/api/alunos/" + ALUNO.replace(" ", "%20") + "/predicao", "POST", {}),
                        ("/api/alunos/" + ALUNO.replace(" ", "%20") + "/predicao", "POST", {"recencia_dias": 1}), ("/api/diretoria", "GET", None)):
            urllib.request.urlopen(urllib.request.Request(base + u, data=json.dumps(d).encode() if d is not None else None, method=m,
                                                          headers={"Content-Type": "application/json"})).read()
        pg.goto(base + "/#fila"); pg.wait_for_selector("tr[data-aluno]"); pg.wait_for_timeout(1200)
        mover(640, 360, 1)

        # ---------------------------------------------------------------- 04 fila
        print("gravando cenas...")
        g.iniciar("04_fila"); t0 = time.time()
        ate(pg.locator("#status")); pg.wait_for_timeout(2600)
        ate(pg.locator("#fila-meta")); pg.wait_for_timeout(2600)
        ate(pg.locator("#seg-escopo button[data-escopo=fila]")); pg.wait_for_timeout(2800)
        ate(pg.locator("tr.grupo").first, 0.2); pg.wait_for_timeout(2400)
        ate(pg.locator(f"tr[data-aluno='{ALUNO}'] .barra")); pg.wait_for_timeout(2000)
        for _ in range(7):
            pg.mouse.wheel(0, 260); pg.wait_for_timeout(420)
        pg.wait_for_timeout(1200)
        for _ in range(7):
            pg.mouse.wheel(0, -260); pg.wait_for_timeout(260)
        completar(t0, alvo("04")); g.parar(acelerar_para=alvo("04"))

        # ---------------------------------------------------------------- 05 aluno
        g.iniciar("05_aluno"); t0 = time.time()
        clicar(pg.locator(f"tr[data-aluno='{ALUNO}']"), 600); pg.wait_for_selector("#btn-live"); pg.wait_for_timeout(1800)
        ate(pg.locator(".g-num div").nth(0)); pg.wait_for_timeout(1300)
        ate(pg.locator(".g-num div").nth(1)); pg.wait_for_timeout(1300)
        ate(pg.locator("ul.fatores")); pg.wait_for_timeout(2600)
        clicar(pg.locator("#btn-live")); pg.wait_for_function("document.querySelector('#live-out').textContent.includes('ms')"); pg.wait_for_timeout(2600)
        clicar(pg.locator("#btn-ese")); pg.wait_for_function("document.querySelector('#live-out').textContent.includes('Se voltar')"); pg.wait_for_timeout(3600)
        ate(pg.locator(".spark")); pg.wait_for_timeout(1500)
        pg.locator("#gaveta").evaluate("e => e.scrollTo({top: 560, behavior: 'smooth'})"); pg.wait_for_timeout(1200)
        ate(pg.locator("#msg-sug")); pg.wait_for_timeout(1500)
        completar(t0, alvo("05")); g.parar(acelerar_para=alvo("05"))

        # ---------------------------------------------------------------- 06 registro
        g.iniciar("06_registro"); t0 = time.time()
        pg.locator("#gaveta").evaluate("e => e.scrollTo({top: 900, behavior: 'smooth'})"); pg.wait_for_timeout(1300)
        clicar(pg.locator(".res-btns button[data-r=REATIVADO]")); pg.wait_for_timeout(1200)
        ate(pg.locator("#r-canal")); pg.wait_for_timeout(900)
        digitar(pg.locator("#r-resp"), RESP); pg.wait_for_timeout(400)
        digitar(pg.locator("#r-obs"), "Demonstração: mandei o resumo; retoma quarta."); pg.wait_for_timeout(700)
        clicar(pg.locator("#btn-gravar")); pg.wait_for_selector(".gravado"); pg.wait_for_timeout(800)
        pg.locator("#gaveta").evaluate("e => e.scrollTo({top: e.scrollHeight, behavior: 'smooth'})"); pg.wait_for_timeout(1000)
        ate(pg.locator(".gravado")); pg.wait_for_timeout(2200)
        ate(pg.locator("#hist li").first); pg.wait_for_timeout(1500)
        completar(t0, alvo("06")); g.parar(acelerar_para=alvo("06"))

        # ---------------------------------------------------------------- 07 prova SQL
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        g.iniciar("07_sql"); t0 = time.time()
        clicar(pg.locator(".abas a[data-aba=tecnico]")); pg.wait_for_selector("#provas button"); pg.wait_for_timeout(700)
        pg.locator("#provas").scroll_into_view_if_needed(); pg.wait_for_timeout(500)
        clicar(pg.locator("#provas button[data-p=ultimos_contatos]")); pg.wait_for_selector("#prova-saida table"); pg.wait_for_timeout(500)
        pg.evaluate("window.scrollBy({top: 260, behavior: 'smooth'})"); pg.wait_for_timeout(1000)
        ate(pg.locator("#prova-saida table tbody tr").first); pg.wait_for_timeout(2400)
        pg.locator("#provas").scroll_into_view_if_needed()
        clicar(pg.locator("#provas button[data-p=status_fila]")); pg.wait_for_selector("#prova-saida table"); pg.wait_for_timeout(2000)
        clicar(pg.locator("#provas button[data-p=duality_view]")); pg.wait_for_selector("#prova-saida table"); pg.wait_for_timeout(600)
        ate(pg.locator("#prova-saida table tbody tr").first, 0.3); pg.wait_for_timeout(1500)
        completar(t0, alvo("07")); g.parar(acelerar_para=alvo("07"))

        # ---------------------------------------------------------------- 08 scoring (acelerado)
        pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(400)
        pg.evaluate("""() => { const d = document.createElement('div'); d.id='__acel'; d.textContent='⏩ trecho acelerado';
            Object.assign(d.style,{position:'fixed',top:'78px',right:'18px',zIndex:99999,background:'#FFB703',color:'#0B2545',
            font:'600 14px Inter,sans-serif',padding:'6px 12px',borderRadius:'999px'}); document.body.appendChild(d); }""")
        g.iniciar("08_scoring")
        ate(pg.locator("#tec-job")); pg.wait_for_timeout(900)
        clicar(pg.locator("#btn-scoring"))
        pg.wait_for_selector("#scoring-msg.ok", timeout=180000); pg.wait_for_timeout(600)
        ate(pg.locator("#scoring-msg")); pg.wait_for_timeout(1500)
        ate(pg.locator("#tec-execucoes table tbody tr").first); pg.wait_for_timeout(1200)
        g.parar(acelerar_para=alvo("08"))
        pg.evaluate("document.getElementById('__acel').remove()")

        # ---------------------------------------------------------------- 09 diretoria
        g.iniciar("09_diretoria"); t0 = time.time()
        clicar(pg.locator(".abas a[data-aba=diretoria]")); pg.wait_for_selector(".kpi"); pg.wait_for_timeout(1500)
        for k in ("na_fila", "receita_anual_em_risco", "contatos_registrados", "receita_preservada_estimada"):
            ate(pg.locator(f".kpi[data-k={k}]")); pg.wait_for_timeout(1500)
        ate(pg.locator("#dir-resultados")); pg.wait_for_timeout(1300)
        digitar(pg.locator("#ticket"), "400"); pg.wait_for_timeout(500)
        clicar(pg.locator("#form-ticket button")); pg.wait_for_timeout(1200)
        ate(pg.locator(".kpi[data-k=receita_preservada_estimada]")); pg.wait_for_timeout(1800)
        ate(pg.locator("#ticket-msg")); pg.wait_for_timeout(1200)
        completar(t0, alvo("09")); g.parar(acelerar_para=alvo("09"))
        b.close()

    if not a.manter:
        http = lambda m, u, d=None: urllib.request.urlopen(urllib.request.Request(base + u, data=json.dumps(d).encode() if d else None,
                                                                              method=m, headers={"Content-Type": "application/json"}))
        http("PUT", "/api/parametros", {"ticket_mensal": 350})
        cur.execute("DELETE FROM CONTATO_RESULTADO WHERE RESPONSAVEL = :r", r=RESP)
        cur.execute("UPDATE RISCO_ALUNO_SNAPSHOT SET STATUS_ATENDIMENTO='PENDENTE', OBSERVACAO=NULL WHERE NOME = :n", n=ALUNO)
        conn.commit()
        print("limpeza: contato de demonstração apagado e ticket de volta a R$ 350")
    print("ok")


if __name__ == "__main__":
    main()
