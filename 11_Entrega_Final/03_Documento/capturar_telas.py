# -*- coding: utf-8 -*-
"""capturar_telas.py - prints reais do MVP (API em http://127.0.0.1:8080) para o documento e o pitch.
Registra 1 contato de DEMONSTRACAO (responsavel 'Mariana (demonstração)'), fotografa e depois apaga (--manter para nao apagar).
Uso: python capturar_telas.py [--url ...] [--manter]"""
import argparse, os, sys
from pathlib import Path
import oracledb
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
IMG = AQUI / "img"; IMG.mkdir(exist_ok=True)
RESP = "Mariana (demonstração)"
ap = argparse.ArgumentParser(); ap.add_argument("--url", default="http://127.0.0.1:8080"); ap.add_argument("--manter", action="store_true")
a = ap.parse_args()
for k in list(os.environ):
    if k.startswith(("CHROME_", "CLAUDE", "ELECTRON_")):
        os.environ.pop(k)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 860}, device_scale_factor=1.5)
    pg.goto(a.url + "/#fila"); pg.wait_for_selector("tr[data-aluno]"); pg.wait_for_timeout(600)
    pg.screenshot(path=str(IMG / "mvp_1_fila.png"))
    pg.click("tr[data-aluno='Aluno 0068']"); pg.wait_for_selector("#btn-live"); pg.wait_for_timeout(500)
    pg.click("#btn-ese"); pg.wait_for_function("document.querySelector('#live-out').textContent.includes('%')"); pg.wait_for_timeout(300)
    pg.screenshot(path=str(IMG / "mvp_2_aluno.png"))
    pg.click(".res-btns button[data-r=REATIVADO]")
    pg.fill("#r-resp", RESP)
    pg.select_option("#r-canal", "WHATSAPP")
    pg.fill("#r-obs", "registro de demonstração: travou no início da Fase 5; enviei resumo; retoma quarta")
    pg.click("#btn-gravar"); pg.wait_for_selector(".gravado"); pg.wait_for_timeout(600)
    pg.locator(".gravado").scroll_into_view_if_needed(); pg.locator("#gaveta").evaluate("e => e.scrollTop = e.scrollTop + 160"); pg.wait_for_timeout(300)
    pg.screenshot(path=str(IMG / "mvp_3_registro.png"))
    pg.keyboard.press("Escape")
    pg.goto(a.url + "/#diretoria"); pg.wait_for_selector(".kpi"); pg.wait_for_timeout(800)
    pg.screenshot(path=str(IMG / "mvp_4_diretoria.png"))
    pg.goto(a.url + "/#tecnico"); pg.wait_for_selector("#provas button"); pg.wait_for_timeout(500)
    pg.click("#provas button[data-p=ultimos_contatos]"); pg.wait_for_selector("#prova-saida table"); pg.wait_for_timeout(400)
    pg.locator("#prova-saida").scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    pg.screenshot(path=str(IMG / "mvp_5_tecnico.png"))
    b.close()

if not a.manter:
    c = oracledb.connect(user="STARTUP", password=os.environ.get("ORACLE_PASSWORD", "Startup2026"),
                         dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))
    cur = c.cursor()
    cur.execute("DELETE FROM CONTATO_RESULTADO WHERE RESPONSAVEL = :r", r=RESP)
    cur.execute("""UPDATE RISCO_ALUNO_SNAPSHOT s SET STATUS_ATENDIMENTO='PENDENTE', OBSERVACAO=NULL
                    WHERE STATUS_ATENDIMENTO <> 'PENDENTE' AND NOT EXISTS (SELECT 1 FROM CONTATO_RESULTADO c WHERE c.NOME=s.NOME)""")
    c.commit()
print("telas em", IMG)
