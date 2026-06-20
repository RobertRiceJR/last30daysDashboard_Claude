@echo off
REM Repo-root launcher: resolves Python 3.13 (avoids the Anaconda 3.10 on PATH)
REM and forwards all args to the orchestrator.  Usage:  run doctor | run run | run kpi ...
setlocal
set "PYTHONIOENCODING=utf-8"
set "PY=C:\Users\terri\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=py -3.13"
%PY% "%~dp0src\orchestrator.py" %*
