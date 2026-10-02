"""Servidor de prueba con una base temporal separada; no toca la base de desarrollo."""
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import urllib.request
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("QA_PORT", "8012"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulso.settings")

# Cierre limpio exclusivo de este servidor temporal, sin detener procesos ajenos.
if "--stop" in sys.argv:
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}/_qa/stop/", method="POST",
                                     headers={"X-QA-Token": (ROOT / ".local" / "ui_password").read_text().strip()})
    with urllib.request.urlopen(request) as response:
        print(response.read().decode())
    sys.exit(0)

import django
django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test.utils import setup_databases, teardown_databases
from django.core.wsgi import get_wsgi_application

# Nombre distinto a la base de las pruebas unitarias y a la base del alumno.
connection.settings_dict["TEST"]["NAME"] = "test_pulso_ui"
with socket.socket() as probe:
    # Rechazar un puerto ocupado antes de recrear la base exclusiva de QA.
    probe.bind(("127.0.0.1", PORT))
old_config = setup_databases(verbosity=0, interactive=False)
try:
    call_command("seed_demo")
    password = secrets.token_urlsafe(24)
    (ROOT / ".local" / "ui_password").write_text(password, encoding="utf-8")
    User = get_user_model()
    User.objects.create_user("QAViewer", "viewer@example.test", password, first_name="Usuario", last_name="Prueba")
    User.objects.create_superuser("QAManager", "manager@example.test", password)
    application = get_wsgi_application()
    def qa_application(environ, start_response):
        if environ.get("PATH_INFO") == "/_qa/stop/" and environ.get("REQUEST_METHOD") == "POST" and secrets.compare_digest(environ.get("HTTP_X_QA_TOKEN", ""), password):
            start_response("200 OK", [("Content-Type", "text/plain")])
            threading.Thread(target=server.shutdown, daemon=True).start()
            return [b"Cerrando servidor temporal de pruebas."]
        return application(environ, start_response)

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = False

        def server_bind(self):
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            return super().server_bind()

    with make_server("127.0.0.1", PORT, qa_application, server_class=ThreadedServer) as server:
        print(f"Servidor QA aislado en http://127.0.0.1:{PORT}/", flush=True)
        server.serve_forever()
finally:
    teardown_databases(old_config, verbosity=0)
