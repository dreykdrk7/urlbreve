from dataclasses import dataclass
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
import secrets
import string

from accounts.models import UserProfile

from .models import ShortURL, ShortURLDailyStats
from .validators import RESERVED_SLUGS, validate_safe_slug


SLUG_ALPHABET = string.ascii_letters + string.digits


@dataclass(frozen=True)
class VisitResult:
    status: str
    destination_url: str | None = None


VISIT_REDIRECT = "redirect"
VISIT_UNAVAILABLE = "unavailable"
VISIT_INVALID_PASSWORD = "invalid_password"


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


def resolve_anonymous_short_url(slug: str, for_update: bool = False) -> ShortURL | None:
    queryset = ShortURL.objects.filter(
        public_mode=ShortURL.PublicMode.ANONYMOUS,
        slug=slug,
    )
    if for_update:
        queryset = queryset.select_for_update()
    else:
        queryset = queryset.select_related("owner__profile")
    return queryset.first()


def resolve_namespaced_short_url(
    namespace: str,
    slug: str,
    for_update: bool = False,
) -> ShortURL | None:
    profile = UserProfile.objects.select_related("user").filter(
        public_namespace=namespace,
    ).first()
    if profile is None:
        return None

    queryset = ShortURL.objects.filter(
        public_mode=ShortURL.PublicMode.NAMESPACE,
        owner=profile.user,
        slug=slug,
    )
    if for_update:
        queryset = queryset.select_for_update()
    else:
        queryset = queryset.select_related("owner__profile")
    return queryset.first()


def record_click(short_url: ShortURL) -> None:
    now = timezone.now()
    today = timezone.localdate(now)

    short_url.click_count = F("click_count") + 1
    short_url.last_clicked_at = now
    short_url.save(update_fields=["click_count", "last_clicked_at", "updated_at"])

    stats, _ = ShortURLDailyStats.objects.get_or_create(
        short_url=short_url,
        date=today,
        defaults={"clicks": 0},
    )
    stats.clicks = F("clicks") + 1
    stats.save(update_fields=["clicks"])


def visit_short_url(short_url: ShortURL | None, password: str | None = None) -> VisitResult:
    if short_url is None or not short_url.is_available:
        return VisitResult(VISIT_UNAVAILABLE)

    if short_url.password_hash and not check_password(password or "", short_url.password_hash):
        return VisitResult(VISIT_INVALID_PASSWORD)

    destination_url = short_url.destination_url
    record_click(short_url)
    return VisitResult(VISIT_REDIRECT, destination_url=destination_url)


def visit_anonymous_short_url(slug: str, password: str | None = None) -> VisitResult:
    with transaction.atomic():
        short_url = resolve_anonymous_short_url(slug, for_update=True)
        return visit_short_url(short_url, password=password)


def visit_namespaced_short_url(
    namespace: str,
    slug: str,
    password: str | None = None,
) -> VisitResult:
    with transaction.atomic():
        short_url = resolve_namespaced_short_url(namespace, slug, for_update=True)
        return visit_short_url(short_url, password=password)
