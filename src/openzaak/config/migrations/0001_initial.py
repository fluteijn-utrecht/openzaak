# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
# Generated by Django 2.2.10 on 2020-03-17 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NLXConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "directory",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("demo", "Demo"),
                            ("preprod", "Pre-prod"),
                            ("prod", "Prod"),
                        ],
                        max_length=50,
                        verbose_name="NLX directory",
                    ),
                ),
                ("outway", models.URLField(blank=True, verbose_name="outway address")),
            ],
            options={"verbose_name": "NLX configuration",},
        ),
    ]
