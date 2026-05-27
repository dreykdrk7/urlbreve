# Generated for urlbreve initial architecture.

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
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
                    "public_namespace",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "Use 3-64 ASCII letters, numbers, hyphens "
                                    "or underscores; start and end with a "
                                    "letter or number."
                                ),
                                regex=(
                                    "^(?=.{3,64}$)[A-Za-z0-9]"
                                    "(?:[A-Za-z0-9_-]*[A-Za-z0-9])$"
                                ),
                            )
                        ],
                    ),
                ),
                ("prefer_public_namespace", models.BooleanField(default=False)),
                ("api_key_hash", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="userprofile",
            index=models.Index(fields=["public_namespace"], name="idx_profile_namespace"),
        ),
    ]
