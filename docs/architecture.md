# Arquitectura inicial

## Rutas previstas

- `/` - home con creación anónima rápida.
- `/register/` - registro de usuario.
- `/login/` - login.
- `/logout/` - logout mediante POST.
- `/dashboard/` - panel privado mínimo.
- `/profile/` - edición de perfil básico.
- `/profile/api-key/rotate/` - rotación de API key mediante POST.
- `/profile/api-key/revoke/` - revocación de API key mediante POST.
- `/links/new/` - creación autenticada de URL corta.
- `/links/<id>/` - detalle básico de URL propia.
- `/links/<id>/edit/` - edición de campos permitidos.
- `/links/<id>/delete/` - ocultado mediante soft delete.
- `/a/<slug>/` - redirección pública anónima/global.
- `/<namespace>/<slug>/` - redirección pública bajo namespace de usuario.
- `/api/shorten/` - creación de URL corta por API JSON.
- `/api/links/` - listado de URLs propias por API key.
- `/report/` - formulario publico de reporte de abuso.
- `/admin/` - administración de Django.
- `/healthz/` - healthcheck básico.

En esta microfase están activos `/`, `/register/`, `/login/`, `/logout/`,
`/dashboard/`, `/profile/`, `/profile/api-key/rotate/`,
`/profile/api-key/revoke/`, `/links/new/`, `/links/<id>/`,
`/links/<id>/edit/`, `/links/<id>/delete/`, `/a/<slug>/`,
`/<namespace>/<slug>/`, `/api/shorten/`, `/api/links/`, `/report/`,
`/healthz/` y `/admin/`.

## Modelo de privacidad

urlbreve no debe guardar IPs, user-agent, referrer, geolocalización ni
identificadores de tracking. Las estadísticas se diseñan como contadores
agregados, por ejemplo clics diarios por enlace mediante `ShortURLDailyStats`.

Las redirecciones públicas no persisten datos del visitante. En producción
también habrá que revisar configuración de reverse proxy y logs web para
alinear la infraestructura con esta política.

El despliegue de producción documentado usa nginx con `access_log off` y no
reenvía `X-Forwarded-For`, `X-Real-IP`, `Forwarded`, `User-Agent` ni `Referer`
a Django. La aplicación solo necesita `Host` y `X-Forwarded-Proto` para generar
URLs correctas y operar detrás de TLS.

## Modos de URL

`ShortURL.public_mode` define dos modos iniciales:

- `anonymous`: slug global bajo `/a/<slug>/`. Puede pertenecer a un usuario,
  pero la URL pública no expone su namespace.
- `namespace`: slug bajo `/<namespace>/<slug>/`. Requiere owner y usa el
  `UserProfile.public_namespace` actual del usuario.

El namespace público vive en `UserProfile` y es único. Se puede editar, así que
los enlaces namespaced se modelan por `owner + slug` y no duplican el namespace
como texto en cada URL. Esto evita inconsistencias si el usuario cambia su
namespace.

## Gestión autenticada de URLs

La gestión inicial de `ShortURL` vive en vistas Django protegidas por login. El
dashboard muestra las URLs propias no eliminadas y su ruta pública conceptual,
clicks, expiración, límite y estado.

Campos editables al crear:

- `destination_url`;
- `slug`, opcional;
- `title`;
- `public_mode`;
- `expires_days`;
- `max_clicks`;
- `password`.

Si `slug` queda vacío, se genera un código aleatorio seguro de 8 caracteres y se
comprueba que no colisione en el modo elegido. Si el usuario informa un slug, se
valida con la regla ASCII conservadora y se comprueba colisión antes de guardar.

Campos editables después de crear:

- `destination_url`;
- `title`;
- `expires_at`;
- `max_clicks`;
- `is_active`;
- `password`.

Campos no editables después de crear:

- `slug`;
- `public_mode`;
- `owner`.

La contraseña queda guardada como hash en `password_hash`. El flujo público
muestra un formulario de contraseña solo cuando el enlace existe y está
disponible.

## Creación anónima web

La home `/` expone un formulario de creación sin login. Este flujo crea
`ShortURL` con:

- `owner=None`;
- `public_mode=anonymous`;
- ruta pública `/a/<slug>/`;
- `destination_url`;
- `slug`, opcional;
- `expires_days`;
- `max_clicks`;
- `password`, opcional.

