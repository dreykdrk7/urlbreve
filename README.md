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

- `/` - home simple.
- `/register/` - registro.
- `/login/` - login.
- `/logout/` - logout mediante POST.
- `/dashboard/` - panel privado mínimo.
- `/profile/` - edición del perfil básico.
- `/links/new/` - creación autenticada de URL corta.
- `/links/<id>/` - detalle básico de una URL propia.
- `/links/<id>/edit/` - edición de campos permitidos.
- `/links/<id>/delete/` - ocultado mediante soft delete.
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
- contraseña opcional, guardada solo como hash y sin flujo público todavía.

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

## Estado

Microfase actual:

- arquitectura Django creada;
- PostgreSQL preparado en Docker;
- modelos mínimos para perfiles, URLs cortas y estadísticas diarias;
- registro/login/logout con templates Django;
- dashboard privado mínimo;
- edición de namespace público y preferencia de modo;
- creación, listado, detalle, edición limitada y soft delete de URLs propias;
- página inicial y endpoint `/healthz/`;
- documentación y licencia AGPLv3.

No están implementadas todavía las redirecciones públicas, la API pública ni el
rate limiting.
