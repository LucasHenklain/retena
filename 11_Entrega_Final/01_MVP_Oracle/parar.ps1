# Para a API do MVP Retena (o banco continua no Docker; para parar o banco: docker stop oracle-free)
param([switch]$Banco, [string]$Container = "oracle-free")
$pidArq = Join-Path $PSScriptRoot "logs\api.pid"
if (Test-Path $pidArq) {
    try { Stop-Process -Id (Get-Content $pidArq) -Force -ErrorAction Stop; Write-Host "API parada." } catch { Write-Host "API ja estava parada." }
    Remove-Item $pidArq -ErrorAction SilentlyContinue
} else { Write-Host "Nenhuma API iniciada por iniciar.ps1." }
if ($Banco) { docker stop $Container | Out-Null; Write-Host "Banco $Container parado." }
