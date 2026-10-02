param([string]$Python = "python", [switch]$BaseExterna)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
# No es necesario activar el entorno para usar su interprete directamente.
if (!(Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear .venv. Instala Python 3.12 o 3.13." }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de dependencias." }
if ($BaseExterna) {
    & .\.venv\Scripts\python.exe scripts/local_db.py config
} else {
    & .\.venv\Scripts\python.exe scripts/local_db.py init
}
if ($LASTEXITCODE -ne 0) { throw "Revisa la configuracion de PostgreSQL y .env." }
& .\.venv\Scripts\python.exe manage.py migrate
if ($LASTEXITCODE -ne 0) { throw "No se pudieron aplicar las migraciones." }
& .\.venv\Scripts\python.exe manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar los estilos." }
& .\.venv\Scripts\python.exe manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw "No se pudo cargar el catalogo de ejemplo." }
Write-Host "Listo. Crea tu administrador con: .\.venv\Scripts\python.exe manage.py createsuperuser"
Write-Host "Luego inicia con: .\scripts\iniciar.ps1"
