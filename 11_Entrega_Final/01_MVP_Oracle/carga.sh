#!/bin/sh
# Servico "carga" do docker compose (perfil completo): prepara o banco uma unica vez.
set -e
mkdir -p /tmp/logs
# os scripts gravam logs ao lado de si: trabalha numa copia gravavel do 06_Oracle (montado somente leitura)
rm -rf /tmp/06_Oracle && cp -r /entrega/06_Oracle /tmp/06_Oracle
ORA=/tmp/06_Oracle
N=$(python -c "import oracledb,os
try:
    c=oracledb.connect(user=os.environ['ORACLE_USER'],password=os.environ['ORACLE_PASSWORD'],dsn=os.environ['ORACLE_DSN']);cur=c.cursor();cur.execute('select count(*) from risco_aluno_snapshot');print(cur.fetchone()[0])
except Exception: print(0)")
if [ "$N" = "0" ]; then
  echo "[carga] banco vazio: carregando eventos e treinando modelos OML (10-15 min)"
  python $ORA/scripts/carregar_eventos.py --parquet /entrega/08_Dados/logs_lms.parquet --log /tmp/logs/01.log
  for f in 02_features_transicao 03_features_semanais 04_oml_modelos 05_scoring_views 06_avaliacao; do
    echo "[carga] $f"
    python $ORA/scripts/executar_sql.py $ORA/sql/$f.sql --log /tmp/logs/$f.log --max-linhas 5 | grep "Fim:"
  done
else
  echo "[carga] snapshot ja existe ($N alunos) - pulando carga e treino"
fi
echo "[carga] objetos do MVP"
python $ORA/scripts/executar_sql.py /app/sql/08_mvp_contato_resultado.sql --max-linhas 5 | grep "Fim:"
echo "[carga] pronto"
