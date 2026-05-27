from django.db.models import Q
import secrets
import string

from .models import ShortURL
from .validators import RESERVED_SLUGS, validate_safe_slug


SLUG_ALPHABET = string.ascii_letters + string.digits


def slug_exists(slug: str, public_mode: str, owner=None) -> bool:
    query = Q(slug=slug, public_mode=public_mode)
    if public_mode == ShortURL.PublicMode.NAMESPACE:
        query &= Q(owner=owner)
    return ShortURL.objects.filter(query).exists()


def slug_is_available(slug: str, public_mode: str, owner=None) -> bool:
    if slug.lower() in RESERVED_SLUGS:
        return False
    if public_mode == ShortURL.PublicMode.NAMESPACE and owner is None:
        return False
    return not slug_exists(slug, public_mode, owner=owner)


def generate_random_slug(public_mode: str, owner=None, length: int = 8) -> str:
    while True:
        slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(length))
        validate_safe_slug(slug)
        if slug_is_available(slug, public_mode, owner=owner):
            return slug
