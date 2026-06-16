@echo off
title Robot RJ Call - Sincronizacion ZKTeco
color 0A
echo ===================================================
echo INICIANDO MOTOR DE ASISTENCIA...
echo ===================================================

cd /d "%~dp0"

"venv\Scripts\python.exe" "robot_asistencia_rj.py"

pause