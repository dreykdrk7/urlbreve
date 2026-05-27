# urlbreve

urlbreve es un acortador de URLs privacy-first, open source y construido con
Django sin frontend separado. El objetivo es que el código sea pequeño,
auditable y razonable para producción low-cost en un VPS.

## Privacidad

El proyecto parte de una política explícita de mínimos:

- no guardar IPs;
- no guardar user-agent;
- no hacer geotracking;
- no añadir trackers;
- no crear analytics invasivos;
- mantener solo estadísticas agregadas y anónimas.

No existe un índice público de enlaces. Los enlaces se descubren solo por URL
directa.

## Stack

- Django 5.2 LTS
- PostgreSQL
- Gunicorn
- Docker y Docker Compose
- Templates y views de Django, sin React/Vue/Next

## Levantar con Docker

```bash
docker compose build
docker compose up
```

La app queda disponible en `http://localhost:8000/` y el healthcheck básico en
`http://localhost:8000/healthz/`.

`docker-compose.yml` incluye valores de desarrollo para arrancar rápido. Para
producción, define variables reales equivalentes a `.env.example` desde el
entorno del servidor o desde tu gestor de despliegue. Django no carga `.env`
por sí mismo.

## Comandos básicos

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 manage.py migrate
python3 manage.py test
```

Dentro de Docker:

```bash
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py test
```

## Rutas activas

- `/` - home con creación anónima rápida.
- `/register/` - registro.
- `/login/` - login.
- `/logout/` - logout mediante POST.
- `/dashboard/` - panel privado mínimo.
- `/profile/` - edición del perfil básico.
- `/profile/api-key/rotate/` - rotación de API key mediante POST.
- `/profile/api-key/revoke/` - revocación de API key mediante POST.
- `/links/new/` - creación autenticada de URL corta.
- `/links/<id>/` - detalle básico de una URL propia.
- `/links/<id>/edit/` - edición de campos permitidos.
- `/links/<id>/delete/` - ocultado mediante soft delete.
- `/api/shorten/` - creación de URL corta mediante API JSON.
- `/report/` - formulario publico de reporte de abuso.
- `/a/<slug>/` - redirección pública anónima/global.
- `/<namespace>/<slug>/` - redirección pública bajo namespace.
- `/healthz/` - healthcheck.
- `/admin/` - administración Django.

El email de registro es opcional para reducir datos personales desde el inicio.
Cada cuenta recibe un `UserProfile` automáticamente con un namespace público
inicial basado en el username. El namespace se normaliza a ASCII minúsculo y,
si colisiona, se genera una variante segura como `nombre-2`.

## Gestión de URLs

Desde el dashboard, un usuario autenticado puede crear URLs cortas propias. La
creación permite:

- `destination_url`, solo `http://` o `https://`;
- `slug` opcional; si se deja vacío se genera un código seguro de 8 caracteres;
- `title` opcional;
- `public_mode`, con modos `anonymous` y `namespace`;
- `expires_days`, donde `0` significa que no expira;
- `max_clicks`, donde `0` significa ilimitado;
- contraseña opcional, guardada solo como hash.

Después de crear, no se pueden editar `slug`, `public_mode` ni `owner`. Sí se
pueden editar destino, título, expiración, límite de clicks, estado activo y
contraseña.

Las URLs no se borran físicamente desde la UI. La acción de ocultar marca
`deleted_at`; esas URLs dejan de aparecer en el dashboard normal, pero el slug
sigue reservado por las constraints de base de datos.

Reglas de colisión:

- modo `anonymous`: `slug` único globalmente para la ruta conceptual
  `/a/<slug>/`;
- modo `namespace`: `slug` único por usuario para la ruta conceptual
  `/<namespace>/<slug>/`;
- si un slug manual colisiona, se devuelve un error con sugerencias.

## Creación anónima web

La home `/` permite crear enlaces anónimos sin iniciar sesión. Estos enlaces:

- usan siempre `public_mode=anonymous`;
- quedan con `owner=None`;
- tienen ruta pública `/a/<slug>/`;
- pueden tener slug opcional, expiración, límite de clicks y contraseña;
- no aparecen en ningún dashboard;
- no tienen recuperación ni edición posterior.

La creación anónima web reutiliza las mismas validaciones de destino, slug,
colisiones, generación aleatoria y hash de contraseña que la creación
autenticada. También usa el rate limiting privacy-first por sesión con
`URLBREVE_ANONYMOUS_DAILY_LIMIT`.

## Redirecciones públicas

Las rutas públicas activas son `/a/<slug>/` para enlaces anónimos/globales y
`/<namespace>/<slug>/` para enlaces namespaced. Antes de redirigir se comprueba
que el enlace:

