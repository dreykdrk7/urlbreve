# Cierre operativo v1.1

Este documento resume el estado de producción de urlbreve v1.1 y deja
pendientes operativos recomendados para futuras ventanas de mantenimiento.

## Estado actual de v1.1

- Producción activa en `https://urlbreve.es`.
- Dominio principal y `www` apuntando por DNS en INWX a `51.38.225.243`.
- VPS `vps-40567620` en OVH.
- Usuario operativo: `deploy`.
- App desplegada en `/opt/apps/urlbreve/app`.
- Proxy Caddy en Docker en `/opt/apps/shared/proxy`.
- Caddy termina HTTPS y reenvía a `urlbreve-web:8000`.
- Caddy sirve `/static/*` desde el volumen `urlbreve_staticfiles`.
- Home developer-oriented desplegada, con sección API-first visible.
- `/admin/` protegido por Caddy Basic Auth antes del login normal de Django
  admin. Usuario Basic Auth: `adminwall`; la contraseña se guarda fuera del
  repo.
- `/api/shorten/` no está protegido por Basic Auth y sigue disponible para la
  API pública.
- Docker project name de la app: `urlbreve`.
- Compose de producción con `docker-compose.prod.yml`,
  `docker-compose.vps.yml` y `.env.production` no versionado en el VPS.
- `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` y `DATABASE_URL` rotados tras la
  exposición accidental durante el despliegue.

Funcionalidad validada:

- Home developer-oriented OK.
- Sección API-first visible en la home.
- Creación de URL OK.
- Redirección pública OK.
- `/admin/` devuelve `401` sin Basic Auth y conserva el login normal de Django
  detrás.
- Estáticos del admin OK.
- `/api/shorten/` accesible sin Basic Auth.
- `/healthz/` devuelve `{"status": "ok"}`.
- `python3 manage.py check` OK.

## Validaciones realizadas

- DNS de `urlbreve.es` y `www.urlbreve.es` apuntando al VPS.
- HTTPS servido por Caddy.
- Reverse proxy hacia `urlbreve-web:8000`.
- Estáticos servidos por Caddy desde el volumen compartido.
- App Django operativa con PostgreSQL.
- Healthcheck de Django OK.
- `/admin/` protegido por Basic Auth de Caddy.
- `/static/admin/css/base.css` público para cargar estilos/assets del admin.
- `/api/shorten/` no protegido por Basic Auth.
- Secretos de producción rotados sin documentar valores.

## Decisiones tomadas

- Mantener app Django server-side sin frontend build.
- Mantener Docker Compose para app y base de datos.
- Separar el proxy Caddy en un stack compartido.
- No versionar `.env.production`.
- Servir estáticos con Caddy desde `urlbreve_staticfiles`, evitando que Django
  sirva estáticos en producción.
- Mantener el enfoque privacy-first: no introducir analytics, trackers, fuentes
  externas ni scripts externos.
- Posicionar la home como landing para desarrolladores web con ejemplo real de
  API request/response.
- Añadir Caddy Basic Auth a `/admin/` como defensa adicional sin tocar Django.
- Rotar secretos expuestos y actualizar `DATABASE_URL` en producción.
- No tocar `dgt-scraper` durante la puesta en producción de urlbreve.

## Evidencias operativas

- Backup previo a rotación de secretos:
  `/opt/apps/shared/backups/urlbreve/urlbreve-20260528T085147Z-pre-secret-rotation.sql`.
- Backup de Caddyfile previo a Basic Auth:
  `/opt/apps/shared/proxy/Caddyfile.backup-20260528T090031Z`.
- No se documentan contraseñas, hashes ni valores de `.env.production`.

## Pendientes recomendados

1. Configurar backup automatizado.

   Crear backups periódicos de PostgreSQL, copiarlos fuera del VPS, cifrarlos y
   probar restauraciones. Ver [`backups.md`](backups.md).

2. Planificar una ventana para `apt upgrade`.

   Revisar especialmente Docker, containerd y systemd. Hacerlo con backup
   reciente y comprobación posterior de contenedores, Caddy y app.

3. Añadir monitorización básica.

   Como mínimo, alertas de disponibilidad de `/healthz/`, uso de disco,
   expiración TLS, estado de contenedores y espacio de backups.

## Cierre

El proyecto queda cerrado en estado v1.1 hasta futura necesidad funcional,
operativa o de seguridad. El runbook de producción es la referencia para
operación diaria e incidencias.

## Referencias operativas

- Runbook: [`production-runbook.md`](production-runbook.md).
- Backups: [`backups.md`](backups.md).
- Guía genérica de despliegue: [`production-deploy.md`](production-deploy.md).
