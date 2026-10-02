# Pulso Tickets · backend_eva2

Venta de entradas para conciertos. Proyecto nuevo e independiente del backend anterior, con Django, DRF, JWT, PostgreSQL, templates y un modelo en **tercera forma normal**.

Autor: **Vicente Mateo Durán Díaz · AP-N4-C1 · 2026**.

Los conciertos, recintos e imagenes del catalogo inicial son ficticios. Los pagos son una **simulacion explicita**: no hay tarjetas, cargos ni devoluciones bancarias reales.

## 1. Iniciar en este computador

La carpeta `.venv`, el archivo `.env`, PostgreSQL portable y el catalogo de ejemplo ya estan preparados. No ejecutes `startproject` ni `startapp` de nuevo.

Abre PowerShell en esta carpeta:

```powershell
cd "C:\Users\vimat\Desktop\Clases\2do sm\backend\backend_eva2"
.\.venv\Scripts\python.exe scripts/local_db.py start
```

**Primera vez solamente:** crea tu administrador. Elige tu propio usuario, correo y contrasena; al escribir la clave no se muestran caracteres en la terminal.

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Luego inicia la web:

```powershell
.\scripts\iniciar.ps1
```

Abre **http://127.0.0.1:8012/**. En **Ingresar** puedes usar el administrador para entrar a Gestion. En **Crear cuenta** se registran espectadores, nunca administradores. No se copiaron usuarios ni claves de proyectos anteriores.

Si el puerto esta ocupado: ` .\scripts\iniciar.ps1 -Puerto 8013 ` y abre `http://127.0.0.1:8013/`.

Para detener: `Ctrl+C` en el servidor web; luego, en la terminal:

```powershell
.\scripts\detener.ps1
```

## 2. Si quieres activar el entorno manualmente

**`.venv` es la carpeta de Python. `.env` es un archivo de configuracion. No son lo mismo.**

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/local_db.py start
python manage.py runserver 127.0.0.1:8012 --nostatic
```

Los scripts de la seccion anterior funcionan **sin activar** el entorno, porque llaman directamente a su Python.

Si PowerShell bloquea un script, permite scripts solo en esa terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Alternativa sin cambiar esa politica:

```powershell
.\.venv\Scripts\python.exe scripts/local_db.py start
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8012 --nostatic
```

## 3. Instalacion nueva u otro computador

Repositorio: [Vitoco6844/backend_eva2](https://github.com/Vitoco6844/backend_eva2). Si es privado, el profesor necesita una invitacion con acceso; tener el enlace no basta.

Requisitos: Windows x64, Python **3.12 o 3.13**, internet para descargar dependencias y aproximadamente 1 GB libre para PostgreSQL portable. No hace falta Node para ejecutar la aplicacion. Descarga el repositorio o clonalo:

```powershell
git clone https://github.com/Vitoco6844/backend_eva2.git
```

```powershell
cd "RUTA\backend_eva2"
.\scripts\configurar.ps1
.\.venv\Scripts\python.exe manage.py createsuperuser
.\scripts\iniciar.ps1
```

`configurar.ps1` crea `.venv`, instala las versiones fijadas, genera claves aleatorias en `.env` si no existe, prepara PostgreSQL local, aplica migraciones, prepara estilos y carga seis eventos ficticios. No instala un servicio de Windows, no toca otras bases y no crea usuarios de la web.

Si Python tiene otro nombre o ruta:

```powershell
.\scripts\configurar.ps1 -Python "C:\ruta\a\python.exe"
```

No copies `.venv` entre computadores: los entornos virtuales contienen rutas locales. Recrealo en el destino. Tampoco subas `.env`, `.local`, `.runtime`, `media` o `staticfiles` a GitHub; `.gitignore` ya los excluye.

### PostgreSQL ya instalado o Linux/macOS

Usa PostgreSQL 14 o superior y Python compatible. Crea una base y un usuario propios, instala `requirements.txt`, y configura `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` en `.env`. Genera `DJANGO_SECRET_KEY` con al menos 40 caracteres aleatorios. En Windows puedes ejecutar `configurar.ps1 -BaseExterna` e `iniciar.ps1 -BaseExterna`. El descargador portable es exclusivo de Windows; Django no requiere ese descargador si ya tienes PostgreSQL.

Con la conexion configurada:

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8012 --nostatic
```

## 4. Uso

