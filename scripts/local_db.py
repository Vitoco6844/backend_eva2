"""PostgreSQL portable aislado: no instala servicios ni modifica otras bases."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
LOCAL = ROOT / ".local"
BIN = RUNTIME / "pgsql" / "bin"
DATA = LOCAL / "postgres"
URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260616"


def run(args, **kwargs):
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    return subprocess.run([str(a) for a in args], check=True, **options, **kwargs)


def configuration():
    """Las claves se generan una vez; nunca se imprimen ni se versionan."""
    import environ
    LOCAL.mkdir(exist_ok=True)
    target = ROOT / ".env"
    if not target.exists():
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        example = example.replace("DJANGO_SECRET_KEY=\n", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(56)}\n")
        example = example.replace("DB_PASSWORD=\n", f"DB_PASSWORD={secrets.token_urlsafe(32)}\n")
        target.write_text(example, encoding="utf-8")
    env = environ.Env()
    environ.Env.read_env(target)
    return env


def install():
    RUNTIME.mkdir(exist_ok=True)
    if (BIN / "pg_ctl.exe").exists():
        return
    archive = RUNTIME / "postgresql.zip"
    if not archive.exists():
        print("Descargando PostgreSQL 17.11 desde EDB (aprox. 382 MB)...")
        partial = RUNTIME / "postgresql.download"
        urllib.request.urlretrieve(URL, partial)
        partial.replace(archive)
    print("Extrayendo PostgreSQL portable...")
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            destination = (RUNTIME / item.filename).resolve()
            if not destination.is_relative_to(RUNTIME.resolve()):
                raise RuntimeError("Ruta no segura dentro del archivo descargado.")
        bundle.extractall(RUNTIME)


def start(env):
    if not (DATA / "PG_VERSION").exists():
        raise RuntimeError("Primero ejecuta configurar.ps1 para inicializar la base.")
    status = subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"], capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if status.returncode == 0:
        print("PostgreSQL local ya esta activo.")
        return
    run([BIN / "pg_ctl.exe", "-D", DATA, "-l", LOCAL / "postgres.log", "-o",
         f"-h 127.0.0.1 -p {env('DB_PORT')}", "-w", "start"])


def initialize(env):
    import psycopg
    from psycopg import sql
    install()
    password_file = LOCAL / "bootstrap-password"
    if not (DATA / "PG_VERSION").exists():
        password_file.write_text(secrets.token_urlsafe(40), encoding="ascii")
        run([BIN / "initdb.exe", "-D", DATA, "-U", "pulso_bootstrap", "--pwfile", password_file,
             "--auth-host=scram-sha-256", "--auth-local=scram-sha-256", "--encoding=UTF8", "--locale=C"])
    start(env)
    if not password_file.exists():
        raise RuntimeError("Falta la clave local de inicializacion. No se modifico la base existente.")
    with psycopg.connect(host="127.0.0.1", port=env("DB_PORT"), dbname="postgres", user="pulso_bootstrap",
                         password=password_file.read_text().strip(), autocommit=True) as connection:
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [env("DB_USER")]).fetchone():
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN CREATEDB PASSWORD {}").format(sql.Identifier(env("DB_USER")), sql.Literal(env("DB_PASSWORD"))))
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", [env("DB_NAME")]).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(env("DB_NAME")), sql.Identifier(env("DB_USER"))))
    print("Base aislada lista. El usuario de la aplicacion no es superusuario de PostgreSQL.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "start", "stop", "config"])
    args = parser.parse_args()
    env = configuration()
    if args.action == "init":
        initialize(env)
    elif args.action == "start":
        start(env)
    elif args.action == "stop" and (DATA / "postmaster.pid").exists():
        run([BIN / "pg_ctl.exe", "-D", DATA, "-m", "fast", "-w", "stop"])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"No se pudo completar: {error}", file=sys.stderr)
        sys.exit(1)
