# Cierre operativo v1

Este documento resume el estado de producción de urlbreve v1 y deja pendientes
operativos recomendados para la siguiente ventana de mantenimiento.

## Estado actual de v1

- Producción activa en `https://urlbreve.es`.
- Dominio principal y `www` apuntando por DNS en INWX a `51.38.225.243`.
- VPS `vps-40567620` en OVH.
- Usuario operativo: `deploy`.
- App desplegada en `/opt/apps/urlbreve/app`.
- Proxy Caddy en Docker en `/opt/apps/shared/proxy`.
- Caddy termina HTTPS y reenvía a `urlbreve-web:8000`.
- Caddy sirve `/static/*` desde el volumen `urlbreve_staticfiles`.
- Docker project name de la app: `urlbreve`.
- Compose de producción con `docker-compose.prod.yml`,
  `docker-compose.vps.yml` y `.env.production` no versionado en el VPS.

Funcionalidad validada:

- Creación de URL OK.
- Redirección pública OK.
- Admin de Django OK.
- Estáticos del admin OK.
- `python3 manage.py check` OK.

## Validaciones realizadas

- DNS de `urlbreve.es` y `www.urlbreve.es` apuntando al VPS.
- HTTPS servido por Caddy.
- Reverse proxy hacia `urlbreve-web:8000`.
- Estáticos servidos por Caddy desde el volumen compartido.
- App Django operativa con PostgreSQL.
- Healthcheck de Django OK.
- Admin accesible por HTTPS.

## Decisiones tomadas

- Mantener app Django server-side sin frontend build.
- Mantener Docker Compose para app y base de datos.
- Separar el proxy Caddy en un stack compartido.
- No versionar `.env.production`.
- Servir estáticos con Caddy desde `urlbreve_staticfiles`, evitando que Django
  sirva estáticos en producción.
- Mantener el enfoque privacy-first: no introducir analytics, trackers, fuentes
  externas ni scripts externos.
- No tocar `dgt-scraper` durante la puesta en producción de urlbreve.

## Pendientes recomendados

1. Rotar `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD`.

   Durante el despliegue se mostraron accidentalmente en salida de Compose.
   Aunque no deben quedar en el repo, conviene tratarlos como expuestos y
   rotarlos en una ventana controlada.

2. Configurar backup automatizado.

   Crear backups periódicos de PostgreSQL, copiarlos fuera del VPS, cifrarlos y
   probar restauraciones. Ver [`backups.md`](backups.md).

3. Valorar protección adicional de `/admin/`.

   Opciones posibles: allowlist de IP si encaja con operación, ruta interna por
   VPN, autenticación adicional a nivel de proxy o rate limiting específico que
   no contradiga la política privacy-first.

4. Planificar una ventana para `apt upgrade`.

   Revisar especialmente Docker, containerd y systemd. Hacerlo con backup
   reciente y comprobación posterior de contenedores, Caddy y app.

5. Añadir monitorización básica.

   Como mínimo, alertas de disponibilidad de `/healthz/`, uso de disco,
   expiración TLS, estado de contenedores y espacio de backups.

## Referencias operativas

- Runbook: [`production-runbook.md`](production-runbook.md).
- Backups: [`backups.md`](backups.md).
- Guía genérica de despliegue: [`production-deploy.md`](production-deploy.md).
