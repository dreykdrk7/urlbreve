from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

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

    def get_public_path(self) -> str:
        if self.public_mode == self.PublicMode.NAMESPACE and self.owner_id:
            namespace = self.owner.profile.public_namespace
            return f"/{namespace}/{self.slug}/"
        return f"/a/{self.slug}/"

    def get_public_url(self, request=None) -> str:
        path = self.get_public_path()
        if request is None:
            return path
        return request.build_absolute_uri(path)

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_click_limit_reached(self) -> bool:
        return bool(self.max_clicks and self.click_count >= self.max_clicks)

    @property
    def is_available(self) -> bool:
        return (
            self.deleted_at is None
            and self.is_active
            and not self.is_disabled
            and not self.is_expired
            and not self.is_click_limit_reached
        )

    @property
    def status_label(self) -> str:
        if self.deleted_at:
            return "eliminada"
        if self.is_disabled:
            return "desactivada"
        if not self.is_active:
            return "inactiva"
        if self.is_expired:
            return "expirada"
        if self.is_click_limit_reached:
            return "agotada"
        return "activa"

    def mark_deleted(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def get_absolute_url(self):
        return reverse("links:detail", kwargs={"pk": self.pk})

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
