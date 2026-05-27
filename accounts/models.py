from django.conf import settings
from django.db import models

from .validators import validate_public_namespace


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    public_namespace = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_public_namespace],
    )
    prefer_public_namespace = models.BooleanField(default=False)
    api_key_hash = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_namespace"], name="idx_profile_namespace"),
        ]

    def __str__(self) -> str:
        return self.public_namespace or str(self.user)
