# Generated for urlbreve auth/profile architecture.

import accounts.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="public_namespace",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                unique=True,
                validators=[accounts.validators.validate_public_namespace],
            ),
        ),
    ]
