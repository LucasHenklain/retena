<#
.SYNOPSIS
  Retena - pipeline completo Oracle (Free 26ai em Docker): subir banco, carregar logs do LMS,
  gerar features, treinar modelos OML in-database, criar views de scoring/JSON, avaliar e gerar evidencias.

.DESCRIPTION
  Ordem de execucao (cada passo grava um log em evidencias/logs/):
    0. docker compose up -d           (pula se o container oracle-free ja estiver "healthy")
    1. carregar_eventos.py            (executa sql/01_ddl.sql e carrega 08_Dados/logs_lms.parquet)
    2. sql/02_features_transicao.sql  (FEATURES_TRANSICAO_FASE)
    3. sql/03_features_semanais.sql   (SQL Macro FN_FEATURES_SEMANAIS + BASE_RISCO_SEMANAL)
    4. sql/04_oml_modelos.sql         (DBMS_DATA_MINING.CREATE_MODEL2: RF + 2 GLM)
    5. sql/05_scoring_views.sql       (VW_RISCO_ALUNO_ATUAL, snapshot, job, VW_RISCO_JSON, duality view)
    6. sql/06_avaliacao.sql           (AUC COMPUTE_ROC, confusao, top-20%, lift, atributos)
    7. sql/07_apex_ready.sql          (5 consultas para o dashboard APEX)
    8. gerar_evidencias.py            (TXT/CSV/JSON + evidencias.html + evidencia_NN.png)

.PARAMETER SemDocker   Nao tenta subir o container (banco ja esta em pe em outro host/porta).
.PARAMETER SemCarga    Pula o passo 1 (EVENTOS_LMS ja carregada) - poupa ~1 min.
.PARAMETER SemPng      Gera evidencias sem renderizar PNG (sem Edge).
.PARAMETER PararNoErro Interrompe o pipeline no primeiro statement com erro.

.EXAMPLE
  .\scripts\run_all.ps1
  .\scripts\run_all.ps1 -SemCarga -SemPng
#>
param(
    [switch]$SemDocker,
    [switch]$SemCarga,
    [switch]$SemPng,
    [switch]$PararNoErro
)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot          # ...\06_Oracle
$Sql  = Join-Path $Raiz "sql"
$Scr  = Join-Path $Raiz "scripts"
$Logs = Join-Path $Raiz "evidencias\logs"
New-Item -ItemType Directory -Force $Logs | Out-Null

# conexao (mesmos defaults de scripts/executar_sql.py; sobrescreva via ambiente ou .env)
if (-not $env:ORACLE_USER)     { $env:ORACLE_USER     = "STARTUP" }
if (-not $env:ORACLE_PASSWORD) { $env:ORACLE_PASSWORD = "Startup2026" }
if (-not $env:ORACLE_DSN)      { $env:ORACLE_DSN      = "localhost:1521/FREEPDB1" }

$t0 = Get-Date
function Passo([string]$msg) { Write-Host ("`n[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg) -ForegroundColor Cyan }
function Falhou([string]$msg) { Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }

# ------------------------------------------------------------------ 0) banco
if (-not $SemDocker) {
    Passo "0/8 Container oracle-free (gvenzl/oracle-free:slim-faststart)"
    $status = ""
    try { $status = (docker inspect --format "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}" oracle-free) } catch { $status = "" }
    if ($status -notlike "running|healthy") {
        Push-Location $Raiz
        if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
        docker compose up -d
        Pop-Location
        Write-Host "  aguardando healthcheck (primeira subida: 1-3 min)..."
        $limite = (Get-Date).AddMinutes(8)
        do {
            Start-Sleep -Seconds 10
            $h = (docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" oracle-free)
            Write-Host "  health = $h"
        } while ($h -ne "healthy" -and (Get-Date) -lt $limite)
        if ($h -ne "healthy") { Falhou "container nao ficou healthy em 8 min (docker logs oracle-free)" }
    } else { Write-Host "  ja em execucao e healthy" }
}

# ------------------------------------------------------------------ 1) DDL + carga
$flagErro = @(); if ($PararNoErro) { $flagErro = @("--parar-no-erro") }
if (-not $SemCarga) {
    Passo "1/8 DDL (01_ddl.sql) + carga de EVENTOS_LMS (carregar_eventos.py)"
    python (Join-Path $Scr "carregar_eventos.py") --log (Join-Path $Logs "carga_eventos.log")
    if ($LASTEXITCODE -ne 0) { Falhou "carregar_eventos.py" }
} else { Passo "1/8 carga pulada (-SemCarga)" }

# ------------------------------------------------------------------ 2..7) scripts SQL
$etapas = @(
    @{ n = "2/8"; arq = "02_features_transicao.sql"; desc = "features por (aluno, fase)" },
    @{ n = "3/8"; arq = "03_features_semanais.sql";  desc = "SQL Macro + BASE_RISCO_SEMANAL" },
    @{ n = "4/8"; arq = "04_oml_modelos.sql";        desc = "treino OML (CREATE_MODEL2)" },
    @{ n = "5/8"; arq = "05_scoring_views.sql";      desc = "scoring, snapshot, job, JSON, duality view (~2 min)" },
    @{ n = "6/8"; arq = "06_avaliacao.sql";          desc = "AUC/COMPUTE_ROC, confusao, top-20%, lift" },
    @{ n = "7/8"; arq = "07_apex_ready.sql";         desc = "consultas APEX" }
)
foreach ($e in $etapas) {
    Passo "$($e.n) $($e.arq) - $($e.desc)"
    $log = Join-Path $Logs ([IO.Path]::GetFileNameWithoutExtension($e.arq) + ".log")
    python (Join-Path $Scr "executar_sql.py") (Join-Path $Sql $e.arq) --log $log --max-linhas 40 @flagErro | Select-String -Pattern "ERRO em|Fim:"
    if ($LASTEXITCODE -ne 0) { Falhou "$($e.arq) (ver $log)" }
}

# ------------------------------------------------------------------ 8) evidencias
Passo "8/8 gerar_evidencias.py - TXT/CSV/JSON + evidencias.html + PNG"
$args8 = @(); if ($SemPng) { $args8 = @("--sem-png") }
python (Join-Path $Scr "gerar_evidencias.py") @args8
if ($LASTEXITCODE -ne 0) { Falhou "gerar_evidencias.py" }

$dur = (Get-Date) - $t0
Write-Host ("`nConcluido em {0:mm\:ss}. Evidencias em {1}" -f $dur, (Join-Path $Raiz "evidencias")) -ForegroundColor Green
Get-ChildItem (Join-Path $Raiz "evidencias") -File | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
