# Converte os .html gerados por `python gerar_pdfs.py --so-html` em PDF com o Edge headless (um perfil por arquivo, sequencial).
# Uso: powershell -ExecutionPolicy Bypass -File converter_pdfs.ps1
$Edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$Aqui = $PSScriptRoot
Get-ChildItem -Path $Aqui -Recurse -Filter *.html | Where-Object { Test-Path ($_.FullName -replace '\.html$', '.md') } | ForEach-Object {
    $html = $_.FullName; $pdf = $html -replace '\.html$', '.pdf'
    if (Test-Path $pdf) { Remove-Item -Force $pdf }
    $perfil = Join-Path $env:TEMP ("edge_pdf_" + [IO.Path]::GetFileNameWithoutExtension($html))
    $url = "file:///" + ($html -replace '\\', '/')
    $p = Start-Process -FilePath $Edge -ArgumentList "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--allow-file-access-from-files", "--user-data-dir=$perfil", "--no-pdf-header-footer", "--print-to-pdf=$pdf", $url -PassThru -WindowStyle Hidden
    if (-not $p.WaitForExit(90000)) { $p.Kill(); Write-Host ("TIMEOUT " + $_.Name) -ForegroundColor Yellow }
    if (Test-Path $pdf) { Write-Host ("ok      " + ($pdf.Substring($Aqui.Length + 1))); Remove-Item -Force $html } else { Write-Host ("FALHOU  " + $_.Name) -ForegroundColor Red }
}
