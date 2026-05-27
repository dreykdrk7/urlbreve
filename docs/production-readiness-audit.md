# Auditoría de preparación para producción

Fecha: 2026-05-27

## Resumen ejecutivo

urlbreve está en estado **GO WITH WARNINGS** para pasar a una fase de despliegue
en VPS y dominio propios. El MVP funcional está cubierto por tests, el stack de
producción con Docker Compose es válido, PostgreSQL no queda expuesto
públicamente y la configuración nginx sigue la política privacy-first:
`access_log off` y no reenvío de IP, user-agent ni referrer a Django.

Durante la auditoría se aplicaron varios ajustes pequeños de hardening:

- contenedor web ejecutándose como usuario no root;
- fallo explícito si producción arranca con `DJANGO_SECRET_KEY` placeholder;
- soporte de credenciales URL-encoded en `DATABASE_URL`;
- límites de memoria para uploads/formularios/JSON desde Django;
- settings de HSTS/referrer policy configurables;
- nginx con `error_log` reducido a nivel `crit`;
- Gunicorn de producción limitado a un worker mientras el rate limiting use
  cache local;
- test para parseo seguro de `DATABASE_URL`.

No se encontraron hallazgos críticos que bloqueen un despliegue controlado. Sí
hay advertencias operativas importantes antes de abrir tráfico real.

## Estado general

**GO WITH WARNINGS**

Recomendación: se puede avanzar a compra/configuración de VPS y dominio, hacer
un despliegue inicial privado o de staging, configurar TLS, backups y variables
reales, y solo entonces abrir uso público.

## Hallazgos por severidad

### Critical

No se encontraron hallazgos críticos.

### High

- **TLS no está automatizado dentro del stack de Compose.**
  `docker-compose.prod.yml` expone nginx en `80` y documenta TLS como capa
  externa o extensión futura. Esto es aceptable para un VPS low-cost, pero no
  debe abrirse uso real con login/admin/API sobre HTTP plano. Antes de uso
  público, termina TLS con Caddy, Traefik, nginx-proxy, certbot u otra capa
  controlada, y confirma `X-Forwarded-Proto=https`.

### Medium

- **Rate limiting depende de cache local.**
  La configuración de producción queda en un worker de Gunicorn para evitar que
  los contadores se dividan entre procesos. Antes de aumentar workers, réplicas
  o instancias, hay que añadir Redis u otro backend de cache compartido.

- **Admin público en `/admin/`.**
  Django admin queda protegido por autenticación, CSRF y TLS cuando se despliega
  correctamente, pero sigue siendo una superficie sensible. Para producción
  pública conviene usar contraseñas fuertes, revisar superusuarios, y valorar
  restricción por VPN, túnel SSH, allowlist operacional o protección externa.

- **Borrado de usuarios requiere política.**
  `ShortURL.owner` usa `SET_NULL`, pero los enlaces `namespace` requieren owner.
  El borrado directo de usuarios con enlaces namespaced puede chocar con las
  constraints o dejar una política ambigua. No borrar usuarios desde admin hasta
  definir si se anonimiza, se bloquea, se transfiere o se conserva la cuenta.

- **Límites anónimos por sesión son deliberadamente imperfectos.**
  La creación anónima web/API y reportes se limitan sin IP, usando sesión o
  entidad. Clientes que descartan cookies pueden esquivar parte de estos
  límites. En producción inicial se recomienda mantener
  `URLBREVE_ANONYMOUS_API_ENABLED=False`.

### Low

- **HSTS queda desactivado por defecto.**
  `DJANGO_SECURE_HSTS_SECONDS=0` es prudente hasta confirmar HTTPS estable. Tras
  validar dominio y TLS, puede subirse a un valor alto, por ejemplo `31536000`.

- **Logs críticos de nginx podrían contener metadatos en casos extremos.**
  `access_log` está desactivado y `error_log` queda en `crit`; aun así, cualquier
  proxy delante debe revisarse para no persistir IP, user-agent ni referrer.

- **API key lookup es lineal.**
  `get_user_for_api_key()` verifica hashes iterando perfiles con API key. Es
  simple y seguro para MVP pequeño, pero conviene rediseñarlo si crece el número
  de usuarios o integraciones.

- **No hay CSP estricta.**
  La app no usa recursos externos ni trackers, pero tiene CSS y un pequeño JS
  inline para copiar enlaces. Una CSP estricta requeriría ajustar estilos/scripts
  y puede quedar para hardening posterior.

- **Imágenes Docker no están fijadas por digest en los archivos fuente.**
  Se usan tags razonables (`python:3.12-slim`, `postgres:16-alpine`,
  `nginx:1.27-alpine`). Para despliegues reproducibles estrictos, fijar digest.

## Revisión de seguridad Django

- `DEBUG` se lee desde entorno y producción lo define como `False`.
- `DJANGO_SECRET_KEY` ahora falla explícitamente en producción si está vacío,
  usa el default inseguro o conserva prefijo `CHANGE_ME`.
- `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` se configuran desde entorno.
- Cookies seguras, SSL redirect y HSTS son configurables por entorno.
- `SECURE_PROXY_SSL_HEADER` está definido para operar detrás de proxy TLS.
- `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` quedan en 1 MiB
  por defecto.
- Admin usa Django estándar. Pendiente operativo: proteger acceso en VPS.
- Formularios públicos tienen CSRF, validación de longitud y honeypot donde
  aplica.

## Revisión privacy-first

