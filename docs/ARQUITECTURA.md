# Arquitectura y alcance tecnico

## Componentes

| Carpeta | Responsabilidad |
| --- | --- |
| `pulso` | Configuracion por entorno y enrutamiento global. |
| `accounts` | Usuario extendido, registro, JWT, cookies, CSRF, permisos y renovacion. |
| `catalog` | ORM de recintos, eventos, localidades y tarifas; serializers, filtros y CRUD. |
| `sales` | Carrito, compras, entradas, auditoria y servicios transaccionales. |
| `web` | Vistas HTML, formularios visuales, contexto, errores y formato de dinero. |
| `templates` | Pantallas propias para publico, espectador y organizador. |
| `static` | CSS, JavaScript, iconos Lucide e imagenes originales locales. |
| `tests` | Pruebas aisladas con PostgreSQL. |
| `scripts` | Configuracion, arranque y pruebas de navegador. |

Recorrido: **URL HTML -> vista Django -> template -> JavaScript/fetch -> API DRF -> serializer/permisos -> servicio -> ORM/PostgreSQL**. La navegacion y las redirecciones regresan a URLs HTML. `ModelViewSet` implementa el CRUD individual del catalogo; `APIView` y acciones de compra exponen operaciones de negocio especificas.

## Autenticacion

- Usuario propio basado en `AbstractUser`. Roles `ESPECTADOR` y `ORGANIZADOR` con choices.
- Registro publico rechaza campos de privilegios y aplica validadores de contrasena.
- `createsuperuser` crea un organizador; no existe una URL de Django Admin.
- SimpleJWT emite access de 15 minutos y refresh de 7 dias con claim `rol`.
- Tokens en cookies **HttpOnly**, `SameSite=Lax`; el JavaScript no lee ni almacena JWT en localStorage.
- Renovacion rota y revoca el refresh previo. Un bloqueo sobre el token pendiente evita reutilizacion simultanea.
- Logout revoca refresh y elimina cookies; el carrito sigue en PostgreSQL.
- Como en un JWT de corta vida habitual, una copia externa de un access ya emitido puede vivir hasta su vencimiento tras logout. Cambiar contrasena o desactivar la cuenta invalida sus operaciones inmediatamente; no se afirma revocacion universal instantanea del access al salir.
- Los permisos consultan el usuario actual en base de datos; un claim antiguo no conserva privilegios revocados.
- Se acepta `Authorization: Bearer ...` para clientes API. Las cookies exigen CSRF para escrituras, incluyendo login, registro, renovacion y logout. El cliente envia `X-CSRFToken` desde la cookie CSRF legible.
- Las vistas privadas renuevan la sesion antes de pedir otro ingreso. Sin cuenta valida no renderizan los datos protegidos.
- Swagger y esquema requieren organizador, no basta con ocultar su enlace.

## Endpoints principales

La nomenclatura es minuscula y termina en `/`. Las rutas HTML no se confunden con estas.

| Ruta API | Operaciones | Permiso |
| --- | --- | --- |
| `/api/auth/registro/` | POST | Publico con CSRF; solo espectador |
| `/api/auth/login/`, `refresh/`, `logout/` | POST | Credenciales/token/cookies y CSRF segun operacion |
| `/api/auth/me/` | GET | Autenticado |
| `/api/eventos/`, `/api/eventos/{id}/` | GET y CRUD | Lectura publica de publicados; escritura organizador |
| `/api/eventos/{id}/sectores/` | GET | Publico para evento visible |
| `/api/recintos/`, `/api/recintos/{id}/` | GET y CRUD | Lectura publica activa; escritura organizador |
| `/api/sectores/`, `/api/sectores/{id}/` | GET y CRUD | Lectura publica visible; escritura organizador |
| `/api/carrito/` | GET, POST, DELETE | Espectador propietario |
| `/api/carro-tickets/` | GET, POST, DELETE | Alias equivalente al nombre de la pauta |
| `/api/carrito/items/` | POST | Agrega cantidad a una localidad |
| `/api/carrito/items/{id}/` | PATCH, DELETE | Ajusta cantidad absoluta o elimina; propietario |
| `/api/checkout/` | POST | Espectador; resumen firmado y clave idempotente |
| `/api/compras/`, `/api/compras/{uuid}/` | GET | Propias del espectador; todas para organizador |
| `/api/compras/{uuid}/pagar/` | POST | Espectador propietario; simulacion |
| `/api/compras/pagar/` | POST | Equivalente con identificador de compra en el cuerpo |
| `/api/compras/{uuid}/estado/` | PATCH | Solo organizador |
| `/api/mis-entradas/` | GET | Entradas propias del espectador |
| `/api/entradas/validar/` | POST | Organizador; UUID y evento |
| `/api/docs/`, `/api/schema/` | GET | Solo organizador |

