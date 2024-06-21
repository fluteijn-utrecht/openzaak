# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
# Generated by Django 4.2.11 on 2024-06-14 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "documenten",
            "0032_remove_enkelvoudiginformatieobject_documenten_enkelvoudiginformatieobject__informatieobjecttype_base",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="enkelvoudiginformatieobject",
            name="identificatie",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Een binnen een gegeven context ondubbelzinnige referentie naar het INFORMATIEOBJECT.",
                max_length=40,
            ),
        ),
    ]