- Modelos revisados: no hay campos para IP, user-agent, referrer, geolocalización
  ni fingerprinting.
- Redirecciones solo incrementan `click_count`, `last_clicked_at` y
  `ShortURLDailyStats`.
- Reportes de abuso no guardan email ni datos técnicos del visitante.
- Password gate no persiste intentos.
- API no devuelve `api_key_hash`, `password_hash` ni owner sensible.
- nginx producción tiene `access_log off` y no reenvía IP, user-agent ni referrer
  a Django.
- Gunicorn no configura access logs.

## Revisión API

- `POST /api/shorten/` valida JSON, destino `http/https`, slug, colisiones,
  expiración, límite de clicks y contraseña opcional.
- `GET /api/links/` exige `X-API-Key`, limita por usuario, filtra por owner,
  excluye `owner=None` y soporta filtros/paginación.
- Errores esperados cubiertos: `400`, `401`, `403`, `409`, `429`.
- La API anónima puede desactivarse en producción.
- No se detectó exposición cross-user en listado.

## Revisión redirects

- `/a/<slug>/` y `/<namespace>/<slug>/` resuelven rutas separadas.
- Antes de redirigir se comprueba disponibilidad: activo, no disabled, no
  soft-deleted, no expirado, no agotado.
- `max_clicks=1` queda protegido con transacción y `select_for_update`.
- Password gate incrementa estadísticas solo con contraseña correcta.
- Cooldown por enlace bloquea antes de comprobar contraseña.
- Página unavailable no revela si el enlace existió, expiró o fue moderado.

## Revisión anti-abuse

- Rate limits por usuario, API key, sesión y enlace.
- Honeypot silencioso en `/report/`.
- Abuse reports sin datos personales obligatorios.
- Acciones de moderación en admin para `is_disabled`.
- Pendiente: límites por `reported_path`, bloqueo de dominios abusivos y cache
  compartida antes de escalar.

## Revisión Docker y producción

- Dockerfile validado con `collectstatic` y usuario no root.
- Compose desarrollo válido.
- Compose producción válido con `web`, `db` y `nginx`.
- PostgreSQL no expone puerto público en producción.
- Staticfiles se sirven por nginx desde volumen compartido.
- nginx expone solo `80`; TLS queda fuera del stack base.
- `.env.production.example` documenta variables reales esperadas.
- Backups y restore están documentados.

## Revisión documentación

- `README.md`: actualizado y coherente con API, privacy-first y deploy.
- `docs/architecture.md`: refleja rutas, modelos, privacy, rate limiting y
  despliegue.
- `docs/rate-limiting-privacy-first.md`: refleja limitaciones actuales y fases.
- `docs/production-deploy.md`: cubre VPS, Docker, env, migraciones,
  collectstatic, superuser, TLS, backups, restore, logs y updates.
- `LICENSE`: AGPLv3 presente.

## Cambios aplicados

- `Dockerfile`: usuario no root `app`.
- `config/settings.py`: validación de secret key de producción, decode de
  `DATABASE_URL`, settings HSTS/referrer policy y límites de upload.
- `.env.example` y `.env.production.example`: nuevas variables de hardening.
- `docker-compose.prod.yml`: worker único y variables nuevas.
- `deploy/nginx/urlbreve.conf`: `error_log` reducido a `crit`.
- `accounts/tests.py`: test de `DATABASE_URL` URL-encoded.
- Docs: despliegue/rate limiting/arquitectura/README actualizados.

## Validaciones ejecutadas

- `git status --short`: limpio al inicio.
- `git branch --show-current`: `main`.
- `git log --oneline -10`: último commit inicial `f9fdb0e`.
- `python3 manage.py check`: OK.
- `python3 manage.py makemigrations --check --dry-run`: OK, sin cambios.
- `python3 manage.py test`: OK, 99 tests.
- `docker compose -f docker-compose.yml config`: OK.
- `docker compose -f docker-compose.prod.yml --env-file .env.production.example config`: OK.
- `docker compose --env-file .env.example build web`: OK.
- `docker compose --env-file .env.example up -d web`: OK.
- `docker compose --env-file .env.example exec -T web python manage.py check`: OK.
- `docker compose --env-file .env.example exec -T web python manage.py test`: OK, 99 tests.
- `docker compose --env-file .env.example exec -T web id`: OK, usuario `app`.
- `git diff --check`: OK.

## Checklist final antes de VPS

- Comprar o activar VPS.
- Comprar o configurar dominio.
- Apuntar DNS al VPS.
- Instalar Docker Engine y Docker Compose v2.
- Clonar repo.
- Crear `.env.production` desde `.env.production.example`.
- Reemplazar todos los valores `CHANGE_ME`.
- Configurar `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Levantar PostgreSQL.
- Ejecutar migraciones.
- Ejecutar `collectstatic`.
- Crear superusuario fuerte.
- Configurar TLS antes de uso real.
- Confirmar que nginx/proxy externo no conserva access logs con IP.
- Configurar backups PostgreSQL y probar restore.
- Confirmar `/healthz/`.
- Confirmar login/admin solo por HTTPS.
- Mantener `URLBREVE_ANONYMOUS_API_ENABLED=False` al inicio.

## Recomendación final

Avanzar a VPS/dominio con despliegue controlado. No abrir tráfico público hasta
confirmar TLS, `.env.production` real, backups y política de logs del proxy.
Antes de escalar workers o instancias, añadir cache compartida.
