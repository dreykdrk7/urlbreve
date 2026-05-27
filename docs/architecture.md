# Arquitectura inicial

## Rutas previstas

- `/` - home simple.
- `/register/` - registro de usuario.
- `/login/` - login.
- `/logout/` - logout mediante POST.
- `/dashboard/` - panel privado mínimo.
- `/profile/` - edición de perfil básico.
- `/a/<slug>/` - futuro enlace anónimo/global.
- `/<namespace>/<slug>/` - futuro enlace público bajo namespace de usuario.
- `/api/shorten/` - futuro endpoint API.
- `/admin/` - administración de Django.
- `/healthz/` - healthcheck básico.

En esta microfase están activos `/`, `/register/`, `/login/`, `/logout/`,
`/dashboard/`, `/profile/`, `/healthz/` y `/admin/`.

## Modelo de privacidad

urlbreve no debe guardar IPs, user-agent, geolocalización ni identificadores de
tracking. Las estadísticas se diseñan como contadores agregados, por ejemplo
clics diarios por enlace mediante `ShortURLDailyStats`.

Las futuras redirecciones deberán evitar logs de aplicación con datos de
visitantes. En producción también habrá que revisar configuración de reverse
proxy y logs web para alinear la infraestructura con esta política.

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
sugerir variantes cuando haya colisión. Todavía no consulta la base de datos.

## API futura

La API pública prevista empezará por `/api/shorten/`. La autenticación podrá usar
`X-API-Key`, guardando solo `UserProfile.api_key_hash`; nunca se debe almacenar
la clave en claro.

Pendiente:

- formato de request/response;
- rotación de claves;
- permisos por usuario;
- límites de uso compatibles con la política privacy-first.

## Rate limiting pendiente

El rate limiting queda fuera de esta microfase. Debe diseñarse sin introducir
tracking invasivo. Opciones a evaluar:

- límites por usuario autenticado;
- cuotas por API key hasheada;
- protección anti-abuse a nivel de infraestructura con ventanas cortas;
- mecanismos anónimos que no requieran almacenar IPs crudas.

## Decisiones pendientes

- flujo de creación anónima;
- creación de URLs autenticadas desde dashboard;
- redirecciones y comportamiento de enlaces expirados, desactivados o con
  contraseña;
- formulario o proceso de reporte de abuso;
- política exacta de logs en reverse proxy;
- borrado lógico frente a reutilización futura de slugs;
- endpoints de API y documentación pública.
