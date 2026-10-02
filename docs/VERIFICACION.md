# Verificacion tecnica

Fecha: **2 de octubre de 2026**. Proyecto: **Pulso Tickets / backend_eva2**.

## Resultado comprobado

- `manage.py check`: sin problemas.
- `manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- Migraciones aplicadas en PostgreSQL, sin SQLite ni cambio de motor silencioso.
- `manage.py test tests --noinput`: **75 pruebas aprobadas**; revision de entrega, 27,450 segundos.
- `manage.py spectacular --validate --fail-on-warn`: esquema valido, sin advertencias.
- `pip check`: sin dependencias incompatibles.
- `collectstatic --noinput`: estilos, scripts, imagenes e interfaz Swagger preparados correctamente.
- Dos recorridos de navegador automatizados con Playwright y Microsoft Edge sin errores JavaScript no controlados.
- Capturas revisadas en **1440, 768 y 360 pixeles**. Imagenes y QR cargados; sin desbordamiento horizontal de la pagina. Las tablas administrativas conservan desplazamiento interno cuando lo necesitan.

Las primeras ejecuciones detectaron y permitieron corregir detalles de rutas, opciones HTML, paginacion administrativa y comportamiento de formularios. Los resultados anteriores corresponden a las verificaciones finales satisfactorias, no a intentos fallidos.

## Cobertura automatizada

| Archivo | Pruebas | Temas |
| --- | ---: | --- |
| `tests/test_auth.py` | 19 | JWT/rol, cookies HttpOnly, CSRF, registro sin privilegios, duplicados, claves, expiracion, refresh rotado, logout, usuario inactivo, permisos, Swagger privado, dos dispositivos y cache privada. |
| `tests/test_catalog.py` | 19 | CRUD de organizador, lectura publica, borradores, validaciones, archivos, filtros, proteccion historica, capacidad, 3FN y 404. |
| `tests/test_sales.py` | 31 | Carrito, propietarios, cantidades, precio firmado, version, idempotencia, compra multievento, pago, rollback, UUID por unidad, cancelacion, ingreso y rutas equivalentes a la pauta. |
| `tests/test_concurrency.py` | 6 | Conexiones PostgreSQL simultaneas: ultimo cupo, mismo pago, mismo checkout, misma seleccion, misma cancelacion y misma entrada. |
| **Total** | **75** | Bases de prueba independientes, creadas y eliminadas automaticamente. |

La prueba del ultimo cupo crea dos compras pendientes y lanza sus pagos simultaneamente. Solo una termina PAGADO; la otra recibe conflicto. La disponibilidad termina en cero y se crea una unica entrada. No se ha sustituido esta prueba por un mock de la base.

## Recorridos del navegador

`scripts/ui_smoke.cjs`:

1. Catalogo y carga de todas las imagenes.
2. Intento de agregar sin cuenta, ingreso y regreso al evento.
3. Seleccion de dos entradas y carrito.
4. Checkout, pago rechazado y luego aprobado.
5. Dos entradas independientes y QR privado.
6. Denegacion de gestion y Swagger al espectador.
7. Ingreso de organizador y CRUD individual de recinto.
8. Listado de eventos y validacion de una entrada.
9. Rechazo de reutilizacion del ticket y cancelacion de compra.
10. Swagger con esquema cargado; pantallas publicas y registro en movil/tablet; 404 propio.

`scripts/ui_extended.cjs`:

1. Registro completo de un espectador desde el formulario.
2. Filtro real por ciudad y acceso a compras/entradas.
3. Access invalido y recuperacion de sesion mediante refresh HttpOnly.
4. Creacion de evento borrador y su localidad.
5. Cambio de precio y publicacion.
6. Presencia en cartelera publica.
7. Formularios/listados administrativos a 360 px.
8. Archivo y desaparicion del catalogo publico.
9. Eliminacion del evento sin ventas y sus dependencias.

Las capturas estan en `.local/screenshots/` y se excluyen del repositorio. Los scripts de prueba si forman parte del proyecto.

## Repetir las pruebas de navegador

Es opcional para ejecutar la web. Requiere Node.js y Edge; las versiones JS estan declaradas en `package.json`. No uses el servidor normal: el servidor QA crea una base **`test_pulso_ui`** separada y cuentas sinteticas temporales, sin tocar la base del alumno.

Primera terminal, desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe scripts/local_db.py start
npm install
.\.venv\Scripts\python.exe scripts/ui_server.py
```

Segunda terminal, en la misma carpeta:

```powershell
node scripts/ui_smoke.cjs
node scripts/ui_extended.cjs
.\.venv\Scripts\python.exe scripts/ui_server.py --stop
```

