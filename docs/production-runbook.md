# Runbook de producción

Este runbook describe la operación actual de `urlbreve.es` en producción. No
contiene secretos y asume acceso SSH al VPS con el usuario operativo `deploy`.

## Arquitectura actual

- VPS: `vps-40567620` en OVH.
- Usuario operativo: `deploy`.
- Dominio: `urlbreve.es` y `www.urlbreve.es`.
- DNS: INWX, apuntando a `51.38.225.243`.
- App Django/Gunicorn en Docker, proyecto Compose `urlbreve`.
- PostgreSQL en Docker dentro del mismo proyecto Compose.
- Reverse proxy Caddy en Docker, en el stack compartido.
- Caddy termina HTTPS y hace `reverse_proxy` hacia `urlbreve-web:8000`.
- Caddy monta el volumen `urlbreve_staticfiles` para servir `/static/*`.

Flujo de petición:

```text
Visitante
  -> DNS INWX
  -> VPS 51.38.225.243
  -> caddy-proxy
  -> urlbreve-web:8000
  -> urlbreve-db-1
```

## Rutas importantes

- App en VPS: `/opt/apps/urlbreve/app`.
- Proxy compartido: `/opt/apps/shared/proxy`.
- Archivo de entorno de producción: `/opt/apps/urlbreve/app/.env.production`.
- Caddyfile del proxy: `/opt/apps/shared/proxy/Caddyfile`.
- Backups sugeridos: `/opt/apps/shared/backups/urlbreve`.
- Compose de la app:
  - `docker-compose.prod.yml`
  - `docker-compose.vps.yml`

`.env.production` no está versionado y no debe copiarse al repo ni mostrarse en
salidas compartidas.

No compartas salidas completas de `docker compose config --env-file
.env.production`: pueden expandir secretos como `DJANGO_SECRET_KEY`,
`POSTGRES_PASSWORD` o `DATABASE_URL`.

## Servicios Docker

Contenedores conocidos:

- `urlbreve-web`: Django/Gunicorn.
- `urlbreve-db-1`: PostgreSQL.
- `caddy-proxy`: Caddy HTTPS/reverse proxy.
- `dgt-scraper`: servicio existente ajeno a urlbreve; no tocar desde este
  runbook.

En comandos de Docker Compose de la app se usan los servicios `web` y `db`.

Para evitar depender del directorio actual, entra primero en la app:

```bash
cd /opt/apps/urlbreve/app
```

Comando base de Compose de la app:

```bash
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml
```

## Deploy/update

Flujo recomendado para una actualización normal:

```bash
cd /opt/apps/urlbreve/app
git fetch --all --prune
git status --short
git pull --ff-only
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml build web
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml run --rm web python manage.py migrate
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml run --rm web python manage.py collectstatic --noinput
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml up -d
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T web python manage.py check
```

Antes de cualquier deploy con migraciones o cambios de datos, haz primero un
backup manual de PostgreSQL siguiendo [`backups.md`](backups.md). No continúes
con la actualización hasta saber dónde queda guardado el backup y cómo
restaurarlo si hiciera falta.

## Logs

App:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml logs --tail=200 web
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml logs --tail=200 db
```

Caddy:

```bash
docker logs --tail=200 caddy-proxy
```

Para seguir logs en directo, añade `-f` o `--follow`. No pegues salidas que
puedan contener secretos, cabeceras sensibles o datos de usuarios en issues,
pull requests o chats públicos.

## Healthcheck

Comprobación pública:

```bash
curl -fsS https://urlbreve.es/healthz/
```

Comprobaciones públicas de borde HTTPS:

```bash
curl -I https://urlbreve.es
curl -I https://urlbreve.es/static/admin/css/base.css
curl -I https://urlbreve.es/admin/
```

Resultados esperados:

- `https://urlbreve.es` devuelve `200`.
- `https://urlbreve.es/static/admin/css/base.css` devuelve `200`.
- `https://urlbreve.es/admin/` sin credenciales devuelve `401` por Basic Auth
  de Caddy.
