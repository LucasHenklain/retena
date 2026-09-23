@echo off
title Retena - preparar a banca
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar.ps1" %*
