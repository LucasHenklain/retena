# -*- coding: utf-8 -*-
"""
modelo_financeiro.py - projecao financeira simplificada de 3 anos da Retena (2027-2029).

Todas as premissas abaixo sao ESTIMATIVAS da equipe (rotuladas assim no documento), exceto:
  - precos publicados (01_Documento/anexos/conceito_final.md, secao 9; kit da banca v3)
  - trajetoria de ARR publicada (conceito_final.md secao 10: ano 1 R$ 0,5 mi; ano 2 R$ 1,4 mi; ano 3 R$ 2,5-4,3 mi)
  - preco de lista do Oracle Autonomous AI Database (ECPU FAQ da Oracle; confirmar no price list vigente)
Gera: modelo_financeiro.xlsx (com formulas) e modelo_financeiro.json (lido pelo gerador do documento).
Uso: python modelo_financeiro.py
"""
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

AQUI = Path(__file__).resolve().parent
ANOS = ["Ano 1 (2027)", "Ano 2 (2028)", "Ano 3 (2029)"]

P = {
    # ---------------- receita (motor = alunos ativos sob contrato)
    "preco_efetivo_aluno_mes": 4.00,       # R$/aluno ativo/mes efetivo: mix Pro R$ 6 (<10k) com desconto de conversao do piloto,
                                           # Pro R$ 4 (10-50k) e Essencial R$ 2 (<=5k). E o mesmo R$ 48/ano usado no SAM/SOM publicados.
    "alunos_fim_ano": [10_000, 30_000, 52_000],   # 2 IES / 6 IES / 11 IES medias (~4,7-5 mil alunos cada)
    "alunos_inicio_ano": [0, 10_000, 30_000],
    "meses_receita_ano1": 6,               # contratos do ano 1 comecam no 2o semestre (apos pilotos de 90 dias)
    "novas_ies": [2, 4, 5],
    "setup_por_ies": 15_000,               # faixa publicada R$ 10-25 mil; IES media de ~5 mil alunos
    "pilotos": [6, 8, 10],                 # pilotos de 90 dias a R$ 5 mil (publicado); funil do ano 1: 30 diagnosticos -> 6 pilotos -> 2 contratos
    "preco_piloto": 5_000,
    "megagrupo_upside_alunos": 50_000,     # cenario otimista (fase 2, via ecossistema Oracle): 1 megagrupo
    "megagrupo_preco": 3.00,               # faixa 50k+ publicada
    "megagrupo_meses_ano3": 6,
    # ---------------- impostos e custos variaveis
    "impostos_pct": 0.10,                  # Simples Nacional, anexo III com fator R (6% -> ~11%); media estimada
    "comissao_pct_arr_novo": 0.08,         # comissao de vendas sobre o ARR novo do ano
    # ---------------- Oracle (US$ lista; cambio estimado)
    "usd_brl": 5.50,
    "ecpu_hora_usd": 0.336,                # Autonomous Transaction Processing, ECPU (licenca incluida) - Oracle ECPU FAQ
    "storage_gb_mes_usd": 0.1156,          # ATP storage GB/mes
    "horas_mes": 730,
    "ecpu_medio": [2, 4, 8],               # ano 1: 1 banco de producao (min. 2 ECPU) no 2o semestre; ano 3: 2 bancos
    "storage_gb": [100, 300, 800],
    "meses_oracle_pago_ano1": 6,           # 1o semestre do ano 1 = pilotos no Always Free (custo zero)
    "outros_cogs_mes": [800, 2_000, 4_000],  # monitoramento, backup externo, e-mail transacional, suporte
    # ---------------- equipe (custo total com encargos, R$/ano)
    "equipe": {
        "Socios (5) - pro-labore":            [5 * 3_000 * 12, 5 * 8_000 * 12, 5 * 11_000 * 12],
        "Customer success / implantacao":     [0, 1 * 13_600 * 12, 2 * 13_600 * 12],
        "Vendas (SDR/executivo)":             [0, 1 * 10_200 * 12, 2 * 10_200 * 12],
        "Engenharia (dev pleno)":             [0, 0, 1 * 17_000 * 12],
    },
    # ---------------- demais despesas operacionais (R$/ano)
    "marketing_digital": [36_000, 120_000, 200_000],     # LinkedIn/ABM, conteudo, eventos Semesp/ABED
    "comercial_viagens": [24_000, 60_000, 90_000],
    "ga_admin": [36_000, 60_000, 84_000],                # contabilidade, juridico/LGPD, ferramentas, seguro
}


