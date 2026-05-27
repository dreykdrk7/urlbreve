from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .validators import validate_http_https_url, validate_safe_slug


class ShortURL(models.Model):
    class PublicMode(models.TextChoices):
        ANONYMOUS = "anonymous", "Anonymous/global"
        NAMESPACE = "namespace", "Public namespace"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="short_urls",
        null=True,
        blank=True,
    )
    destination_url = models.URLField(max_length=2048, validators=[validate_http_https_url])
    slug = models.CharField(max_length=64, validators=[validate_safe_slug])
    title = models.CharField(max_length=200, blank=True)
    public_mode = models.CharField(
        max_length=20,
        choices=PublicMode.choices,
        default=PublicMode.ANONYMOUS,
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    max_clicks = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    password_hash = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(public_mode="anonymous"),
                name="uniq_anonymous_slug",
            ),
            models.UniqueConstraint(
                fields=["owner", "slug"],
                condition=models.Q(public_mode="namespace"),
                name="uniq_namespace_owner_slug",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(public_mode="anonymous")
                    | models.Q(owner__isnull=False)
                ),
                name="namespace_mode_requires_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["slug"], name="idx_shorturl_slug"),
            models.Index(fields=["owner", "slug"], name="idx_shorturl_owner_slug"),
            models.Index(fields=["public_mode", "slug"], name="idx_shorturl_mode_slug"),
            models.Index(fields=["is_active", "is_disabled"], name="idx_shorturl_status"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.public_mode == self.PublicMode.NAMESPACE and self.owner_id is None:
            raise ValidationError({"owner": "Namespaced links require an owner."})

    def __str__(self) -> str:
        return f"{self.public_mode}:{self.slug}"


class ShortURLDailyStats(models.Model):
    short_url = models.ForeignKey(
        ShortURL,
        on_delete=models.CASCADE,
        related_name="daily_stats",
    )
    date = models.DateField()
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["short_url", "date"],
                name="uniq_shorturl_daily_stats",
            ),
        ]
        indexes = [
            models.Index(fields=["date"], name="idx_daily_stats_date"),
        ]

    def __str__(self) -> str:
        return f"{self.short_url_id}:{self.date}"
