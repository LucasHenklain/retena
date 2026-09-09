# Empacota a entrega da Fase 6 em um único ZIP, excluindo arquivos de trabalho.
# Uso: powershell -ExecutionPolicy Bypass -File .\empacotar.ps1
param([string]$Sufixo = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$nome = "Retena_Fase6_StartupOne_Entrega$Sufixo"
$staging = Join-Path $env:TEMP "$nome`_staging"
$zip = Join-Path (Split-Path -Parent $root) "$nome.zip"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force $staging | Out-Null

$excluirDirs = @("_work", "_preview", "__pycache__", ".pytest_cache", "v1_longas")
# O vídeo NÃO vai no ZIP (regra da atividade: upload no YouTube e envio do link). Fica na pasta local 07_Video_Pitch.
$excluirArqs = @("*.pyc", "dashboard_tall.png", "_tall_small.png", "_contato*.jpg", "_*.html", "*.tmp", "*.mp4")

Get-ChildItem -Path $root -Recurse -File | Where-Object {
    $rel = $_.FullName.Substring($root.Length + 1)
    $partes = $rel -split '[\\/]'
    $dirBloqueado = $false
    if ($partes.Length -gt 1) {
        foreach ($seg in $partes[0..($partes.Length-2)]) {
            if ($excluirDirs -contains $seg -or $seg.StartsWith("_")) { $dirBloqueado = $true }
        }
    }
    $arqBloqueado = $_.Name.StartsWith("_") -or $_.Name.StartsWith("~$")
    foreach ($p in $excluirArqs) { if ($_.Name -like $p) { $arqBloqueado = $true } }
    # PNGs brutos de b-roll (2,5 MB cada) ficam fora; as versões JPG comprimidas já estão na landing page.
    $brollPng = ($rel -like "*\broll\*.png")
    -not $dirBloqueado -and -not $arqBloqueado -and -not $brollPng -and $_.Name -ne "empacotar.ps1"
} | ForEach-Object {
    $rel = $_.FullName.Substring($root.Length + 1)
    $dest = Join-Path (Join-Path $staging $nome) $rel
    New-Item -ItemType Directory -Force (Split-Path -Parent $dest) | Out-Null
    Copy-Item $_.FullName $dest
}

if (Test-Path $zip) {
    try { Remove-Item $zip -Force -ErrorAction Stop }
    catch {
        # arquivo em uso (ex.: aberto no Explorer/navegador): gera com sufixo de versão
        $zip = Join-Path (Split-Path -Parent $root) ("$nome`_" + (Get-Date -Format "yyyyMMdd_HHmm") + ".zip")
        Write-Output "ZIP anterior em uso; gerando novo arquivo: $zip"
    }
}
Compress-Archive -Path (Join-Path $staging $nome) -DestinationPath $zip -CompressionLevel Optimal
$tam = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Output "ZIP gerado: $zip ($tam MB)"
Remove-Item $staging -Recurse -Force