El puerto 8012 debe estar libre antes de iniciar QA. Si esta ocupado por tu servidor normal, configura `$env:QA_PORT='8014'` en ambas terminales antes de ejecutar los comandos anteriores. No ejecutes dos servidores QA simultaneos: comparten la base temporal. El cierre con `--stop` elimina esa base. Si se interrumpe a la fuerza, la siguiente ejecucion recreara **solo** esa base de pruebas. Las claves sinteticas viven en `.local/ui_password`, no en el repositorio.

En otro sistema sin Edge: instala Chromium con `npx playwright install chromium`. La eleccion predeterminada de Windows es Edge; puede configurarse `PW_CHANNEL=chrome` para Chrome instalado. Las pruebas son locales; no navegan por cuentas personales ni sitios de terceros.

## Trazabilidad con la pauta y las aclaraciones

| Requisito | Implementacion/evidencia |
| --- | --- |
| PostgreSQL, ORM, FK, OneToOne, CHOICES | `settings.py`, modelos/migraciones; tests usan PostgreSQL real. |
| Tercera forma normal | `docs/MODELO_3FN.md`; tarifas versionadas y totales/stock calculados. |
| DRF y JWT con rol | `accounts`, serializers/viewsets/vistas, cookies access/refresh y tests. |
| Carrito persistente por usuario | `Cart.user` OneToOne, items en base y prueba de dos dispositivos/logout. |
| Comprar entradas de varios eventos/localidades | CartItem y PurchaseLine; prueba multievento y rechazo atomico. |
| Stock solo al pagar y reposicion al cancelar | `sales/services.py`, inventario SQL y seis pruebas simultaneas. |
| UUID unico por unidad | Ticket UUID y ordinal; tests y captura de entradas/QR. |
| CRUD de organizador con templates | Panel propio para recintos/eventos/localidades; sin Django Admin ni DRF navegable. |
| Actualizar estados de compra | Accion `/estado/`, validacion individual e ingreso completo administrativo. |
| Filtros django-filter | `catalog/filters.py` y consultas verificadas. |
| Swagger privado | `/api/docs/` y `/api/schema/` bloqueados para anonimos/espectadores. |
| Login obligatorio para carrito | Permiso IsSpectator del backend y recorrido de navegador sin cuenta. |
| 404 con re_path | Ultima ruta en `pulso/urls.py`, handler404 y pruebas HTTP404 reales. |
| Comentarios por bloques | Modulos Python, scripts, templates y secciones CSS. |
| Footer | Nombre completo, seccion y 2026 configurados. |
| Sin carga masiva/CSV | CRUD de un registro; listas y CSV rechazados. Seed es un catalogo sintetico de instalacion, no un importador de usuario. |
| GitHub | Repositorio independiente de entrega: `https://github.com/Vitoco6844/backend_eva2`. Un repositorio privado requiere dar acceso al profesor. |

## Estado de los datos y limites

La base de desarrollo quedo con seis eventos ficticios, cero usuarios y cero compras. Las cuentas de pruebas no se copiaron a ella. El administrador se crea con `createsuperuser`, como indica el README; no hay una contrasena compartida o heredada.

## Revision previa a la entrega (2 de octubre)

Se contrastaron los requisitos generales, checklist y opcion 3 del PDF con modelos, migraciones, permisos, serializers, servicios, rutas, templates y pruebas. Tambien se revisaron las siete aclaraciones del profesor y las dependencias funcionales documentadas en `MODELO_3FN.md`. No se detectaron incumplimientos funcionales en los recorridos verificados.

Se repitieron las 75 pruebas y los dos recorridos de navegador con una base temporal, usando el puerto 8014 para no interferir con el servidor normal. Se hicieron configurables los puertos QA y se ampliaron las exclusiones de Git para respaldos y claves privadas. El control de archivos candidatos no detecto claves locales ni tokens GitHub; `.env.example` conserva vacios los campos secretos. Los archivos generados y las cuentas temporales no forman parte de la entrega.

El PDF exige roles y autenticacion, pero no especifica cuentas de demostracion precreadas. El catalogo inicial es reproducible; el administrador se crea durante la instalacion y los espectadores pueden registrarse desde los templates. Los pagos siguen siendo simulados. Estas verificaciones no equivalen a garantizar ausencia absoluta de errores ni sustituyen la evaluacion del profesor.

Verificado en Windows x64, Python 3.12.14 y PostgreSQL portable 17.11, con las dependencias fijadas en `requirements.txt`. No se ha realizado despliegue en internet, auditoria profesional de seguridad, ensayo de alta carga ni integracion bancaria. No se promete una nota determinada: esta evidencia cubre desarrollo tecnico; la defensa individual se preparara por separado.