- no esté ocultado con `deleted_at`;
- esté activo;
- no esté deshabilitado por moderación;
- no esté expirado;
- no haya agotado `max_clicks`.

Si el enlace no existe o no está disponible, se devuelve una página genérica con
status `404`. La página no revela si el enlace existió, expiró, fue desactivado
o agotó usos.

Si el enlace está disponible y tiene contraseña, se muestra un formulario simple
antes de redirigir. Una contraseña incorrecta no redirige y no incrementa
estadísticas.

Cuando el enlace redirige finalmente a `destination_url`, urlbreve solo actualiza
contadores agregados:

- `ShortURL.click_count`;
- `ShortURL.last_clicked_at`;
- `ShortURLDailyStats.clicks` para la fecha actual.

No se guardan IPs, user-agent, referrer ni datos de tracking del visitante.
El password gate tampoco guarda datos del visitante ni registra intentos.

## Reporte de abuso y moderacion

`/report/` permite que cualquier visitante reporte una ruta sospechosa. El
formulario acepta una ruta como `/a/demo/` o `/namespace/demo/`, un motivo y
detalles opcionales limitados. Si la ruta corresponde a una URL conocida, el
reporte queda asociado internamente a esa `ShortURL`; si no se puede resolver,
se guarda igualmente con `short_url=None` para revision manual.

Los reportes no guardan IP, user-agent, referrer ni email. Tampoco se usa captcha
externo en esta fase.

En el admin de Django se puede filtrar y revisar `AbuseReport`. Los enlaces
tienen acciones de moderacion para marcar `is_disabled=True` o volver a
habilitarlos. Un enlace deshabilitado queda bloqueado por las mismas reglas de
disponibilidad de las redirecciones publicas.

## Rate limiting y anti-abuse

La Fase 1 de rate limiting privacy-first está implementada con Django cache y
sin usar IP, user-agent, referrer ni fingerprinting. La estrategia completa está
documentada en `docs/rate-limiting-privacy-first.md`.

Límites activos:

- creación anónima por API, basada en sesión Django y desactivable por setting;
- creación anónima web, basada en sesión Django;
- creación por API key, limitada por usuario resuelto desde `X-API-Key`;
- creación web autenticada, limitada por `request.user.id`;
- reportes de abuso, limitados por sesión;
- password gate, limitado por sesión y enlace.

La protección de API anónima es deliberadamente imperfecta: clientes que no
conservan cookies pueden esquivar el límite de sesión. En producción se puede
desactivar la API anónima o mantenerla con límites bajos.

## API

`POST /api/shorten/` acepta JSON y responde JSON. Sin `X-API-Key`, crea una URL
anónima/global sin owner y fuerza `public_mode=anonymous`.

Con `X-API-Key` válida, crea la URL asociada al usuario dueño de la clave. En
ese caso `public_mode` puede ser `anonymous` o `namespace`.

La API key se gestiona desde `/profile/`. Solo se muestra en claro al generarla
o rotarla; después se guarda únicamente `UserProfile.api_key_hash`. Revocarla
borra ese hash.

Ejemplo anónimo:

```bash
curl -X POST http://localhost:8000/api/shorten/ \
  -H "Content-Type: application/json" \
  -d '{"destination_url":"https://example.com","slug":"ejemplo"}'
```

Ejemplo con API key:

```bash
curl -X POST http://localhost:8000/api/shorten/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ub_tu_clave" \
  -d '{"destination_url":"https://example.com","public_mode":"namespace"}'
```

Campos admitidos:

- `destination_url`, requerido, solo `http://` o `https://`;
- `slug`, opcional;
- `title`, opcional;
- `public_mode`, opcional;
- `expires_days`, opcional, `0` por defecto;
- `max_clicks`, opcional, `0` por defecto;
- `password`, opcional.

La API no guarda IPs, user-agent, referrer ni API keys en claro.

## Estado

Microfase actual:

- arquitectura Django creada;
- PostgreSQL preparado en Docker;
- modelos mínimos para perfiles, URLs cortas y estadísticas diarias;
- registro/login/logout con templates Django;
- dashboard privado mínimo;
- edición de namespace público y preferencia de modo;
- creación, listado, detalle, edición limitada y soft delete de URLs propias;
- creación anónima web sin recuperación posterior;
- redirecciones públicas con contador agregado diario;
- enlaces protegidos con contraseña;
- API mínima de creación con `X-API-Key`;
- reporte de abuso sin datos personales del visitante;
- moderacion basica con `is_disabled`;
- Fase 1 de rate limiting privacy-first sin IP;
- página inicial y endpoint `/healthz/`;
- documentación y licencia AGPLv3.

No están implementados todavía honeypot, cooldown avanzado por enlace,
cache compartida/Redis ni la revisión fina de logs del VPS/reverse proxy.
