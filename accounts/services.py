from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
import re
import secrets
import unicodedata

from .models import UserProfile
from .validators import RESERVED_NAMESPACES, SAFE_NAMESPACE_RE


API_KEY_PREFIX = "ub_"


def normalize_public_namespace(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    normalized = re.sub(r"[^a-z0-9_-]+", "-", ascii_value)
    normalized = re.sub(r"[-_]{2,}", "-", normalized).strip("-_")
    if len(normalized) < 3:
        normalized = "user"
    normalized = normalized[:64].strip("-_")
    if len(normalized) < 3:
        normalized = "user"
    if normalized in RESERVED_NAMESPACES:
        normalized = f"{normalized}-user"
    if not SAFE_NAMESPACE_RE.fullmatch(normalized):
        normalized = "user"
    return normalized


def namespace_is_available(namespace: str, profile: UserProfile | None = None) -> bool:
    if namespace.lower() in RESERVED_NAMESPACES:
        return False
    queryset = UserProfile.objects.filter(public_namespace__iexact=namespace)
    if profile and profile.pk:
        queryset = queryset.exclude(pk=profile.pk)
    return not queryset.exists()


def generate_unique_public_namespace(seed: str) -> str:
    base = normalize_public_namespace(seed)
    if namespace_is_available(base):
        return base

    counter = 2
    while True:
        suffix = f"-{counter}"
        candidate = f"{base[:64 - len(suffix)].rstrip('-_')}{suffix}"
        if namespace_is_available(candidate):
            return candidate
        counter += 1


def ensure_user_profile(user) -> UserProfile:
    namespace = generate_unique_public_namespace(user.get_username())
    try:
        with transaction.atomic():
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={"public_namespace": namespace},
            )
    except IntegrityError:
        profile = UserProfile.objects.get(user=user)

    if not profile.public_namespace:
        profile.public_namespace = generate_unique_public_namespace(user.get_username())
        profile.save(update_fields=["public_namespace", "updated_at"])
    return profile


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return make_password(raw_key)


def verify_api_key(raw_key: str, api_key_hash: str) -> bool:
    if not raw_key or not api_key_hash:
        return False
    return check_password(raw_key, api_key_hash)


def get_user_for_api_key(raw_key: str):
    if not raw_key:
        return None

    profiles = UserProfile.objects.exclude(api_key_hash="").select_related("user")
    for profile in profiles.iterator():
        if verify_api_key(raw_key, profile.api_key_hash):
            return profile.user
    return None
