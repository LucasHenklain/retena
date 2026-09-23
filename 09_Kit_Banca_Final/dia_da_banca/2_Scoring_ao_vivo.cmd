@echo off
title Retena - scoring in-database (Oracle AI Database 26ai)
cd /d "%~dp0"
mode con: cols=110 lines=45
python "%~dp0scoring_ao_vivo.py" %*
