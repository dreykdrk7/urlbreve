from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import re


SAFE_SLUG_RE = re.compile(r"^(?=.{3,64}$)[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])$")
RESERVED_SLUGS = {
    "admin",
    "api",
    "dashboard",
    "healthz",
    "links",
    "login",
    "logout",
    "profile",
    "register",
    "signup",
}


def validate_safe_slug(value: str) -> None:
    if not SAFE_SLUG_RE.fullmatch(value or ""):
        raise ValidationError(
            "Slug must be 3-64 ASCII letters, numbers, hyphens or underscores, "
            "and must start and end with a letter or number.",
            code="invalid_slug",
        )
    if value.lower() in RESERVED_SLUGS:
        raise ValidationError("This slug is reserved.", code="reserved_slug")


def validate_http_https_url(value: str) -> None:
    validator = URLValidator(schemes=["http", "https"])
    validator(value)


def suggest_slug_variants(slug: str, count: int = 5) -> list[str]:
    """Return deterministic candidate variants for a colliding slug.

    The helper intentionally does not query the database yet. A later creation
    flow can filter these candidates against the active uniqueness constraints.
    """
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", slug.strip())[:58].strip("-_")
    if len(normalized) < 3:
        normalized = "url"
    return [f"{normalized}-{index}" for index in range(2, count + 2)]
