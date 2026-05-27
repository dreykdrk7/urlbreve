# Despliegue en producción

Esta guía describe un despliegue low-cost para urlbreve en un VPS con Docker
Compose, Django, Gunicorn, PostgreSQL y nginx como reverse proxy. El objetivo es
mantener la política privacy-first también en infraestructura.

## Requisitos

- VPS con Linux estable, por ejemplo Debian o Ubuntu LTS.
- 1 vCPU y 1 GB de RAM pueden bastar para un MVP pequeño.
- 10 GB de disco como mínimo; más si esperas muchos datos o backups locales.
- Docker Engine y Docker Compose v2.
- Un dominio apuntando al VPS.
- Acceso SSH con usuario no root o root administrado con cuidado.

## Instalar Docker

En Debian/Ubuntu, usa la documentación oficial de Docker para instalar Docker
Engine y el plugin Compose. Como comprobación:

```bash
docker --version
docker compose version
```

Activa el servicio:

```bash
sudo systemctl enable --now docker
```

## Preparar el proyecto

Clona el repositorio:

```bash
git clone git@github.com:dreykdrk7/urlbreve.git
cd urlbreve
```

Crea el archivo de entorno de producción a partir del ejemplo:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Edita `.env.production` y cambia todos los valores `CHANGE_ME`. No hagas commit
de ese archivo.

Variables importantes:

- `DJANGO_SECRET_KEY`: secreto largo y aleatorio.
- `DJANGO_DEBUG=False`.
- `DJANGO_ALLOWED_HOSTS`: dominio o dominios públicos.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: orígenes HTTPS completos.
- `POSTGRES_PASSWORD`: contraseña fuerte.
- `DATABASE_URL`: debe usar el host `db` dentro de Compose.
- `DJANGO_SESSION_COOKIE_SECURE=True` con HTTPS.
- `DJANGO_CSRF_COOKIE_SECURE=True` con HTTPS.
- `DJANGO_SECURE_SSL_REDIRECT`: ponlo en `True` solo cuando tu proxy TLS envíe
  correctamente `X-Forwarded-Proto=https`.

Si la contraseña de PostgreSQL contiene caracteres especiales, codifícala para
URL en `DATABASE_URL`.

## Levantar servicios

Construye la imagen:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build
```

Arranca PostgreSQL para preparar la base:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db
```

Ejecuta migraciones:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm web python manage.py migrate
```

Recoge estáticos en el volumen compartido con nginx:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
```

Arranca todo:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

Crea un superusuario:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
```

Comprueba el healthcheck público:

```bash
curl http://tu-dominio.example/healthz/
```

## Dominio y TLS

El `docker-compose.prod.yml` incluido expone solo nginx en el puerto `80`.
PostgreSQL no expone puertos públicos y Django/Gunicorn solo queda accesible
dentro de la red de Compose.

Opciones simples para TLS:

- Terminar TLS fuera de este stack, por ejemplo con Caddy, Traefik,
  nginx-proxy o un balanceador del proveedor. Esa capa debe reenviar
  `X-Forwarded-Proto=https` a nginx.
- Extender este stack más adelante con un servicio certbot y un server block
  `443` en nginx.

Para producción real:

- redirige HTTP a HTTPS en la capa TLS;
- usa `DJANGO_CSRF_TRUSTED_ORIGINS=https://tu-dominio`;
- usa `DJANGO_SESSION_COOKIE_SECURE=True`;
- usa `DJANGO_CSRF_COOKIE_SECURE=True`;
- activa `DJANGO_SECURE_SSL_REDIRECT=True` cuando Django reciba
  `X-Forwarded-Proto=https` de forma fiable.

## Nginx privacy-first

La configuración vive en `deploy/nginx/urlbreve.conf`.

Decisiones:

- `access_log off;` para no persistir IPs ni rutas visitadas;
- nivel de `error_log` reducido;
- no se reenvían `X-Forwarded-For`, `X-Real-IP`, `Forwarded`, `User-Agent` ni
  `Referer` a Django;
- se reenvían `Host` y `X-Forwarded-Proto` para construir URLs correctas;
- `client_max_body_size 1m`;
- headers básicos como `X-Content-Type-Options`, `X-Frame-Options` y
  `Referrer-Policy`.

Si colocas otro proxy delante, revisa también sus access logs. La política del
proyecto exige no conservar IPs, user-agent ni referrer salvo defensa temporal
explícita y documentada.

## Logs

Comandos útiles:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs web
docker compose --env-file .env.production -f docker-compose.prod.yml logs nginx
docker compose --env-file .env.production -f docker-compose.prod.yml logs db
```

No actives access logs de nginx ni Gunicorn en operación normal. Los logs de
errores pueden contener contexto técnico; revisa retención y acceso en el VPS.

## Backups PostgreSQL

Crea una carpeta local para backups:

```bash
mkdir -p backups
```

Backup manual:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db pg_dump -U urlbreve urlbreve > backups/urlbreve-YYYY-MM-DD.sql
```

Recomendaciones:

- automatiza backups diarios con cron o systemd timers;
- cifra backups antes de copiarlos fuera del VPS;
- prueba restauraciones periódicamente;
- no mezcles backups con logs de acceso.

## Restore básico

Para restaurar un backup en una base vacía o recién preparada:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db
cat backups/urlbreve-YYYY-MM-DD.sql | docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db psql -U urlbreve urlbreve
```

Después levanta la app:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## Actualización

Flujo recomendado:

```bash
git pull --ff-only
docker compose --env-file .env.production -f docker-compose.prod.yml build web
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm web python manage.py migrate
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T web python manage.py check
```

Si algo falla, conserva el backup anterior y revisa logs de errores, no access
logs de visitantes.

## Comprobaciones operativas

- `/healthz/` responde `{"status": "ok"}`.
- `/admin/` carga solo por HTTPS.
- PostgreSQL no aparece en `ss -tulpn` como puerto público.
- Nginx no escribe access logs.
- `.env.production` tiene permisos restrictivos.
- `DJANGO_DEBUG=False` está activo.
- `DJANGO_ALLOWED_HOSTS` solo contiene dominios esperados.
- Las cookies seguras están activas cuando hay HTTPS.
