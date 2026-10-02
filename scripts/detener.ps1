$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
# Deten primero el servidor web con Ctrl+C en su terminal.
& .\.venv\Scripts\python.exe scripts/local_db.py stop