def calcular():
    r = {"anos": ANOS}
    preco = P["preco_efetivo_aluno_mes"]
    arr_fim = [a * preco * 12 for a in P["alunos_fim_ano"]]
    medio = [(i + f) / 2 for i, f in zip(P["alunos_inicio_ano"], P["alunos_fim_ano"])]
    # ano 1: 2 IES (10 mil alunos) entrando no 2o semestre -> 10 mil x R$ 4 x 6 meses = R$ 240 mil
    # anos 2 e 3: rampa linear -> media de alunos do ano x R$ 4 x 12
    assinatura = [P["alunos_fim_ano"][0] * preco * P["meses_receita_ano1"], medio[1] * preco * 12, medio[2] * preco * 12]
    setup = [n * P["setup_por_ies"] for n in P["novas_ies"]]
    pilotos = [n * P["preco_piloto"] for n in P["pilotos"]]
    receita_bruta = [a + s + p for a, s, p in zip(assinatura, setup, pilotos)]
    impostos = [x * P["impostos_pct"] for x in receita_bruta]
    receita_liq = [b - i for b, i in zip(receita_bruta, impostos)]

    oracle_mes = [(e * P["ecpu_hora_usd"] * P["horas_mes"] + g * P["storage_gb_mes_usd"]) * P["usd_brl"]
                  for e, g in zip(P["ecpu_medio"], P["storage_gb"])]
    oracle_ano = [oracle_mes[0] * P["meses_oracle_pago_ano1"], oracle_mes[1] * 12, oracle_mes[2] * 12]
    outros_cogs = [m * 12 for m in P["outros_cogs_mes"]]
    cs_implantacao = P["equipe"]["Customer success / implantacao"]
    cogs = [o + x + c for o, x, c in zip(oracle_ano, outros_cogs, cs_implantacao)]
    lucro_bruto = [l - c for l, c in zip(receita_liq, cogs)]

    arr_novo = [arr_fim[0], arr_fim[1] - arr_fim[0], arr_fim[2] - arr_fim[1]]
    comissoes = [x * P["comissao_pct_arr_novo"] for x in arr_novo]
    equipe_opex = {k: v for k, v in P["equipe"].items() if k != "Customer success / implantacao"}
    equipe_total = [sum(v[i] for v in equipe_opex.values()) for i in range(3)]
    opex = [equipe_total[i] + P["marketing_digital"][i] + P["comercial_viagens"][i] + P["ga_admin"][i] + comissoes[i]
            for i in range(3)]
    ebitda = [lb - o for lb, o in zip(lucro_bruto, opex)]
    caixa_acum, acc, minimo = [], 0, 0
    for e in ebitda:
        acc += e; caixa_acum.append(acc); minimo = min(minimo, acc)

    # cenario otimista: 1 megagrupo no 2o semestre do ano 3
    mega_receita = P["megagrupo_upside_alunos"] * P["megagrupo_preco"] * P["megagrupo_meses_ano3"]
    mega_arr = P["megagrupo_upside_alunos"] * P["megagrupo_preco"] * 12
    ebitda3_otimista = ebitda[2] + mega_receita * (1 - P["impostos_pct"]) - 4 * P["ecpu_hora_usd"] * P["horas_mes"] * P["usd_brl"] * 6 \
        - mega_arr * P["comissao_pct_arr_novo"]

    # unit economics (ano 2, regime)
    arr_por_ies = 5_000 * preco * 12
    cac = (P["marketing_digital"][1] + P["comercial_viagens"][1] + P["equipe"]["Vendas (SDR/executivo)"][1]
           + comissoes[1]) / P["novas_ies"][1]
    margem_bruta = [lb / rl if rl else 0 for lb, rl in zip(lucro_bruto, receita_liq)]
    mb_regime = 0.80
    ltv = arr_por_ies * mb_regime * 5            # vida media 5 anos (churn logo 20%/ano, estimativa conservadora)
    payback_meses = cac / (arr_por_ies / 12 * mb_regime)
    custo_oracle_por_aluno_mes = [oracle_mes[i] / max(P["alunos_fim_ano"][i], 1) for i in range(3)]

    r.update(dict(
        arr_fim=arr_fim, alunos_fim=P["alunos_fim_ano"], ies_fim=[2, 6, 11], assinatura=assinatura, setup=setup,
        pilotos=pilotos, receita_bruta=receita_bruta, impostos=impostos, receita_liquida=receita_liq,
        oracle_mes=oracle_mes, oracle_ano=oracle_ano, outros_cogs=outros_cogs, cs_implantacao=cs_implantacao,
        cogs=cogs, lucro_bruto=lucro_bruto, margem_bruta=margem_bruta, equipe=equipe_opex, equipe_total=equipe_total,
        marketing=P["marketing_digital"], comercial=P["comercial_viagens"], ga=P["ga_admin"], comissoes=comissoes,
        opex=opex, ebitda=ebitda, caixa_acumulado=caixa_acum, necessidade_caixa=-minimo,
        mega_receita_ano3=mega_receita, mega_arr=mega_arr, arr_ano3_otimista=arr_fim[2] + mega_arr,
        ebitda_ano3_otimista=ebitda3_otimista,
        arr_por_ies=arr_por_ies, cac_por_ies=cac, ltv_por_ies=ltv, ltv_cac=ltv / cac, payback_meses=payback_meses,
        custo_oracle_por_aluno_mes=custo_oracle_por_aluno_mes, premissas=P,
    ))
    return r