No permite namespace, título ni asociación posterior a una cuenta. El enlace no
aparece en dashboard, no puede editarse desde la UI autenticada y no tiene flujo
de recuperación. La página de resultado muestra la URL corta, expiración, límite
de clicks y si está protegida por contraseña.

El formulario anónimo reutiliza la misma base de validación que la creación
autenticada: URL destino `http://`/`https://`, slugs ASCII conservadores,
sugerencias de colisión, generación aleatoria de 8 caracteres y guardado de
contraseña solo como hash.

## Soft delete y disponibilidad

La acción de ocultar una URL marca `deleted_at` y no borra físicamente la fila.
Las URLs con `deleted_at` no aparecen en el dashboard/listado normal. Por ahora,
los slugs de URLs ocultas siguen bloqueados por las constraints de unicidad para
evitar reutilización accidental y preservar auditabilidad.

`ShortURL` expone helpers de dominio:

- `get_public_path()`;
- `get_public_url(request=None)`;
- `is_expired`;
- `is_click_limit_reached`;
- `is_available`;
- `mark_deleted()`.

`is_available` indica disponibilidad operativa para redirecciones: no eliminada,
activa, no deshabilitada, no expirada y sin límite de clicks agotado. Un enlace
puede estar disponible y requerir contraseña.

## Redirecciones públicas y estadísticas

Las rutas públicas activas son:

- `/a/<slug>/`, que busca `ShortURL.public_mode=anonymous`;
- `/<namespace>/<slug>/`, que resuelve `UserProfile.public_namespace` y luego
  busca `ShortURL.public_mode=namespace` para ese owner.

Antes de redirigir, la vista entra en una transacción y bloquea la fila de
`ShortURL` con `select_for_update`. Esto evita una carrera evidente con
`max_clicks=1`: el primer acceso incrementa el contador y el segundo ya ve el
límite agotado.

Si el enlace no existe o no está disponible, se devuelve una página genérica
`links/unavailable.html` con status `404`. La respuesta no indica si el enlace
existió, expiró, fue deshabilitado, fue ocultado o agotó usos.

Si el enlace está disponible y tiene `password_hash`, se muestra
`links/password_gate.html`. El formulario soporta GET y POST en las mismas rutas
públicas `/a/<slug>/` y `/<namespace>/<slug>/`. Una contraseña incorrecta muestra
un error genérico y no registra estadísticas.

Si el enlace está disponible y no requiere contraseña, o si la contraseña fue
correcta, se registra únicamente:

- incremento de `ShortURL.click_count`;
- actualización de `ShortURL.last_clicked_at`;
- incremento de `ShortURLDailyStats.clicks` para la fecha local actual.

No se guardan IPs, user-agent ni referrer en el modelo de estadísticas. Tampoco
se guardan intentos fallidos del password gate.

## Reportes de abuso y moderacion

`/report/` permite crear `AbuseReport` desde una vista publica con Django
templates. El formulario pide solo:

- `reported_path`;
- `reason`;
- `details`, opcional y limitado.

No se solicita email ni se persisten IP, user-agent, referrer u otros datos del
visitante. El formulario incluye un campo honeypot no persistente y oculto para
usuarios normales. Si `URLBREVE_REPORT_HONEYPOT_ENABLED=True` y el campo llega
relleno, la vista devuelve la misma pantalla de reporte recibido pero no crea
`AbuseReport`. No se integra captcha externo para evitar dependencias y tracking
de terceros.

Al recibir un reporte, `links.services.resolve_reported_path()` normaliza la
ruta e intenta resolver:

- `/a/<slug>/` contra enlaces `anonymous`;
- `/<namespace>/<slug>/` contra `UserProfile.public_namespace` y enlaces
  `namespace`.

Si la ruta se resuelve, `AbuseReport.short_url` apunta al enlace. Si no, el
reporte se conserva con `short_url=None` y `reported_path` normalizado para
revision manual.

El admin registra `AbuseReport` y permite filtrar por estado, motivo y fecha.
`ShortURLAdmin` incluye acciones para deshabilitar o rehabilitar enlaces
seleccionados. Deshabilitar un enlace marca `ShortURL.is_disabled=True`; la
redireccion publica ya lo bloquea mediante `ShortURL.is_available` sin revelar
al visitante el motivo exacto.