- `curl -fsS https://urlbreve.es/healthz/` devuelve `{"status": "ok"}`.

Comprobación desde el contenedor web:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T web python manage.py check
```

Comprobación rápida de estado de contenedores:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Puntos funcionales mínimos tras deploy:

- `/healthz/` responde OK por HTTPS.
- Home carga por `https://urlbreve.es/`.
- La sección API-first de la home está visible.
- Creación de URL funciona.
- Redirección pública funciona.
- `/admin/` queda protegido por Caddy Basic Auth antes del login normal de
  Django admin.
- Estáticos del admin cargan correctamente.
- `/api/shorten/` no queda protegido por Basic Auth y sigue disponible para la
  API pública.

## Migraciones y collectstatic

Migraciones:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml run --rm web python manage.py migrate
```

Collectstatic:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml run --rm web python manage.py collectstatic --noinput
```

Check de Django:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T web python manage.py check
```

## Caddy y staticfiles

Caddy vive en `/opt/apps/shared/proxy` y su configuración está en
`/opt/apps/shared/proxy/Caddyfile`. Está separado del stack de la app. Termina
TLS para `urlbreve.es` y `www.urlbreve.es`, y reenvía tráfico dinámico a
`urlbreve-web:8000`.

Los estáticos se publican mediante el volumen Docker `urlbreve_staticfiles`.
Django escribe ahí con `collectstatic`, y Caddy monta el mismo volumen para
servir `/static/*` directamente. Por eso, después de cambios en CSS, admin o
assets estáticos, ejecuta `collectstatic` antes de validar visualmente.

`/admin/` tiene una capa adicional de Caddy Basic Auth antes del login normal de
Django admin. El usuario configurado es `adminwall`; la contraseña no debe
guardarse en el repo, documentación, issues ni chats. El backup del Caddyfile
previo a esta protección quedó en
`/opt/apps/shared/proxy/Caddyfile.backup-20260528T090031Z`.

Mantén estas reglas al tocar Caddy:

- `/static/*`, incluyendo `/static/admin/*`, debe seguir público para cargar
  CSS y assets del admin.
- `/api/shorten/` no debe quedar protegido por Basic Auth.
- El reverse proxy general hacia `urlbreve-web:8000` debe mantenerse.
- La credencial de Basic Auth no debe guardarse en texto plano.

No activar logs de acceso con IP, user-agent o referrer salvo necesidad
temporal, documentada y acotada. La política del proyecto es privacy-first.

## Rollback básico

Rollback de código, cuando la base de datos sigue siendo compatible:

```bash
cd /opt/apps/urlbreve/app
git status --short
git log --oneline -5
git checkout <commit_anterior_estable>
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml build web
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml run --rm web python manage.py collectstatic --noinput
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml up -d
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T web python manage.py check
```

Si el despliegue incluyó migraciones no compatibles hacia atrás, decide antes si
hay migración inversa segura o si toca restaurar backup. Restaurar base de datos
puede perder datos creados después del backup; hazlo solo con una decisión
operativa explícita.

Tras estabilizar, vuelve a dejar el repo en una rama o commit conocido.

## Checklist post-deploy

- `git status --short` limpio o con cambios esperados.
- Contenedores `urlbreve-web`, `urlbreve-db-1` y `caddy-proxy` arriba.
- `python manage.py check` OK dentro de `web`.
- `/healthz/` OK en HTTPS.
- Home, creación de URL y redirección OK.
- `/admin/` devuelve `401` sin Basic Auth y llega al login Django con
  credenciales válidas.
- `/static/admin/css/base.css` devuelve `200`.
- `/api/shorten/` no está protegido por Basic Auth.
- Logs recientes sin errores nuevos.
- `.env.production` sigue con permisos restrictivos y no se ha mostrado en
  salidas compartidas.
- Backup reciente disponible si el deploy tocó migraciones o datos.