def xlsx(r, caminho):
    wb = Workbook()
    ws = wb.active; ws.title = "Projecao 3 anos"
    azul = PatternFill("solid", fgColor="0B2545"); branco = Font(color="FFFFFF", bold=True)
    ws.append(["Retena - projecao financeira simplificada (R$) - ESTIMATIVAS da equipe; premissas na aba Premissas"])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append([])
    ws.append(["Linha"] + ANOS)
    for c in ws[3]:
        c.fill = azul; c.font = branco
    linhas = [
        ("Alunos ativos sob contrato (fim do ano)", r["alunos_fim"]),
        ("IES clientes (fim do ano)", r["ies_fim"]),
        ("ARR no fim do ano", r["arr_fim"]),
        ("Receita de assinatura", r["assinatura"]),
        ("Setup / implantação", r["setup"]),
        ("Pilotos de 90 dias", r["pilotos"]),
        ("RECEITA BRUTA", None),
        ("(-) Impostos sobre receita", [-x for x in r["impostos"]]),
        ("RECEITA LÍQUIDA", None),
        ("(-) Oracle Autonomous AI Database", [-x for x in r["oracle_ano"]]),
        ("(-) Outros custos de servir", [-x for x in r["outros_cogs"]]),
        ("(-) Customer success / implantação", [-x for x in r["cs_implantacao"]]),
        ("LUCRO BRUTO", None),
    ] + [(f"(-) {k}", [-x for x in v]) for k, v in r["equipe"].items()] + [
        ("(-) Marketing digital", [-x for x in r["marketing"]]),
        ("(-) Comercial e viagens", [-x for x in r["comercial"]]),
        ("(-) G&A (contabilidade, jurídico/LGPD, ferramentas)", [-x for x in r["ga"]]),
        ("(-) Comissões (8% do ARR novo)", [-x for x in r["comissoes"]]),
        ("EBITDA", None),
        ("Caixa acumulado (sem captação)", None),
    ]
    idx = {}
    for nome, vals in linhas:
        row = ws.max_row + 1
        idx[nome] = row
        if vals is not None:
            ws.append([nome] + [round(v, 2) for v in vals])
        else:
            ws.append([nome])
    for j in range(3):
        col = get_column_letter(2 + j)
        ws[f"{col}{idx['RECEITA BRUTA']}"] = f"=SUM({col}{idx['Receita de assinatura']}:{col}{idx['Pilotos de 90 dias']})"
        ws[f"{col}{idx['RECEITA LÍQUIDA']}"] = f"={col}{idx['RECEITA BRUTA']}+{col}{idx['(-) Impostos sobre receita']}"
        ws[f"{col}{idx['LUCRO BRUTO']}"] = f"=SUM({col}{idx['RECEITA LÍQUIDA']}:{col}{idx['(-) Customer success / implantação']})"
        ws[f"{col}{idx['EBITDA']}"] = f"=SUM({col}{idx['LUCRO BRUTO']}:{col}{idx['(-) Comissões (8% do ARR novo)']})"
        prev = f"+{get_column_letter(1 + j)}{idx['Caixa acumulado (sem captação)']}" if j else ""
        ws[f"{col}{idx['Caixa acumulado (sem captação)']}"] = f"={col}{idx['EBITDA']}{prev}"
    for nome in ("RECEITA BRUTA", "RECEITA LÍQUIDA", "LUCRO BRUTO", "EBITDA", "Caixa acumulado (sem captação)"):
        for c in ws[idx[nome]]:
            c.font = Font(bold=True)
    for row in ws.iter_rows(min_row=4, min_col=2, max_col=4):
        for c in row:
            c.number_format = '#,##0;[Red]-#,##0'
    ws.column_dimensions["A"].width = 52
    for col in "BCD":
        ws.column_dimensions[col].width = 16
    ws.freeze_panes = "B4"

    w2 = wb.create_sheet("Premissas")
    w2.append(["Premissa", "Valor", "Fonte / natureza"])
    for c in w2[1]:
        c.fill = azul; c.font = branco
    fontes = {
        "preco_efetivo_aluno_mes": "Estimativa: mix das faixas publicadas (Pro R$ 6/4/3; Essencial R$ 2) - mesmo R$ 48/ano do SAM/SOM",
        "ecpu_hora_usd": "Oracle Autonomous Database ECPU FAQ (lista, licença incluída) - confirmar no price list vigente",
        "storage_gb_mes_usd": "Oracle Autonomous Database ECPU FAQ (ATP storage) - confirmar no price list vigente",
        "preco_piloto": "Publicado (conceito_final.md seção 9)",
        "setup_por_ies": "Faixa publicada R$ 10-25 mil; valor médio estimado para IES de ~5 mil alunos",
        "megagrupo_preco": "Faixa 50 mil+ publicada (R$ 3,00)",
        "usd_brl": "Estimativa de câmbio",
        "impostos_pct": "Estimativa: Simples Nacional anexo III com fator R",
    }
    for k, v in P.items():
        if k == "equipe":
            for kk, vv in v.items():
                w2.append([f"equipe: {kk}", json.dumps(vv), "Estimativa (custo total com encargos, R$/ano)"])
        else:
            w2.append([k, json.dumps(v) if isinstance(v, list) else v, fontes.get(k, "Estimativa da equipe")])
    w2.column_dimensions["A"].width = 40; w2.column_dimensions["B"].width = 26; w2.column_dimensions["C"].width = 90

    w3 = wb.create_sheet("Unit economics")
    for k, v in [("ARR por IES média (5 mil alunos × R$ 4 × 12)", r["arr_por_ies"]), ("CAC por IES (ano 2)", r["cac_por_ies"]),
                 ("LTV por IES (margem 80%, vida 5 anos)", r["ltv_por_ies"]), ("LTV/CAC", r["ltv_cac"]),
                 ("Payback do CAC (meses)", r["payback_meses"]),
                 ("Necessidade de caixa (pior saldo acumulado)", r["necessidade_caixa"]),
                 ("ARR ano 3 cenário otimista (+1 megagrupo)", r["arr_ano3_otimista"]),
                 ("EBITDA ano 3 cenário otimista", r["ebitda_ano3_otimista"])]:
        w3.append([k, round(v, 2)])
    w3.column_dimensions["A"].width = 50; w3.column_dimensions["B"].width = 18
    wb.save(caminho)


