# -*- coding: utf-8 -*-
"""
Etapa 01 — Preparação e normalização dos eventos do LMS.

Lê o parquet bruto (logs do LMS), padroniza tipos e nomes, deriva colunas
analíticas (timestamp, aluno_id, fase_num, capítulo, tipo de conteúdo, flags
de evento, hora, noite, fim de semana) e salva `outputs/eventos_normalizados.parquet`.

Decisões:
- Linhas com nome "-" (usuário não identificado) são descartadas: não podem
  ser atribuídas a alunos e representam < 1% dos eventos.
- Eventos administrativos (matrícula, notas lançadas por tutor, rotinas cron,
  configurações de curso) recebem `is_atividade_aluno = False`. Eles ficam no
  arquivo para auditoria, mas as métricas de engajamento e o rótulo de
  inatividade usam apenas eventos em que o aluno efetivamente agiu no LMS
  (origem "web" e evento não administrativo).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    ARQ_PARQUET_BRUTO,
    DIR_OUTPUTS,
    EVENTOS_ADMINISTRATIVOS,
    EVENTOS_ENTREGA_TAREFA,
    EVENTOS_NOTA,
    EVENTO_PROGRESSO,
    EVENTO_QUIZ_ENTREGA,
    EVENTO_QUIZ_INICIO,
    log,
)

ARQ_SAIDA = DIR_OUTPUTS / "eventos_normalizados.parquet"

# Mapeamento do prefixo do contexto ("Player HTML: Cap 3 - ...") para tipo de conteúdo.
MAPA_TIPO_CONTEUDO = {
    "Player HTML": "HTML",
    "Player PDF": "PDF",
    "Player de Vídeo": "Vídeo",
    "Player de Áudio": "Áudio",
    "Questionário": "Questionário",
    "Tarefa": "Tarefa",
}


def classificar_tipo_conteudo(contexto: pd.Series) -> pd.Series:
    prefixo = contexto.fillna("").str.split(":").str[0].str.strip()
    tipo = prefixo.map(MAPA_TIPO_CONTEUDO)
    return tipo.fillna("Outro")


def main() -> None:
    log(f"Lendo {ARQ_PARQUET_BRUTO}")
    bruto = pd.read_parquet(ARQ_PARQUET_BRUTO)
    n_total = len(bruto)
    log(f"Eventos brutos: {n_total:,}")

    # --- descarta usuários não identificados -------------------------------
    mask_aluno = bruto["nome"].fillna("-").str.match(r"^Aluno \d+$")
    n_descartados = int((~mask_aluno).sum())
    df = bruto.loc[mask_aluno].copy()
    log(f"Descartadas {n_descartados:,} linhas sem aluno identificável (nome '-')")

    # --- normalização ---------------------------------------------------------
    df["timestamp"] = pd.to_datetime(df["hora"], format="%d/%m/%Y %H:%M")
    df["data"] = df["timestamp"].dt.normalize()
    df["aluno_id"] = df["nome"].str.strip()
    df["fase_num"] = df["fase"].str.extract(r"(\d+)", expand=False).astype("int8")
    df["capitulo"] = (
        df["contexto"].str.extract(r"Cap (\d+)", expand=False).astype("float").astype("Int16")
    )
    df["tipo_conteudo"] = classificar_tipo_conteudo(df["contexto"])

    # --- flags de evento --------------------------------------------------------
    df["is_progresso"] = df["evento"].eq(EVENTO_PROGRESSO)
    df["is_quiz_inicio"] = df["evento"].eq(EVENTO_QUIZ_INICIO)
    df["is_quiz_entrega"] = df["evento"].eq(EVENTO_QUIZ_ENTREGA)
    df["is_entrega_tarefa"] = df["evento"].isin(EVENTOS_ENTREGA_TAREFA)
    df["is_nota"] = df["evento"].isin(EVENTOS_NOTA)
    df["is_administrativo"] = df["evento"].isin(EVENTOS_ADMINISTRATIVOS)
    # Ação efetiva do aluno na plataforma (base para engajamento e rótulo).
    df["is_atividade_aluno"] = (~df["is_administrativo"]) & df["origem"].eq("web")

    # --- tempo ------------------------------------------------------------------
    df["hora_dia"] = df["timestamp"].dt.hour.astype("int8")
    df["noite"] = df["hora_dia"].between(19, 23)
    df["dia_semana"] = df["timestamp"].dt.dayofweek.astype("int8")  # 0 = segunda
    df["fim_de_semana"] = df["dia_semana"] >= 5

    colunas = [
        "timestamp", "data", "aluno_id", "fase", "fase_num", "capitulo", "tipo_conteudo",
        "contexto", "componente", "evento", "origem",
        "is_progresso", "is_quiz_inicio", "is_quiz_entrega", "is_entrega_tarefa", "is_nota",
        "is_administrativo", "is_atividade_aluno",
        "hora_dia", "noite", "dia_semana", "fim_de_semana",
    ]
    df = df[colunas].sort_values(["aluno_id", "timestamp"]).reset_index(drop=True)

    # A coluna "hora" do brief é a hora cheia do evento; mantemos como `hora` também
    # para aderência ao nome pedido.
    df["hora"] = df["hora_dia"]

    df.to_parquet(ARQ_SAIDA, index=False)
    log(f"Salvo {ARQ_SAIDA} ({len(df):,} eventos, {df['aluno_id'].nunique()} alunos)")

    # --- resumo ---------------------------------------------------------------
    resumo = {
        "eventos_brutos": n_total,
        "eventos_descartados_sem_aluno": n_descartados,
        "eventos_normalizados": len(df),
        "eventos_atividade_aluno": int(df["is_atividade_aluno"].sum()),
        "eventos_administrativos": int(df["is_administrativo"].sum()),
        "alunos_distintos": int(df["aluno_id"].nunique()),
        "alunos_com_atividade": int(df.loc[df["is_atividade_aluno"], "aluno_id"].nunique()),
        "periodo": [str(df["data"].min().date()), str(df["data"].max().date())],
        "eventos_com_capitulo": int(df["capitulo"].notna().sum()),
        "capitulo_max_por_fase": df.groupby("fase_num")["capitulo"].max().astype(int).to_dict(),
        "tipo_conteudo": df["tipo_conteudo"].value_counts().to_dict(),
    }
    for k, v in resumo.items():
        log(f"  {k}: {v}")


if __name__ == "__main__":
    main()
