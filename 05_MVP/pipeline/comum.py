# -*- coding: utf-8 -*-
"""
Constantes e utilitários compartilhados pelo pipeline do MVP.

Todos os caminhos são relativos à raiz de 05_MVP, de modo que os scripts
funcionam independentemente do diretório de trabalho atual.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
RAIZ_MVP = Path(__file__).resolve().parent.parent
DIR_OUTPUTS = RAIZ_MVP / "outputs"
DIR_FIGS = DIR_OUTPUTS / "figs"
DIR_MODEL = RAIZ_MVP / "model"
DIR_DASHBOARD = RAIZ_MVP / "dashboard"
ARQ_PARQUET_BRUTO = RAIZ_MVP.parent / "08_Dados" / "logs_lms.parquet"

for _d in (DIR_OUTPUTS, DIR_FIGS, DIR_MODEL, DIR_DASHBOARD):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Domínio do curso
# ---------------------------------------------------------------------------
# Total de capítulos por fase (informado no brief e confirmado nos logs).
CAPITULOS_POR_FASE = {1: 10, 2: 12, 3: 10, 4: 11, 5: 8}
NOMES_FASES = {
    1: "Fase 1 - Pensando Aplicação Mobile",
    2: "Fase 2 - Serviços São Fundamentais",
    3: "Fase 3 - Evolução Tecnológica",
    4: "Fase 4 - Integração",
    5: "Fase 5 - Tecnologias",
}

# Data do último evento da base (referência "hoje" para KPIs).
DATA_REFERENCIA = pd.Timestamp("2026-08-26")
# Cortes semanais (domingos) usados para gerar a base aluno-semana.
PRIMEIRO_CORTE = pd.Timestamp("2026-02-01")
ULTIMO_CORTE = pd.Timestamp("2026-08-23")
HORIZONTE_ROTULO_DIAS = 21
# Split temporal do modelo principal.
DATA_SPLIT_TESTE = pd.Timestamp("2026-06-01")

# Faixas de risco (probabilidade prevista de inatividade em 21 dias).
LIMIAR_ALTO = 0.60
LIMIAR_MEDIO = 0.30

# ---------------------------------------------------------------------------
# Classificação de eventos
# ---------------------------------------------------------------------------
# Eventos administrativos/sistêmicos: gerados por tutor, coordenação ou rotinas
# (cron) e apenas *afetam* o aluno; não representam ação do aluno no LMS.
EVENTOS_ADMINISTRATIVOS = {
    "Criação de enrolment para usuário",
    "Usuário inscrito no curso",
    "Usuário removido do curso",
    "Desinscrição de usuário atualizada",
    "Instância de inscrição criada",
    "Papel atribuído",
    "Papel desatribuído",
    "Membro adcionado ao grupo",
    "Membro removido do grupo",
    "Grupo criado",
    "Grupo apagado",
    "Reprocessamento de curso executado",
    "Nota assign enviado",
    "Nota Sub AD enviada",
    "Usuário recebeu nota",
    "O envio foi avaliado.",
    "Nota excluída",
    "Alteração de nota em caso de atraso",
    "Uma prorrogação foi concedida.",
    "Evento criado no calendário",
    "Evento atualizado no calendário",
    "Evento excluído do calendário",
    "Criado relação de conteúdos",
    "Conteúdo relacionado com codrelacoes",
    "Conteúdo desrelacionado de codrelacoes",
    "Codrelações removidos de Atividade On-Line",
    "Curso relacionado com codrelacao",
    "Criação de conteúdo em lote",
    "Conteúdo duplicado",
    "Duplicação múltipla de conteúdos concluída",
    "Módulo de curso atualizado",
    "Módulo de curso criado",
    "Módulo de curso excluído",
    "Módulos de um curso copiado para outro curso",
    "Módulos de uma disciplina copiado para outro curso",
    "Atualização da ocultação da atividade",
    "Criado feedbaack pra conteudo",
    "Atividade On-Line atualizada",
    "Atividade presencial disponibilizada",
    "Sobreposição de questionário criada",
    "Sobreposição de questionário atualizada",
    "Tipo de envio de nota adicionado em assign",
    "Tipo de envio de nota adicionado em quiz",
    "Tipo de envio de nota removido de quiz",
    "Curso criado",
    "Curso atualizado",
    "Seção do curso criada",
    "Tópico de curso atualizado",
    "Erro ao tentar registrar o tempo de visualização de um conteúdo HTML",
}

EVENTO_PROGRESSO = "Progresso de conteúdo atualizado"
EVENTO_QUIZ_INICIO = "Tentativa do questionário iniciada"
EVENTO_QUIZ_ENTREGA = "Tentativa do questionário entregue"
EVENTOS_ENTREGA_TAREFA = {
    "Um envio foi submetido.",
    "Entregou uma atividade",
    "Submissão criada.",
    "Atividade On-Line enviada",
}
EVENTOS_NOTA = {"Usuário recebeu nota", "Nota assign enviado", "Nota Sub AD enviada"}

# Paleta sóbria compartilhada por figuras e dashboard.
PALETA = {
    "primaria": "#0B1F3A",
    "acento": "#22C55E",
    "alerta": "#F59E0B",
    "critico": "#EF4444",
    "fundo": "#F6F7FB",
    "cinza": "#6B7280",
    "cinza_claro": "#E5E7EB",
    "azul": "#2563EB",
    "azul_claro": "#93C5FD",
}


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def salvar_json(obj, caminho: Path) -> None:
    """Salva JSON legível (UTF-8, indentado), convertendo tipos numpy/pandas."""

    def _conv(o):
        import numpy as np

        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if pd.isna(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp,)):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        if isinstance(o, float) and pd.isna(o):
            return None
        raise TypeError(f"Tipo não serializável: {type(o)}")

    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_conv)


def carregar_json(caminho: Path):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def faixa_risco(p: float) -> str:
    """Converte probabilidade em faixa de risco (Alto/Médio/Baixo)."""
    if p >= LIMIAR_ALTO:
        return "Alto"
    if p >= LIMIAR_MEDIO:
        return "Médio"
    return "Baixo"


def log(msg: str) -> None:
    print(f"[{pd.Timestamp.now():%H:%M:%S}] {msg}", flush=True)
