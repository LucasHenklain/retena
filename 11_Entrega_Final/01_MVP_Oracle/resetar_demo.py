# -*- coding: utf-8 -*-
"""resetar_demo.py - volta o MVP ao estado inicial de demonstração: apaga TODOS os contatos registrados,
devolve a fila para PENDENTE e o ticket para R$ 350. Use antes de uma apresentação ou de um teste com usuário.
Uso: python resetar_demo.py [--sim]   (sem --sim pede confirmação)"""
import os, sys
import oracledb

if "--sim" not in sys.argv and input("Apagar todos os contatos registrados e voltar a fila ao estado inicial? [s/N] ").strip().lower() != "s":
    sys.exit("cancelado")
c = oracledb.connect(user=os.environ.get("ORACLE_USER", "STARTUP"), password=os.environ.get("ORACLE_PASSWORD", "Startup2026"),
                     dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))
cur = c.cursor()
cur.execute("DELETE FROM CONTATO_RESULTADO"); n = cur.rowcount
cur.execute("UPDATE RISCO_ALUNO_SNAPSHOT SET STATUS_ATENDIMENTO = 'PENDENTE', OBSERVACAO = NULL WHERE STATUS_ATENDIMENTO <> 'PENDENTE'")
cur.execute("UPDATE PARAMETRO_IES SET VALOR = 350, DT_ATUALIZACAO = SYSTIMESTAMP WHERE CHAVE = 'TICKET_MENSAL'")
c.commit()
print(f"{n} contato(s) apagado(s); fila e ticket (R$ 350) no estado inicial.")
