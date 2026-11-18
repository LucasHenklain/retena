# Retena — MVP final sobre Oracle AI Database

Fluxo principal de ponta a ponta, com persistência no Oracle:

```
fila de segunda (RISCO_ALUNO_SNAPSHOT, pontuado por OML via DBMS_SCHEDULER)
  → painel do aluno (motivos PREDICTION_DETAILS + predição ao vivo PREDICTION_PROBABILITY + "e se")
  → registro do contato (PRC_REGISTRAR_CONTATO grava CONTATO_RESULTADO e atualiza a fila na mesma transação)
  → diretoria (VW_DIRETORIA_RESUMO recalcula receita em risco e preservada; ticket em PARAMETRO_IES)
```

## Como executar (Windows, um comando)

Pré-requisitos: **Docker Desktop** em execução e **Python 3.10+** no PATH. Cerca de 8 GB livres em disco (imagem do Oracle Free).

1. Dê dois cliques em **`INICIAR_MVP.cmd`** (ou rode `powershell -ExecutionPolicy Bypass -File iniciar.ps1`).
2. Na primeira vez, o script baixa a imagem `gvenzl/oracle-free`, cria o container `oracle-free`, carrega os 684.723 eventos de `../../08_Dados/logs_lms.parquet` e executa `../../06_Oracle/sql/02–06` (features, treino OML, scoring, job, avaliação): **10 a 15 minutos** (12 min medidos num banco novo). Nas vezes seguintes, cerca de 1 minuto.
3. O navegador abre em **http://127.0.0.1:8080**. Documentação da API: http://127.0.0.1:8080/docs. Painel offline da fase anterior: http://127.0.0.1:8080/offline/.

Opções: `iniciar.ps1 -Porta 8090 -OraclePorta 1522 -Container retena-oracle` cria um banco novo e isolado; `-Recarregar` refaz carga e treino; `-SemNavegador`.
Parar: `parar.ps1` (API) e `parar.ps1 -Banco` (também o container).

## Linux / macOS (tudo em container)

```
docker compose --profile completo up -d --build
docker compose logs -f carga        # aguarde "[carga] pronto" (10–15 min na 1a vez)
# abra http://127.0.0.1:8080
```

Atrás de proxy com inspeção TLS, passe a cadeia da empresa no build: `docker compose build --secret id=ca,src=<cadeia.pem>`.

## Verificar que funciona

```
python verificar_mvp.py            # 15 checagens: API e, em paralelo, SQL direto no banco; apaga o contato de teste no fim
python resetar_demo.py             # volta ao estado inicial (apaga TODOS os contatos; pede confirmação)
```

Último resultado: `logs/verificacao_mvp.txt` (16/11/2026: todos os passos passaram).

## O que tem aqui

| Caminho | Conteúdo |
|---|---|
| `sql/08_mvp_contato_resultado.sql` | `PARAMETRO_IES`, `CONTATO_RESULTADO`, `PRC_REGISTRAR_CONTATO`, `VW_FILA_COORDENACAO`, `VW_DIRETORIA_RESUMO`, `VW_RESULTADO_CONTATOS` (idempotente) |
| `api/app.py` | API FastAPI + python-oracledb (modo thin): 12 rotas; consultas da "Prova em SQL" são fixas (sem SQL arbitrário) |
| `web/` | Interface (HTML/CSS/JS sem dependências externas; fontes e logo da marca locais) |
| `iniciar.ps1`, `INICIAR_MVP.cmd`, `parar.ps1` | Subida e parada no Windows |
| `docker-compose.yml`, `Dockerfile`, `carga.sh` | Banco e (perfil `completo`) carga + API em container |
| `verificar_mvp.py`, `resetar_demo.py` | Teste ponta a ponta e reset da demonstração |
| `logs/` | Logs da última execução e da verificação |

## Credenciais (somente ambiente local de demonstração)

Usuário de aplicação `STARTUP` / `Startup2026` em `localhost:1521/FREEPDB1` (SYS/SYSTEM com a mesma senha). Troque por variáveis de ambiente (`ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`) em qualquer uso fora desta máquina.

## Limitações conhecidas

Dados do LMS congelados em 26/08/2026 (re-pontuar só muda o carimbo); "receita preservada" é estimativa até o LMS confirmar o retorno do aluno; sem login por papel ainda; Autonomous AI Database, APEX/ORDS e Select AI estão no roadmap (runbook em `../../06_Oracle/oci`). Contatos mostrados em vídeo e imagens são de demonstração — nenhum aluno real foi contatado.
