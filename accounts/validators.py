from django.core.exceptions import ValidationError
import re


SAFE_NAMESPACE_RE = re.compile(r"^(?=.{3,64}$)[a-z0-9](?:[a-z0-9_-]*[a-z0-9])$")
RESERVED_NAMESPACES = {
    "a",
    "admin",
    "api",
    "dashboard",
    "healthz",
    "login",
    "logout",
    "media",
    "profile",
    "register",
    "signup",
    "static",
}


def validate_public_namespace(value: str) -> None:
    if not SAFE_NAMESPACE_RE.fullmatch(value or ""):
        raise ValidationError(
            "Use 3-64 lowercase ASCII letters, numbers, hyphens or "
            "underscores; start and end with a letter or number.",
            code="invalid_namespace",
        )
    if value.lower() in RESERVED_NAMESPACES:
        raise ValidationError("This namespace is reserved.", code="reserved_namespace")