if __name__ == "__main__":
    r = calcular()
    xlsx(r, AQUI / "modelo_financeiro.xlsx")
    (AQUI / "modelo_financeiro.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    f = lambda v: f"{v/1000:,.0f} mil".replace(",", ".")
    for i, a in enumerate(ANOS):
        print(f"{a}: ARR {f(r['arr_fim'][i])} | receita bruta {f(r['receita_bruta'][i])} | lucro bruto {f(r['lucro_bruto'][i])} "
              f"(MB {r['margem_bruta'][i]:.0%}) | opex {f(r['opex'][i])} | EBITDA {f(r['ebitda'][i])} | caixa {f(r['caixa_acumulado'][i])}")
    print(f"Oracle/mes: {[round(x) for x in r['oracle_mes']]} | por aluno/mes: {[round(x, 3) for x in r['custo_oracle_por_aluno_mes']]}")
    print(f"necessidade de caixa {f(r['necessidade_caixa'])} | CAC {f(r['cac_por_ies'])} | LTV {f(r['ltv_por_ies'])} | LTV/CAC {r['ltv_cac']:.1f} | payback {r['payback_meses']:.1f} m")
    print(f"otimista ano 3: ARR {f(r['arr_ano3_otimista'])}, EBITDA {f(r['ebitda_ano3_otimista'])}")