- Publico: catalogo, filtros y detalle de conciertos.
- Espectador: registro, carrito persistente, compra pendiente, pago demo, historial, entradas individuales con UUID y QR imprimible.
- Organizador: CRUD de recintos, eventos y localidades; precios, capacidades, ventas, cancelaciones e ingresos.
- Para publicar: crear evento en borrador, agregar una localidad con precio y cambiar el evento a Publicado.
- El carrito **no reserva ni descuenta**. El pago exitoso consume cupos. Una cancelacion los libera una sola vez.
- Cada entrada se valida una vez. El organizador puede registrar el ingreso completo de una compra desde su detalle, con confirmacion explicita.
- Los registros con compras no se borran ni cambian su identidad historica. Se archivan o desactivan. Los cambios de precio crean una tarifa nueva.
- Swagger: `/api/docs/`, solo organizadores. El esquema `/api/schema/` tambien esta protegido.
- No hay Django Admin, interfaz navegable de DRF, carga CSV ni importador masivo.

## 5. Problemas frecuentes

| Mensaje o sintoma | Solucion |
| --- | --- |
| `No module named django` | Usa `.\.venv\Scripts\python.exe` o activa **este** `.venv`, no el de otro proyecto. |
| `manage.py` no existe | Entra a `backend_eva2`; ahi esta `manage.py`. |
| No existe `.venv\Scripts\python.exe` | Ejecuta `scripts\configurar.ps1` con un Python instalado. |
| Falta `DJANGO_SECRET_KEY` | Ejecuta la configuracion inicial. Revisa que `.env` exista, no solo `.env.example`. |
| Conexion rechazada a PostgreSQL | Ejecuta `python scripts/local_db.py start` desde el entorno. Revisa `DB_PORT=55432`. |
| Contrasena de PostgreSQL incorrecta | Revisa `.env`; no borres la base ni regeneres claves a ciegas. La clave de la base no es la del usuario de la web. |
| Puerto ocupado | Cambia el puerto web con `-Puerto 8013`. Para PostgreSQL cambia `DB_PORT` solo con su instancia detenida. |
| Clave de la web olvidada | `python manage.py changepassword TU_USUARIO`. Luego vuelve a ingresar. |
| Estilos viejos o faltantes | `python manage.py collectstatic --noinput`, reinicia el servidor y recarga con Ctrl+F5. |
| Error CSRF | Usa siempre el mismo host (`127.0.0.1`, no alternarlo con `localhost`), recarga e ingresa. En HTTP local `COOKIE_SECURE=False`. |
| Evento no aparece | Comprueba Publicado, fecha futura, recinto activo y localidades activas. |
| No se puede borrar un registro | Hay dependencias o compras historicas: archiva/desactiva, o borra primero las dependencias sin ventas. |

No borres `.local/postgres` ni `.env`: contienen la base local y sus credenciales. Si vuelves a ejecutar `seed_demo`, no modifica eventos existentes. Sus fechas se fijan al crearlos; cuando pase el tiempo debes crear nuevos eventos desde Gestion.

## 6. Pruebas y documentos tecnicos

Con PostgreSQL iniciado:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test tests --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py spectacular --file .local/schema.yml --validate --fail-on-warn
```

Las pruebas crean y eliminan una base `test_...` separada. El usuario PostgreSQL local tiene `CREATEDB` para ese fin, pero **no** es superusuario de PostgreSQL.

- [Modelo relacional y tercera forma normal](docs/MODELO_3FN.md).
- [Arquitectura, endpoints y decisiones](docs/ARQUITECTURA.md).
- [Verificacion y pruebas de navegador](docs/VERIFICACION.md).
- [Procedencia de las imagenes](static/images/README.md).

## 7. Archivos de la entrega

Se versionan codigo Python, migraciones, templates, CSS/JavaScript, imagenes originales, licencias, pruebas, scripts de instalacion, documentacion, `requirements.txt` y `.env.example` sin claves.

No se versionan `.env` (secretos), `.venv`/`env` (entornos que se recrean), `.runtime` (PostgreSQL descargado), `.local` (base y evidencias temporales), `media` (archivos subidos localmente), `staticfiles` (resultado de collectstatic), caches, logs, respaldos, claves privadas ni `node_modules`. Las migraciones y `seed_demo` reconstruyen la estructura y el catalogo; las cuentas se crean en cada instalacion. No se comparte una clave de administrador.

Este es un proyecto academico ejecutable en local, **no un despliegue de produccion ni una pasarela real**. Subirlo a GitHub no inicia un servidor publico. Para publicar la web en internet se requieren HTTPS, cookies seguras, configuracion de servidor/media, copias de seguridad y una integracion de pagos real.
