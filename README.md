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
- `/healthz/` - healthcheck.
- `/admin/` - administración Django.

El email de registro es opcional para reducir datos personales desde el inicio.
Cada cuenta recibe un `UserProfile` automáticamente con un namespace público
inicial basado en el username. El namespace se normaliza a ASCII minúsculo y,
si colisiona, se genera una variante segura como `nombre-2`.

## Estado

Microfase actual:

- arquitectura Django creada;
- PostgreSQL preparado en Docker;
- modelos mínimos para perfiles, URLs cortas y estadísticas diarias;
- registro/login/logout con templates Django;
- dashboard privado mínimo;
- edición de namespace público y preferencia de modo;
- página inicial y endpoint `/healthz/`;
- documentación y licencia AGPLv3.

No están implementadas todavía la creación de URLs, las redirecciones
completas, la API pública ni el rate limiting.