## API pública inicial

`POST /api/shorten/` usa Django puro y `JsonResponse`. No se introduce Django
REST Framework en esta fase.

Autenticación:

- sin `X-API-Key`, la creación es anónima, `owner=None` y
  `public_mode=anonymous`;
- con `X-API-Key` válida, la creación queda asociada al usuario dueño de la
  clave;
- con `X-API-Key` inválida, se devuelve `401` genérico;
- `public_mode=namespace` requiere una API key válida.

`UserProfile.api_key_hash` guarda solo el hash de la clave. La clave en claro se
muestra una sola vez al generarla o rotarla desde `/profile/`. Revocar la clave
deja `api_key_hash` vacío.

Payload admitido:

- `destination_url`, requerido;
- `slug`, opcional;
- `title`, opcional;
- `public_mode`, opcional;
- `expires_days`, opcional, entero `>= 0`;
- `max_clicks`, opcional, entero `>= 0`;
- `password`, opcional.

Validaciones:

- `destination_url` solo admite `http://` o `https://`;
- slug manual usa la misma regla ASCII conservadora que la UI;
- slug vacío genera código aleatorio de 8 caracteres;
- colisiones devuelven `409` con sugerencias;
- JSON inválido o campos inválidos devuelven `400`;
- métodos distintos de POST devuelven `405`.

Respuesta exitosa `201`:

- `id`;
- `short_url`;
- `public_path`;
- `destination_url`;
- `title`;
- `public_mode`;
- `expires_at`;
- `max_clicks`;
- `password_protected`.

La API no guarda IP, user-agent, referrer ni API keys en claro. Tampoco devuelve
`api_key_hash`.

`GET /api/links/` lista URLs propias del usuario resuelto desde `X-API-Key`.
No hay modo anónimo para esta ruta. Si la clave falta o es inválida, devuelve
`401` genérico.

Scope:

- solo `ShortURL.owner=user` asociado a la API key;
- excluye URLs anónimas `owner=None`;
- excluye URLs de otros usuarios;
- excluye `deleted_at` por defecto.

Query params:

- `destination_url`: match exacto;
- `slug`: match exacto;
- `public_mode`: `anonymous` o `namespace`;
- `include_deleted`: `false` por defecto;
- `limit`: `50` por defecto, máximo `100`;
- `offset`: `0` por defecto.

Respuesta `200`:

- `count`;
- `limit`;
- `offset`;
- `results`, con campos públicos/operativos de cada URL propia.

Cada item incluye `id`, `short_url`, `public_path`, `destination_url`, `title`,
`slug`, `public_mode`, `expires_at`, `max_clicks`, `click_count`, `is_active`,
`is_disabled`, `deleted_at`, `password_protected`, `created_at`, `updated_at` y
`last_clicked_at`. No incluye `owner`, `api_key_hash` ni `password_hash`.

El listado usa el mismo valor `URLBREVE_API_KEY_DAILY_LIMIT` con un bucket de
cache propio para lecturas, de forma que una integración pueda comprobar si una
URL destino ya existe antes de crear otra sin mezclar el contador con
`POST /api/shorten/`.

## Registro y perfil

El registro usa `django.contrib.auth` y un formulario propio sobre
`UserCreationForm`. El email es opcional por decisión privacy-first: la cuenta
puede existir sin pedir un dato personal adicional.

Al crear una cuenta, `accounts.services.ensure_user_profile()` crea el
`UserProfile` si no existe. El `public_namespace` inicial se deriva del
`username`:

- se normaliza a ASCII;
- se pasa a minúsculas;
- se sustituyen grupos de caracteres no permitidos por `-`;
- se limita a 3-64 caracteres;
- se evita usar rutas reservadas;
- si ya existe, se genera una variante segura como `nombre-2`.

La edición manual del namespace es más estricta: se recorta y pasa a minúsculas,
pero debe cumplir la regla conservadora sin espacios ni unicode problemático.
También se rechazan namespaces reservados o ya usados por otra cuenta.

## Colisiones y constraints

Decisión actual:

- los slugs `anonymous` son únicos globalmente por `slug`;
- los slugs `namespace` son únicos por `owner + slug`;
- `namespace` requiere `owner`;
- `UserProfile.public_namespace` es único.

