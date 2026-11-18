<#
.SYNOPSIS
  Retena MVP - sobe TUDO com um comando: Oracle AI Database 26ai Free (Docker) + carga/treino/scoring OML
  (se o banco estiver vazio) + tabelas do MVP + API FastAPI + abre o painel no navegador.

.DESCRIPTION
  1. confere Docker e Python (instala as bibliotecas de requirements.txt se faltarem)
  2. reaproveita o container Oracle se ja existir; senao cria com docker compose (imagem gvenzl/oracle-free)
  3. se RISCO_ALUNO_SNAPSHOT nao existir (banco novo): carrega os 684.723 eventos de 08_Dados/logs_lms.parquet
     e executa 06_Oracle/sql/02..06 (features, treino OML, scoring, job, avaliacao) - 10 a 15 min na 1a vez
  4. executa sql/08_mvp_contato_resultado.sql (idempotente)
  5. sobe a API em http://127.0.0.1:<Porta> numa janela separada e abre o navegador

.EXAMPLE
  .\iniciar.ps1
  .\iniciar.ps1 -Porta 8090 -OraclePorta 1522 -Container retena-oracle   # banco novo, isolado
  .\iniciar.ps1 -Recarregar                                             # refaz carga + treino + scoring
#>
param(
    [int]$Porta = 8080,
    [int]$OraclePorta = 1521,
    [string]$Container = "oracle-free",
    [switch]$Recarregar,
    [switch]$SemNavegador
)
# "Continue": no Windows PowerShell 5.1, stderr de executavel nativo com "Stop" vira excecao; usamos $LASTEXITCODE
$ErrorActionPreference = "Continue"
$Aqui    = $PSScriptRoot
$Entrega = (Resolve-Path (Join-Path $Aqui "..\..")).Path
$Oracle  = Join-Path $Entrega "06_Oracle"
$Logs    = Join-Path $Aqui "logs"
New-Item -ItemType Directory -Force $Logs | Out-Null
$t0 = Get-Date
function Passo([string]$m) { Write-Host ("`n[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) -ForegroundColor Cyan }
function Falhou([string]$m) { Write-Host "`nERRO: $m" -ForegroundColor Red; exit 1 }

if (-not $env:ORACLE_USER)     { $env:ORACLE_USER = "STARTUP" }
if (-not $env:ORACLE_PASSWORD) { $env:ORACLE_PASSWORD = "Startup2026" }
$env:ORACLE_DSN = "localhost:$OraclePorta/FREEPDB1"
$env:PYTHONIOENCODING = "utf-8"

# ------------------------------------------------------------------ 1) pre-requisitos
Passo "1/5 Pre-requisitos (Docker e Python)"
try { docker info --format "{{.ServerVersion}}" | Out-Null } catch { Falhou "Docker nao esta em execucao. Abra o Docker Desktop e rode de novo." }
if ($LASTEXITCODE -ne 0) { Falhou "Docker nao esta em execucao. Abra o Docker Desktop e rode de novo." }
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { Falhou "Python 3.10+ nao encontrado no PATH (https://www.python.org/downloads/)." }
python -c "import fastapi, uvicorn, oracledb, pandas, pyarrow" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  instalando bibliotecas Python (requirements.txt)..."
    python -m pip install --quiet -r (Join-Path $Aqui "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Falhou "pip install falhou" }
}
Write-Host "  Docker ok; Python $(python -c 'import sys;print(sys.version.split()[0])') ok"

# ------------------------------------------------------------------ 2) banco
Passo "2/5 Oracle AI Database 26ai Free (container '$Container', porta $OraclePorta)"
$existe = docker ps -a --filter "name=^/$Container$" --format "{{.Names}}"
if ($existe) {
    $estado = docker inspect --format "{{.State.Status}}" $Container
    if ($estado -ne "running") { Write-Host "  iniciando container existente..."; docker start $Container | Out-Null }
    else { Write-Host "  container ja em execucao" }
} else {
    Write-Host "  criando container (1a vez: download da imagem gvenzl/oracle-free, alguns minutos)..."
    $env:ORACLE_CONTAINER = $Container; $env:ORACLE_PORT = "$OraclePorta"
    Push-Location $Aqui
    docker compose -p "retena-$($Container.ToLower())" up -d oracle
    $rc = $LASTEXITCODE
    Pop-Location
    if ($rc -ne 0) { Falhou "docker compose up falhou" }
}
$limite = (Get-Date).AddMinutes(10)
do {
    $h = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" $Container
    if ($h -eq "healthy") { break }
    Write-Host "  aguardando o banco ficar pronto (health = $h)..."
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $limite)
if ($h -ne "healthy") { Falhou "o banco nao ficou pronto em 10 min (docker logs $Container)" }
Write-Host "  banco pronto: $env:ORACLE_DSN"

# ------------------------------------------------------------------ 3) carga + treino + scoring (so se necessario)
Passo "3/5 Dados, modelos OML e scoring"
$check = python -c "import oracledb,os;c=oracledb.connect(user=os.environ['ORACLE_USER'],password=os.environ['ORACLE_PASSWORD'],dsn=os.environ['ORACLE_DSN']);cur=c.cursor();cur.execute('select count(*) from risco_aluno_snapshot');print(cur.fetchone()[0])" 2>$null
if ($Recarregar -or -not $check -or [int]$check -eq 0) {
    Write-Host "  banco sem o snapshot de risco: executando o pipeline Oracle completo (10-15 min)..."
    python (Join-Path $Oracle "scripts\carregar_eventos.py") --log (Join-Path $Logs "01_carga_eventos.log")
    if ($LASTEXITCODE -ne 0) { Falhou "carga dos eventos (ver logs\01_carga_eventos.log)" }
    foreach ($arq in "02_features_transicao.sql", "03_features_semanais.sql", "04_oml_modelos.sql", "05_scoring_views.sql", "06_avaliacao.sql") {
        Write-Host "  executando $arq ..."
        $log = Join-Path $Logs ([IO.Path]::GetFileNameWithoutExtension($arq) + ".log")
        python (Join-Path $Oracle "scripts\executar_sql.py") (Join-Path $Oracle "sql\$arq") --log $log --max-linhas 20 | Select-String -Pattern "Fim:"
        if ($LASTEXITCODE -ne 0) { Falhou "$arq (ver $log)" }
    }
} else { Write-Host "  snapshot ja existe ($check alunos pontuados) - pulando carga e treino (use -Recarregar para refazer)" }

# ------------------------------------------------------------------ 4) objetos do MVP
Passo "4/5 Tabelas e regras do MVP (CONTATO_RESULTADO, PARAMETRO_IES, PRC_REGISTRAR_CONTATO, views)"
python (Join-Path $Oracle "scripts\executar_sql.py") (Join-Path $Aqui "sql\08_mvp_contato_resultado.sql") --log (Join-Path $Logs "08_mvp_contato_resultado.log") --max-linhas 10 | Select-String -Pattern "Fim:"
if ($LASTEXITCODE -ne 0) { Falhou "08_mvp_contato_resultado.sql (ver logs\08_mvp_contato_resultado.log)" }

# ------------------------------------------------------------------ 5) API + navegador
Passo "5/5 API e painel em http://127.0.0.1:$Porta"
$pidArq = Join-Path $Logs "api.pid"
if (Test-Path $pidArq) { try { Stop-Process -Id (Get-Content $pidArq) -Force -ErrorAction Stop } catch {} }
$apiArgs = @("-m", "uvicorn", "app:app", "--app-dir", "`"$(Join-Path $Aqui 'api')`"", "--host", "127.0.0.1", "--port", "$Porta")
$proc = Start-Process python -ArgumentList $apiArgs -PassThru -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $Logs "api.out.log") -RedirectStandardError (Join-Path $Logs "api.err.log")
$proc.Id | Set-Content $pidArq
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try { $r = Invoke-RestMethod "http://127.0.0.1:$Porta/api/saude" -TimeoutSec 5; if ($r.ok) { $ok = $true; break } } catch {}
}
if (-not $ok) { Falhou "a API nao respondeu (ver logs\api.err.log)" }
$dur = (Get-Date) - $t0
Write-Host ("`nRetena MVP no ar em {0:mm\:ss}: http://127.0.0.1:{1}" -f $dur, $Porta) -ForegroundColor Green
Write-Host "  Banco: $($r.banco)"
Write-Host "  $($r.alunos) alunos pontuados | $($r.contatos) contatos registrados | ultimo scoring $($r.dt_scoring)"
Write-Host "  Teste ponta a ponta: python verificar_mvp.py --url http://127.0.0.1:$Porta"
Write-Host "  Parar: .\parar.ps1   (API)   |   docker stop $Container   (banco)"
if (-not $SemNavegador) { Start-Process "http://127.0.0.1:$Porta/#fila" }