GET `/api/eventos/` admite `q`, `nombre`, `artista`, `ciudad`, `recinto`, `fecha_desde`, `fecha_hasta`, `precio_min`, `precio_max`, `disponibles`, `estado` y paginacion. `catalogo=true` fuerza la cartelera publica incluso si quien consulta es organizador. Los rangos de precio se aplican a una **misma** localidad disponible; no se mezclan minimos/maximos de localidades diferentes.

GET `/api/compras/` filtra por `status` y busca cliente/evento con `q`; nunca amplifica los permisos del espectador. `/api/sectores/` filtra por `event`.

## Checkout y pagos

1. El carrito permanece en la base y no reserva inventario.
2. GET carrito devuelve version, precios actuales, total calculado y resumen firmado que vence a los 30 minutos.
3. POST checkout verifica propietario, version, firma y disponibilidad. Una tarifa nueva obliga a aceptar de nuevo el resumen. Crea compra PENDIENTE y limpia carrito de forma atomica.
4. `checkout_key` identifica reintentos. La misma solicitud devuelve la compra anterior; otra solicitud con esa clave produce 409.
5. El pago demo recibe `result=approved` o `declined`. Esta eleccion sirve exclusivamente para simular escenarios academicos. **No es validacion de un banco**.
6. Pago aprobado bloquea compra/inventario, valida todos los sectores, cambia a PAGADO y emite UUID por unidad en una sola transaccion.
7. El total se obtiene del historial de tarifas, no del cuerpo de la peticion. No se aceptan precios, propietarios, totales o estados ocultos enviados por el cliente.

## Estados

```text
PENDIENTE -> PAGADO -> ENTREGADO
     |          |           |
     +----------+-----------+-> CANCELADO
```

- PENDIENTE a PAGADO: pago demo aprobado y capacidad suficiente.
- PAGADO a ENTREGADO: todas las entradas utilizadas, ya sea individualmente en Control de acceso o por confirmacion explicita de ingreso completo del organizador.
- CANCELADO es terminal. Repetir la cancelacion no agrega capacidad dos veces.
- Se permite cancelar una compra entregada porque la pauta exige reposicion al cancelar. Se advierte al organizador, se exige motivo, se conserva `used_at` y se anulan los UUID. No implica reembolso real.
- En compras de varios eventos, validar una entrada no entrega las restantes. La accion de ingreso completo advierte que comprende todos los eventos de la compra.

## Errores y seguridad

- 400: datos invalidos; 401: identidad ausente o vencida; 403: rol/CSRF; 404: recurso inexistente o ajeno; 409: stock, historia protegida, estado o idempotencia; 415: formato no admitido.
- `re_path` al final y `handler404` manejan rutas y objetos inexistentes sin devolver falsos 200. Las paginas tienen HTML propio y un enlace de regreso; los endpoints responden JSON.
- DEBUG=False por defecto, sin traceback en la interfaz. No hay renderer navegable DRF.
- Fotos JPG/PNG/WebP reales verificadas por Pillow, maximo 5 MB. No se admiten SVG subidos ni archivos CSV como catalogo.
- Templates escapan texto y JavaScript usa `textContent`; no inserta nombres o descripciones de usuarios como HTML.
- Registro/login/refresh/logout tienen limite de frecuencia de demostracion con cache local. Un despliegue distribuido necesita cache compartida y politica de proteccion adecuada.
- `next` solo permite redirecciones locales hacia paginas HTML.
- Claves fuera de Git. PostgreSQL portable escucha solo en `127.0.0.1`, usa SCRAM y usuario de aplicacion sin superprivilegios de base.

## Limites deliberados

No incluye banco real, correo real, fila virtual, reserva temporal, asientos numerados, devoluciones bancarias, marketplace multiempresa o cargas CSV. El QR identifica una entrada y requiere validacion en servidor; no es un QR dinamico antifraude. El PDF de entrada se obtiene con la impresion del navegador.

En produccion: HTTPS y cookies Secure obligatorios, servidor WSGI adecuado, host/proxy de confianza, servidor de archivos, copias de seguridad, monitoreo, secretos administrados y pasarela con callbacks autenticados e idempotentes. Los ajustes de desarrollo WhiteNoise y el usuario CREATEDB para pruebas no son una recomendacion de produccion.

Fuentes de base: investigacion previa en `../investigacion_eva2_tickets/`, PDF EVA-2 proporcionado y aclaraciones del profesor. El cambio de modelado respecto de la propuesta previa esta descrito en `MODELO_3FN.md`.