Esto permite que exista `abc` como enlace anónimo y también `abc` bajo el
namespace de un usuario, porque las rutas públicas son distintas.

Los slugs se validan con una expresión ASCII conservadora: 3 a 64 caracteres,
letras, números, guiones y guiones bajos, empezando y terminando por letra o
número. Se rechazan espacios, unicode problemático, emojis y slugs reservados.

Los namespaces públicos usan una variante en minúsculas de esa regla para evitar
ambigüedad visual en rutas públicas.

Existe `links.validators.suggest_slug_variants()` como helper preparado para
sugerir variantes cuando haya colisión. En la creación autenticada se usa para
mostrar alternativas cuando un slug manual ya existe.

## Rate limiting privacy-first

La Fase 1 de rate limiting runtime está implementada sin IP, user-agent,
referrer, geolocalización ni fingerprinting. El diseño completo vive en
`docs/rate-limiting-privacy-first.md`.

La implementación actual usa Django cache con ventana diaria basada en
`timezone.localdate()` y claves por entidad:

- creación web: `request.user.id`;
- creación anónima web: sesión Django;
- API con `X-API-Key`: usuario resuelto desde la clave;
- API listing con `X-API-Key`: usuario resuelto desde la clave;
- API anónima: sesión Django;
- reportes: sesión Django;
- password gate: sesión Django + `ShortURL.id`.

El password gate tiene dos capas:

- límite diario por sesión Django + `ShortURL.id`;
- cooldown corto por `ShortURL.id`, útil aunque el cliente descarte cookies.

Ambas capas cuentan todos los POST válidos de contraseña, tanto correctos como
incorrectos. El cooldown por enlace se consume antes de comprobar la contraseña.
Al superar cualquiera de los límites, no se comprueba la contraseña, no se
redirige y no se registran clicks ni estadísticas diarias.

La API anónima puede desactivarse con `URLBREVE_ANONYMOUS_API_ENABLED`. Si está
activa, el límite por sesión no detiene clientes que descartan cookies; por eso
debe mantenerse bajo en producción.

El cooldown por enlace no persiste intentos en base de datos y sus claves de
cache no incluyen IP, user-agent, referrer ni fingerprinting.

Settings actuales:

- `DJANGO_SESSION_COOKIE_SECURE`;
- `DJANGO_CSRF_COOKIE_SECURE`;
- `DJANGO_SECURE_SSL_REDIRECT`;
- `URLBREVE_ANONYMOUS_API_ENABLED`;
- `URLBREVE_RATE_LIMITING_ENABLED`;
- `URLBREVE_ANONYMOUS_DAILY_LIMIT`;
- `URLBREVE_AUTHENTICATED_DAILY_LIMIT`;
- `URLBREVE_API_KEY_DAILY_LIMIT`;
- `URLBREVE_REPORT_SESSION_DAILY_LIMIT`;
- `URLBREVE_REPORT_HONEYPOT_ENABLED`;
- `URLBREVE_PASSWORD_GATE_SESSION_LIMIT`;
- `URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_ENABLED`;
- `URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_LIMIT`;
- `URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_SECONDS`.

Siguen pendientes Redis o cache compartida para varias instancias, límites por
`reported_path`, bloqueo futuro de dominios abusivos y protección temporal de
infraestructura sin access logs persistentes.

## Despliegue de producción

La configuración de producción vive en:

- `.env.production.example`, como plantilla de variables reales;
- `docker-compose.prod.yml`, con servicios `web`, `db` y `nginx`;
- `deploy/nginx/urlbreve.conf`, con reverse proxy privacy-first;
- `docs/production-deploy.md`, con operación paso a paso.

Decisiones:

- solo nginx expone puerto público;
- PostgreSQL no expone puertos al host;
- Gunicorn queda detrás de nginx en red interna de Compose;
- staticfiles se comparten mediante volumen Docker;
- nginx sirve `/static/`;
- nginx no escribe access logs;
- nginx no reenvía IP, user-agent ni referrer de visitante a Django;
- TLS queda documentado como capa externa o extensión futura del stack.

## Decisiones pendientes

- política exacta de logs en reverse proxy;
- borrado lógico frente a reutilización futura de slugs;
- siguientes fases de anti-abuse compatibles con la política privacy-first.
