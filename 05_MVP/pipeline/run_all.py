# -*- coding: utf-8 -*-
"""
Executa o pipeline completo do MVP (etapas 01 → 06) em ordem.

Cada etapa roda em um subprocesso com o mesmo interpretador Python; a execução
para na primeira etapa que falhar (código de saída ≠ 0) e o código de saída
dessa etapa é propagado.

Uso:
    python pipeline/run_all.py            # roda tudo
    python pipeline/run_all.py --de 05    # começa na etapa 05 (pula 01–04)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

DIR_PIPELINE = Path(__file__).resolve().parent

ETAPAS = [
    ("01", "01_preparar_eventos.py", "Normalizar eventos brutos do LMS"),
    ("02", "02_features_semanais.py", "Construir features aluno-semana e rótulo"),
    ("03", "03_treinar_modelo.py", "Treinar e avaliar modelos (risco 21d + transição de fases)"),
    ("04", "04_scoring_e_atrito.py", "Scoring atual, KPIs e atrito de conteúdo"),
    ("05", "05_gerar_figuras.py", "Figuras PNG"),
    ("06", "06_gerar_dashboard.py", "Dashboard HTML autocontido"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Roda o pipeline do MVP Retena de ponta a ponta.")
    parser.add_argument("--de", default="01", help="Etapa inicial (01..06). Padrão: 01.")
    args = parser.parse_args()

    etapas = [e for e in ETAPAS if e[0] >= args.de]
    if not etapas:
        print(f"Nenhuma etapa >= {args.de}. Etapas válidas: {', '.join(e[0] for e in ETAPAS)}")
        return 2

    inicio_total = time.time()
    print(f"Pipeline Retena — {len(etapas)} etapa(s) · python {sys.version.split()[0]}")
    print("=" * 72)
    for codigo, arquivo, descricao in etapas:
        caminho = DIR_PIPELINE / arquivo
        if not caminho.exists():
            print(f"[{codigo}] ERRO: arquivo não encontrado: {caminho}")
            return 1
        print(f"[{codigo}] {descricao}  ({arquivo})")
        inicio = time.time()
        resultado = subprocess.run([sys.executable, str(caminho)], cwd=str(DIR_PIPELINE))
        duracao = time.time() - inicio
        if resultado.returncode != 0:
            print("=" * 72)
            print(f"[{codigo}] FALHOU com código {resultado.returncode} após {duracao:.1f}s. Pipeline interrompido.")
            return resultado.returncode
        print(f"[{codigo}] OK em {duracao:.1f}s")
        print("-" * 72)
    print(f"Pipeline concluído em {time.time() - inicio_total:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
