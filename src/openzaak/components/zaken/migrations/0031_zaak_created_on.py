# Generated by Django 3.2.23 on 2024-04-09 12:59

import datetime

from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0030_remove_zaak_resultaattoelichting"),
    ]

    operations = [
        migrations.AddField(
            model_name="zaak",
            name="created_on",
            field=models.DateTimeField(
                auto_now_add=True,
                default=datetime.datetime(2024, 4, 9, 12, 59, 18, 517349, tzinfo=utc),
                verbose_name="created on",
            ),
            preserve_default=False,
        ),
    ]
