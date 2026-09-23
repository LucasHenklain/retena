# preparar.ps1 — deixa este notebook pronto para a Banca Final (Retena, 23/09/2026)
# 1) mantém o notebook acordado  2) Docker + Oracle local  3) roda o job de scoring (carimbo de hoje)
# 4) servidor local de reserva  5) abre dashboard, site e vídeo no Edge  6) abre o deck no PowerPoint
# Uso: 1_Preparar.cmd   (ou: powershell -ExecutionPolicy Bypass -File preparar.ps1 [-SemAbrir] [-SemJob])
param([switch]$SemAbrir, [switch]$SemJob)
$ErrorActionPreference = "Continue"
$Aqui = $PSScriptRoot; $Kit = Split-Path -Parent $Aqui; $Entrega = Split-Path -Parent $Kit
$Log = Join-Path $Aqui "preparacao.log"; $Porta = 8765
function Passo($m) { $l = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m; Write-Host $l; Add-Content -Path $Log -Value $l -Encoding utf8 }
function Aviso($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) -ForegroundColor Yellow; Add-Content -Path $Log -Value ("AVISO " + $m) -Encoding utf8 }

Write-Host ""; Write-Host "  RETENA · preparação da banca" -ForegroundColor Cyan; Write-Host ""
Add-Content -Path $Log -Value ("===== " + (Get-Date -Format "dd/MM/yyyy HH:mm:ss") + " =====") -Encoding utf8

# 0) manter acordado enquanto esta janela estiver aberta (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
try {
    Add-Type -Namespace Retena -Name Awake -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);' -ErrorAction Stop
    [Retena.Awake]::SetThreadExecutionState([uint32]2147483651) | Out-Null
    Passo "0/6 Notebook não vai dormir nem apagar a tela enquanto esta janela estiver aberta."
} catch { Aviso "não consegui ativar o keep-awake: $($_.Exception.Message). Desative a suspensão manualmente." }

# 1) Docker Desktop
Passo "1/6 Docker"
$dockerOk = $false
try { docker info 2>$null | Out-Null; $dockerOk = ($LASTEXITCODE -eq 0) } catch { $dockerOk = $false }
if (-not $dockerOk) {
    Aviso "Docker não está respondendo; iniciando o Docker Desktop (até 4 min)..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" | Out-Null
    $lim = (Get-Date).AddMinutes(4)
    do { Start-Sleep -Seconds 5; try { docker info 2>$null | Out-Null; $dockerOk = ($LASTEXITCODE -eq 0) } catch { $dockerOk = $false } } while (-not $dockerOk -and (Get-Date) -lt $lim)
}
if ($dockerOk) { Passo "Docker ok." } else { Aviso "Docker não subiu. Seguindo sem o Oracle ao vivo: use 06_Oracle/evidencias e ultimo_scoring.txt." }

# 2) Oracle Free (container oracle-free)
$oracleOk = $false
if ($dockerOk) {
    Passo "2/6 Oracle AI Database 26ai Free (container oracle-free)"
    $st = docker inspect --format "{{.State.Status}}" oracle-free 2>$null
    if ($st -ne "running") { Passo "Subindo o container (leva ~1 min)..."; docker start oracle-free 2>$null | Out-Null }
    $lim = (Get-Date).AddMinutes(5); $h = ""
    do {
        $h = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" oracle-free 2>$null
        if ($h -ne "healthy") { Write-Host ("   ... {0}" -f $(if ($h) { $h } else { "aguardando" })); Start-Sleep -Seconds 6 }
    } while ($h -ne "healthy" -and (Get-Date) -lt $lim)
    $oracleOk = ($h -eq "healthy")
    if ($oracleOk) { Passo "Oracle healthy (STARTUP @ localhost:1521/FREEPDB1)." } else { Aviso "Oracle não ficou healthy em 5 min." }
}

# 3) Job de scoring in-database (carimbo DT_SCORING de hoje; mesmos dados, base parceira até 26/08)
if ($oracleOk -and -not $SemJob) {
    Passo "3/6 Rodando JOB_RETENA_SCORING_SEMANAL (DBMS_SCHEDULER.RUN_JOB, ~25 s)..."
    python (Join-Path $Aqui "scoring_ao_vivo.py") --sem-pausa
    if ($LASTEXITCODE -eq 0) { Passo "Scoring concluído; resultado salvo em ultimo_scoring.txt (plano B para print)." } else { Aviso "scoring_ao_vivo.py terminou com erro; veja a saída acima." }
} elseif ($SemJob) { Passo "3/6 Job de scoring pulado (-SemJob)." } else { Aviso "3/6 Job de scoring pulado: Oracle indisponível." }

# 4) Servidor local de reserva (dashboard, landing e kit sem internet)
Passo "4/6 Servidor local de reserva"
$ocupada = $false
try { $ocupada = Test-NetConnection -ComputerName 127.0.0.1 -Port $Porta -InformationLevel Quiet -WarningAction SilentlyContinue } catch { $ocupada = $false }
if (-not $ocupada) {
    Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "-m", "http.server", "$Porta", "--bind", "127.0.0.1", "--directory", "`"$Entrega`"" | Out-Null
    Start-Sleep -Seconds 2
}
Passo "Reserva offline: http://localhost:$Porta/05_MVP/dashboard/index.html?modo=diretoria"

# 5) Internet e abas
Passo "5/6 Verificando o site publicado"
$online = $false
try { $r = Invoke-WebRequest -Uri "https://lucashenklain.github.io/retena/dashboard/" -UseBasicParsing -TimeoutSec 15; $online = ($r.StatusCode -eq 200 -and $r.Content -match "IES parceira") } catch { $online = $false }
if ($online) {
    Passo "Site publicado acessível: usando as URLs online."
    $dash = "https://lucashenklain.github.io/retena/dashboard/?modo=diretoria"; $site = "https://lucashenklain.github.io/retena/#roi"; $video = "https://youtu.be/HZrcLvIJCC4"
} else {
    Aviso "Sem acesso ao site publicado: abrindo as versões locais (dashboard, landing e vídeo MP4)."
    $dash = "http://localhost:$Porta/05_MVP/dashboard/index.html?modo=diretoria"; $site = "http://localhost:$Porta/04_Landing_Page/index.html#roi"; $video = Join-Path $Entrega "07_Video_Pitch\Retena_Pitch_Banca_Final.mp4"
}
if (-not $SemAbrir) {
    Start-Process msedge.exe -ArgumentList "--new-window", $dash, $site, $video | Out-Null
    Passo "Edge aberto: dashboard (visão Diretoria) · site (ROI) · vídeo."
    Start-Sleep -Seconds 2
    Start-Process (Join-Path $Kit "Retena_Banca_Final.pptx") | Out-Null
    Passo "6/6 Deck aberto no PowerPoint (F5 para apresentar; Alt+F5 para o modo apresentador com notas)."
} else { Passo "6/6 Abertura de janelas pulada (-SemAbrir)." }

Write-Host ""
Write-Host "  PRONTO. Checklist:" -ForegroundColor Green
Write-Host "   • No dashboard, digite 'Aluno 0227' na busca da fila (visão Coordenação) e volte para Diretoria."
Write-Host "   • Scoring ao vivo na pergunta da banca: 2_Scoring_ao_vivo.cmd (25 s)."
Write-Host "   • Plano B sem internet: URLs locais acima; deck em PDF em 09_Kit_Banca_Final; prints em A1 do apêndice."
Write-Host "   • Deixe ESTA janela aberta durante a apresentação (mantém o notebook acordado). Feche ao terminar."
Write-Host ""
while ($true) { Start-Sleep -Seconds 300 }
