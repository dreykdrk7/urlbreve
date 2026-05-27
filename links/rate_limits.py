from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int


def rate_limiting_enabled() -> bool:
    return bool(settings.URLBREVE_RATE_LIMITING_ENABLED)


def _daily_timeout() -> int:
    now = timezone.localtime()
    tomorrow = datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=now.tzinfo,
    )
    return max(1, int((tomorrow - now).total_seconds()))


def _cache_key(scope: str, identifier: str) -> str:
    today = timezone.localdate().isoformat()
    return f"urlbreve:rate-limit:{today}:{scope}:{identifier}"


def consume_daily_limit(scope: str, identifier: str | int, limit: int) -> RateLimitResult:
    if not rate_limiting_enabled() or limit <= 0:
        return RateLimitResult(allowed=True, count=0, limit=limit)

    key = _cache_key(scope, str(identifier))
    timeout = _daily_timeout()
    cache.add(key, 0, timeout=timeout)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        count = 1
    return RateLimitResult(allowed=count <= limit, count=count, limit=limit)


def get_or_create_session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def consume_session_daily_limit(request, scope: str, limit: int) -> RateLimitResult:
    if not rate_limiting_enabled() or limit <= 0:
        return RateLimitResult(allowed=True, count=0, limit=limit)
    session_key = get_or_create_session_key(request)
    return consume_daily_limit(scope, f"session:{session_key}", limit)


def consume_user_daily_limit(scope: str, user_id: int, limit: int) -> RateLimitResult:
    return consume_daily_limit(scope, f"user:{user_id}", limit)


def consume_password_gate_limit(request, short_url_id: int, limit: int) -> RateLimitResult:
    if not rate_limiting_enabled() or limit <= 0:
        return RateLimitResult(allowed=True, count=0, limit=limit)
    session_key = get_or_create_session_key(request)
    identifier = f"session:{session_key}:short-url:{short_url_id}"
    return consume_daily_limit("password-gate", identifier, limit)
