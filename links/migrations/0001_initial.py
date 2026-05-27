# Generated for urlbreve initial architecture.

import django.db.models.deletion
import links.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShortURL",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "destination_url",
                    models.URLField(
                        max_length=2048,
                        validators=[links.validators.validate_http_https_url],
                    ),
                ),
                (
                    "slug",
                    models.CharField(
                        max_length=64,
                        validators=[links.validators.validate_safe_slug],
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=200)),
                (
                    "public_mode",
                    models.CharField(
                        choices=[
                            ("anonymous", "Anonymous/global"),
                            ("namespace", "Public namespace"),
                        ],
                        default="anonymous",
                        max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("max_clicks", models.PositiveIntegerField(default=0)),
                ("click_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_disabled", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("password_hash", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_clicked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="short_urls",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ShortURLDailyStats",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField()),
                ("clicks", models.PositiveIntegerField(default=0)),
                (
                    "short_url",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_stats",
                        to="links.shorturl",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="shorturl",
            constraint=models.UniqueConstraint(
                condition=models.Q(("public_mode", "anonymous")),
                fields=("slug",),
                name="uniq_anonymous_slug",
            ),
        ),
        migrations.AddConstraint(
            model_name="shorturl",
            constraint=models.UniqueConstraint(
                condition=models.Q(("public_mode", "namespace")),
                fields=("owner", "slug"),
                name="uniq_namespace_owner_slug",
            ),
        ),
        migrations.AddConstraint(
            model_name="shorturl",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("public_mode", "anonymous"))
                    | models.Q(("owner__isnull", False))
                ),
                name="namespace_mode_requires_owner",
            ),
        ),
        migrations.AddIndex(
            model_name="shorturl",
            index=models.Index(fields=["slug"], name="idx_shorturl_slug"),
        ),
        migrations.AddIndex(
            model_name="shorturl",
            index=models.Index(fields=["owner", "slug"], name="idx_shorturl_owner_slug"),
        ),
        migrations.AddIndex(
            model_name="shorturl",
            index=models.Index(fields=["public_mode", "slug"], name="idx_shorturl_mode_slug"),
        ),
        migrations.AddIndex(
            model_name="shorturl",
            index=models.Index(fields=["is_active", "is_disabled"], name="idx_shorturl_status"),
        ),
        migrations.AddConstraint(
            model_name="shorturldailystats",
            constraint=models.UniqueConstraint(
                fields=("short_url", "date"),
                name="uniq_shorturl_daily_stats",
            ),
        ),
        migrations.AddIndex(
            model_name="shorturldailystats",
            index=models.Index(fields=["date"], name="idx_daily_stats_date"),
        ),
    ]
