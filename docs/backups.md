# Backups

Esta guía cubre backups manuales básicos de PostgreSQL para producción. Los
backups pueden contener datos reales y no deben guardarse en el repo.

## Ruta sugerida en el VPS

Usar una ruta compartida fuera del checkout de la app:

```bash
mkdir -p /opt/apps/shared/backups/urlbreve
chmod 700 /opt/apps/shared/backups/urlbreve
```

No guardar dumps en `/opt/apps/urlbreve/app`, no hacer commit de backups y no
adjuntarlos a issues, pull requests o chats.

## Backup manual

Desde el VPS:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T db pg_dump -U urlbreve urlbreve > /opt/apps/shared/backups/urlbreve/urlbreve-$(date +%Y-%m-%d-%H%M%S).sql
```

Comprobar que el archivo existe y tiene tamaño razonable:

```bash
ls -lh /opt/apps/shared/backups/urlbreve
```

Opcionalmente comprimirlo:

```bash
gzip /opt/apps/shared/backups/urlbreve/urlbreve-YYYY-MM-DD-HHMMSS.sql
```

## Restore básico

Restaurar un backup debe hacerse con cuidado. Si la base destino contiene datos,
pueden mezclarse, duplicarse o fallar inserts por constraints. Para un restore
limpio, prepara antes una base vacía o una base recién recreada.

Ejemplo desde un dump SQL sin comprimir:

```bash
cd /opt/apps/urlbreve/app
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml up -d db
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T db psql -U urlbreve urlbreve < /opt/apps/shared/backups/urlbreve/urlbreve-YYYY-MM-DD-HHMMSS.sql
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml up -d
docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T web python manage.py check
```

Ejemplo desde un dump comprimido:

```bash
cd /opt/apps/urlbreve/app
gzip -dc /opt/apps/shared/backups/urlbreve/urlbreve-YYYY-MM-DD-HHMMSS.sql.gz | docker compose --project-name urlbreve --env-file .env.production -f docker-compose.prod.yml -f docker-compose.vps.yml exec -T db psql -U urlbreve urlbreve
```

Después de restaurar, validar:

- `python manage.py check` dentro de `web`.
- `/healthz/` por HTTPS.
- Login/admin si procede.
- Creación y redirección de una URL de prueba si el entorno es producción y la
  operación está autorizada.

## Recomendaciones

- Automatizar backups fuera del VPS como siguiente paso operativo.
- Mantener al menos una copia cifrada en almacenamiento externo.
- Probar restauraciones periódicamente en un entorno no productivo.
- Definir retención, por ejemplo diarios durante 7 días y semanales durante 4
  semanas.
- No mezclar backups con logs de acceso.
- Rotar credenciales si un backup o secreto se expone accidentalmente.
